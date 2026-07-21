"""Unit tesztek a nlp.normalizer modulhoz."""

from __future__ import annotations

from hangoskonyv.core.enums import TokenType
from hangoskonyv.nlp.normalizer import tokenize_and_normalize


def _find_token(tokens, text_prefix: str):
    for token in tokens:
        if token.text.startswith(text_prefix):
            return token
    raise AssertionError(f"Nincs ilyen kezdetű token: {text_prefix!r} ebben: {tokens}")


class TestNumberTokens:
    def test_simple_number_gets_hint(self) -> None:
        tokens = tokenize_and_normalize("25 alma volt.")
        number_token = _find_token(tokens, "25")
        assert number_token.type is TokenType.NUMBER
        assert number_token.pronunciation_hint == "huszonöt"

    def test_percent_number(self) -> None:
        tokens = tokenize_and_normalize("50%-uk beleegyezett.")
        percent_token = _find_token(tokens, "50%")
        assert percent_token.type is TokenType.NUMBER
        assert percent_token.pronunciation_hint == "ötven százalék"


class TestDateTokens:
    def test_full_date_becomes_single_token(self) -> None:
        tokens = tokenize_and_normalize("2024. március 15. volt a dátum.")
        date_token = _find_token(tokens, "2024")
        assert date_token.type is TokenType.DATE
        assert date_token.pronunciation_hint == "kétezerhuszonnégy március tizenötödike"


class TestRomanNumeralTokens:
    def test_roman_numeral_with_period_gets_ordinal_hint(self) -> None:
        tokens = tokenize_and_normalize("A III. fejezetben történt.")
        roman_token = _find_token(tokens, "III.")
        assert roman_token.type is TokenType.ROMAN_NUMERAL
        assert roman_token.pronunciation_hint == "harmadik"


class TestAbbreviationTokens:
    def test_known_abbreviation_gets_expansion(self) -> None:
        tokens = tokenize_and_normalize("Elmentem pl. Budapestre.")
        abbrev_token = _find_token(tokens, "pl.")
        assert abbrev_token.type is TokenType.ABBREVIATION
        assert abbrev_token.pronunciation_hint == "például"

    def test_abbreviation_without_expansion_has_none_hint(self) -> None:
        tokens = tokenize_and_normalize("16. sz. óta létezik.")
        abbrev_token = _find_token(tokens, "sz.")
        assert abbrev_token.type is TokenType.ABBREVIATION
        assert abbrev_token.pronunciation_hint is None


class TestUnitTokens:
    def test_unit_after_number_is_recognized(self) -> None:
        tokens = tokenize_and_normalize("50 km-re volt.")
        unit_token = _find_token(tokens, "km")
        assert unit_token.type is TokenType.UNIT
        assert unit_token.pronunciation_hint == "kilométer"

    def test_unit_only_recognized_after_number(self) -> None:
        # Az "m" önmagában, szám nélkül nem mértékegység-token.
        tokens = tokenize_and_normalize("Az m betűvel kezdődik.")
        m_token = _find_token(tokens, "m")
        assert m_token.type is not TokenType.UNIT


class TestPlainWords:
    def test_ordinary_word_has_no_hint(self) -> None:
        tokens = tokenize_and_normalize("Szia világ.")
        word_token = _find_token(tokens, "Szia")
        assert word_token.type is TokenType.WORD
        assert word_token.pronunciation_hint is None
