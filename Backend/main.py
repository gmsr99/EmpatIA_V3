"""
EmpatIA Backend - Agente de voz empático para idosos
Baseado no Google Gen AI Agent Development Kit (ADK)
"""

import asyncio
import logging
import signal
import sys

import structlog
from structlog.stdlib import LoggerFactory

from src.agent.empatia_agent import agent
from src.server.websocket_server import ws_server
from src.config import settings

# Configurar logging estruturado com flush automático
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=False,
)

# Forçar flush do stdout para logging aparecer imediatamente
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logger = structlog.get_logger(__name__)


class EmpatIABackend:
    """Aplicação principal do backend EmpatIA."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()

    def setup_signal_handlers(self):
        """Configura handlers para sinais de sistema (SIGINT, SIGTERM)."""

        def signal_handler(signum, frame):
            logger.info(f"Sinal {signum} recebido, a encerrar...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def startup(self):
        """Inicializa todos os componentes do backend."""
        logger.info("=" * 60)
        logger.info("EmpatIA Backend - A iniciar")
        logger.info("=" * 60)

        logger.info("Configuração:")
        logger.info(f"  - PostgreSQL: {settings.postgres_host}:{settings.postgres_port}")
        logger.info(f"  - Database: {settings.postgres_db}")
        logger.info(f"  - WebSocket: {settings.websocket_host}:{settings.websocket_port}")
        logger.info(f"  - Modelo: {settings.gemini_model}")
        logger.info(f"  - Voz: {settings.gemini_voice}")
        logger.info(f"  - Idioma: {settings.gemini_language}")

        try:
            # Inicializar agente
            logger.info("A inicializar agente EmpatIA...")
            try:
                await asyncio.wait_for(agent.initialize(), timeout=30)
            except asyncio.TimeoutError:
                logger.error("❌ Timeout (30s) ao inicializar agente - verificar conexão PostgreSQL")
                raise

            # Iniciar servidor WebSocket
            logger.info("A iniciar servidor WebSocket...")
            await ws_server.start()

            logger.info("=" * 60)
            logger.info("✅ EmpatIA Backend PRONTO")
            logger.info(f"WebSocket disponível em: ws://{settings.websocket_host}:{settings.websocket_port}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Erro fatal durante inicialização: {e}")
            sys.exit(1)

    async def shutdown(self):
        """Encerra todos os componentes graciosamente."""
        logger.info("A encerrar EmpatIA Backend...")

        try:
            # Parar servidor WebSocket
            await ws_server.stop()

            # Encerrar agente
            await agent.shutdown()

            logger.info("EmpatIA Backend encerrado com sucesso")

        except Exception as e:
            logger.error(f"Erro durante encerramento: {e}")

    async def run(self):
        """Loop principal da aplicação."""
        self.setup_signal_handlers()

        await self.startup()

        # Aguardar sinal de shutdown
        await self.shutdown_event.wait()

        await self.shutdown()


async def main():
    """Ponto de entrada principal."""
    backend = EmpatIABackend()
    await backend.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Encerramento forçado pelo utilizador")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
