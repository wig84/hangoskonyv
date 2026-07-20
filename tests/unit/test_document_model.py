"""Unit tesztek a core.document modellhez."""

from __future__ import annotations

import pytest

from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence, Token
from hangoskonyv.core.enums import SentenceType, TokenType


class TestSentence:
    def test_word_count(self) -> None:
        sentence = Sentence(raw_text="Ez egy teszt mondat.")
        assert sentence.word_count == 4

    def test_default_type_is_statement(self) -> None:
        sentence = Sentence(raw_text="Alapértelmezett mondat.")
        assert sentence.type is SentenceType.STATEMENT

    def test_empty_raw_text_raises(self) -> None:
        with pytest.raises(ValueError, match="nem lehet üres"):
            Sentence(raw_text="   ")

    def test_dialogue_sentence_with_speaker(self) -> None:
        sentence = Sentence(
            raw_text="– Szia! – mondta Éva.",
            type=SentenceType.DIALOGUE,
            speaker="Éva",
        )
        assert sentence.speaker == "Éva"
        assert sentence.type is SentenceType.DIALOGUE

    def test_tokens_default_empty(self) -> None:
        sentence = Sentence(raw_text="Üres tokenlista alapból.")
        assert sentence.tokens == []

    def test_tokens_can_be_populated(self) -> None:
        tokens = [
            Token(text="Húsz", type=TokenType.NUMBER, pronunciation_hint="húsz"),
            Token(text="kilométer", type=TokenType.UNIT),
        ]
        sentence = Sentence(raw_text="Húsz kilométer.", tokens=tokens)
        assert len(sentence.tokens) == 2
        assert sentence.tokens[0].pronunciation_hint == "húsz"


class TestParagraph:
    def test_text_joins_sentences(self) -> None:
        paragraph = Paragraph(
            sentences=[
                Sentence(raw_text="Első mondat."),
                Sentence(raw_text="Második mondat."),
            ]
        )
        assert paragraph.text == "Első mondat. Második mondat."

    def test_word_count_sums_sentences(self) -> None:
        paragraph = Paragraph(
            sentences=[
                Sentence(raw_text="Egy kettő három."),
                Sentence(raw_text="Négy öt."),
            ]
        )
        assert paragraph.word_count == 5

    def test_empty_paragraph(self) -> None:
        paragraph = Paragraph()
        assert paragraph.text == ""
        assert paragraph.word_count == 0

    def test_dialogue_block_flag(self) -> None:
        paragraph = Paragraph(is_dialogue_block=True)
        assert paragraph.is_dialogue_block is True


class TestChapter:
    def test_text_joins_paragraphs_with_blank_line(self) -> None:
        chapter = Chapter(
            title="Első fejezet",
            paragraphs=[
                Paragraph(sentences=[Sentence(raw_text="Bekezdés egy.")]),
                Paragraph(sentences=[Sentence(raw_text="Bekezdés kettő.")]),
            ],
        )
        assert chapter.text == "Bekezdés egy.\n\nBekezdés kettő."

    def test_negative_order_raises(self) -> None:
        with pytest.raises(ValueError, match="nem lehet negatív"):
            Chapter(title="Hibás fejezet", order=-1)

    def test_is_empty_true_for_no_paragraphs(self) -> None:
        chapter = Chapter(title="Üres fejezet")
        assert chapter.is_empty is True

    def test_is_empty_false_with_content(self) -> None:
        chapter = Chapter(
            title="Tartalmas fejezet",
            paragraphs=[Paragraph(sentences=[Sentence(raw_text="Van tartalom.")])],
        )
        assert chapter.is_empty is False

    def test_word_count_sums_paragraphs(self) -> None:
        chapter = Chapter(
            title="Fejezet",
            paragraphs=[
                Paragraph(sentences=[Sentence(raw_text="Egy kettő.")]),
                Paragraph(sentences=[Sentence(raw_text="Három négy öt.")]),
            ],
        )
        assert chapter.word_count == 5


class TestBook:
    def test_chapter_count(self) -> None:
        book = Book(
            title="Gömbvillám",
            author="Cixin Liu",
            chapters=[
                Chapter(title="Előszó", order=0),
                Chapter(title="Egyetem", order=1),
            ],
        )
        assert book.chapter_count == 2

    def test_total_word_count(self) -> None:
        book = Book(
            title="Teszt könyv",
            author="Teszt Szerző",
            chapters=[
                Chapter(
                    title="Fejezet 1",
                    paragraphs=[Paragraph(sentences=[Sentence(raw_text="Egy kettő három.")])],
                ),
                Chapter(
                    title="Fejezet 2",
                    paragraphs=[Paragraph(sentences=[Sentence(raw_text="Négy öt.")])],
                ),
            ],
        )
        assert book.total_word_count == 5

    def test_default_language_is_hungarian(self) -> None:
        book = Book(title="Könyv", author="Szerző")
        assert book.language == "hu"

    def test_chapters_sorted_by_order(self) -> None:
        book = Book(
            title="Rendezetlen könyv",
            author="Szerző",
            chapters=[
                Chapter(title="Harmadik", order=2),
                Chapter(title="Első", order=0),
                Chapter(title="Második", order=1),
            ],
        )
        sorted_titles = [chapter.title for chapter in book.chapters_sorted()]
        assert sorted_titles == ["Első", "Második", "Harmadik"]

    def test_empty_book_has_zero_totals(self) -> None:
        book = Book(title="Üres könyv", author="Senki")
        assert book.chapter_count == 0
        assert book.total_word_count == 0
