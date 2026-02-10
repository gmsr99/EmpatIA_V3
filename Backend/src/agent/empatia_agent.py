"""EmpatIA Agent - Pipeline modular: Deepgram STT → Gemini Flash → Azure TTS."""

import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, AsyncIterator, List, Tuple, Callable, Awaitable
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
            stt=settings.deepgram_model,
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
            # Normalizar nome da tool: PascalCase -> snake_case
            # Gemini pode retornar "ManageMemory" em vez de "manage_memory"
            tool_name_normalized = re.sub(r'(?<!^)(?=[A-Z])', '_', tool_name).lower()

            # Gemini às vezes chama a tool pela ação em vez do nome
            # ex: "add" ou "search" em vez de "manage_memory"
            MEMORY_ACTION_ALIASES = {"add", "update", "delete", "search"}
            if tool_name_normalized in MEMORY_ACTION_ALIASES:
                # Injetar a ação nos args e redirecionar para manage_memory
                tool_input["action"] = tool_name_normalized.upper()
                tool_name_normalized = "manage_memory"

            logger.info(
                "Executando tool",
                tool_name=tool_name,
                tool_name_normalized=tool_name_normalized,
                tool_input=tool_input,
                tool_input_type=type(tool_input).__name__,
            )

            if tool_name_normalized == "manage_memory":
                if not isinstance(tool_input, dict):
                    logger.error(
                        "tool_input nao e dict",
                        tool_input=tool_input,
                        type=type(tool_input),
                    )
                    return {"success": False, "error": "Parametros invalidos"}

                params = ManageMemoryInput(**tool_input)
                return await manage_memory_tool(params, user_id)

            elif tool_name_normalized == "google_search":
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
                logger.warning("Tool desconhecida", tool_name=tool_name, tool_name_normalized=tool_name_normalized)
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

    # Abreviaturas PT que terminam em ponto mas NAO sao fim de frase
    _PT_ABBREVIATIONS = {
        "Sr", "Sra", "Dr", "Dra", "Prof", "Eng", "Exc",
        "Exmo", "Exma", "Av", "R", "Tel", "Fig", "Vol",
    }

    @classmethod
    def _extract_sentences(cls, text: str) -> Tuple[List[str], str]:
        """
        Extrai frases completas de um buffer de texto.

        Respeita abreviaturas portuguesas (Sr., Dr., etc.) para nao
        partir frases como "Sim, Sr. Joao Pedro" no ponto errado.

        Returns:
            (lista_de_frases_completas, buffer_restante)
        """
        sentences = []
        i = 0
        last_split = 0

        while i < len(text):
            if text[i] in ".!?":
                # Se e ponto, verificar se e abreviatura
                if text[i] == ".":
                    j = i - 1
                    while j >= last_split and text[j].isalpha():
                        j -= 1
                    word_before = text[j + 1 : i]
                    if word_before in cls._PT_ABBREVIATIONS:
                        i += 1
                        continue

                # Verificar se seguido de espaco/fim (verdadeiro fim de frase)
                next_i = i + 1
                if next_i >= len(text) or text[next_i] in " \n\t":
                    sentence = text[last_split : next_i].strip()
                    if sentence:
                        sentences.append(sentence)
                    # Saltar whitespace apos pontuacao
                    while next_i < len(text) and text[next_i] in " \n\t":
                        next_i += 1
                    last_split = next_i
                    i = next_i
                    continue

            i += 1

        remaining = text[last_split:]
        return sentences, remaining

    async def _generate_greeting(
        self,
        session: EmpatIASession,
        system_prompt: str,
        tool_declarations: list,
        execute_tool: Callable,
        transcript_callback: Optional[Callable[[str, str], Awaitable[None]]],
    ) -> AsyncIterator[bytes]:
        """
        Gera saudacao proativa quando a sessao inicia.

        O LLM recebe "[SESSION_START]" e produz uma saudacao personalizada
        baseada na hora do dia e no perfil do utilizador.
        """
        try:
            greeting_text = ""

            async for chunk in self.llm_service.generate_response(
                user_text="[SESSION_START]",
                system_prompt=system_prompt,
                conversation_history=[],
                tool_declarations=tool_declarations,
                execute_tool=execute_tool,
            ):
                greeting_text += chunk

            if greeting_text:
                audio_pcm = await self.tts_service.synthesize(greeting_text)
                if audio_pcm:
                    chunk_size = 32000
                    for i in range(0, len(audio_pcm), chunk_size):
                        yield audio_pcm[i : i + chunk_size]

                session.add_turn("assistant", greeting_text)
                session.conversation_history.append(
                    {"role": "model", "text": greeting_text}
                )

                if transcript_callback:
                    await transcript_callback("assistant", greeting_text)

                logger.info("Saudacao proativa enviada", text=greeting_text[:80])

        except Exception as e:
            logger.error("Erro ao gerar saudacao", error=str(e), exc_info=True)

    async def stream_conversation(
        self,
        session: EmpatIASession,
        audio_stream: AsyncIterator[bytes],
        transcript_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> AsyncIterator[bytes]:
        """
        Pipeline de conversa com saudacao proativa e barge-in:
        Greeting → Audio consumer (background) → VAD → STT → LLM → TTS → Audio

        O audio e consumido continuamente por uma task em background que
        alimenta o VAD. Se o utilizador falar enquanto o agente esta a
        responder (barge-in), a resposta TTS e interrompida.

        Args:
            session: Sessao do utilizador
            audio_stream: Stream de audio de entrada do cliente
            transcript_callback: Callback para enviar transcricoes (role, text)

        Yields:
            Bytes de audio de resposta (PCM 16-bit 24kHz)
        """
        # Obter contexto do utilizador
        context = await session.get_context()
        system_prompt = get_system_prompt(
            user_profile=context["profile"],
            recent_episodes=context["recent_episodes"],
        )

        # Declaracoes de tools
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

        # --- Infraestrutura de VAD + barge-in ---
        vad = VADProcessor()
        utterance_queue: asyncio.Queue[bytes] = asyncio.Queue()
        agent_outputting = asyncio.Event()
        barge_in_event = asyncio.Event()

        async def audio_consumer():
            """Task em background: consome audio, alimenta VAD, detecta barge-in."""
            async for chunk in audio_stream:
                utterance = vad.feed(chunk)
                if utterance is not None:
                    await utterance_queue.put(utterance)
                # Se o agente esta a enviar TTS e o utilizador comeca a falar
                if agent_outputting.is_set() and vad.is_speaking:
                    barge_in_event.set()

        consumer_task = asyncio.create_task(audio_consumer())

        logger.info(
            "A iniciar conversa (greeting + barge-in)",
            user_id=session.user_id,
            session_id=session.session_id,
        )

        try:
            # --- Passo 0: Saudacao proativa ---
            async for audio_chunk in self._generate_greeting(
                session,
                system_prompt,
                tool_declarations,
                execute_tool,
                transcript_callback,
            ):
                yield audio_chunk

            # --- Loop principal de conversa ---
            # Grace period: apos a primeira utterance do VAD, aguardar mais
            # audio antes de enviar ao STT. Isto permite ao utilizador fazer
            # pausas entre frases sem que o agente responda prematuramente.
            GRACE_PERIOD_S = 1.5

            while True:
                # Aguardar primeira utterance
                try:
                    utterance_pcm = await asyncio.wait_for(
                        utterance_queue.get(), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    if audio_stream.closed:
                        break
                    continue

                # Acumular utterances adicionais dentro do grace period
                accumulated_audio = bytearray(utterance_pcm)
                while True:
                    try:
                        more_pcm = await asyncio.wait_for(
                            utterance_queue.get(), timeout=GRACE_PERIOD_S
                        )
                        accumulated_audio.extend(more_pcm)
                        logger.debug(
                            "Grace period: utterance adicional acumulada",
                            total_bytes=len(accumulated_audio),
                        )
                    except asyncio.TimeoutError:
                        # Grace period expirou — processar audio acumulado
                        break

                # Passo 1: STT (audio completo do utilizador)
                user_text = await self.stt_service.transcribe(
                    bytes(accumulated_audio)
                )

                if not user_text:
                    logger.warning("STT retornou texto vazio, a ignorar turno")
                    continue

                logger.info("Utilizador disse", text=user_text[:100])

                if transcript_callback:
                    await transcript_callback("user", user_text)

                session.add_turn("user", user_text)
                session.conversation_history.append(
                    {"role": "user", "text": user_text}
                )

                # Passo 2: LLM + TTS com barge-in
                agent_outputting.set()
                barge_in_event.clear()
                sentence_buffer = ""
                full_response = ""
                barged = False

                async for text_chunk in self.llm_service.generate_response(
                    user_text=user_text,
                    system_prompt=system_prompt,
                    conversation_history=session.conversation_history[:-1],
                    tool_declarations=tool_declarations,
                    execute_tool=execute_tool,
                ):
                    sentence_buffer += text_chunk
                    full_response += text_chunk

                    sentences, sentence_buffer = self._extract_sentences(
                        sentence_buffer
                    )

                    for sentence in sentences:
                        audio_pcm = await self.tts_service.synthesize(sentence)
                        if audio_pcm:
                            chunk_size = 32000
                            for i in range(0, len(audio_pcm), chunk_size):
                                if barge_in_event.is_set():
                                    barged = True
                                    break
                                yield audio_pcm[i : i + chunk_size]
                        if barged:
                            break
                    if barged:
                        break

                # Flush do texto restante (so se nao houve barge-in)
                if not barged and sentence_buffer.strip():
                    audio_pcm = await self.tts_service.synthesize(
                        sentence_buffer.strip()
                    )
                    if audio_pcm:
                        chunk_size = 32000
                        for i in range(0, len(audio_pcm), chunk_size):
                            if barge_in_event.is_set():
                                break
                            yield audio_pcm[i : i + chunk_size]

                agent_outputting.clear()

                # Registar turno do assistente
                if full_response:
                    session.add_turn("assistant", full_response)
                    session.conversation_history.append(
                        {"role": "model", "text": full_response}
                    )
                    if transcript_callback:
                        await transcript_callback("assistant", full_response)

                if barged:
                    logger.info("Barge-in: resposta interrompida pelo utilizador")

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
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

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
