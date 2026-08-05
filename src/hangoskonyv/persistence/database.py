"""SQLite kapcsolatkezelés és séma-inicializálás.

Egyfelhasználós, beágyazott adatbázis (a felhasználó gépén futó
desktop/CLI alkalmazáshoz) — nincs szükség kapcsolat-poolra vagy
szerver-kliens architektúrára, a stdlib `sqlite3` pontosan ennyit
ad, amennyi kell.

A séma verziózás nélküli, egyszerű `CREATE TABLE IF NOT EXISTS`
alapú — ha a séma a jövőben bővül, ide kerülnek majd explicit
migrációs lépések (pl. `ALTER TABLE ... ADD COLUMN`, verziószám
ellenőrzéssel).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hangoskonyv.core.exceptions import PersistenceError

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    source_path TEXT NOT NULL,
    cover_image BLOB,
    added_at TEXT NOT NULL,
    last_played_at TEXT
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_order INTEGER NOT NULL,
    position_seconds REAL NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS playback_state (
    book_id INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
    chapter_order INTEGER NOT NULL,
    position_seconds REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_book_id ON bookmarks(book_id);
"""


class Database:
    """SQLite kapcsolat becsomagolása, séma-inicializálással és
    tranzakció-kezeléssel."""

    def __init__(self, db_path: Path | str) -> None:
        """
        Args:
            db_path: Az adatbázisfájl elérési útja. A `:memory:`
                speciális érték (elsősorban teszteléshez) egy
                kizárólag memóriában létező adatbázist hoz létre.
        """
        db_path_str = str(db_path)
        if db_path_str != ":memory:":
            Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(db_path_str, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        try:
            self._connection.executescript(_SCHEMA_SQL)
            self._connection.commit()
        except sqlite3.Error as exc:
            raise PersistenceError(f"Nem sikerült inicializálni az adatbázis sémát: {exc}") from exc

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        """Tranzakciós kontextus: a blokk sikeres lefutása után commit,
        kivétel esetén automatikus rollback.

        Raises:
            PersistenceError: Ha az SQL végrehajtása hibát dob.
        """
        cur = self._connection.cursor()
        try:
            yield cur
            self._connection.commit()
        except sqlite3.Error as exc:
            self._connection.rollback()
            raise PersistenceError(f"Adatbázis-művelet sikertelen: {exc}") from exc
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
