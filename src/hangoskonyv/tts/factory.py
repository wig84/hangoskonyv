"""TTS motor név -> `AbstractTTS` implementáció leképezés.

Ugyanaz a minta, mint a `parsers.ParserFactory`-nál: a hívó kód
(a CLI, majd később a GUI) csak egy motor-nevet (pl. a
`settings.toml`-ból beolvasva) ad meg, nem kell tudnia a konkrét
osztályról.
"""

from __future__ import annotations

from hangoskonyv.core.exceptions import ConfigValidationError
from hangoskonyv.tts.base import AbstractTTS
from hangoskonyv.tts.piper_tts import PiperTTS

_ENGINES: dict[str, type[AbstractTTS]] = {
    "piper": PiperTTS,
    # "xtts": XTTSTTS,          # 2. fázisban
    # "elevenlabs": ElevenLabsTTS,  # 2. fázisban
}


class TTSFactory:
    """A megadott motor-névhez tartozó `AbstractTTS` példányt adja vissza."""

    def get_engine(self, name: str) -> AbstractTTS:
        """
        Raises:
            ConfigValidationError: Ha `name` nem egy regisztrált motor.
        """
        engine_class = _ENGINES.get(name.lower())
        if engine_class is None:
            available = ", ".join(sorted(_ENGINES))
            raise ConfigValidationError(
                f"Ismeretlen TTS motor: {name!r}. Elérhető motorok: {available}"
            )
        return engine_class()
