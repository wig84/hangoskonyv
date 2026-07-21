"""Szövegrészek tokenekké bontása, kiejtési javaslatokkal ellátva.

Ez a modul a `Sentence.raw_text`-ből épít `Token` listát, minden
tokenhez (ahol releváns) kiejtési javaslatot (`pronunciation_hint`)
rendelve: számok, dátumok, római számok, mértékegységek, ismert
rövidítések.

Feldolgozási sorrend:

1. Dátum-minták felismerése és kiemelése ELŐSZÖR (mielőtt az
   általános tokenizáló szétszedné a "2024. március 15." mintát
   külön szám- és szótokenekre) — enélkül a nap száma (15) tévesen
   sima számként, nem sorszámnévként kapna kiejtést.
2. A megmaradt szövegrészek általános tokenizálása: szó, szám,
   írásjel bontásra.
3. Minden token osztályozása (szám, római szám, rövidítés, egyéb).

Ismert egyszerűsítések:

- A mondatvégi írásjel (pl. az utolsó pont) a szó-reguláris kifejezés
  miatt gyakran az utolsó szó tokenjéhez tapad (pl. `"volt."` egyetlen
  WORD tokenként, nem `"volt"` + `"."` külön). Ez a kiejtést nem
  rontja el, csak azt jelenti, hogy a mondatvégi írásjel nem mindig
  jelenik meg önálló PUNCTUATION tokenként.
- A kötőjellel kapcsolt toldalékok (pl. "km-re", "50%-uk") nem
  kerülnek nyelvtanilag szétbontásra a mértékegység/szám és a
  toldalék között — a toldalék önálló, kiejtési javaslat nélküli
  WORD tokenként jelenik meg.
"""

from __future__ import annotations

import re

from hangoskonyv.core.document import Token
from hangoskonyv.core.enums import TokenType
from hangoskonyv.nlp.hungarian_rules import (
    ABBREVIATIONS,
    ABBREVIATION_EXPANSIONS,
    MONTH_NAMES,
    UNIT_ABBREVIATIONS,
)
from hangoskonyv.nlp.numbers import DAY_OF_MONTH_WORDS, cardinal_to_words, ordinal_to_words
from hangoskonyv.nlp.roman_numerals import is_roman_numeral, roman_to_int

_MONTH_NAME_TO_NUMBER = {name: number for number, name in MONTH_NAMES.items()}
_MONTH_PATTERN = "|".join(name.capitalize() for name in MONTH_NAMES.values())

_DATE_PATTERN = re.compile(
    rf"(?P<year>\d{{3,4}})\.\s+(?P<month>{_MONTH_PATTERN})\s+(?P<day>\d{{1,2}})\.",
    re.IGNORECASE,
)

_TOKEN_PATTERN = re.compile(
    r"\d+(?:[ .]\d{3})*%?"          # számok, opcionális ezres tagolással és % jellel
    r"|[A-Za-zÀ-ÖØ-öø-ÿ]+\.?"       # szavak, opcionális záró ponttal (rövidítés/kezdőbetű)
    r"|[^\sA-Za-zÀ-ÖØ-öø-ÿ\d]"      # egyéb, nem szóköz karakter (írásjel)
)


def _make_date_token(match: re.Match[str]) -> Token:
    year = int(match.group("year"))
    month_number = _MONTH_NAME_TO_NUMBER[match.group("month").lower()]
    day = int(match.group("day"))
    month_name = MONTH_NAMES[month_number]
    day_word = DAY_OF_MONTH_WORDS.get(day)

    if day_word is None:
        # Érvénytelen napszám (pl. elgépelés a forrásszövegben, "35.") —
        # inkább a nyers szöveget hagyjuk meg, mint hogy kivétellel álljunk le.
        return Token(text=match.group(0), type=TokenType.DATE, pronunciation_hint=None)

    hint = f"{cardinal_to_words(year)} {month_name} {day_word}"
    return Token(text=match.group(0), type=TokenType.DATE, pronunciation_hint=hint)


def _classify_word_token(raw: str, *, preceded_by_number: bool) -> Token:
    stripped = raw.rstrip(".")
    has_period = raw.endswith(".") and not stripped.endswith(".")

    if raw.lower() in ABBREVIATIONS:
        return Token(
            text=raw,
            type=TokenType.ABBREVIATION,
            pronunciation_hint=ABBREVIATION_EXPANSIONS.get(raw.lower()),
        )

    if preceded_by_number and raw.lower() in UNIT_ABBREVIATIONS:
        return Token(text=raw, type=TokenType.UNIT, pronunciation_hint=UNIT_ABBREVIATIONS[raw.lower()])

    if is_roman_numeral(stripped):
        value = roman_to_int(stripped)
        # Római szám pont nélkül ritkán fordul elő önmagában (pl. "X"
        # mint önálló szó/betűjel) — csak a pontos (has_period) formát
        # alakítjuk sorszámnévvé, hogy elkerüljük a hamis pozitívokat.
        if has_period:
            return Token(
                text=raw, type=TokenType.ROMAN_NUMERAL, pronunciation_hint=ordinal_to_words(value)
            )

    return Token(text=raw, type=TokenType.WORD)


def tokenize_and_normalize(text: str) -> list[Token]:
    """A megadott szöveget `Token`-ök listájává alakítja, kiejtési
    javaslatokkal ellátva a felismert számokat, dátumokat, római
    számokat, mértékegységeket és ismert rövidítéseket.

    Args:
        text: A tokenizálandó (jellemzően egy `Sentence.raw_text`) szöveg.

    Returns:
        A felismert tokenek listája, a szövegbeli sorrendjükben.
    """
    tokens: list[Token] = []
    position = 0

    for date_match in _DATE_PATTERN.finditer(text):
        if date_match.start() > position:
            tokens.extend(_tokenize_plain(text[position : date_match.start()]))
        tokens.append(_make_date_token(date_match))
        position = date_match.end()

    if position < len(text):
        tokens.extend(_tokenize_plain(text[position:]))

    return tokens


def _tokenize_plain(text: str) -> list[Token]:
    tokens: list[Token] = []
    previous_was_number = False

    for raw_match in _TOKEN_PATTERN.finditer(text):
        raw = raw_match.group(0)

        if raw[0].isdigit():
            is_percent = raw.endswith("%")
            digits = raw.rstrip("%").replace(" ", "").replace(".", "")
            value = int(digits) if digits else 0
            hint = cardinal_to_words(value)
            if is_percent:
                hint += " " + UNIT_ABBREVIATIONS["%"]
            tokens.append(Token(text=raw, type=TokenType.NUMBER, pronunciation_hint=hint))
            previous_was_number = True
            continue

        if raw.isalpha() or (raw.endswith(".") and raw[:-1].isalpha()):
            tokens.append(_classify_word_token(raw, preceded_by_number=previous_was_number))
            previous_was_number = False
            continue

        tokens.append(Token(text=raw, type=TokenType.PUNCTUATION))
        previous_was_number = False

    return tokens
