"""Az összes formátum-specifikus parser közös interfésze.

Minden konkrét parser (EpubParser, később PdfParser, MobiParser,
TxtParser) ebből származik. A `ParserFactory` ezen az interfészen
keresztül választja ki és hívja meg a megfelelő implementációt,
így a hívó kódnak (pl. a CLI-nek) soha nem kell formátum-specifikus
elágazást tartalmaznia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from hangoskonyv.core.document import Book


class AbstractParser(ABC):
    """Egy könyvfájl-formátumot `Book` domain modellé alakító parser."""

    @abstractmethod
    def supports(self, path: Path) -> bool:
        """Igazat ad vissza, ha ez a parser képes feldolgozni a fájlt.

        A döntés jellemzően a fájlkiterjesztésen alapul, de
        implementáció-specifikusan finomabb ellenőrzés is végezhető
        (pl. az EPUB esetén a ZIP-konténer és a mimetype fájl
        meglétének ellenőrzése).
        """

    @abstractmethod
    def parse(self, path: Path) -> Book:
        """A megadott fájlt `Book` domain modellé alakítja.

        Args:
            path: A feldolgozandó könyvfájl elérési útja.

        Returns:
            A feltöltött `Book` objektum, fejezetekre és bekezdésekre
            bontva. A mondatszintű bontás ezen a ponton még naiv
            (egy bekezdés = egy `Sentence`); a tényleges, magyar
            nyelvi szabályokat alkalmazó mondatbontást az `nlp`
            modul végzi el egy külön feldolgozási lépésben.

        Raises:
            CorruptFileError: Ha a fájl sérült vagy nem a várt
                szerkezetű.
        """
