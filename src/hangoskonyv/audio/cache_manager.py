"""Hash alapú, fejezetenkénti hangfájl-gyorsítótár.

A cél: ha egy fejezet szövege, a használt TTS motor vagy a hang
beállításai (modell, sebesség, hangerő, beszélő) nem változtak a
legutóbbi generálás óta, ne generáljuk újra a hangot — ez a
leghosszabb (és API/erőforrás-szempontból legköltségesebb) lépés
a teljes pipeline-ban.

Gyorsítótár-szerkezet a lemezen:

    <cache_root>/<book.content_hash>/<fejezet_sorszám>_<cache_kulcs>.wav

A könyvenkénti almappa azt is jelenti, hogy egy megváltozott EPUB
(más `content_hash`) automatikusan egy teljesen új gyorsítótár-térben
kezdi a generálást — a régi bejegyzések érintetlenül megmaradnak,
amíg valaki explicit nem törli őket (`invalidate_book`).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from hangoskonyv.core.document import Book, Chapter
from hangoskonyv.core.exceptions import CacheWriteError
from hangoskonyv.tts.base import AudioSegment, VoiceSettings
from hangoskonyv.utils.hashing import hash_text

logger = logging.getLogger(__name__)


class CacheManager:
    """Fejezetenkénti, hash-kulcs alapú hangfájl-gyorsítótár."""

    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root

    def compute_cache_key(self, chapter: Chapter, voice: VoiceSettings, engine_name: str) -> str:
        """Egy fejezethez tartozó cache-kulcsot számol.

        A kulcs a fejezet teljes szövegéből, a TTS motor nevéből és a
        hang minden releváns beállításából áll össze — ha bármelyik
        változik, a kulcs is megváltozik, ami automatikus
        cache-invalidálást eredményez (a régi bejegyzés egyszerűen
        nem lesz többé elérhető az új kulccsal).
        """
        payload = "|".join(
            [
                chapter.text,
                engine_name,
                str(voice.voice_model_path),
                str(voice.speed),
                str(voice.volume),
                str(voice.speaker_id),
            ]
        )
        return hash_text(payload)

    def _chapter_path(self, book: Book, chapter: Chapter, cache_key: str) -> Path:
        book_dir = self._cache_root / book.content_hash
        return book_dir / f"{chapter.order:03d}_{cache_key}.wav"

    def get_cached_path(self, book: Book, chapter: Chapter, cache_key: str) -> Path | None:
        """A gyorsítótárazott hangfájl elérési útja, ha létezik, egyébként None."""
        path = self._chapter_path(book, chapter, cache_key)
        return path if path.exists() else None

    def store(
        self, book: Book, chapter: Chapter, cache_key: str, audio: AudioSegment
    ) -> Path:
        """A megadott hangot a gyorsítótárba menti, és visszaadja az elérési utat.

        Raises:
            CacheWriteError: Ha a mentés lemezhiba miatt sikertelen.
        """
        path = self._chapter_path(book, chapter, cache_key)
        try:
            audio.save(path)
        except OSError as exc:
            raise CacheWriteError(f"Nem sikerült a gyorsítótárba menteni: {path}") from exc
        logger.debug("Gyorsítótárba mentve: %s", path)
        return path

    def invalidate_book(self, book: Book) -> None:
        """Egy könyv teljes gyorsítótár-tartalmát törli."""
        book_dir = self._cache_root / book.content_hash
        if book_dir.exists():
            shutil.rmtree(book_dir)
            logger.info("Gyorsítótár törölve: %s", book_dir)
