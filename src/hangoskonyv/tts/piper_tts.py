"""Piper TTS motor implementációja.

A Piper (https://github.com/OHF-Voice/piper1-gpl) egy gyors, teljesen
offline futó neurális beszédszintetizátor — pontosan ez kell egy
könyv-hosszúságú, fejezetenkénti hanggenerálásához, ahol nem
akarunk hálózati API-hívásokra (és azok költségére/megbízhatóságára)
támaszkodni.

A `piper` Python csomagot (és a hangmodellt) szándékosan lustán,
a metódusokon belül importáljuk/töltjük be, nem a modul tetején.
Ennek két oka van:

1. Így a `PiperTTS` osztály (és minden, ami rá épül) akkor is
   importálható és tesztelhető marad, ha a `piper` csomag éppen
   nincs telepítve (pl. ebben a fejlesztői környezetben, ahol nincs
   hálózat a telepítéshez).
2. A hangmodell (.onnx fájl) betöltése erőforrás-igényes; nem
   akarjuk minden `PiperTTS()` példányosításnál lefuttatni, csak
   amikor ténylegesen szükség van rá — ezért egy egyszerű,
   elérési út szerinti gyorsítótárat (`_voice_cache`) tartunk.

Licenc-megjegyzés: az eredeti (MIT licencű) `rhasspy/piper`
repository 2025 októberében archiválásra került, a fejlesztés azóta
a GPL-3.0 licencű `OHF-Voice/piper1-gpl` fork-ban folytatódik. A
`piper-tts` csomag jelenlegi verziói (1.5.0+) ebből származnak. Ez
nem befolyásolja a hangoskonyv saját licencét, de érdemes figyelembe
venni, ha a projektet terjesztenéd — lásd a README licenc-szekcióját.
"""

from __future__ import annotations

import io
import logging
import wave
from pathlib import Path

from hangoskonyv.core.exceptions import SynthesisError, TTSEngineNotAvailableError
from hangoskonyv.tts.base import AbstractTTS, AudioSegment, VoiceSettings

logger = logging.getLogger(__name__)


class PiperTTS(AbstractTTS):
    """A Piper TTS motort becsomagoló `AbstractTTS` implementáció."""

    def __init__(self) -> None:
        self._voice_cache: dict[Path, object] = {}

    @property
    def supports_ssml(self) -> bool:
        return False

    def is_available(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return True

    def _load_voice(self, model_path: Path):
        if not self.is_available():
            raise TTSEngineNotAvailableError(
                "A 'piper' csomag nincs telepítve. Telepítés: pip install piper-tts"
            )
        if not model_path.exists():
            raise TTSEngineNotAvailableError(f"Nem található Piper hangmodell: {model_path}")

        if model_path not in self._voice_cache:
            from piper import PiperVoice

            logger.info("Piper hangmodell betöltése: %s", model_path)
            self._voice_cache[model_path] = PiperVoice.load(str(model_path))
        return self._voice_cache[model_path]

    def synthesize(self, content: str, voice: VoiceSettings) -> AudioSegment:
        piper_voice = self._load_voice(voice.voice_model_path)

        from piper import SynthesisConfig

        syn_config = SynthesisConfig(
            volume=voice.volume,
            # A Piper `length_scale` paramétere fordítottan arányos a
            # sebességgel: minél kisebb, annál gyorsabb a felolvasás.
            length_scale=1.0 / voice.speed if voice.speed > 0 else 1.0,
            speaker_id=voice.speaker_id,
        )

        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wav_file:
                piper_voice.synthesize_wav(content, wav_file, syn_config=syn_config)
        except Exception as exc:  # a piper belső kivételei nem ismertek előre
            raise SynthesisError(f"A Piper szintézis sikertelen volt: {exc}") from exc

        buffer.seek(0)
        with wave.open(buffer, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()

        return AudioSegment(
            audio_bytes=buffer.getvalue(),
            sample_rate=sample_rate,
            sample_width=sample_width,
            channels=channels,
        )
