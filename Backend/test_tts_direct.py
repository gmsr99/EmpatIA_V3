#!/usr/bin/env python3
"""Test TTS Service directly"""
import asyncio
from src.services import TTSService
from src.config import settings

async def test():
    print("=" * 60)
    print(f"Settings voice: {settings.tts_voice_name}")
    print("=" * 60)

    tts = TTSService()
    await tts.initialize()

    print(f"TTS Service voice_name: {tts.voice_name}")
    print(f"TTS Service sample_rate: {tts.sample_rate}")
    print(f"TTS Service speaking_rate: {tts.speaking_rate}")
    print("=" * 60)

    # Try to synthesize
    print("Synthesizing test audio...")
    audio = await tts.synthesize("Olá, isto é um teste.")
    print(f"Audio generated: {len(audio)} bytes")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test())
