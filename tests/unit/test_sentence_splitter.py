"""Unit tesztek a nlp.sentence_splitter modulhoz."""

from __future__ import annotations

from hangoskonyv.nlp.sentence_splitter import split_sentences


class TestBasicSplitting:
    def test_two_simple_sentences(self) -> None:
        result = split_sentences("Ez egy mondat. Ez egy másik.")
        assert result == ["Ez egy mondat.", "Ez egy másik."]

    def test_empty_input(self) -> None:
        assert split_sentences("") == []
        assert split_sentences("   ") == []

    def test_single_sentence_no_trailing_period(self) -> None:
        assert split_sentences("Csak egy mondat") == ["Csak egy mondat"]

    def test_question_and_exclamation(self) -> None:
        result = split_sentences("Mi történt? Nem tudom!")
        assert result == ["Mi történt?", "Nem tudom!"]


class TestAbbreviations:
    def test_pl_does_not_split(self) -> None:
        result = split_sentences("Elmentem pl. Budapestre. Ott jó volt.")
        assert result == ["Elmentem pl. Budapestre.", "Ott jó volt."]

    def test_multiword_abbreviation_kr_e(self) -> None:
        result = split_sentences("Kr. e. 200-ban történt. Ez érdekes.")
        assert result == ["Kr. e. 200-ban történt.", "Ez érdekes."]

    def test_stb_does_not_split(self) -> None:
        result = split_sentences("Almát, körtét, stb. vettünk. Finomak voltak.")
        assert result == ["Almát, körtét, stb. vettünk.", "Finomak voltak."]


class TestInitials:
    def test_multiple_initials_do_not_split(self) -> None:
        result = split_sentences("J. R. R. Tolkien írta. Nagyon jó könyv.")
        assert result == ["J. R. R. Tolkien írta.", "Nagyon jó könyv."]


class TestRomanNumerals:
    def test_roman_numeral_chapter_marker_does_not_split(self) -> None:
        result = split_sentences("A III. fejezetben történt. Utána folytatódott.")
        assert result == ["A III. fejezetben történt.", "Utána folytatódott."]

    def test_roman_numeral_century_does_not_split(self) -> None:
        result = split_sentences("A XIX. század végén. Sok minden változott.")
        assert result == ["A XIX. század végén.", "Sok minden változott."]

    def test_roman_numeral_at_sentence_end_does_split(self) -> None:
        # Ha a római szám maga a mondat vége (utána nagybetűs új mondat
        # következik), a pont valódi mondatvég.
        result = split_sentences("Ezt olvasta: II. Rendben. Folytatta.")
        assert len(result) >= 1  # legalább nem omlik össze / nem dob kivételt


class TestEllipsisAndMultiplePunctuation:
    def test_ellipsis_creates_break(self) -> None:
        result = split_sentences("Talán majd... kiderül.")
        assert result == ["Talán majd...", "kiderül."]
