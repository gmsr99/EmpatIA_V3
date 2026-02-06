"""EmpatIA Agent - Pipeline modular: Groq STT → Gemini Flash Lite → WaveNet TTS."""

import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, AsyncIterator, List, Tuple
import uuid

import structlog
from google.genai import types

from src.config import settings
from src.database import MemoryStore, DatabaseConnection
from src.agent.system_prompt import get_system_prompt
from src.services import STTService, LLMService, TTSService, ReportService, VADProcessor
from src.tools import (
    manage_memory_tool,
    ManageMemoryInput,
    MANAGE_MEMORY_TOOL_DEFINITION,
    google_search_tool,
    GoogleSearchInput,
    GOOGLE_SEARCH_TOOL_DEFINITION,
)

logger = structlog.get_logger(__name__)


class EmpatIASession:
    """Representa uma sessao de conversa com o utilizador."""

    def __init__(self, user_id: str, session_id: Optional[str] = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.started_at = datetime.now()
        self.conversation_turns = []  # Para logging/report (com timestamps)
        self.conversation_history = []  # Para o LLM: [{"role": "user"|"model", "text": "..."}]
        self.key_topics = set()
        self.memory_store = MemoryStore()

    async def get_context(self) -> Dict[str, Any]:
        """Obtem o contexto completo do utilizador para injetar no system prompt."""
        profile = await self.memory_store.get_user_profile(self.user_id)
        recent_episodes = await self.memory_store.get_recent_episodes(
            self.user_id, limit=3
        )

        return {
            "profile": profile,
            "recent_episodes": recent_episodes,
        }

    def add_turn(self, speaker: str, text: str):
        """Adiciona um turno de conversa."""
        self.conversation_turns.append(
            {"speaker": speaker, "text": text, "timestamp": datetime.now()}
        )

    async def save_episode(self, summary: str, emotional_tone: str):
        """Guarda o episodio de conversa na base de dados."""
        duration = (datetime.now() - self.started_at).seconds // 60

        await self.memory_store.save_episode(
            user_id=self.user_id,
            session_id=self.session_id,
            summary=summary,
            key_topics=list(self.key_topics),
            emotional_tone=emotional_tone,
            started_at=self.started_at,
            duration_minutes=duration,
        )

        logger.info(
            "Episodio guardado",
            user_id=self.user_id,
            session_id=self.session_id,
            duration=duration,
        )


class EmpatIAAgent:
    """Agente EmpatIA com pipeline modular: STT → LLM → TTS."""

    def __init__(self):
        self.active_sessions: Dict[str, EmpatIASession] = {}
        self.memory_store = MemoryStore()

        # Servicos da pipeline
        self.stt_service = STTService()
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.report_service = ReportService()

    async def initialize(self):
        """Inicializa o agente, base de dados e todos os servicos."""
        await DatabaseConnection.get_pool()
        # Inicializar schema (seguro para multiplas execucoes - usa IF NOT EXISTS)
        await DatabaseConnection.init_schema()
        logger.info("Schema verificado/inicializado")

        # Inicializar servicos
        await self.llm_service.initialize()
        await self.tts_service.initialize()
        await self.report_service.initialize()
        # STTService inicializa o client no __init__ (sem async setup)

        logger.info(
            "Agente EmpatIA inicializado (pipeline modular)",
            stt=settings.groq_stt_model,
            llm=settings.gemini_llm_model,
            tts=settings.tts_voice_name,
            report=settings.gemini_report_model,
        )

    async def create_session(self, user_id: str) -> EmpatIASession:
        """Cria uma nova sessao para o utilizador."""
        session = EmpatIASession(user_id)
        self.active_sessions[session.session_id] = session

        logger.info(
            "Nova sessao criada",
            user_id=user_id,
            session_id=session.session_id,
        )

        return session

    async def get_session(self, session_id: str) -> Optional[EmpatIASession]:
        """Obtem uma sessao existente."""
        return self.active_sessions.get(session_id)

    async def _execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Executa uma tool do agente."""
        try:
            logger.info(
                "Executando tool",
                tool_name=tool_name,
                tool_input=tool_input,
                tool_input_type=type(tool_input).__name__,
            )

            if tool_name == "manage_memory":
                if not isinstance(tool_input, dict):
                    logger.error(
                        "tool_input nao e dict",
                        tool_input=tool_input,
                        type=type(tool_input),
                    )
                    return {"success": False, "error": "Parametros invalidos"}

                params = ManageMemoryInput(**tool_input)
                return await manage_memory_tool(params, user_id)

            elif tool_name == "google_search":
                if not isinstance(tool_input, dict):
                    logger.error(
                        "tool_input nao e dict",
                        tool_input=tool_input,
                        type=type(tool_input),
                    )
                    return {"success": False, "error": "Parametros invalidos"}

                params = GoogleSearchInput(**tool_input)
                return await google_search_tool(params)

            else:
                logger.warning("Tool desconhecida", tool_name=tool_name)
                return {"error": f"Tool desconhecida: {tool_name}"}

        except Exception as e:
            logger.error(
                "Erro ao executar tool",
                tool_name=tool_name,
                tool_input=tool_input,
                tool_input_type=type(tool_input).__name__,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def _extract_sentences(text: str) -> Tuple[List[str], str]:
        """
        Extrai frases completas de um buffer de texto.

        Returns:
            (lista_de_frases_completas, buffer_restante)
        """
        sentences = []
        # Procurar frases terminadas em . ! ? seguido de espaco ou fim
        pattern = r"([^.!?]*[.!?])(?:\s|$)"

        while True:
            match = re.search(pattern, text)
            if match:
                sentence = match.group(1).strip()
                if sentence:
                    sentences.append(sentence)
                text = text[match.end() :]
            else:
                break

        return sentences, text

    async def stream_conversation(
        self, session: EmpatIASession, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        """
        Pipeline de conversa turn-based:
        Audio → VAD → Groq STT → Gemini Flash Lite (com tools) → WaveNet TTS → Audio

        Args:
            session: Sessao do utilizador
            audio_stream: Stream de audio de entrada do cliente

        Yields:
            Bytes de audio de resposta (PCM 16-bit 24kHz)
        """
        # Obter contexto do utilizador
        context = await session.get_context()
        system_prompt = get_system_prompt(
            user_profile=context["profile"],
            recent_episodes=context["recent_episodes"],
        )

        # Declaracoes de tools (reutilizadas do sistema anterior)
        tool_declarations = [
            types.FunctionDeclaration(
                name=MANAGE_MEMORY_TOOL_DEFINITION["name"],
                description=MANAGE_MEMORY_TOOL_DEFINITION["description"],
                parameters=MANAGE_MEMORY_TOOL_DEFINITION["parameters"],
            ),
            types.FunctionDeclaration(
                name=GOOGLE_SEARCH_TOOL_DEFINITION["name"],
                description=GOOGLE_SEARCH_TOOL_DEFINITION["description"],
                parameters=GOOGLE_SEARCH_TOOL_DEFINITION["parameters"],
            ),
        ]

        # Callback para execucao de tools
        async def execute_tool(
            tool_name: str, tool_args: Dict[str, Any]
        ) -> Dict[str, Any]:
            return await self._execute_tool(tool_name, tool_args, session.user_id)

        # Processador VAD
        vad = VADProcessor()

        logger.info(
            "A iniciar conversa turn-based",
            user_id=session.user_id,
            session_id=session.session_id,
        )

        try:
            # Processar utterances detectadas pelo VAD
            async for utterance_pcm in vad.process_stream(audio_stream):
                # Passo 1: STT — Converter fala em texto
                user_text = await self.stt_service.transcribe(utterance_pcm)

                if not user_text:
                    logger.warning("STT retornou texto vazio, a ignorar turno")
                    continue

                logger.info("Utilizador disse", text=user_text[:100])

                # Registar turno do utilizador
                session.add_turn("user", user_text)
                session.conversation_history.append(
                    {"role": "user", "text": user_text}
                )

                # Passo 2: LLM — Gerar resposta de texto (streaming)
                sentence_buffer = ""
                full_response = ""

                async for text_chunk in self.llm_service.generate_response(
                    user_text=user_text,
                    system_prompt=system_prompt,
                    conversation_history=session.conversation_history[:-1],
                    tool_declarations=tool_declarations,
                    execute_tool=execute_tool,
                ):
                    sentence_buffer += text_chunk
                    full_response += text_chunk

                    # Detectar limites de frase para TTS progressivo
                    sentences, sentence_buffer = self._extract_sentences(
                        sentence_buffer
                    )

                    for sentence in sentences:
                        # Passo 3: TTS — Converter frase para audio
                        audio_pcm = await self.tts_service.synthesize(sentence)
                        if audio_pcm:
                            # Enviar em chunks (max 32KB) para nao sobrecarregar o WS
                            chunk_size = 32000  # ~0.67s de audio a 24kHz 16-bit
                            for i in range(0, len(audio_pcm), chunk_size):
                                yield audio_pcm[i : i + chunk_size]

                # Flush do texto restante no buffer
                if sentence_buffer.strip():
                    audio_pcm = await self.tts_service.synthesize(
                        sentence_buffer.strip()
                    )
                    if audio_pcm:
                        chunk_size = 32000
                        for i in range(0, len(audio_pcm), chunk_size):
                            yield audio_pcm[i : i + chunk_size]

                # Registar turno do assistente
                if full_response:
                    session.add_turn("assistant", full_response)
                    session.conversation_history.append(
                        {"role": "model", "text": full_response}
                    )

                logger.info(
                    "Turno completo", response_length=len(full_response)
                )

        except asyncio.CancelledError:
            logger.info("Conversa cancelada pelo cliente")
        except Exception as e:
            logger.error(
                "Erro na pipeline de conversa",
                error=str(e),
                session_id=session.session_id,
                exc_info=True,
            )
            raise
        finally:
            # Flush de buffer VAD restante
            remaining = vad.close()
            if remaining and len(remaining) > 1000:
                user_text = await self.stt_service.transcribe(remaining)
                if user_text:
                    session.add_turn("user", user_text)

        logger.info(
            "Conversa finalizada",
            session_id=session.session_id,
            turns=len(session.conversation_turns),
        )

    async def end_session(self, session_id: str):
        """Termina uma sessao, gera relatorio e guarda o episodio."""
        session = self.active_sessions.get(session_id)
        if session:
            # Gerar relatorio usando Gemini 2.0 Flash
            report = await self.report_service.generate_report(
                session.conversation_turns
            )

            # Guardar episodio com dados reais do relatorio
            session.key_topics = set(report.get("key_topics", []))

            await session.save_episode(
                summary=report.get("summary", "Conversa com EmpatIA"),
                emotional_tone=report.get("emotional_tone", "neutro"),
            )

            del self.active_sessions[session_id]

            logger.info(
                "Sessao terminada com relatorio",
                session_id=session_id,
                summary=report.get("summary", "")[:80],
            )

    async def shutdown(self):
        """Encerra o agente graciosamente."""
        for session_id in list(self.active_sessions.keys()):
            await self.end_session(session_id)

        await DatabaseConnection.close_pool()
        logger.info("Agente EmpatIA encerrado")


# Instancia global do agente
agent = EmpatIAAgent()
