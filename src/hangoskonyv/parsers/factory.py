"""Fájlformátum -> parser leképezés.

A `ParserFactory` egyetlen belépési pontot ad a hívó kódnak
(elsősorban a CLI-nek): nem kell tudnia, hogy EPUB, PDF vagy MOBI
fájllal dolgozik-e, csak a fájl elérési útját adja át.

Új formátum támogatása (pl. PDF a 2. fázisban) annyi, hogy a
konkrét `AbstractParser` implementációt regisztráljuk itt — a hívó
kód nem változik.
"""

from __future__ import annotations

from pathlib import Path

from hangoskonyv.core.exceptions import UnsupportedFormatError
from hangoskonyv.parsers.base import AbstractParser
from hangoskonyv.parsers.epub_parser import EpubParser


class ParserFactory:
    """A fájl kiterjesztéséhez tartozó `AbstractParser` példányt adja vissza."""

    def __init__(self, parsers: list[AbstractParser] | None = None) -> None:
        """
        Args:
            parsers: A regisztrált parserek listája. Ha None, az
                alapértelmezett készletet használja (jelenleg csak
                `EpubParser`; a PDF/MOBI/TXT parserek a 2. fázisban
                kerülnek ide).
        """
        self._parsers: list[AbstractParser] = parsers if parsers is not None else [EpubParser()]

    def get_parser(self, path: Path) -> AbstractParser:
        """Az adott fájlhoz illő parsert adja vissza.

        Raises:
            UnsupportedFormatError: Ha egyik regisztrált parser sem
                támogatja a fájl formátumát.
        """
        for parser in self._parsers:
            if parser.supports(path):
                return parser
        raise UnsupportedFormatError(
            f"Nincs regisztrált parser ehhez a formátumhoz: {path.suffix} ({path})"
        )
