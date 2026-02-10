"""TTS Service - Text-to-Speech usando Azure Cognitive Services."""

import asyncio

import structlog
import azure.cognitiveservices.speech as speechsdk

from src.config import settings

logger = structlog.get_logger(__name__)


class TTSService:
    """Text-to-Speech usando Azure Cognitive Services (vozes PT-PT Neural)."""

    def __init__(self):
        self.speech_config: speechsdk.SpeechConfig | None = None
        self.synthesizer: speechsdk.SpeechSynthesizer | None = None
        self.voice_name = settings.tts_voice_name
        self.sample_rate = settings.tts_sample_rate
        self.speaking_rate = settings.tts_speaking_rate

    async def initialize(self):
        """Inicializa a configuração Azure Speech e synthesizer reutilizável."""
        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        self.speech_config.speech_synthesis_voice_name = self.voice_name

        # Formato de saída: PCM raw 24kHz 16-bit mono (compatível com frontend)
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
        )

        # Reutilizar synthesizer - evita overhead de criar conexão por cada frase
        self.synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=None,
        )

        logger.info("TTS Service inicializado (Azure)", voice=self.voice_name)

    def _build_ssml(self, text: str) -> str:
        """Build SSML with prosody controls for warm, natural speech."""
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        return (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xml:lang="pt-PT">'
            f'<voice name="{self.voice_name}">'
            f'<prosody rate="{self.speaking_rate}" pitch="+5%">'
            f"{escaped}"
            '<break time="1ms"/>'
            "</prosody>"
            "</voice>"
            "</speak>"
        )

    async def synthesize(self, text: str) -> bytes:
        """
        Sintetiza texto para audio PCM 16-bit 24kHz usando SSML.

        Args:
            text: Texto para sintetizar

        Returns:
            Bytes raw PCM 16-bit 24kHz mono.
            O frontend espera exactamente este formato.
        """
        if not self.synthesizer:
            raise RuntimeError("TTS Service nao inicializado")

        if not text or not text.strip():
            return b""

        try:
            ssml = self._build_ssml(text)

            # Azure SDK é síncrono - correr em thread para não bloquear o event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self.synthesizer.speak_ssml_async(ssml).get()
            )

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_bytes = result.audio_data

                logger.info(
                    "TTS sintese completa",
                    text_length=len(text),
                    audio_size_bytes=len(audio_bytes),
                    text_preview=text[:60],
                )

                return audio_bytes

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(
                    "TTS sintese cancelada",
                    reason=str(cancellation.reason),
                    error=cancellation.error_details,
                )
                return b""

            return b""

        except Exception as e:
            logger.error(
                "TTS sintese falhou",
                error=str(e),
                text=text[:60],
                exc_info=True,
            )
            return b""
