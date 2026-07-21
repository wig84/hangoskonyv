"""Unit tesztek a nlp.dialogue_detector modulhoz."""

from __future__ import annotations

from hangoskonyv.core.enums import SentenceType
from hangoskonyv.nlp.dialogue_detector import detect_sentence_type, extract_speaker


class TestDetectSentenceType:
    def test_statement(self) -> None:
        assert detect_sentence_type("Ez egy kijelentő mondat.") is SentenceType.STATEMENT

    def test_question(self) -> None:
        assert detect_sentence_type("Hogy vagy ma?") is SentenceType.QUESTION

    def test_exclamation(self) -> None:
        assert detect_sentence_type("Micsoda nap volt ez!") is SentenceType.EXCLAMATION

    def test_dialogue_with_en_dash(self) -> None:
        assert detect_sentence_type("– Szia! – mondta Éva.") is SentenceType.DIALOGUE

    def test_dialogue_with_hyphen(self) -> None:
        assert detect_sentence_type("- Ez is párbeszéd.") is SentenceType.DIALOGUE

    def test_quote_with_hungarian_quotes(self) -> None:
        assert detect_sentence_type("„Ez egy idézet.”") is SentenceType.QUOTE

    def test_empty_string_is_statement(self) -> None:
        assert detect_sentence_type("") is SentenceType.STATEMENT

    def test_dialogue_takes_priority_over_question(self) -> None:
        # A párbeszéd-jelleg elsőbbséget élvez, de a nyers szöveg
        # (raw_text) megőrzi a kérdőjelet az SSML-generáló számára.
        assert detect_sentence_type("– Hogy vagy?") is SentenceType.DIALOGUE


class TestExtractSpeaker:
    def test_single_name_after_mondta(self) -> None:
        assert extract_speaker("– Szia! – mondta Éva.") == "Éva"

    def test_two_word_name(self) -> None:
        assert extract_speaker("– Nankingban – mondta Csao Jü Vang bácsinak.") == "Csao Jü"

    def test_kérdezte_verb(self) -> None:
        assert extract_speaker("– Miért? – kérdezte Péter.") == "Péter"

    def test_no_speaker_pattern_returns_none(self) -> None:
        assert extract_speaker("Ez egy sima mondat beszéd-ige nélkül.") is None

    def test_vágta_rá_verb(self) -> None:
        assert extract_speaker("– Soha! – vágta rá Csao Jü.") == "Csao Jü"
