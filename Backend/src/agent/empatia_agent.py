"""EmpatIA Agent - Agente de voz empático baseado no Google ADK."""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any, AsyncIterator
import uuid

import structlog
from google import genai
from google.genai import types

from src.config import settings
from src.database import MemoryStore, DatabaseConnection
from src.agent.system_prompt import get_system_prompt
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
    """Representa uma sessão de conversa com o utilizador."""

    def __init__(self, user_id: str, session_id: Optional[str] = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.started_at = datetime.now()
        self.conversation_turns = []
        self.key_topics = set()
        self.memory_store = MemoryStore()

    async def get_context(self) -> Dict[str, Any]:
        """Obtém o contexto completo do utilizador para injetar no system prompt."""
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
        """Guarda o episódio de conversa na base de dados."""
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
            "Episódio guardado",
            user_id=self.user_id,
            session_id=self.session_id,
            duration=duration,
        )


class EmpatIAAgent:
    """Agente EmpatIA com suporte a streaming de áudio bidireccional."""

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.active_sessions: Dict[str, EmpatIASession] = {}
        self.memory_store = MemoryStore()

    async def initialize(self):
        """Inicializa o agente e a conexão com a base de dados."""
        await DatabaseConnection.get_pool()
        # Inicializar schema (seguro para múltiplas execuções - usa IF NOT EXISTS)
        await DatabaseConnection.init_schema()
        logger.info("✅ Schema verificado/inicializado")

        # Configurar autenticação Vertex AI
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials

        # Inicializar cliente com Vertex AI
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )

        logger.info(
            "Agente EmpatIA inicializado",
            project=settings.google_cloud_project,
            region=settings.google_cloud_region,
        )

    async def create_session(self, user_id: str) -> EmpatIASession:
        """Cria uma nova sessão para o utilizador."""
        session = EmpatIASession(user_id)
        self.active_sessions[session.session_id] = session

        logger.info(
            "Nova sessão criada",
            user_id=user_id,
            session_id=session.session_id,
        )

        return session

    async def get_session(self, session_id: str) -> Optional[EmpatIASession]:
        """Obtém uma sessão existente."""
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
                # Validar que tool_input é dict
                if not isinstance(tool_input, dict):
                    logger.error(
                        "tool_input não é dict",
                        tool_input=tool_input,
                        type=type(tool_input),
                    )
                    return {"success": False, "error": "Parâmetros inválidos"}

                params = ManageMemoryInput(**tool_input)
                return await manage_memory_tool(params, user_id)

            elif tool_name == "google_search":
                if not isinstance(tool_input, dict):
                    logger.error(
                        "tool_input não é dict",
                        tool_input=tool_input,
                        type=type(tool_input),
                    )
                    return {"success": False, "error": "Parâmetros inválidos"}

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

    async def stream_conversation(
        self, session: EmpatIASession, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        """
        Mantém uma conversa de voz bidireccional streaming.

        Args:
            session: Sessão do utilizador
            audio_stream: Stream de áudio de entrada do cliente

        Yields:
            Bytes de áudio de resposta
        """
        if not self.client:
            raise RuntimeError("Agente não inicializado")

        # Obter contexto do utilizador
        context = await session.get_context()
        system_prompt = get_system_prompt(
            user_profile=context["profile"],
            recent_episodes=context["recent_episodes"],
        )

        # Configurar modelo com voice config, generation config e tools
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=system_prompt)]
            ),
            generation_config=types.GenerationConfig(
                temperature=settings.gemini_temperature,
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=settings.gemini_voice
                    )
                )
            ),
            tools=[
                types.Tool(function_declarations=[
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
                ])
            ],
        )

        logger.info(
            "A iniciar conversa streaming",
            user_id=session.user_id,
            session_id=session.session_id,
            voice=settings.gemini_voice,
        )

        try:
            logger.info("A conectar à Gemini Live API", model=settings.gemini_model)
            async with self.client.aio.live.connect(
                model=settings.gemini_model, config=config
            ) as live_session:
                logger.info("Conexão Live estabelecida (system_instruction no config)")

                # Processar audio stream de entrada
                async def send_audio():
                    """Envia áudio do cliente para o modelo."""
                    chunks_sent = 0
                    total_bytes = 0
                    try:
                        async for audio_chunk in audio_stream:
                            chunks_sent += 1
                            chunk_size = len(audio_chunk)
                            total_bytes += chunk_size

                            if chunks_sent == 1:
                                logger.info("Primeiro chunk de áudio enviado ao Gemini", chunk_size=chunk_size)
                            if chunks_sent % 50 == 0:
                                logger.info(
                                    f"Enviados {chunks_sent} chunks de áudio ao Gemini",
                                    total_bytes=total_bytes,
                                    avg_chunk_size=total_bytes // chunks_sent
                                )

                            await live_session.send_realtime_input(
                                audio=types.Blob(
                                    mime_type="audio/pcm;rate=16000",
                                    data=audio_chunk,
                                )
                            )
                    except Exception as e:
                        logger.error("Erro no send_audio", error=str(e), chunks_sent=chunks_sent)

                # Iniciar task de envio
                send_task = asyncio.create_task(send_audio())

                # Processar respostas do modelo
                audio_responses = 0
                text_responses = 0
                turn_count = 0
                session_active = True

                try:
                    # Loop contínuo para manter sessão aberta
                    while session_active and not send_task.done():
                        try:
                            # Receber respostas com timeout
                            async for response in live_session.receive():
                                # Log de TODOS os tipos de resposta
                                logger.debug(
                                    "Resposta Gemini recebida",
                                    has_server_content=bool(response.server_content),
                                    has_tool_call=bool(response.tool_call),
                                )

                                # Processar server content (áudio de resposta)
                                if response.server_content:
                                    server_content = response.server_content

                                    # model_turn contém os parts com áudio/texto
                                    if server_content.model_turn and server_content.model_turn.parts:
                                        for part in server_content.model_turn.parts:
                                            # Áudio de resposta
                                            if part.inline_data and part.inline_data.data:
                                                audio_responses += 1
                                                audio_size = len(part.inline_data.data)
                                                logger.info(f"🔊 Áudio recebido #{audio_responses}", size=audio_size)
                                                yield part.inline_data.data

                                            # Texto de resposta (para logging)
                                            if part.text:
                                                text_responses += 1
                                                session.add_turn("assistant", part.text)
                                                logger.info(
                                                    f"💬 Texto recebido #{text_responses}",
                                                    text=part.text[:100] if len(part.text) > 100 else part.text
                                                )

                                    # Verificar se o turno está completo
                                    if server_content.turn_complete:
                                        turn_count += 1
                                        logger.info(f"✅ Turn #{turn_count} completo - aguardando mais input...")
                                        # NÃO sair do loop - continuar a escutar

                                    # Verificar se foi interrompido
                                    if server_content.interrupted:
                                        logger.info("⚠️ Resposta interrompida pelo utilizador")

                                # Processar tool calls
                                if response.tool_call:
                                    tool_call = response.tool_call
                                    function_calls = tool_call.function_calls if hasattr(tool_call, 'function_calls') else []

                                    for call in function_calls:
                                        call_name = call.name if hasattr(call, 'name') else None
                                        call_args = call.args if hasattr(call, 'args') else {}

                                        if call_name:
                                            logger.info("Tool call recebido", tool_name=call_name, args_type=type(call_args).__name__)

                                            # Converter args para dict se for protobuf Struct
                                            if hasattr(call_args, '_pb'):
                                                # É um protobuf Struct, converter para dict
                                                import json
                                                from google.protobuf.json_format import MessageToDict
                                                call_args = MessageToDict(call_args._pb)
                                            elif not isinstance(call_args, dict):
                                                # Tentar converter para dict
                                                call_args = dict(call_args) if call_args else {}

                                            tool_result = await self._execute_tool(
                                                call_name, call_args, session.user_id
                                            )

                                            # Enviar resultado da tool
                                            await live_session.send_tool_response(
                                                function_responses=types.FunctionResponse(
                                                    name=call_name,
                                                    response=tool_result,
                                                )
                                            )

                                # Processar setup_complete (confirmação inicial)
                                if hasattr(response, 'setup_complete') and response.setup_complete:
                                    logger.info("Setup da sessão Live completo")

                            # Se o iterador terminou, pode significar que a sessão fechou
                            logger.info("Iterador receive() terminou, verificando estado...")

                        except StopAsyncIteration:
                            logger.info("Receive iterator exhausted, session may have ended")
                            session_active = False

                except asyncio.CancelledError:
                    logger.info("Stream cancelado pelo cliente")
                    session_active = False

                finally:
                    send_task.cancel()
                    try:
                        await send_task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            logger.error(
                "Erro na conversa streaming",
                error=str(e),
                session_id=session.session_id,
            )
            raise

        logger.info(
            "Conversa finalizada",
            session_id=session.session_id,
            turns=len(session.conversation_turns),
        )

    async def end_session(self, session_id: str):
        """Termina uma sessão e guarda o episódio."""
        session = self.active_sessions.get(session_id)
        if session:
            # Gerar resumo e guardar episódio
            # (isto poderia usar o próprio Gemini para resumir)
            await session.save_episode(
                summary="Conversa com EmpatIA",
                emotional_tone="neutro",
            )

            del self.active_sessions[session_id]

            logger.info("Sessão terminada", session_id=session_id)

    async def shutdown(self):
        """Encerra o agente graciosamente."""
        for session_id in list(self.active_sessions.keys()):
            await self.end_session(session_id)

        await DatabaseConnection.close_pool()
        logger.info("Agente EmpatIA encerrado")


# Instância global do agente
agent = EmpatIAAgent()
