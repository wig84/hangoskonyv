"""Enum típusok a hangoskonyv domain modelljéhez.

Ezek a típusok a szövegfeldolgozás (nlp modul) által rögzített
szerkezeti/annotációs információt hordozzák, amit a későbbi
pipeline-elemek (SSML builder, TTS) használnak fel.
"""

from __future__ import annotations

from enum import Enum, auto


class SentenceType(Enum):
    """Egy mondat szerkezeti/pragmatikai típusa.

    Az nlp modul (dialogue_detector, sentence_splitter) tölti ki
    ezt az annotációt a nyers szöveg elemzése alapján. Az SSML
    builder ez alapján dönt a hanglejtésről és a szünetekről.
    """

    STATEMENT = auto()
    """Kijelentő mondat (alapértelmezett)."""

    QUESTION = auto()
    """Kérdő mondat."""

    EXCLAMATION = auto()
    """Felkiáltó mondat."""

    DIALOGUE = auto()
    """Párbeszédben elhangzó, szereplőhöz köthető mondat."""

    QUOTE = auto()
    """Idézet (nem feltétlenül párbeszéd, pl. idézett szöveg)."""


class TokenType(Enum):
    """Egy token (szó/írásjel/speciális egység) típusa.

    Ez teszi lehetővé, hogy a normalizáló (pl. számok, dátumok,
    mértékegységek kiejtett alakra alakítása) célzottan azonosítsa
    a kezelendő tokeneket anélkül, hogy reguláris kifejezésekkel
    újra és újra át kellene fésülnie a nyers szöveget.
    """

    WORD = auto()
    """Hétköznapi szó."""

    NUMBER = auto()
    """Számjegyekkel írt szám (pl. '1923')."""

    ROMAN_NUMERAL = auto()
    """Római számmal írt érték (pl. 'III.')."""

    DATE = auto()
    """Dátum (pl. '2024. március 15.')."""

    UNIT = auto()
    """Mértékegység (pl. 'km', 'kg', '%')."""

    PUNCTUATION = auto()
    """Írásjel."""

    ABBREVIATION = auto()
    """Rövidítés (pl. 'pl.', 'Kr. e.')."""
