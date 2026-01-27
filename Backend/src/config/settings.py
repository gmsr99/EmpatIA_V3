"""Configurações centralizadas do EmpatIA Backend."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do ambiente."""

    # Google Cloud / Vertex AI
    google_application_credentials: str = Field(
        "vertex-key.json", env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    google_cloud_project: str = Field("empatia-480916", env="GOOGLE_CLOUD_PROJECT")
    google_cloud_region: str = Field("europe-southwest1", env="GOOGLE_CLOUD_REGION")

    # PostgreSQL
    postgres_host: str = Field("72.60.89.5", env="POSTGRES_HOST")
    postgres_port: int = Field(5433, env="POSTGRES_PORT")
    postgres_db: str = Field("bd_vet_empatia3", env="POSTGRES_DB")
    postgres_user: str = Field("postgres", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")

    # WebSocket Server
    websocket_host: str = Field("0.0.0.0", env="WEBSOCKET_HOST")
    websocket_port: int = Field(8765, env="WEBSOCKET_PORT")

    # Gemini Model Configuration
    gemini_model: str = Field(
        "gemini-live-2.5-flash-native-audio", env="GEMINI_MODEL"
    )
    gemini_voice: str = Field("Kore", env="GEMINI_VOICE")
    gemini_language: str = Field("pt-PT", env="GEMINI_LANGUAGE")
    gemini_temperature: float = Field(0.6, env="GEMINI_TEMPERATURE")

    @property
    def postgres_dsn(self) -> str:
        """Retorna a DSN de conexão PostgreSQL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_async_dsn(self) -> str:
        """Retorna a DSN assíncrona de conexão PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
