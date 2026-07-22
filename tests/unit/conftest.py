"""Közös pytest fixture-ök és segédosztályok a unit tesztekhez."""

from __future__ import annotations

import io
import wave

import pytest

from hangoskonyv.tts.base import AbstractTTS, AudioSegment, VoiceSettings


class FakeTTS(AbstractTTS):
    """Determinisztikus, valódi szintézis nélküli `AbstractTTS` test double.

    Nem a Pipert mockolja (azt a `test_piper_tts.py` teszi meg), hanem
    egy teljesen motor-független, gyors "hangot" ad vissza — így a
    `CacheManager`/`AudioGenerator` tesztjei a TTS motortól függetlenül,
    gyorsan futnak, és pontosan mérhető, hányszor hívódott meg a
    szintézis (ez a cache-viselkedés ellenőrzésének kulcsa).
    """

    def __init__(self) -> None:
        self.synthesize_call_count = 0
        self.synthesized_texts: list[str] = []

    @property
    def supports_ssml(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True

    def synthesize(self, content: str, voice: VoiceSettings) -> AudioSegment:
        self.synthesize_call_count += 1
        self.synthesized_texts.append(content)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 10)

        return AudioSegment(
            audio_bytes=buffer.getvalue(), sample_rate=16000, sample_width=2, channels=1
        )


@pytest.fixture
def fake_tts() -> FakeTTS:
    return FakeTTS()
