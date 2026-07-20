"""Tesztek az EpubParser-hez.

A tesztek egy része a valódi `Gömbvillám.epub` fixtúrán fut
(integrációs jellegű ellenőrzés), más része szintetikus, minimális
EPUB-okat épít memóriában, hogy a hibakezelési ágakat (sérült fájl,
hiányzó container.xml stb.) izoláltan tesztelje.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from hangoskonyv.core.exceptions import CorruptFileError, UnsupportedFormatError
from hangoskonyv.parsers.epub_parser import EpubParser
from hangoskonyv.parsers.factory import ParserFactory
from hangoskonyv.utils.hashing import hash_file

FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "sample_books" / "Cixin_Liu_-_Gömbvillám.epub"
)


@pytest.fixture(scope="module")
def parsed_book():
    """A valódi teszt-EPUB egyszer kerül feldolgozásra a modulon belül,
    mert a feldolgozás (ZIP olvasás, XML parse) nem triviálisan gyors."""
    parser = EpubParser()
    return parser.parse(FIXTURE_PATH)


class TestSupports:
    def test_supports_epub_extension(self) -> None:
        parser = EpubParser()
        assert parser.supports(Path("konyv.epub")) is True

    def test_supports_is_case_insensitive(self) -> None:
        parser = EpubParser()
        assert parser.supports(Path("konyv.EPUB")) is True

    def test_does_not_support_other_extension(self) -> None:
        parser = EpubParser()
        assert parser.supports(Path("konyv.pdf")) is False


class TestParseRealBookMetadata:
    def test_title(self, parsed_book) -> None:
        assert parsed_book.title == "Gömbvillám"

    def test_author(self, parsed_book) -> None:
        assert parsed_book.author == "Cixin Liu"

    def test_language(self, parsed_book) -> None:
        assert parsed_book.language == "hu"

    def test_content_hash_matches_file_hash(self, parsed_book) -> None:
        assert parsed_book.content_hash == hash_file(FIXTURE_PATH)

    def test_cover_image_is_present_and_looks_like_jpeg(self, parsed_book) -> None:
        assert parsed_book.cover_image is not None
        assert parsed_book.cover_image[:2] == b"\xff\xd8"  # JPEG magic bytes


class TestParseRealBookChapterFiltering:
    def test_non_narrative_titles_are_excluded(self, parsed_book) -> None:
        titles = {chapter.title.strip().lower() for chapter in parsed_book.chapters}
        for excluded in ("borító", "copyright"):
            assert excluded not in titles

    def test_part_divider_page_is_excluded(self, parsed_book) -> None:
        # "ELSŐ RÉSZ" önmagában csak egy 2 szavas rész-elválasztó oldal,
        # a min_word_count=5 alapértelmezés miatt ki kell, hogy essen.
        titles = {chapter.title.strip().lower() for chapter in parsed_book.chapters}
        assert "első rész" not in titles

    def test_untitled_spine_files_are_excluded(self, parsed_book) -> None:
        # A címlap/fordítói jegyzet/kiadói ajánló fájloknak nincs
        # toc.ncx bejegyzésük, ezért egyáltalán nem válnak fejezetté.
        assert parsed_book.chapter_count < 43  # kevesebb, mint az összes spine fájl

    def test_real_chapters_are_present(self, parsed_book) -> None:
        titles = [chapter.title for chapter in parsed_book.chapters]
        assert "ELŐSZÓ" in titles
        assert "EGYETEM" in titles

    def test_first_chapter_is_eloszo(self, parsed_book) -> None:
        assert parsed_book.chapters[0].title == "ELŐSZÓ"


class TestParseRealBookOrdering:
    def test_chapters_have_sequential_order(self, parsed_book) -> None:
        orders = [chapter.order for chapter in parsed_book.chapters]
        assert orders == list(range(len(orders)))

    def test_chapters_sorted_matches_chapters(self, parsed_book) -> None:
        # Mivel a parser már sorrendben adja vissza a fejezeteket, a
        # rendezett nézetnek meg kell egyeznie az eredeti listával.
        assert parsed_book.chapters_sorted() == parsed_book.chapters


class TestParseRealBookParagraphContent:
    def test_first_chapter_has_paragraphs(self, parsed_book) -> None:
        eloszo = next(ch for ch in parsed_book.chapters if ch.title == "ELŐSZÓ")
        assert len(eloszo.paragraphs) > 0

    def test_paragraph_text_does_not_duplicate_heading(self, parsed_book) -> None:
        eloszo = next(ch for ch in parsed_book.chapters if ch.title == "ELŐSZÓ")
        first_paragraph_text = eloszo.paragraphs[0].text
        # A <h3>ELŐSZÓ</h3> címsor nem duplikálódhat a bekezdés elején.
        assert not first_paragraph_text.startswith("ELŐSZÓ ELŐSZÓ")
        assert "születésnapom" in first_paragraph_text

    def test_paragraphs_use_naive_single_sentence(self, parsed_book) -> None:
        # 2. iterációban a mondatbontás még nem történik meg: minden
        # bekezdés egyetlen (a teljes bekezdést tartalmazó) Sentence-ből áll.
        eloszo = next(ch for ch in parsed_book.chapters if ch.title == "ELŐSZÓ")
        assert len(eloszo.paragraphs[0].sentences) == 1


class TestParserFactory:
    def test_factory_selects_epub_parser(self) -> None:
        factory = ParserFactory()
        parser = factory.get_parser(Path("konyv.epub"))
        assert isinstance(parser, EpubParser)

    def test_factory_raises_for_unsupported_format(self) -> None:
        factory = ParserFactory()
        with pytest.raises(UnsupportedFormatError):
            factory.get_parser(Path("konyv.mobi"))


class TestEpubParserErrorHandling:
    def test_not_a_zip_file_raises_corrupt_file_error(self, tmp_path: Path) -> None:
        fake_epub = tmp_path / "hamis.epub"
        fake_epub.write_text("ez nem egy zip fájl")

        parser = EpubParser()
        with pytest.raises(CorruptFileError):
            parser.parse(fake_epub)

    def test_missing_mimetype_raises_corrupt_file_error(self, tmp_path: Path) -> None:
        broken_epub = tmp_path / "hianyos.epub"
        with zipfile.ZipFile(broken_epub, "w") as archive:
            archive.writestr("META-INF/container.xml", "<container></container>")

        parser = EpubParser()
        with pytest.raises(CorruptFileError, match="mimetype"):
            parser.parse(broken_epub)

    def test_missing_container_xml_raises_corrupt_file_error(self, tmp_path: Path) -> None:
        broken_epub = tmp_path / "hianyos_container.epub"
        with zipfile.ZipFile(broken_epub, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip")

        parser = EpubParser()
        with pytest.raises(CorruptFileError, match="container.xml"):
            parser.parse(broken_epub)
