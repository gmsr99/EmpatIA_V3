"""STT Service - Speech-to-Text usando Deepgram Nova-3."""

import io
import wave

import structlog
from deepgram import AsyncDeepgramClient

from src.config import settings

logger = structlog.get_logger(__name__)


class STTService:
    """Speech-to-Text usando Deepgram Nova-3."""

    def __init__(self):
        self.client = AsyncDeepgramClient(api_key=settings.deepgram_api_key)
        self.model = settings.deepgram_model
        self.language = settings.deepgram_language

    def _pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        """
        Converte PCM 16-bit 16kHz mono raw para formato WAV.
        Deepgram requer um formato de ficheiro de audio valido.
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
            # Converter PCM para WAV
            wav_bytes = self._pcm_to_wav(pcm_audio)

            # Async - não bloqueia o event loop
            response = await self.client.listen.v1.media.transcribe_file(
                request=wav_bytes,
                model=self.model,
                language=self.language,
                smart_format=True,  # Formatação automática de pontuação
            )

            # Extrair o texto transcrito
            text = ""
            if (
                response
                and hasattr(response, "results")
                and response.results
                and hasattr(response.results, "channels")
                and response.results.channels
                and len(response.results.channels) > 0
            ):
                channel = response.results.channels[0]
                if (
                    hasattr(channel, "alternatives")
                    and channel.alternatives
                    and len(channel.alternatives) > 0
                ):
                    text = channel.alternatives[0].transcript.strip()

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
