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

    # Gemini Model Configuration (legacy - kept for google_search tool)
    gemini_model: str = Field(
        "gemini-live-2.5-flash-native-audio", env="GEMINI_MODEL"
    )
    gemini_voice: str = Field("Kore", env="GEMINI_VOICE")
    gemini_language: str = Field("pt-PT", env="GEMINI_LANGUAGE")
    gemini_temperature: float = Field(0.6, env="GEMINI_TEMPERATURE")

    # Deepgram (STT - Nova-3)
    deepgram_api_key: str = Field(..., env="DEEPGRAM_API_KEY")
    deepgram_model: str = Field("nova-3", env="DEEPGRAM_MODEL")
    deepgram_language: str = Field("pt", env="DEEPGRAM_LANGUAGE")

    # Gemini LLM (text reasoning - replaces Gemini Live)
    gemini_llm_model: str = Field("gemini-2.5-flash", env="GEMINI_LLM_MODEL")

    # Azure Cognitive Services TTS (Neural voices)
    azure_speech_key: str = Field(..., env="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field("westeurope", env="AZURE_SPEECH_REGION")
    tts_voice_name: str = Field("pt-PT-RaquelNeural", env="TTS_VOICE_NAME")
    tts_sample_rate: int = Field(24000, env="TTS_SAMPLE_RATE")
    tts_speaking_rate: float = Field(0.9, env="TTS_SPEAKING_RATE")

    # Report generation (Gemini 2.0 Flash)
    gemini_report_model: str = Field("gemini-2.0-flash", env="GEMINI_REPORT_MODEL")

    # VAD (Voice Activity Detection)
    vad_silence_threshold: float = Field(0.01, env="VAD_SILENCE_THRESHOLD")
    vad_silence_duration_ms: int = Field(700, env="VAD_SILENCE_DURATION_MS")
    vad_min_speech_duration_ms: int = Field(300, env="VAD_MIN_SPEECH_DURATION_MS")

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
