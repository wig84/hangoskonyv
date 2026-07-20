"""A hangoskonyv projekt saját exception hierarchiája.

Minden modul a saját, specifikus kivétel-osztályát a megfelelő
alaposztályból származtatja, hogy a hívó kód (pl. a CLI vagy a
GUI worker) egységesen, de szükség esetén finomhangolva tudja
kezelni a hibákat.

Hierarchia:

    HangoskonyvError
        ParserError
            UnsupportedFormatError
            CorruptFileError
        NlpError
            SentenceSplitError
            NormalizationError
        TTSError
            TTSEngineNotAvailableError
            SynthesisError
        CacheError
            CacheWriteError
            CacheCorruptError
        ConfigError
            ConfigValidationError
        PersistenceError
        PluginError
            PluginLoadError
"""

from __future__ import annotations


class HangoskonyvError(Exception):
    """A projekt összes egyedi kivételének közös őse.

    A hívó kód ezt elkapva minden, a hangoskonyv csomagból
    származó (azaz nem véletlen, alacsony szintű Python) hibát
    egységesen tud kezelni.
    """


# --- Parser réteg -----------------------------------------------------


class ParserError(HangoskonyvError):
    """Könyvfájl feldolgozása közben történt hiba."""


class UnsupportedFormatError(ParserError):
    """A megadott fájlformátumhoz nincs regisztrált parser."""


class CorruptFileError(ParserError):
    """A bemeneti fájl sérült vagy nem a várt szerkezetű."""


# --- NLP réteg ----------------------------------------------------------


class NlpError(HangoskonyvError):
    """Szövegfeldolgozás (mondatbontás, normalizálás) közben történt hiba."""


class SentenceSplitError(NlpError):
    """A mondatbontás nem tudott konzisztens eredményt előállítani."""


class NormalizationError(NlpError):
    """Szám/dátum/mértékegység normalizálás közben történt hiba."""


# --- TTS réteg ------------------------------------------------------------


class TTSError(HangoskonyvError):
    """A beszédszintézis (TTS) rétegben történt hiba."""


class TTSEngineNotAvailableError(TTSError):
    """A kért TTS motor nem elérhető (pl. hiányzó modell vagy binary)."""


class SynthesisError(TTSError):
    """A TTS motor a szintézis közben hibát jelzett."""


# --- Audio cache réteg ------------------------------------------------


class CacheError(HangoskonyvError):
    """A generált hangfájlok cache-elésével kapcsolatos hiba."""


class CacheWriteError(CacheError):
    """A cache-be írás nem sikerült (pl. lemez tele, jogosultság)."""


class CacheCorruptError(CacheError):
    """A cache-ben talált fájl sérült vagy olvashatatlan."""


# --- Konfiguráció ---------------------------------------------------------


class ConfigError(HangoskonyvError):
    """Konfiguráció betöltésével/érvényesítésével kapcsolatos hiba."""


class ConfigValidationError(ConfigError):
    """A konfiguráció szintaktikailag helyes, de érvénytelen értéket tartalmaz."""


# --- Perzisztencia (adatbázis) --------------------------------------------


class PersistenceError(HangoskonyvError):
    """Adatbázis-műveletek (könyvjelző, állapotmentés) közben történt hiba."""


# --- Plugin rendszer -----------------------------------------------------


class PluginError(HangoskonyvError):
    """Plugin betöltésével/futtatásával kapcsolatos hiba."""


class PluginLoadError(PluginError):
    """Egy plugin betöltése sikertelen volt."""
