"""Script de teste para verificar conectividade e configuração."""

import asyncio
import sys

import structlog

from src.config import settings
from src.database.connection import DatabaseConnection

logger = structlog.get_logger(__name__)


async def test_database():
    """Testa a conexão à base de dados PostgreSQL."""
    print("🔍 A testar conexão PostgreSQL...")
    print(f"   Host: {settings.postgres_host}")
    print(f"   Porta: {settings.postgres_port}")
    print(f"   Database: {settings.postgres_db}")
    print(f"   User: {settings.postgres_user}")
    print()

    try:
        # Testar conexão
        pool = await DatabaseConnection.get_pool()
        print("✅ Pool de conexões criado")

        # Testar query simples
        version = await DatabaseConnection.fetchval("SELECT version()")
        print(f"✅ Conexão estabelecida")
        print(f"   PostgreSQL: {version.split(',')[0]}")

        # Verificar extensão pgvector
        has_vector = await DatabaseConnection.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )

        if has_vector:
            print("✅ Extensão pgvector instalada")
        else:
            print("⚠️  Extensão pgvector NÃO instalada")
            print("   Execute: CREATE EXTENSION vector;")

        # Verificar tabelas
        tables = await DatabaseConnection.fetch(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_profiles', 'user_memories', 'conversation_episodes')
            """
        )

        if len(tables) == 3:
            print("✅ Todas as tabelas existem")
            for table in tables:
                count = await DatabaseConnection.fetchval(
                    f"SELECT COUNT(*) FROM {table['table_name']}"
                )
                print(f"   - {table['table_name']}: {count} registos")
        else:
            print(f"⚠️  Apenas {len(tables)}/3 tabelas encontradas")
            print("   Execute o schema SQL: python -c 'from src.database.connection import DatabaseConnection; import asyncio; asyncio.run(DatabaseConnection.init_schema())'")

        await DatabaseConnection.close_pool()
        print("\n✅ Teste de base de dados concluído com sucesso!")
        return True

    except Exception as e:
        print(f"\n❌ Erro ao conectar à base de dados:")
        print(f"   {str(e)}")
        return False


async def test_google_api():
    """Testa a autenticação Vertex AI."""
    print("\n🔍 A testar Vertex AI...")

    import os

    # Verificar se o ficheiro de credenciais existe
    creds_path = settings.google_application_credentials
    if not os.path.exists(creds_path):
        print(f"❌ Ficheiro de credenciais não encontrado: {creds_path}")
        return False

    print(f"   Credenciais: {creds_path}")
    print(f"   Project: {settings.google_cloud_project}")
    print(f"   Region: {settings.google_cloud_region}")

    try:
        from google import genai
        from google.genai import types

        # Configurar credenciais
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region,
        )

        print(f"   Modelo configurado: {settings.gemini_model}")

        # Testar autenticação básica com modelo disponível em europe-southwest1
        # (o modelo Live só funciona com live.connect, não com generate_content)
        print("   A testar autenticação básica...")
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents="Responde apenas 'OK'",
        )

        print("✅ Vertex AI autenticado com sucesso")
        print(f"   Resposta de teste: {response.text.strip()}")

        # Verificar se o modelo Live está configurado
        if "live" in settings.gemini_model.lower():
            print(f"✅ Modelo Live configurado: {settings.gemini_model}")
            print("   (Será testado quando o agente iniciar)")

        return True

    except Exception as e:
        print(f"❌ Erro ao testar Vertex AI:")
        print(f"   {str(e)}")
        return False


async def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("EmpatIA Backend - Teste de Configuração")
    print("=" * 60)
    print()

    db_ok = await test_database()
    api_ok = await test_google_api()

    print("\n" + "=" * 60)

    if db_ok and api_ok:
        print("✅ TODOS OS TESTES PASSARAM")
        print("=" * 60)
        print("\nO sistema está pronto para executar:")
        print("  $ python main.py")
        sys.exit(0)
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("=" * 60)
        print("\nVerifique o ficheiro .env e as credenciais.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
