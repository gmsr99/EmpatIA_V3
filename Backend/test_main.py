#!/usr/bin/env python3
"""Versão de teste do main.py com prints para debug."""

import asyncio
import sys

def log(msg):
    print(msg)
    sys.stdout.flush()

log("1. A importar módulos...")

import signal
log("2. signal ✓")

import structlog
log("3. structlog ✓")

from src.config import settings
log("4. settings ✓")

from src.agent.empatia_agent import agent
log("5. agent ✓")

from src.server.websocket_server import ws_server
log("6. ws_server ✓")


async def main():
    log("7. Entrando em main()")

    log(f"8. Configuração:")
    log(f"   - PostgreSQL: {settings.postgres_host}:{settings.postgres_port}")
    log(f"   - WebSocket: {settings.websocket_host}:{settings.websocket_port}")

    log("9. A inicializar agente...")
    try:
        await asyncio.wait_for(agent.initialize(), timeout=15)
        log("10. ✅ Agente inicializado")
    except asyncio.TimeoutError:
        log("10. ❌ TIMEOUT ao inicializar agente")
        return
    except Exception as e:
        log(f"10. ❌ ERRO: {e}")
        return

    log("11. A iniciar WebSocket server...")
    try:
        await ws_server.start()
        log("12. ✅ WebSocket server iniciado")
    except Exception as e:
        log(f"12. ❌ ERRO WebSocket: {e}")
        return

    log("=" * 50)
    log("✅ BACKEND PRONTO!")
    log(f"WebSocket: ws://{settings.websocket_host}:{settings.websocket_port}")
    log("=" * 50)
    log("Pressione Ctrl+C para sair...")

    # Manter o server a correr
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log("Cancelado")


if __name__ == "__main__":
    log("0. Iniciando...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nEncerrado pelo utilizador")
    except Exception as e:
        log(f"ERRO FATAL: {e}")
