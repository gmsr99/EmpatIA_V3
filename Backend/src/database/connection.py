"""Gestão de conexão assíncrona ao PostgreSQL."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class DatabaseConnection:
    """Gestor de conexões assíncronas ao PostgreSQL com pool."""

    _pool: Optional[Pool] = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get_pool(cls) -> Pool:
        """Obtém ou cria o pool de conexões."""
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    logger.info(
                        "A criar pool de conexões PostgreSQL",
                        host=settings.postgres_host,
                        port=settings.postgres_port,
                        database=settings.postgres_db,
                    )
                    try:
                        cls._pool = await asyncio.wait_for(
                            asyncpg.create_pool(
                                host=settings.postgres_host,
                                port=settings.postgres_port,
                                user=settings.postgres_user,
                                password=settings.postgres_password,
                                database=settings.postgres_db,
                                min_size=2,
                                max_size=10,
                                command_timeout=30,
                                connection_class=asyncpg.Connection,
                            ),
                            timeout=10,
                        )

                        logger.info("✅ Pool de conexões criado com sucesso")

                        # Registar o tipo vector do pgvector
                        try:
                            async with cls._pool.acquire() as conn:
                                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                            logger.info("✅ Extensão vector registada")
                        except Exception as e:
                            logger.warning("Erro ao registar extensão vector", error=str(e))

                    except asyncio.TimeoutError:
                        logger.error(
                            "❌ Timeout ao conectar ao PostgreSQL (10s)",
                            host=settings.postgres_host,
                            port=settings.postgres_port,
                        )
                        raise
                    except Exception as e:
                        logger.error(
                            "❌ Erro ao criar pool de conexões",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        """Fecha o pool de conexões."""
        if cls._pool is not None:
            async with cls._lock:
                if cls._pool is not None:
                    await cls._pool.close()
                    cls._pool = None
                    logger.info("Pool de conexões fechado")

    @classmethod
    @asynccontextmanager
    async def acquire(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """Context manager para obter uma conexão do pool."""
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            yield connection

    @classmethod
    async def execute(cls, query: str, *args) -> str:
        """Executa uma query sem retorno."""
        async with cls.acquire() as conn:
            return await conn.execute(query, *args)

    @classmethod
    async def fetch(cls, query: str, *args) -> list:
        """Executa uma query e retorna todos os resultados."""
        async with cls.acquire() as conn:
            return await conn.fetch(query, *args)

    @classmethod
    async def fetchrow(cls, query: str, *args) -> Optional[asyncpg.Record]:
        """Executa uma query e retorna uma linha."""
        async with cls.acquire() as conn:
            return await conn.fetchrow(query, *args)

    @classmethod
    async def fetchval(cls, query: str, *args):
        """Executa uma query e retorna um valor."""
        async with cls.acquire() as conn:
            return await conn.fetchval(query, *args)

    @classmethod
    async def init_schema(cls) -> None:
        """Inicializa o schema da base de dados."""
        import os

        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "sql",
            "schema.sql",
        )

        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            async with cls.acquire() as conn:
                await conn.execute(schema_sql)
                logger.info("Schema da base de dados inicializado")
        else:
            logger.warning(
                "Ficheiro de schema não encontrado", path=schema_path
            )


async def get_db() -> DatabaseConnection:
    """Factory function para obter a instância de conexão."""
    return DatabaseConnection
