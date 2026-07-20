"""Unit tesztek a ChapterFilter komponenshez."""

from __future__ import annotations

from hangoskonyv.core.document import Chapter, Paragraph, Sentence
from hangoskonyv.parsers.chapter_filter import ChapterFilter


def _chapter_with_words(title: str, word_count: int, order: int = 0) -> Chapter:
    text = " ".join(f"szó{i}" for i in range(word_count))
    paragraphs = [Paragraph(sentences=[Sentence(raw_text=text)])] if word_count else []
    return Chapter(title=title, paragraphs=paragraphs, order=order)


class TestChapterFilterDefaultTitles:
    def test_skips_known_non_narrative_title(self) -> None:
        chapter_filter = ChapterFilter()
        chapter = _chapter_with_words("Borító", word_count=10)
        assert chapter_filter.should_skip(chapter) is True

    def test_skip_is_case_insensitive(self) -> None:
        chapter_filter = ChapterFilter()
        chapter = _chapter_with_words("COPYRIGHT", word_count=10)
        assert chapter_filter.should_skip(chapter) is True

    def test_skip_is_accent_insensitive(self) -> None:
        chapter_filter = ChapterFilter()
        # "Borito" ékezet nélkül is találjon rá a "Borító" mintára.
        chapter = _chapter_with_words("borito", word_count=10)
        assert chapter_filter.should_skip(chapter) is True

    def test_keeps_real_chapter(self) -> None:
        chapter_filter = ChapterFilter()
        chapter = _chapter_with_words("ELŐSZÓ", word_count=200)
        assert chapter_filter.should_skip(chapter) is False


class TestChapterFilterEmptyChapters:
    def test_skips_empty_chapter(self) -> None:
        chapter_filter = ChapterFilter()
        chapter = Chapter(title="Üres fejezet")
        assert chapter_filter.should_skip(chapter) is True


class TestChapterFilterMinWordCount:
    def test_min_word_count_disabled_by_default(self) -> None:
        chapter_filter = ChapterFilter()
        chapter = _chapter_with_words("Rövid, de valódi fejezet", word_count=3)
        assert chapter_filter.should_skip(chapter) is False

    def test_min_word_count_skips_short_chapter_when_enabled(self) -> None:
        chapter_filter = ChapterFilter(min_word_count=5)
        chapter = _chapter_with_words("ELSŐ RÉSZ", word_count=2)
        assert chapter_filter.should_skip(chapter) is True

    def test_min_word_count_keeps_long_enough_chapter(self) -> None:
        chapter_filter = ChapterFilter(min_word_count=5)
        chapter = _chapter_with_words("Valódi fejezet", word_count=50)
        assert chapter_filter.should_skip(chapter) is False


class TestChapterFilterCustomTitles:
    def test_custom_skip_titles_override_default(self) -> None:
        chapter_filter = ChapterFilter(skip_titles=frozenset({"utószó"}))
        skip_chapter = _chapter_with_words("Utószó", word_count=100)
        keep_chapter = _chapter_with_words("Borító", word_count=100)
        assert chapter_filter.should_skip(skip_chapter) is True
        # Az alapértelmezett lista nem aktív, ha egyéni listát adunk meg.
        assert chapter_filter.should_skip(keep_chapter) is False


class TestFilterChapters:
    def test_filter_chapters_removes_only_matching(self) -> None:
        chapter_filter = ChapterFilter()
        chapters = [
            _chapter_with_words("Borító", word_count=5, order=0),
            _chapter_with_words("ELŐSZÓ", word_count=200, order=1),
            _chapter_with_words("Copyright", word_count=20, order=2),
            _chapter_with_words("EGYETEM", word_count=500, order=3),
        ]
        filtered = chapter_filter.filter_chapters(chapters)
        assert [chapter.title for chapter in filtered] == ["ELŐSZÓ", "EGYETEM"]
