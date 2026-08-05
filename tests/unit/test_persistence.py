"""Unit tesztek a persistence csomaghoz.

Minden teszt `:memory:` SQLite adatbázist használ (kivéve a
fájl-alapú tárolást kifejezetten ellenőrző eseteket), hogy gyors és
egymástól izolált maradjon.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hangoskonyv.core.document import Book, Chapter
from hangoskonyv.persistence.database import Database
from hangoskonyv.persistence.repositories import (
    BookmarkRepository,
    BookRepository,
    PlaybackStateRepository,
)


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    yield database
    database.close()


def _make_book(content_hash: str = "hash-1", title: str = "Teszt könyv") -> Book:
    return Book(
        title=title,
        author="Teszt szerző",
        chapters=[Chapter(title="Első fejezet", order=0)],
        content_hash=content_hash,
    )


class TestDatabase:
    def test_creates_parent_directories_for_file_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nested" / "sub" / "library.db"
        database = Database(db_path)
        assert db_path.exists()
        database.close()

    def test_reopening_existing_db_preserves_data(self, tmp_path: Path) -> None:
        db_path = tmp_path / "library.db"
        db1 = Database(db_path)
        BookRepository(db1).add_or_get(_make_book(), source_path=Path("x.epub"))
        db1.close()

        db2 = Database(db_path)
        record = BookRepository(db2).get_by_content_hash("hash-1")
        assert record is not None
        db2.close()

    def test_context_manager_closes_connection(self) -> None:
        with Database(":memory:") as database:
            assert database is not None


class TestBookRepository:
    def test_add_or_get_creates_new_book(self, db: Database) -> None:
        repo = BookRepository(db)
        record = repo.add_or_get(_make_book(), source_path=Path("konyv.epub"))

        assert record.id is not None
        assert record.title == "Teszt könyv"
        assert record.last_played_at is None

    def test_add_or_get_is_idempotent_on_content_hash(self, db: Database) -> None:
        repo = BookRepository(db)
        book = _make_book()

        record1 = repo.add_or_get(book, source_path=Path("konyv.epub"))
        record2 = repo.add_or_get(book, source_path=Path("konyv.epub"))

        assert record1.id == record2.id
        assert len(repo.list_all()) == 1

    def test_get_by_content_hash_returns_none_when_missing(self, db: Database) -> None:
        repo = BookRepository(db)
        assert repo.get_by_content_hash("nincs-ilyen") is None

    def test_cover_image_blob_roundtrip(self, db: Database) -> None:
        repo = BookRepository(db)
        book = _make_book()
        book.cover_image = b"\xff\xd8\xff\xe0-fake-jpeg-bytes"

        record = repo.add_or_get(book, source_path=Path("konyv.epub"))
        fetched = repo.get_by_id(record.id)

        assert fetched.cover_image == b"\xff\xd8\xff\xe0-fake-jpeg-bytes"

    def test_update_last_played(self, db: Database) -> None:
        repo = BookRepository(db)
        record = repo.add_or_get(_make_book(), source_path=Path("konyv.epub"))
        assert record.last_played_at is None

        repo.update_last_played(record.id)

        assert repo.get_by_id(record.id).last_played_at is not None

    def test_list_all_returns_all_books(self, db: Database) -> None:
        repo = BookRepository(db)
        repo.add_or_get(_make_book("h1", "Első könyv"), source_path=Path("a.epub"))
        repo.add_or_get(_make_book("h2", "Második könyv"), source_path=Path("b.epub"))

        assert len(repo.list_all()) == 2

    def test_delete_removes_book(self, db: Database) -> None:
        repo = BookRepository(db)
        record = repo.add_or_get(_make_book(), source_path=Path("konyv.epub"))

        repo.delete(record.id)

        assert repo.get_by_id(record.id) is None


class TestBookmarkRepository:
    def test_add_and_list_for_book(self, db: Database) -> None:
        book_record = BookRepository(db).add_or_get(_make_book(), source_path=Path("x.epub"))
        bookmark_repo = BookmarkRepository(db)

        bookmark_repo.add(book_record.id, chapter_order=1, position_seconds=30.0, note="jegyzet")
        bookmark_repo.add(book_record.id, chapter_order=0, position_seconds=5.0)

        bookmarks = bookmark_repo.list_for_book(book_record.id)
        assert len(bookmarks) == 2
        # chapter_order szerint rendezve
        assert bookmarks[0].chapter_order == 0
        assert bookmarks[1].note == "jegyzet"

    def test_delete_bookmark(self, db: Database) -> None:
        book_record = BookRepository(db).add_or_get(_make_book(), source_path=Path("x.epub"))
        bookmark_repo = BookmarkRepository(db)
        bookmark = bookmark_repo.add(book_record.id, chapter_order=0, position_seconds=1.0)

        bookmark_repo.delete(bookmark.id)

        assert bookmark_repo.list_for_book(book_record.id) == []

    def test_bookmarks_deleted_when_book_deleted(self, db: Database) -> None:
        book_repo = BookRepository(db)
        book_record = book_repo.add_or_get(_make_book(), source_path=Path("x.epub"))
        bookmark_repo = BookmarkRepository(db)
        bookmark_repo.add(book_record.id, chapter_order=0, position_seconds=1.0)

        book_repo.delete(book_record.id)

        assert bookmark_repo.list_for_book(book_record.id) == []


class TestPlaybackStateRepository:
    def test_get_returns_none_when_no_state(self, db: Database) -> None:
        book_record = BookRepository(db).add_or_get(_make_book(), source_path=Path("x.epub"))
        assert PlaybackStateRepository(db).get(book_record.id) is None

    def test_save_and_get(self, db: Database) -> None:
        book_record = BookRepository(db).add_or_get(_make_book(), source_path=Path("x.epub"))
        state_repo = PlaybackStateRepository(db)

        state_repo.save(book_record.id, chapter_order=2, position_seconds=88.5)
        state = state_repo.get(book_record.id)

        assert state.chapter_order == 2
        assert state.position_seconds == 88.5

    def test_save_overwrites_previous_state(self, db: Database) -> None:
        book_record = BookRepository(db).add_or_get(_make_book(), source_path=Path("x.epub"))
        state_repo = PlaybackStateRepository(db)

        state_repo.save(book_record.id, chapter_order=1, position_seconds=10.0)
        state_repo.save(book_record.id, chapter_order=4, position_seconds=200.0)

        state = state_repo.get(book_record.id)
        assert state.chapter_order == 4
        assert state.position_seconds == 200.0

    def test_state_deleted_when_book_deleted(self, db: Database) -> None:
        book_repo = BookRepository(db)
        book_record = book_repo.add_or_get(_make_book(), source_path=Path("x.epub"))
        state_repo = PlaybackStateRepository(db)
        state_repo.save(book_record.id, chapter_order=0, position_seconds=1.0)

        book_repo.delete(book_record.id)

        assert state_repo.get(book_record.id) is None
