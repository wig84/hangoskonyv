"""Repository osztályok az adatbázis-táblákhoz.

A hívó kód (a jövőbeli GUI, illetve a CLI) sosem ír SQL-t közvetlenül
— mindig ezeken a repository-kon keresztül olvas/ír. Ez teszi
lehetővé, hogy az alatta lévő tárolási mechanizmus (jelenleg stdlib
`sqlite3`) szükség esetén lecserélhető legyen anélkül, hogy a hívó
kódot módosítani kellene.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hangoskonyv.core.document import Book
from hangoskonyv.persistence.database import Database
from hangoskonyv.persistence.models import BookmarkRecord, BookRecord, PlaybackStateRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class BookRepository:
    """A `books` tábla CRUD műveletei."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add_or_get(self, book: Book, source_path: Path) -> BookRecord:
        """Felveszi a könyvet a könyvtárba, ha még nincs benne (a
        `content_hash` alapján azonosítva); ha már szerepel, a
        meglévő rekordot adja vissza új sor létrehozása nélkül."""
        existing = self.get_by_content_hash(book.content_hash)
        if existing is not None:
            return existing

        added_at = _now_iso()
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO books
                    (content_hash, title, author, source_path, cover_image, added_at, last_played_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    book.content_hash,
                    book.title,
                    book.author,
                    str(source_path),
                    book.cover_image,
                    added_at,
                ),
            )
            new_id = cur.lastrowid

        return BookRecord(
            id=new_id,
            content_hash=book.content_hash,
            title=book.title,
            author=book.author,
            source_path=str(source_path),
            cover_image=book.cover_image,
            added_at=_parse_dt(added_at),
            last_played_at=None,
        )

    def get_by_id(self, book_id: int) -> BookRecord | None:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def get_by_content_hash(self, content_hash: str) -> BookRecord | None:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM books WHERE content_hash = ?", (content_hash,))
            row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def list_all(self) -> list[BookRecord]:
        """Az összes könyvtárbeli könyv, a legutóbb hallgatott elöl
        (a még sosem hallgatottak a hozzáadás sorrendjében, a végén)."""
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT * FROM books ORDER BY last_played_at IS NULL, last_played_at DESC, added_at DESC"
            )
            rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def update_last_played(self, book_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE books SET last_played_at = ? WHERE id = ?", (_now_iso(), book_id)
            )

    def delete(self, book_id: int) -> None:
        """A könyvet és a hozzá tartozó könyvjelzőket/állapotot is törli
        (a `ON DELETE CASCADE` miatt)."""
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))

    @staticmethod
    def _row_to_record(row) -> BookRecord:
        return BookRecord(
            id=row["id"],
            content_hash=row["content_hash"],
            title=row["title"],
            author=row["author"],
            source_path=row["source_path"],
            cover_image=row["cover_image"],
            added_at=_parse_dt(row["added_at"]),
            last_played_at=_parse_dt(row["last_played_at"]),
        )


class BookmarkRepository:
    """A `bookmarks` tábla CRUD műveletei."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add(
        self, book_id: int, chapter_order: int, position_seconds: float, note: str | None = None
    ) -> BookmarkRecord:
        created_at = _now_iso()
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookmarks (book_id, chapter_order, position_seconds, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (book_id, chapter_order, position_seconds, note, created_at),
            )
            new_id = cur.lastrowid

        return BookmarkRecord(
            id=new_id,
            book_id=book_id,
            chapter_order=chapter_order,
            position_seconds=position_seconds,
            note=note,
            created_at=_parse_dt(created_at),
        )

    def list_for_book(self, book_id: int) -> list[BookmarkRecord]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT * FROM bookmarks WHERE book_id = ? "
                "ORDER BY chapter_order, position_seconds",
                (book_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete(self, bookmark_id: int) -> None:
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))

    @staticmethod
    def _row_to_record(row) -> BookmarkRecord:
        return BookmarkRecord(
            id=row["id"],
            book_id=row["book_id"],
            chapter_order=row["chapter_order"],
            position_seconds=row["position_seconds"],
            note=row["note"],
            created_at=_parse_dt(row["created_at"]),
        )


class PlaybackStateRepository:
    """A `playback_state` tábla műveletei — könyvenként pontosan egy sor,
    ez tárolja, hol tartott a felhasználó legutóbb."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def save(self, book_id: int, chapter_order: int, position_seconds: float) -> PlaybackStateRecord:
        """Elmenti (vagy felülírja) a könyv aktuális lejátszási pozícióját."""
        updated_at = _now_iso()
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO playback_state (book_id, chapter_order, position_seconds, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(book_id) DO UPDATE SET
                    chapter_order = excluded.chapter_order,
                    position_seconds = excluded.position_seconds,
                    updated_at = excluded.updated_at
                """,
                (book_id, chapter_order, position_seconds, updated_at),
            )
        return PlaybackStateRecord(
            book_id=book_id,
            chapter_order=chapter_order,
            position_seconds=position_seconds,
            updated_at=_parse_dt(updated_at),
        )

    def get(self, book_id: int) -> PlaybackStateRecord | None:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM playback_state WHERE book_id = ?", (book_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return PlaybackStateRecord(
            book_id=row["book_id"],
            chapter_order=row["chapter_order"],
            position_seconds=row["position_seconds"],
            updated_at=_parse_dt(row["updated_at"]),
        )
