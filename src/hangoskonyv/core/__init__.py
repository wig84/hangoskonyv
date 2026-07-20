"""Core domain modell: könyvfájl-formátumtól és TTS-motortól független.

Ez a csomag szándékosan nem függ semmilyen külső könyvtártól
(se GUI-tól, se TTS-től, se fájlformátum-parsertől), hogy a projekt
"tiszta magja" maradjon és bármelyik felsőbb réteg tesztelhesse
anélkül, hogy a többi réteget be kellene húznia.
"""

from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence, Token
from hangoskonyv.core.enums import SentenceType, TokenType
from hangoskonyv.core.exceptions import (
    CacheCorruptError,
    CacheError,
    CacheWriteError,
    ConfigError,
    ConfigValidationError,
    CorruptFileError,
    HangoskonyvError,
    NlpError,
    NormalizationError,
    ParserError,
    PersistenceError,
    PluginError,
    PluginLoadError,
    SentenceSplitError,
    SynthesisError,
    TTSEngineNotAvailableError,
    TTSError,
    UnsupportedFormatError,
)

__all__ = [
    # document model
    "Book",
    "Chapter",
    "Paragraph",
    "Sentence",
    "Token",
    # enums
    "SentenceType",
    "TokenType",
    # exceptions
    "HangoskonyvError",
    "ParserError",
    "UnsupportedFormatError",
    "CorruptFileError",
    "NlpError",
    "SentenceSplitError",
    "NormalizationError",
    "TTSError",
    "TTSEngineNotAvailableError",
    "SynthesisError",
    "CacheError",
    "CacheWriteError",
    "CacheCorruptError",
    "ConfigError",
    "ConfigValidationError",
    "PersistenceError",
    "PluginError",
    "PluginLoadError",
]
