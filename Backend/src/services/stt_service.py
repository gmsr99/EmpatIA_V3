"""STT Service - Speech-to-Text usando Groq Whisper v3."""

import io
import wave

import structlog
from groq import AsyncGroq

from src.config import settings

logger = structlog.get_logger(__name__)


class STTService:
    """Speech-to-Text usando Groq Whisper Large v3."""

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_stt_model
        self.language = settings.groq_stt_language

    def _pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        """
        Converte PCM 16-bit 16kHz mono raw para formato WAV.
        O Groq Whisper requer um formato de ficheiro de audio valido.
        """
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(pcm_bytes)
        wav_buffer.seek(0)
        return wav_buffer.read()

    async def transcribe(self, pcm_audio: bytes) -> str:
        """
        Transcreve audio PCM para texto.

        Args:
            pcm_audio: Bytes raw PCM 16-bit 16kHz mono

        Returns:
            Texto transcrito. String vazia se a transcricao falhar.
        """
        try:
            wav_bytes = self._pcm_to_wav(pcm_audio)

            # Groq espera um tuplo de ficheiro: (filename, bytes, content_type)
            transcription = await self.client.audio.transcriptions.create(
                file=("utterance.wav", wav_bytes, "audio/wav"),
                model=self.model,
                language=self.language,
                response_format="text",
            )

            text = (
                transcription.strip()
                if isinstance(transcription, str)
                else str(transcription).strip()
            )

            logger.info(
                "STT transcricao completa",
                text_length=len(text),
                audio_size_bytes=len(pcm_audio),
                text_preview=text[:80] if text else "(vazio)",
            )

            return text

        except Exception as e:
            logger.error("STT transcricao falhou", error=str(e), exc_info=True)
            return ""
