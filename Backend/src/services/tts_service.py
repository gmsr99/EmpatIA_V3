"""TTS Service - Text-to-Speech usando Google Cloud WaveNet."""

from typing import Optional

import structlog
from google.cloud import texttospeech_v1 as texttospeech

from src.config import settings

logger = structlog.get_logger(__name__)


class TTSService:
    """Text-to-Speech usando Google Cloud WaveNet (vozes PT-PT)."""

    def __init__(self):
        self.client: Optional[texttospeech.TextToSpeechAsyncClient] = None
        self.voice_name = settings.tts_voice_name
        self.sample_rate = settings.tts_sample_rate
        self.speaking_rate = settings.tts_speaking_rate

    async def initialize(self):
        """Inicializa o cliente TTS."""
        # Usa GOOGLE_APPLICATION_CREDENTIALS automaticamente
        self.client = texttospeech.TextToSpeechAsyncClient()
        logger.info("TTS Service inicializado", voice=self.voice_name)

    async def synthesize(self, text: str) -> bytes:
        """
        Sintetiza texto para audio PCM 16-bit 24kHz.

        Args:
            text: Texto para sintetizar

        Returns:
            Bytes raw PCM 16-bit 24kHz mono.
            O frontend espera exactamente este formato.
        """
        if not self.client:
            raise RuntimeError("TTS Service nao inicializado")

        if not text or not text.strip():
            return b""

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code="pt-PT",
                name=self.voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                speaking_rate=self.speaking_rate,
            )

            response = await self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            # LINEAR16 retorna WAV (com header de 44 bytes).
            # O frontend espera PCM raw, portanto removemos o header.
            audio_bytes = response.audio_content

            if audio_bytes[:4] == b"RIFF":
                audio_bytes = audio_bytes[44:]

            logger.info(
                "TTS sintese completa",
                text_length=len(text),
                audio_size_bytes=len(audio_bytes),
                text_preview=text[:60],
            )

            return audio_bytes

        except Exception as e:
            logger.error(
                "TTS sintese falhou",
                error=str(e),
                text=text[:60],
                exc_info=True,
            )
            return b""
