"""Unit tesztek a PiperTTS-hez.

Két csoportra oszlanak:

1. **Valós esetek** — ebben a fejlesztői környezetben a `piper`
   csomag ténylegesen nincs telepítve, így ezek a tesztek a
   "motor nem elérhető" hibaágat valódi körülmények között
   ellenőrzik, mock nélkül.
2. **Mock-olt esetek** — egy minimális, hamis `piper` modult
   regisztrálunk a `sys.modules`-ba, hogy a sikeres szintézis
   logikai útját (VoiceSettings -> SynthesisConfig fordítás,
   AudioSegment felépítése, gyorsítótárazás) is ellenőrizni tudjuk
   valódi hangmodell és hálózat nélkül.
"""

from __future__ import annotations

import sys
import types
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from hangoskonyv.core.exceptions import SynthesisError, TTSEngineNotAvailableError
from hangoskonyv.tts.base import VoiceSettings
from hangoskonyv.tts.piper_tts import PiperTTS


class TestSupportsSsml:
    def test_piper_does_not_support_ssml(self) -> None:
        assert PiperTTS().supports_ssml is False


class TestRealEnvironmentWithoutPiper:
    """Ezek a tesztek feltételezik, hogy a `piper` csomag nincs telepítve.

    Ha a fejlesztői gépeden telepítve van a `piper-tts`, ezek a
    tesztek átugorhatók (skip) — lásd a `pytest.importorskip`-fordítottját
    végző feltételt.
    """

    def _piper_actually_installed(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return True

    def test_is_available_false(self) -> None:
        if self._piper_actually_installed():
            pytest.skip("A piper csomag telepítve van ezen a gépen.")
        assert PiperTTS().is_available() is False

    def test_synthesize_raises_when_not_installed(self, tmp_path: Path) -> None:
        if self._piper_actually_installed():
            pytest.skip("A piper csomag telepítve van ezen a gépen.")
        tts = PiperTTS()
        voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")
        with pytest.raises(TTSEngineNotAvailableError, match="piper"):
            tts.synthesize("Szia világ.", voice)


# --- Mock-olt piper modul a sikeres útvonal teszteléséhez -------------------


@dataclass
class _FakeSynthesisConfig:
    volume: float = 1.0
    length_scale: float = 1.0
    speaker_id: int | None = None


class _FakePiperVoice:
    load_call_count = 0
    last_synthesize_kwargs: dict | None = None

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    @classmethod
    def load(cls, path: str) -> "_FakePiperVoice":
        cls.load_call_count += 1
        return cls(path)

    def synthesize_wav(self, text: str, wav_file: wave.Wave_write, syn_config=None) -> None:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)
        type(self).last_synthesize_kwargs = {"text": text, "syn_config": syn_config}


@pytest.fixture
def fake_piper_module(monkeypatch: pytest.MonkeyPatch):
    """Regisztrál egy minimális hamis `piper` modult a sys.modules-ban."""
    _FakePiperVoice.load_call_count = 0
    _FakePiperVoice.last_synthesize_kwargs = None

    fake_module = types.ModuleType("piper")
    fake_module.PiperVoice = _FakePiperVoice
    fake_module.SynthesisConfig = _FakeSynthesisConfig
    monkeypatch.setitem(sys.modules, "piper", fake_module)
    return fake_module


class TestSynthesizeWithFakePiper:
    def test_returns_audio_segment_with_correct_metadata(
        self, fake_piper_module, tmp_path: Path
    ) -> None:
        model_path = tmp_path / "hang.onnx"
        model_path.write_bytes(b"nem valodi onnx tartalom")

        tts = PiperTTS()
        result = tts.synthesize("Szia világ.", VoiceSettings(voice_model_path=model_path))

        assert result.sample_rate == 22050
        assert result.channels == 1
        assert result.sample_width == 2
        assert len(result.audio_bytes) > 0

    def test_missing_model_raises_even_with_piper_available(
        self, fake_piper_module, tmp_path: Path
    ) -> None:
        tts = PiperTTS()
        missing_model = tmp_path / "nincs_ilyen.onnx"
        with pytest.raises(TTSEngineNotAvailableError, match="hangmodell"):
            tts.synthesize("Szia.", VoiceSettings(voice_model_path=missing_model))

    def test_speed_converts_to_inverse_length_scale(
        self, fake_piper_module, tmp_path: Path
    ) -> None:
        model_path = tmp_path / "hang.onnx"
        model_path.write_bytes(b"x")

        tts = PiperTTS()
        tts.synthesize("Gyors felolvasás.", VoiceSettings(voice_model_path=model_path, speed=2.0))

        syn_config = _FakePiperVoice.last_synthesize_kwargs["syn_config"]
        assert syn_config.length_scale == pytest.approx(0.5)

    def test_voice_is_cached_across_calls(self, fake_piper_module, tmp_path: Path) -> None:
        model_path = tmp_path / "hang.onnx"
        model_path.write_bytes(b"x")

        tts = PiperTTS()
        tts.synthesize("Első hívás.", VoiceSettings(voice_model_path=model_path))
        tts.synthesize("Második hívás.", VoiceSettings(voice_model_path=model_path))

        assert _FakePiperVoice.load_call_count == 1

    def test_synthesis_error_wrapped(
        self, fake_piper_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        model_path = tmp_path / "hang.onnx"
        model_path.write_bytes(b"x")

        def _raise(self, *args, **kwargs):
            raise RuntimeError("belső piper hiba")

        monkeypatch.setattr(_FakePiperVoice, "synthesize_wav", _raise)

        tts = PiperTTS()
        with pytest.raises(SynthesisError):
            tts.synthesize("Szia.", VoiceSettings(voice_model_path=model_path))
