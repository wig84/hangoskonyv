"""Unit tesztek a nlp.numbers modulhoz."""

from __future__ import annotations

import pytest

from hangoskonyv.nlp.numbers import DAY_OF_MONTH_WORDS, cardinal_to_words, ordinal_to_words


class TestCardinalToWords:
    @pytest.mark.parametrize(
        "number,expected",
        [
            (0, "nulla"),
            (1, "egy"),
            (2, "kettő"),
            (9, "kilenc"),
            (10, "tíz"),
            (11, "tizenegy"),
            (19, "tizenkilenc"),
            (20, "húsz"),
            (21, "huszonegy"),
            (30, "harminc"),
            (99, "kilencvenkilenc"),
            (100, "száz"),
            (101, "százegy"),
            (200, "kétszáz"),
            (999, "kilencszázkilencvenkilenc"),
            (1000, "ezer"),
            (1001, "ezeregy"),
            (2000, "kétezer"),
            (12000, "tizenkétezer"),
            (1923, "ezerkilencszázhuszonhárom"),
            (2024, "kétezerhuszonnégy"),
            (1000000, "millió"),
            (2000000, "kétmillió"),
            (1000000000, "milliárd"),
        ],
    )
    def test_known_values(self, number: int, expected: str) -> None:
        assert cardinal_to_words(number) == expected

    def test_negative_number(self) -> None:
        assert cardinal_to_words(-5) == "mínusz öt"


class TestOrdinalToWords:
    @pytest.mark.parametrize(
        "number,expected",
        [
            (1, "első"),
            (2, "második"),
            (3, "harmadik"),
            (10, "tizedik"),
            (11, "tizenegyedik"),
            (12, "tizenkettedik"),
            (20, "huszadik"),
            (21, "huszonegyedik"),
            (22, "huszonkettedik"),
            (23, "huszonharmadik"),
            (30, "harmincadik"),
            (31, "harmincegyedik"),
            (100, "századik"),
            (1000, "ezredik"),
        ],
    )
    def test_known_values(self, number: int, expected: str) -> None:
        assert ordinal_to_words(number) == expected

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            ordinal_to_words(-1)


class TestDayOfMonthWords:
    def test_all_31_days_present(self) -> None:
        assert set(DAY_OF_MONTH_WORDS.keys()) == set(range(1, 32))

    def test_first_day_is_irregular(self) -> None:
        # "elseje", nem a szabályos "első" + toldalék minta.
        assert DAY_OF_MONTH_WORDS[1] == "elseje"

    def test_fifteenth_day(self) -> None:
        assert DAY_OF_MONTH_WORDS[15] == "tizenötödike"
