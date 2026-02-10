#!/usr/bin/env python3
"""Test pt-BR-Neural2-B voice"""
import asyncio
from google.cloud import texttospeech_v1

async def test_voice():
    try:
        client = texttospeech_v1.TextToSpeechAsyncClient()

        # Test synthesis with pt-BR-Neural2-B
        synthesis_input = texttospeech_v1.SynthesisInput(text="Olá, como está?")
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code="pt-BR",
            name="pt-BR-Neural2-B"
        )
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            speaking_rate=0.9
        )

        response = await client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        print(f"✅ SUCCESS: Voice 'pt-BR-Neural2-B' works!")
        print(f"   Audio bytes: {len(response.audio_content)}")
        print(f"   Voice: Male Neural2 (Brazilian Portuguese)")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_voice())
