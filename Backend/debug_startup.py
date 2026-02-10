#!/usr/bin/env python3
"""Debug startup - identifica onde o backend congela"""
import asyncio
import sys
from src.config import settings

async def test_startup():
    print("=" * 60)
    print("DEBUG STARTUP")
    print("=" * 60)

    # 1. Test PostgreSQL connection
    print(f"\n1. Testando conexão PostgreSQL...")
    print(f"   Host: {settings.postgres_host}:{settings.postgres_port}")
    try:
        from src.database import DatabaseConnection
        print("   Importação OK")

        print("   A conectar ao pool...")
        pool = await asyncio.wait_for(DatabaseConnection.get_pool(), timeout=5)
        print(f"   ✅ Pool criado: {pool}")

        print("   A testar query...")
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"   ✅ Query OK: {result}")
    except asyncio.TimeoutError:
        print("   ❌ TIMEOUT: Conexão PostgreSQL demorou >5s")
        print("   Causa provável: VPS inacessível ou firewall bloqueando")
        return False
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

    # 2. Test Google credentials
    print(f"\n2. Testando credenciais Google...")
    print(f"   Ficheiro: {settings.google_application_credentials}")
    import os
    if os.path.exists(settings.google_application_credentials):
        print("   ✅ Ficheiro existe")
    else:
        print(f"   ❌ Ficheiro NÃO existe!")
        return False

    # 3. Test TTS Service init
    print(f"\n3. Testando TTS Service...")
    try:
        from src.services import TTSService
        tts = TTSService()
        await asyncio.wait_for(tts.initialize(), timeout=5)
        print("   ✅ TTS inicializado")
    except asyncio.TimeoutError:
        print("   ❌ TIMEOUT: TTS demorou >5s")
        return False
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

    # 4. Test LLM Service init
    print(f"\n4. Testando LLM Service...")
    try:
        from src.services import LLMService
        llm = LLMService()
        await asyncio.wait_for(llm.initialize(), timeout=5)
        print("   ✅ LLM inicializado")
    except asyncio.TimeoutError:
        print("   ❌ TIMEOUT: LLM demorou >5s")
        return False
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_startup())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Interrompido pelo utilizador")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
