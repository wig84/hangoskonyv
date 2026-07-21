"""Mondatbontás magyar nyelvi szabályok figyelembevételével.

A naiv "pont = mondatvég" szabály tévedne a rövidítéseknél
("pl.", "Kr. e." stb.), a kezdőbetűknél ("J. R. R. Tolkien") és a
sorszámozott listáknál/címeknél ("III. fejezet"). Ez a modul ezeket
a kivételeket kezeli.

A `!`, `?` és a hármaspont (`…` vagy `...`) mindig mondatvégnek
számít — ezekhez a magyar nyelvben nincs rövidítés-kollízió.
"""

from __future__ import annotations

import re

from hangoskonyv.nlp.hungarian_rules import ABBREVIATIONS
from hangoskonyv.nlp.roman_numerals import is_roman_numeral

_SENTENCE_END_PUNCTUATION = re.compile(r"[.!?…]+")
_TRAILING_WORD = re.compile(r"(\S+)$")


def _is_abbreviation_word(word: str) -> bool:
    return word.lower() in ABBREVIATIONS


def _is_real_sentence_boundary(text: str, start: int, end: int) -> bool:
    """Eldönti, hogy a `text[start:end]` írásjel-csoport valódi
    mondatvég-e, vagy egy rövidítés/kezdőbetű/sorszám része."""
    punctuation = text[start:end]

    if "!" in punctuation or "?" in punctuation or "…" in punctuation:
        return True
    if len(punctuation) >= 2:
        # Több egymást követő pont (pl. "...") -> hármaspont, mondatvég.
        return True

    preceding = text[:start]
    match = _TRAILING_WORD.search(preceding)
    if not match:
        return True
    word = match.group(1)

    if _is_abbreviation_word(word + "."):
        return False
    if len(word) == 1 and word.isupper():
        return False  # kezdőbetű, pl. "J."
    if is_roman_numeral(word):
        following = text[end:]
        stripped_following = following.lstrip()
        if stripped_following and stripped_following[0].islower():
            return False  # pl. "III. fejezet" — a pont itt sorszám-jelölő

    return True


def split_sentences(text: str) -> list[str]:
    """A megadott (bekezdésnyi) szöveget mondatokra bontja.

    Args:
        text: A feldolgozandó, egy bekezdésnyi nyers szöveg.

    Returns:
        A felismert mondatok listája, a mondatvégi írásjellel együtt,
        felesleges szóközök nélkül. Üres bemenetre üres listát ad.
    """
    text = text.strip()
    if not text:
        return []

    boundaries: list[int] = []
    for match in _SENTENCE_END_PUNCTUATION.finditer(text):
        if _is_real_sentence_boundary(text, match.start(), match.end()):
            boundaries.append(match.end())

    sentences: list[str] = []
    start = 0
    for end in boundaries:
        candidate = text[start:end].strip()
        if candidate:
            sentences.append(candidate)
        start = end

    remainder = text[start:].strip()
    if remainder:
        sentences.append(remainder)

    return sentences
