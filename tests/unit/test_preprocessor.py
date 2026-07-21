"""Tesztek a Preprocessor-hoz.

Szintetikus `Book`-on ellenőrzi az egyes viselkedéseket, majd a
valódi Gömbvillám EPUB-on végigfuttatva átfogó, integrációs jellegű
ellenőrzést végez (a teljes parser -> NLP lánc együttes helyességét).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence
from hangoskonyv.core.enums import SentenceType
from hangoskonyv.nlp.preprocessor import Preprocessor
from hangoskonyv.parsers.epub_parser import EpubParser

FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "sample_books" / "Cixin_Liu_-_Gömbvillám.epub"
)


class TestPreprocessorOnSyntheticBook:
    def test_splits_naive_paragraph_into_multiple_sentences(self) -> None:
        paragraph = Paragraph(
            sentences=[Sentence(raw_text="Ez az első mondat. Ez a második mondat.")]
        )
        chapter = Chapter(title="Teszt", paragraphs=[paragraph])
        book = Book(title="Teszt könyv", author="Teszt szerző", chapters=[chapter])

        Preprocessor().process_book(book)

        assert len(paragraph.sentences) == 2
        assert paragraph.sentences[0].raw_text == "Ez az első mondat."
        assert paragraph.sentences[1].raw_text == "Ez a második mondat."

    def test_dialogue_paragraph_flag_is_set(self) -> None:
        paragraph = Paragraph(sentences=[Sentence(raw_text="– Szia! – mondta Éva.")])
        chapter = Chapter(title="Teszt", paragraphs=[paragraph])
        book = Book(title="Teszt könyv", author="Teszt szerző", chapters=[chapter])

        Preprocessor().process_book(book)

        # A "!" mondatvégnek számít, ezért ez a bekezdés két mondatra bomlik:
        # "– Szia!" és "– mondta Éva." — a beszélő a tag-mondathoz kötődik.
        assert paragraph.is_dialogue_block is True
        assert all(s.type is SentenceType.DIALOGUE for s in paragraph.sentences)
        speakers = [s.speaker for s in paragraph.sentences if s.speaker]
        assert speakers == ["Éva"]

    def test_tokens_are_populated(self) -> None:
        paragraph = Paragraph(sentences=[Sentence(raw_text="25 alma volt az asztalon.")])
        chapter = Chapter(title="Teszt", paragraphs=[paragraph])
        book = Book(title="Teszt könyv", author="Teszt szerző", chapters=[chapter])

        Preprocessor().process_book(book)

        assert len(paragraph.sentences[0].tokens) > 0

    def test_returns_same_book_instance(self) -> None:
        book = Book(title="Teszt", author="Szerző")
        result = Preprocessor().process_book(book)
        assert result is book


@pytest.fixture(scope="module")
def processed_real_book():
    book = EpubParser().parse(FIXTURE_PATH)
    return Preprocessor().process_book(book)


class TestPreprocessorOnRealBook:
    def test_sentence_count_exceeds_paragraph_count(self, processed_real_book) -> None:
        total_paragraphs = sum(len(ch.paragraphs) for ch in processed_real_book.chapters)
        total_sentences = sum(
            len(p.sentences) for ch in processed_real_book.chapters for p in ch.paragraphs
        )
        # Egy bekezdés jellemzően több mondatból áll, tehát a mondatok
        # száma jelentősen meghaladja a bekezdésekét.
        assert total_sentences > total_paragraphs

    def test_dialogue_sentences_are_detected(self, processed_real_book) -> None:
        dialogue_count = sum(
            1
            for ch in processed_real_book.chapters
            for p in ch.paragraphs
            for s in p.sentences
            if s.type is SentenceType.DIALOGUE
        )
        assert dialogue_count > 0

    def test_some_speakers_are_identified(self, processed_real_book) -> None:
        speakers = {
            s.speaker
            for ch in processed_real_book.chapters
            for p in ch.paragraphs
            for s in p.sentences
            if s.speaker
        }
        assert len(speakers) > 0

    def test_all_sentences_have_tokens(self, processed_real_book) -> None:
        for chapter in processed_real_book.chapters:
            for paragraph in chapter.paragraphs:
                for sentence in paragraph.sentences:
                    assert len(sentence.tokens) > 0

    def test_no_sentence_is_empty(self, processed_real_book) -> None:
        for chapter in processed_real_book.chapters:
            for paragraph in chapter.paragraphs:
                for sentence in paragraph.sentences:
                    assert sentence.raw_text.strip() != ""
