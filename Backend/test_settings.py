#!/usr/bin/env python3
"""Debug settings loading"""
import os
from src.config import settings

print("=" * 60)
print("DEBUGGING SETTINGS")
print("=" * 60)
print(f"Current directory: {os.getcwd()}")
print(f"TTS_VOICE_NAME env var: {os.getenv('TTS_VOICE_NAME')}")
print(f"Settings tts_voice_name: {settings.tts_voice_name}")
print(f"Settings tts_sample_rate: {settings.tts_sample_rate}")
print(f"Settings tts_speaking_rate: {settings.tts_speaking_rate}")
print("=" * 60)
