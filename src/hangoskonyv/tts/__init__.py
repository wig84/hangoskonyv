"""TTS (beszédszintézis) réteg: AbstractTTS és konkrét motorok."""

from hangoskonyv.tts.base import AbstractTTS, AudioSegment, VoiceSettings
from hangoskonyv.tts.factory import TTSFactory
from hangoskonyv.tts.piper_tts import PiperTTS

__all__ = ["AbstractTTS", "AudioSegment", "VoiceSettings", "TTSFactory", "PiperTTS"]
