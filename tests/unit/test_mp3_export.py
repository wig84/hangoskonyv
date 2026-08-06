"""Unit tesztek a utils.mp3_export modulhoz.

Ezek a tesztek valódi `ffmpeg`-et használnak (nem mockolják), mivel
az elérhető ebben a fejlesztői környezetben — ez a legmegbízhatóbb
mód annak ellenőrzésére, hogy a subprocess-hívás paraméterezése
ténylegesen helyes.
"""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from hangoskonyv.core.exceptions import HangoskonyvError
from hangoskonyv.utils.mp3_export import convert_wav_to_mp3, is_ffmpeg_available


def _make_wav(path: Path, duration_seconds: float = 0.5, sample_rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frame_count = int(sample_rate * duration_seconds)
        wav_file.writeframes(b"\x00\x01" * frame_count)


class TestIsFfmpegAvailable:
    def test_returns_bool(self) -> None:
        assert isinstance(is_ffmpeg_available(), bool)


class TestFfmpegNotAvailable:
    def test_raises_clear_error_when_ffmpeg_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("hangoskonyv.utils.mp3_export.shutil.which", lambda _: None)

        with pytest.raises(HangoskonyvError, match="ffmpeg"):
            convert_wav_to_mp3(tmp_path / "x.wav", tmp_path / "x.mp3")


@pytest.mark.skipif(not is_ffmpeg_available(), reason="ffmpeg nincs telepítve ezen a gépen")
class TestConvertWavToMp3:
    def test_creates_mp3_file(self, tmp_path: Path) -> None:
        wav_path = tmp_path / "teszt.wav"
        mp3_path = tmp_path / "teszt.mp3"
        _make_wav(wav_path)

        convert_wav_to_mp3(wav_path, mp3_path)

        assert mp3_path.exists()
        assert mp3_path.stat().st_size > 0

    def test_missing_input_raises(self, tmp_path: Path) -> None:
        with pytest.raises(HangoskonyvError):
            convert_wav_to_mp3(tmp_path / "nincs.wav", tmp_path / "x.mp3")

    def test_quality_parameter_accepted(self, tmp_path: Path) -> None:
        wav_path = tmp_path / "teszt.wav"
        mp3_path = tmp_path / "teszt.mp3"
        _make_wav(wav_path)

        convert_wav_to_mp3(wav_path, mp3_path, quality=5)

        assert mp3_path.exists()
