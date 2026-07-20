"""Unit tesztek a core.exceptions hierarchiához.

A cél annak biztosítása, hogy az öröklési lánc a tervezett módon
álljon fel, mert erre támaszkodik a hívó kód (pl. a CLI), amikor
csak a `HangoskonyvError`-t fogja el, hogy egységesen kezelje az
összes projekt-specifikus hibát.
"""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "exception_class",
    [
        ParserError,
        UnsupportedFormatError,
        CorruptFileError,
        NlpError,
        SentenceSplitError,
        NormalizationError,
        TTSError,
        TTSEngineNotAvailableError,
        SynthesisError,
        CacheError,
        CacheWriteError,
        CacheCorruptError,
        ConfigError,
        ConfigValidationError,
        PersistenceError,
        PluginError,
        PluginLoadError,
    ],
)
def test_all_exceptions_derive_from_base(exception_class: type[Exception]) -> None:
    assert issubclass(exception_class, HangoskonyvError)


def test_unsupported_format_derives_from_parser_error() -> None:
    assert issubclass(UnsupportedFormatError, ParserError)


def test_cache_write_error_derives_from_cache_error() -> None:
    assert issubclass(CacheWriteError, CacheError)


def test_tts_engine_not_available_derives_from_tts_error() -> None:
    assert issubclass(TTSEngineNotAvailableError, TTSError)


def test_plugin_load_error_derives_from_plugin_error() -> None:
    assert issubclass(PluginLoadError, PluginError)


def test_catching_base_exception_catches_all_subclasses() -> None:
    with pytest.raises(HangoskonyvError):
        raise UnsupportedFormatError("epub nem ismert kiterjesztés")

    with pytest.raises(HangoskonyvError):
        raise SynthesisError("a Piper motor összeomlott")


def test_exception_message_is_preserved() -> None:
    message = "A fájl sérült: hiányzó content.opf"
    try:
        raise CorruptFileError(message)
    except CorruptFileError as exc:
        assert str(exc) == message
