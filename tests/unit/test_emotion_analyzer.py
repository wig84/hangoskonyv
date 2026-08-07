"""Unit tesztek az ai.emotion_analyzer modulhoz."""

from __future__ import annotations

from hangoskonyv.ai.emotion_analyzer import detect_emotion
from hangoskonyv.core.document import Sentence
from hangoskonyv.core.enums import SentenceType


class TestDetectEmotionByKeyword:
    def test_joy(self) -> None:
        sentence = Sentence(raw_text="Nagyon boldog volt aznap.")
        assert detect_emotion(sentence) == "öröm"

    def test_anger(self) -> None:
        sentence = Sentence(raw_text="Dühösen kiabált vele.")
        assert detect_emotion(sentence) == "harag"

    def test_sadness(self) -> None:
        sentence = Sentence(raw_text="Sírva fakadt a szomorú hírtől.")
        assert detect_emotion(sentence) == "szomorúság"

    def test_fear(self) -> None:
        sentence = Sentence(raw_text="Rettegve nézett körül.")
        assert detect_emotion(sentence) == "félelem"

    def test_surprise(self) -> None:
        sentence = Sentence(
            raw_text="Elképesztő volt a látvány, senki sem számított rá."
        )
        assert detect_emotion(sentence) == "meglepetés"

    def test_inflected_form_matches_stem(self) -> None:
        # "dühösen" a "dühös" tő ragozott alakja - a prefix-egyezésnek
        # el kell kapnia.
        sentence = Sentence(raw_text="Dühösen csapta be az ajtót.")
        assert detect_emotion(sentence) == "harag"


class TestDetectEmotionNeutral:
    def test_neutral_sentence_returns_none(self) -> None:
        sentence = Sentence(raw_text="Ez egy teljesen semleges mondat.")
        assert detect_emotion(sentence) is None

    def test_statement_without_keywords_returns_none(self) -> None:
        sentence = Sentence(raw_text="A ház az utca végén állt.")
        assert detect_emotion(sentence) is None


class TestDetectEmotionFallbackSignals:
    def test_exclamation_without_keyword_gets_generic_label(self) -> None:
        sentence = Sentence(raw_text="Micsoda nap volt ez!", type=SentenceType.EXCLAMATION)
        assert detect_emotion(sentence) == "izgatottság"

    def test_all_caps_word_gets_generic_label(self) -> None:
        sentence = Sentence(raw_text="Ez SOHA nem fog megtörténni.")
        assert detect_emotion(sentence) == "izgatottság"

    def test_statement_without_caps_or_exclamation_and_no_keyword_is_none(self) -> None:
        sentence = Sentence(raw_text="Ez egy sima, nyugodt kijelentés.", type=SentenceType.STATEMENT)
        assert detect_emotion(sentence) is None


class TestDetectEmotionPriority:
    def test_keyword_match_takes_priority_over_exclamation_fallback(self) -> None:
        # Van szótári találat ÉS felkiáltás is - a konkrét érzelem
        # (nem a generikus "izgatottság") kell, hogy győzzön.
        sentence = Sentence(raw_text="Milyen boldog vagyok!", type=SentenceType.EXCLAMATION)
        assert detect_emotion(sentence) == "öröm"

    def test_higher_scoring_category_wins_on_multiple_matches(self) -> None:
        # Két "öröm" szótő, egy "harag" szótő -> öröm nyer pontszámban.
        sentence = Sentence(raw_text="Boldogan, örömmel mosolygott, bár kicsit ideges is volt.")
        assert detect_emotion(sentence) == "öröm"
