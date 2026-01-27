#!/usr/bin/env python3
"""Script de teste para identificar bloqueio na inicialização."""

import asyncio
import sys

print("1. A importar módulos...")
sys.stdout.flush()

import asyncpg
print("2. asyncpg importado ✓")
sys.stdout.flush()

from src.config import settings
print("3. settings importado ✓")
sys.stdout.flush()


async def test_postgres():
    print(f"4. A testar conexão PostgreSQL: {settings.postgres_host}:{settings.postgres_port}")
    sys.stdout.flush()

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
            ),
            timeout=5,
        )
        print("5. Conexão PostgreSQL OK ✓")
        sys.stdout.flush()

        result = await conn.fetchval("SELECT 1")
        print(f"6. Query PostgreSQL OK: {result} ✓")
        sys.stdout.flush()

        await conn.close()
        print("7. PostgreSQL fechado ✓")
        sys.stdout.flush()

    except asyncio.TimeoutError:
        print("❌ TIMEOUT: PostgreSQL não responde em 5s")
        sys.stdout.flush()
        return False
    except Exception as e:
        print(f"❌ ERRO PostgreSQL: {e}")
        sys.stdout.flush()
        return False

    return True


async def test_genai():
    print("8. A importar google.genai...")
    sys.stdout.flush()

    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials

    from google import genai
    print("9. google.genai importado ✓")
    sys.stdout.flush()

    print("10. A criar cliente Vertex AI...")
    sys.stdout.flush()

    client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_region,
    )
    print("11. Cliente Vertex AI criado ✓")
    sys.stdout.flush()

    return True


async def main():
    print("=" * 50)
    print("TESTE DE INICIALIZAÇÃO EMPATIA")
    print("=" * 50)
    sys.stdout.flush()

    # Teste 1: PostgreSQL
    if not await test_postgres():
        print("❌ FALHOU em PostgreSQL")
        return

    # Teste 2: GenAI
    if not await test_genai():
        print("❌ FALHOU em GenAI")
        return

    print("=" * 50)
    print("✅ TODOS OS TESTES PASSARAM")
    print("=" * 50)
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
