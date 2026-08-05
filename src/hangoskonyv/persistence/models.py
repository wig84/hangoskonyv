"""Adatbázis-rekordokat reprezentáló dataclass-ok.

Ezek szándékosan NEM a `core.document.Book`-ot használják — a
`core.document.Book` az EPUB-ból frissen feldolgozott, teljes,
mondatokra bontott dokumentummodell (nagy memóriaigényű, nem
perzisztálandó egyben), míg az itteni `BookRecord` csak a
könyvtár-nézethez és állapotmentéshez szükséges metaadatokat
tárolja.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class BookRecord:
    """Egy könyvtárba felvett könyv adatai."""

    id: int
    content_hash: str
    title: str
    author: str
    source_path: str
    cover_image: bytes | None
    added_at: datetime
    last_played_at: datetime | None


@dataclass(slots=True)
class BookmarkRecord:
    """Egy felhasználó által elhelyezett könyvjelző."""

    id: int
    book_id: int
    chapter_order: int
    position_seconds: float
    note: str | None
    created_at: datetime


@dataclass(slots=True)
class PlaybackStateRecord:
    """Egy könyv legutóbbi lejátszási pozíciója (könyvenként egy sor)."""

    book_id: int
    chapter_order: int
    position_seconds: float
    updated_at: datetime
