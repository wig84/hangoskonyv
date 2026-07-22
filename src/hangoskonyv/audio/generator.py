"""Fejezetenkénti hanggenerálás, gyorsítótárazással összekötve.

Ez a modul köti össze a TTS réteget (`AbstractTTS`) a
`CacheManager`-rel: minden fejezethez kiszámolja a cache-kulcsot, és
csak akkor hívja meg a (viszonylag lassú, erőforrás-igényes) TTS
szintézist, ha a gyorsítótárban még nincs érvényes bejegyzés hozzá.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from hangoskonyv.audio.cache_manager import CacheManager
from hangoskonyv.core.document import Book, Chapter
from hangoskonyv.tts.base import AbstractTTS, VoiceSettings

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, Chapter, str], None]
"""(fejezet_index, összes_fejezet_száma, fejezet, státusz) -> None.

A státusz egyike: "cache_hit" (a fejezet már gyorsítótárazva volt),
"generating" (TTS szintézis indul) vagy "done" (a fejezet kész,
akár cache-ből, akár frissen generálva).
"""


class AudioGenerator:
    """Egy `Book` fejezeteihez generál (vagy cache-ből ad vissza) hangfájlokat."""

    def __init__(
        self, tts: AbstractTTS, cache_manager: CacheManager, voice: VoiceSettings
    ) -> None:
        self._tts = tts
        self._cache_manager = cache_manager
        self._voice = voice

    @property
    def _engine_name(self) -> str:
        return type(self._tts).__name__

    def generate_chapter(self, book: Book, chapter: Chapter) -> Path:
        """Egy fejezethez tartozó hangfájl elérési útját adja vissza.

        Ha van érvényes gyorsítótár-bejegyzés (a fejezet szövege és a
        hang beállításai nem változtak), azt adja vissza TTS-hívás
        nélkül. Egyébként meghívja a TTS motort, és a friss eredményt
        gyorsítótárba menti.
        """
        cache_key = self._cache_manager.compute_cache_key(chapter, self._voice, self._engine_name)
        cached_path = self._cache_manager.get_cached_path(book, chapter, cache_key)
        if cached_path is not None:
            logger.info("Gyorsítótárból: '%s' (%s)", chapter.title, cached_path.name)
            return cached_path

        logger.info("Hanggenerálás: '%s' (%d szó)", chapter.title, chapter.word_count)
        audio = self._tts.synthesize(chapter.text, self._voice)
        return self._cache_manager.store(book, chapter, cache_key, audio)

    def generate_book(
        self, book: Book, *, progress_callback: ProgressCallback | None = None
    ) -> list[Path]:
        """A könyv minden fejezetéhez legenerálja (vagy cache-ből adja
        vissza) a hangfájlt, `chapters_sorted()` sorrendben.

        Args:
            book: A feldolgozandó könyv — a fejezetek szövege legyen
                már NLP-előfeldolgozáson átesve (lásd `nlp.Preprocessor`),
                különben a `Chapter.text` a parser naiv, egy-mondatos
                bekezdéseit adná vissza.
            progress_callback: Opcionális visszahívás minden fejezet
                előtt/után — a GUI-integrációhoz (3. fázis) készült elő,
                ez az iteráció még nem hívja fel máshonnan, de az
                interfész már készen áll rá, hogy a GUI réteg ne kelljen
                módosítania ezt a modult.

        Returns:
            A legenerált (vagy gyorsítótárból vett) hangfájlok elérési
            útjainak listája, a fejezetek sorrendjében.
        """
        chapters = book.chapters_sorted()
        total = len(chapters)
        paths: list[Path] = []

        for index, chapter in enumerate(chapters):
            cache_key = self._cache_manager.compute_cache_key(
                chapter, self._voice, self._engine_name
            )
            is_cached = self._cache_manager.get_cached_path(book, chapter, cache_key) is not None

            if progress_callback:
                status = "cache_hit" if is_cached else "generating"
                progress_callback(index, total, chapter, status)

            path = self.generate_chapter(book, chapter)
            paths.append(path)

            if progress_callback:
                progress_callback(index, total, chapter, "done")

        logger.info("Hanggenerálás kész: '%s' — %d fejezet.", book.title, total)
        return paths
