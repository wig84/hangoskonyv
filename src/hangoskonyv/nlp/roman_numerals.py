"""Római számok felismerése és arab számmá alakítása.

A magyar szövegekben a római számok tipikusan század-, uralkodó- vagy
rész-/fejezetjelölésre szolgálnak (pl. "XIX. század", "II. Rákóczi
Ferenc", "III. rész"). Ezekhez a `normalizer` modul sorszámnév
kiejtést rendel (lásd `numbers.ordinal_to_words`).
"""

from __future__ import annotations

import re

_ROMAN_PATTERN = re.compile(r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")

_ROMAN_VALUES: list[tuple[str, int]] = [
    ("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
    ("C", 100), ("XC", 90), ("L", 50), ("XL", 40),
    ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1),
]


def is_roman_numeral(text: str) -> bool:
    """Igazat ad vissza, ha `text` egy érvényes, nem üres római szám.

    Csak nagybetűs formát ismer fel (ez a magyar szövegekben
    szabványos használat), és kizárja az üres stringet, hogy a
    reguláris kifejezés ne illeszkedjen véletlenül semmire.
    """
    if not text:
        return False
    return bool(_ROMAN_PATTERN.match(text))


def roman_to_int(text: str) -> int:
    """Egy érvényes római szám arab (egész szám) megfelelőjét adja vissza.

    Raises:
        ValueError: Ha `text` nem érvényes római szám.
    """
    if not is_roman_numeral(text):
        raise ValueError(f"Érvénytelen római szám: {text!r}")

    result = 0
    position = 0
    for symbol, value in _ROMAN_VALUES:
        while text[position : position + len(symbol)] == symbol:
            result += value
            position += len(symbol)
    return result
