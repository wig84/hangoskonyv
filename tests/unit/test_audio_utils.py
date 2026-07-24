"""Unit tesztek az audio.audio_utils modulhoz."""

from __future__ import annotations

import io
import wave

import pytest

from hangoskonyv.audio.audio_utils import concatenate_audio_segments, generate_silence
from hangoskonyv.core.exceptions import HangoskonyvError
from hangoskonyv.tts.base import AudioSegment


def _wav_duration_ms(audio_bytes: bytes) -> float:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        return 1000 * wav_file.getnframes() / wav_file.getframerate()


def _make_tone(duration_ms: int, sample_rate: int = 16000) -> AudioSegment:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frame_count = int(sample_rate * duration_ms / 1000)
        wav_file.writeframes(b"\x01\x00" * frame_count)
    return AudioSegment(audio_bytes=buffer.getvalue(), sample_rate=sample_rate, sample_width=2, channels=1)


class TestGenerateSilence:
    def test_duration_is_accurate(self) -> None:
        silence = generate_silence(500, sample_rate=16000)
        assert abs(_wav_duration_ms(silence.audio_bytes) - 500) < 1

    def test_all_samples_are_zero(self) -> None:
        silence = generate_silence(100, sample_rate=16000)
        with wave.open(io.BytesIO(silence.audio_bytes), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
        assert set(frames) == {0}

    def test_metadata_matches_arguments(self) -> None:
        silence = generate_silence(200, sample_rate=22050, sample_width=2, channels=2)
        assert silence.sample_rate == 22050
        assert silence.channels == 2


class TestConcatenateAudioSegments:
    def test_total_duration_is_sum_of_parts(self) -> None:
        a = _make_tone(200)
        b = generate_silence(100, sample_rate=16000)
        c = _make_tone(300)

        combined = concatenate_audio_segments([a, b, c])

        assert abs(_wav_duration_ms(combined.audio_bytes) - 600) < 1

    def test_single_segment_passthrough(self) -> None:
        a = _make_tone(150)
        combined = concatenate_audio_segments([a])
        assert abs(_wav_duration_ms(combined.audio_bytes) - 150) < 1

    def test_empty_list_raises(self) -> None:
        with pytest.raises(HangoskonyvError):
            concatenate_audio_segments([])

    def test_mismatched_sample_rate_raises(self) -> None:
        a = _make_tone(100, sample_rate=16000)
        b = _make_tone(100, sample_rate=22050)
        with pytest.raises(HangoskonyvError, match="nem egyezik"):
            concatenate_audio_segments([a, b])

    def test_result_preserves_format(self) -> None:
        a = _make_tone(100, sample_rate=16000)
        b = _make_tone(100, sample_rate=16000)
        combined = concatenate_audio_segments([a, b])
        assert combined.sample_rate == 16000
        assert combined.sample_width == 2
        assert combined.channels == 1
