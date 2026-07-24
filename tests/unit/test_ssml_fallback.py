"""Unit tesztek az ssml.fallback modulhoz."""

from __future__ import annotations

from hangoskonyv.core.document import Chapter, Paragraph, Sentence
from hangoskonyv.core.enums import SentenceType
from hangoskonyv.ssml.fallback import (
    COMMA_PAUSE_MS,
    ELLIPSIS_PAUSE_MS,
    PARAGRAPH_PAUSE_MS,
    QUESTION_EXCLAMATION_PAUSE_MS,
    SENTENCE_PAUSE_MS,
    build_chapter_segments,
)


def _chapter_from_texts(*texts: str, sentence_type: SentenceType = SentenceType.STATEMENT) -> Chapter:
    sentences = [Sentence(raw_text=t, type=sentence_type) for t in texts]
    return Chapter(title="Teszt", paragraphs=[Paragraph(sentences=sentences)])


class TestEllipsisHandling:
    def test_ellipsis_removed_from_text(self) -> None:
        chapter = _chapter_from_texts("Talán majd...")
        segments = build_chapter_segments(chapter)
        assert len(segments) == 1
        assert "." not in segments[0].text
        assert "…" not in segments[0].text
        assert segments[0].text == "Talán majd"

    def test_ellipsis_gets_long_pause(self) -> None:
        chapter = _chapter_from_texts("Talán majd...")
        segments = build_chapter_segments(chapter)
        assert segments[0].pause_after_ms == ELLIPSIS_PAUSE_MS

    def test_unicode_ellipsis_character_also_handled(self) -> None:
        chapter = _chapter_from_texts("Ez egy elgondolkodó szünet…")
        segments = build_chapter_segments(chapter)
        assert "…" not in segments[0].text


class TestSentenceTypePauses:
    def test_statement_gets_sentence_pause(self) -> None:
        chapter = _chapter_from_texts("Ez egy kijelentés.", sentence_type=SentenceType.STATEMENT)
        segments = build_chapter_segments(chapter)
        assert segments[0].pause_after_ms == SENTENCE_PAUSE_MS

    def test_question_gets_longer_pause(self) -> None:
        chapter = _chapter_from_texts("Hogy vagy?", sentence_type=SentenceType.QUESTION)
        segments = build_chapter_segments(chapter)
        assert segments[0].pause_after_ms == QUESTION_EXCLAMATION_PAUSE_MS

    def test_exclamation_gets_longer_pause(self) -> None:
        chapter = _chapter_from_texts("Micsoda nap!", sentence_type=SentenceType.EXCLAMATION)
        segments = build_chapter_segments(chapter)
        assert segments[0].pause_after_ms == QUESTION_EXCLAMATION_PAUSE_MS


class TestCommaSplittingDisabledByDefault:
    def test_default_does_not_split_on_commas(self) -> None:
        chapter = _chapter_from_texts("Bementem a boltba, vettem kenyeret, és hazamentem.")
        segments = build_chapter_segments(chapter)
        assert len(segments) == 1
        assert segments[0].text == "Bementem a boltba, vettem kenyeret, és hazamentem."

    def test_split_on_commas_when_enabled(self) -> None:
        chapter = _chapter_from_texts("Bementem a boltba, vettem kenyeret, és hazamentem.")
        segments = build_chapter_segments(chapter, split_on_commas=True)
        assert len(segments) == 3
        assert segments[0].pause_after_ms == COMMA_PAUSE_MS
        assert segments[1].pause_after_ms == COMMA_PAUSE_MS
        assert segments[2].pause_after_ms == SENTENCE_PAUSE_MS
        assert segments[0].text.endswith(",")


class TestParagraphBoundaries:
    def test_last_segment_of_paragraph_gets_paragraph_pause(self) -> None:
        chapter = Chapter(
            title="Teszt",
            paragraphs=[
                Paragraph(sentences=[Sentence(raw_text="Első bekezdés.")]),
                Paragraph(sentences=[Sentence(raw_text="Második bekezdés.")]),
            ],
        )
        segments = build_chapter_segments(chapter)
        assert len(segments) == 2
        assert segments[0].pause_after_ms == PARAGRAPH_PAUSE_MS
        assert segments[1].pause_after_ms == PARAGRAPH_PAUSE_MS

    def test_empty_chapter_returns_empty_list(self) -> None:
        chapter = Chapter(title="Üres")
        assert build_chapter_segments(chapter) == []

    def test_empty_paragraph_is_skipped(self) -> None:
        chapter = Chapter(
            title="Teszt",
            paragraphs=[Paragraph(sentences=[]), Paragraph(sentences=[Sentence(raw_text="Van tartalom.")])],
        )
        segments = build_chapter_segments(chapter)
        assert len(segments) == 1
