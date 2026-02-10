"""Voice Activity Detection (VAD) - Detecao de fala baseada em energia RMS."""

import math
import struct
import time
from typing import AsyncIterator, Optional

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class VADProcessor:
    """
    VAD server-side baseado em threshold de energia RMS.

    Recebe chunks de audio PCM 16-bit 16kHz mono do AudioStreamQueue.
    Detecta quando o utilizador para de falar (silencio > threshold).
    Emite utterances completas (bytes) prontas para STT.
    """

    def __init__(self):
        self.silence_threshold = settings.vad_silence_threshold
        self.silence_duration_ms = settings.vad_silence_duration_ms
        self.min_speech_duration_ms = settings.vad_min_speech_duration_ms
        self.sample_rate = 16000
        self.bytes_per_sample = 2  # 16-bit

        self._audio_buffer = bytearray()
        self._is_speaking = False
        self._silence_start: Optional[float] = None
        self._speech_start: Optional[float] = None
        self._closed = False

    def _calculate_rms(self, pcm_bytes: bytes) -> float:
        """Calcula energia RMS de audio PCM 16-bit."""
        if len(pcm_bytes) < 2:
            return 0.0

        num_samples = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{num_samples}h", pcm_bytes[: num_samples * 2])
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / num_samples) / 32768.0  # Normalizar para 0-1
        return rms

    @property
    def is_speaking(self) -> bool:
        """Whether the user is currently speaking."""
        return self._is_speaking

    def _reset_state(self):
        """Reset VAD state after utterance."""
        self._audio_buffer = bytearray()
        self._is_speaking = False
        self._silence_start = None
        self._speech_start = None

    def feed(self, chunk: bytes) -> Optional[bytes]:
        """
        Feed a single chunk of audio. Returns complete utterance if detected, None otherwise.

        Pull-based alternative to process_stream() — used by the background
        audio consumer task so we can monitor for barge-in concurrently.
        """
        if self._closed:
            return None

        rms = self._calculate_rms(chunk)
        now = time.monotonic()

        if rms > self.silence_threshold:
            # Speech detected
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start = now
                logger.debug("VAD: Fala iniciada")
            self._silence_start = None
            self._audio_buffer.extend(chunk)

        else:
            # Silence
            if self._is_speaking:
                self._audio_buffer.extend(chunk)

                if self._silence_start is None:
                    self._silence_start = now

                silence_elapsed_ms = (now - self._silence_start) * 1000

                if silence_elapsed_ms >= self.silence_duration_ms:
                    speech_duration_ms = (
                        (now - self._speech_start) * 1000
                        if self._speech_start
                        else 0
                    )

                    if speech_duration_ms >= self.min_speech_duration_ms:
                        utterance = bytes(self._audio_buffer)
                        logger.info(
                            "VAD: Utterance completa",
                            duration_ms=int(speech_duration_ms),
                            size_bytes=len(utterance),
                        )
                        self._reset_state()
                        return utterance

                    self._reset_state()

        return None

    async def process_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        """
        Consome chunks de audio, emite utterances completas.

        Cada bytes emitido e uma utterance completa do utilizador
        (PCM 16-bit 16kHz) pronta para converter em WAV e enviar ao STT.
        """
        async for chunk in audio_stream:
            if self._closed:
                break

            rms = self._calculate_rms(chunk)
            now = time.monotonic()

            if rms > self.silence_threshold:
                # Fala detectada
                if not self._is_speaking:
                    self._is_speaking = True
                    self._speech_start = now
                    logger.debug("VAD: Fala iniciada")
                self._silence_start = None
                self._audio_buffer.extend(chunk)

            else:
                # Silencio
                if self._is_speaking:
                    # Incluir silencio final no buffer
                    self._audio_buffer.extend(chunk)

                    if self._silence_start is None:
                        self._silence_start = now

                    silence_elapsed_ms = (now - self._silence_start) * 1000

                    if silence_elapsed_ms >= self.silence_duration_ms:
                        # Verificar duracao minima de fala
                        speech_duration_ms = (
                            (now - self._speech_start) * 1000
                            if self._speech_start
                            else 0
                        )

                        if speech_duration_ms >= self.min_speech_duration_ms:
                            utterance = bytes(self._audio_buffer)
                            logger.info(
                                "VAD: Utterance completa",
                                duration_ms=int(speech_duration_ms),
                                size_bytes=len(utterance),
                            )
                            yield utterance

                        # Reset estado
                        self._audio_buffer = bytearray()
                        self._is_speaking = False
                        self._silence_start = None
                        self._speech_start = None

    def close(self) -> Optional[bytes]:
        """Fecha o VAD e retorna buffer restante se havia fala em curso."""
        self._closed = True
        if self._is_speaking and len(self._audio_buffer) > 0:
            remaining = bytes(self._audio_buffer)
            self._audio_buffer = bytearray()
            return remaining
        return None
