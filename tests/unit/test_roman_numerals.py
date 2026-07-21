"""Unit tesztek a nlp.roman_numerals modulhoz."""

from __future__ import annotations

import pytest

from hangoskonyv.nlp.roman_numerals import is_roman_numeral, roman_to_int


class TestIsRomanNumeral:
    @pytest.mark.parametrize("text", ["I", "IV", "IX", "XX", "XIX", "MCMXCIX", "III"])
    def test_valid_roman_numerals(self, text: str) -> None:
        assert is_roman_numeral(text) is True

    @pytest.mark.parametrize("text", ["", "iv", "ABC", "IIII1", "VX", "hello"])
    def test_invalid_roman_numerals(self, text: str) -> None:
        assert is_roman_numeral(text) is False


class TestRomanToInt:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("I", 1),
            ("III", 3),
            ("IV", 4),
            ("IX", 9),
            ("XX", 20),
            ("XIX", 19),
            ("L", 50),
            ("C", 100),
            ("MCMXCIX", 1999),
        ],
    )
    def test_known_values(self, text: str, expected: int) -> None:
        assert roman_to_int(text) == expected

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            roman_to_int("nem római szám")
