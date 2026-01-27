"""WebSocket Server para streaming de áudio bidireccional."""

import asyncio
import json
from typing import Optional, Dict
import uuid

import websockets
from websockets.server import WebSocketServerProtocol
import structlog

from src.agent.empatia_agent import agent, EmpatIASession
from src.config import settings

logger = structlog.get_logger(__name__)


class AudioStreamQueue:
    """Queue assíncrona para buffering de áudio."""

    def __init__(self):
        self.queue = asyncio.Queue()
        self.closed = False

    async def put(self, data: bytes):
        """Adiciona dados de áudio à queue."""
        if not self.closed:
            await self.queue.put(data)

    async def __aiter__(self):
        """Itera sobre o stream de áudio."""
        while not self.closed:
            try:
                data = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                yield data
            except asyncio.TimeoutError:
                continue

    def close(self):
        """Fecha o stream."""
        self.closed = True


class WebSocketConnection:
    """Representa uma conexão WebSocket ativa."""

    def __init__(self, websocket: WebSocketServerProtocol, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.session: Optional[EmpatIASession] = None
        self.audio_input_queue = AudioStreamQueue()
        self.is_active = True

    async def handle(self):
        """Processa mensagens do cliente e stream de áudio."""
        try:
            # Criar sessão
            self.session = await agent.create_session(self.user_id)

            logger.info(
                "Conexão WebSocket estabelecida",
                user_id=self.user_id,
                session_id=self.session.session_id,
            )

            # Enviar confirmação de sessão
            await self.send_json(
                {
                    "type": "session_created",
                    "session_id": self.session.session_id,
                    "user_id": self.user_id,
                }
            )

            # Iniciar task de streaming do agente
            stream_task = asyncio.create_task(self._stream_agent_audio())

            # Processar mensagens do cliente
            audio_chunks_received = 0
            async for message in self.websocket:
                if isinstance(message, bytes):
                    # Dados de áudio PCM
                    audio_chunks_received += 1
                    if audio_chunks_received % 50 == 0:  # Log a cada 50 chunks
                        logger.debug(
                            f"Recebido chunk de áudio #{audio_chunks_received}: {len(message)} bytes",
                            user_id=self.user_id
                        )
                    await self.audio_input_queue.put(message)

                elif isinstance(message, str):
                    # Mensagem JSON de controlo
                    await self._handle_control_message(json.loads(message))

            # Quando o cliente desconecta
            self.audio_input_queue.close()
            await stream_task

        except websockets.exceptions.ConnectionClosed:
            logger.info("Cliente desconectado", user_id=self.user_id)

        except Exception as e:
            logger.error("Erro na conexão WebSocket", error=str(e), user_id=self.user_id)

        finally:
            await self.cleanup()

    async def _stream_agent_audio(self):
        """Stream de áudio do agente para o cliente."""
        try:
            logger.info("A iniciar stream de conversa com agente", user_id=self.user_id)
            async for audio_chunk in agent.stream_conversation(
                self.session, self.audio_input_queue
            ):
                if self.is_active:
                    logger.debug(f"Enviando chunk de áudio: {len(audio_chunk)} bytes")
                    await self.websocket.send(audio_chunk)
                else:
                    logger.info("Stream parado (is_active=False)")
                    break

            logger.info("Stream de conversa terminado normalmente", user_id=self.user_id)

        except Exception as e:
            logger.error("Erro no stream de áudio", error=str(e), exc_info=True)

    async def _handle_control_message(self, message: Dict):
        """Processa mensagens de controlo do cliente."""
        msg_type = message.get("type")

        if msg_type == "ping":
            await self.send_json({"type": "pong"})

        elif msg_type == "end_session":
            logger.info("Cliente solicitou fim de sessão", user_id=self.user_id)
            await self.cleanup()

        else:
            logger.warning("Tipo de mensagem desconhecido", msg_type=msg_type)

    async def send_json(self, data: Dict):
        """Envia mensagem JSON para o cliente."""
        try:
            await self.websocket.send(json.dumps(data))
        except Exception as e:
            logger.error("Erro ao enviar JSON", error=str(e))

    async def cleanup(self):
        """Limpa recursos da conexão."""
        self.is_active = False
        self.audio_input_queue.close()

        if self.session:
            await agent.end_session(self.session.session_id)

        logger.info("Conexão limpa", user_id=self.user_id)


class EmpatIAWebSocketServer:
    """Servidor WebSocket para o agente EmpatIA."""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.server = None

    async def handler(self, websocket: WebSocketServerProtocol):
        """Handler principal de conexões WebSocket."""
        # Extrair user_id do path ou query params
        # Formato esperado: ws://host:port/ws?user_id=USER_ID
        # Na versão 13+ do websockets, o path está em websocket.request.path
        path = websocket.request.path
        user_id = self._extract_user_id(websocket, path)

        if not user_id:
            logger.warning("Conexão rejeitada: user_id ausente")
            await websocket.close(1008, "user_id obrigatório")
            return

        connection = WebSocketConnection(websocket, user_id)
        self.connections[user_id] = connection

        try:
            await connection.handle()
        finally:
            if user_id in self.connections:
                del self.connections[user_id]

    def _extract_user_id(
        self, websocket: WebSocketServerProtocol, path: str
    ) -> Optional[str]:
        """Extrai o user_id dos query parameters."""
        try:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(path)
            params = parse_qs(parsed.query)
            return params.get("user_id", [None])[0]
        except Exception as e:
            logger.error("Erro ao extrair user_id", error=str(e))
            return None

    async def start(self):
        """Inicia o servidor WebSocket."""
        logger.info(
            "A iniciar servidor WebSocket",
            host=settings.websocket_host,
            port=settings.websocket_port,
        )

        self.server = await websockets.serve(
            self.handler,
            settings.websocket_host,
            settings.websocket_port,
            ping_interval=20,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,  # 10MB
        )

        logger.info("Servidor WebSocket iniciado")

    async def stop(self):
        """Para o servidor WebSocket."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Servidor WebSocket parado")


# Instância global do servidor
ws_server = EmpatIAWebSocketServer()
