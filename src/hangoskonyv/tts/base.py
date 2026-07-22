"""A TTS (beszédszintézis) réteg közös interfésze és adatstruktúrái.

Minden konkrét TTS motor (PiperTTS, később XTTSTTS, ElevenLabsTTS)
ugyanezt az `AbstractTTS` interfészt implementálja, hogy a hívó kód
(az `audio` modul generátora) motor-függetlenül dolgozhasson, és a
motor cseréje egyetlen konfigurációs érték módosítása legyen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class VoiceSettings:
    """Egy adott felolvasáshoz használt hang beállításai."""

    voice_model_path: Path
    """A hangmodell fájl elérési útja (motor-specifikus formátum,
    Pipernél pl. egy `.onnx` fájl)."""

    speed: float = 1.0
    """Felolvasási sebesség szorzó (1.0 = normál, 2.0 = kétszer olyan
    gyors). A konkrét motor-implementáció felelőssége ezt a saját
    paraméterezésére (pl. Pipernél a fordított `length_scale`-re)
    átfordítani."""

    volume: float = 1.0
    """Hangerő szorzó (1.0 = normál)."""

    speaker_id: int | None = None
    """Több beszélős (multi-speaker) hangmodelleknél a kiválasztott
    beszélő azonosítója. None esetén a modell alapértelmezett
    beszélőjét használjuk."""


@dataclass(slots=True)
class AudioSegment:
    """Egy legenerált hangrészlet, a lejátszáshoz/mentéshez szükséges
    metaadatokkal."""

    audio_bytes: bytes
    """A teljes hangfájl bájtjai (a formátum-specifikus fejléccel együtt,
    pl. egy komplett WAV fájl tartalma)."""

    sample_rate: int
    sample_width: int = 2
    """Mintánkénti bájtok száma (2 = 16 bites PCM)."""
    channels: int = 1
    format: str = "wav"

    def save(self, path: Path) -> None:
        """A hangrészletet a megadott elérési útra menti."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.audio_bytes)


class AbstractTTS(ABC):
    """Egy konkrét TTS motor (beszédszintetizátor) közös interfésze."""

    @property
    @abstractmethod
    def supports_ssml(self) -> bool:
        """Igaz, ha a motor natívan SSML bemenetet is elfogad.

        Ha False, az `ssml` modul fallback módja (nyers szöveg,
        szünet-időzítéssel közelítve) kerül alkalmazásra a motor
        elé — ezt egy későbbi iteráció köti majd össze.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Igaz, ha a motor ténylegesen használható (a szükséges
        csomag/bináris telepítve van). Nem ellenőrzi az adott
        hangmodell meglétét — az a `synthesize` hívás felelőssége.
        """

    @abstractmethod
    def synthesize(self, content: str, voice: VoiceSettings) -> AudioSegment:
        """A megadott szöveget (vagy — ha `supports_ssml` igaz — SSML-t)
        hanggá alakítja.

        Args:
            content: A felolvasandó szöveg (vagy SSML dokumentum).
            voice: A használandó hang beállításai.

        Returns:
            A legenerált hangrészlet.

        Raises:
            TTSEngineNotAvailableError: Ha a motor vagy a hangmodell
                nem elérhető.
            SynthesisError: Ha maga a szintézis hibával állt le.
        """
