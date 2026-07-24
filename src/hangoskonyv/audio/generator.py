"""Fejezetenkénti hanggenerálás, gyorsítótárazással és szünet-
finomhangolással összekötve.

Ez a modul köti össze a TTS réteget (`AbstractTTS`) a
`CacheManager`-rel és a `ssml.fallback` szegmentálással: minden
fejezetet mondat-/vessző-szintű darabokra bontunk (lásd
`ssml.fallback.build_chapter_segments`), mindegyiket külön
szintetizáljuk, majd a darabok közé a megfelelő hosszúságú csendet
illesztve fűzzük össze egyetlen fejezetnyi hanggá. Ez teszi lehetővé,
hogy a mondatvégi/vessző utáni szünetek pontosan szabályozhatók
legyenek, függetlenül attól, mit "gondol" erről maga a TTS motor —
és hogy a hármaspontot ne szó szerint olvassa fel a rendszer.

Csak akkor hívunk TTS szintézist egy fejezethez, ha a gyorsítótárban
még nincs érvényes bejegyzés hozzá (a cache-kulcs a szegmentálási
logika verzióját is figyelembe veszi — lásd `_engine_name` —, tehát
ha ez a logika változik, a régi cache automatikusan érvénytelenné
válik anélkül, hogy kézzel törölni kellene).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from hangoskonyv.audio.audio_utils import concatenate_audio_segments, generate_silence
from hangoskonyv.audio.cache_manager import CacheManager
from hangoskonyv.core.document import Book, Chapter
from hangoskonyv.ssml.fallback import build_chapter_segments
from hangoskonyv.tts.base import AbstractTTS, AudioSegment, VoiceSettings

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, Chapter, str], None]
"""(fejezet_index, összes_fejezet_száma, fejezet, státusz) -> None.

A státusz egyike: "cache_hit" (a fejezet már gyorsítótárazva volt),
"generating" (TTS szintézis indul) vagy "done" (a fejezet kész,
akár cache-ből, akár frissen generálva).
"""

_SEGMENTATION_VERSION = "segmented-v1"
"""A szegmentálási/szünet-logika verziója. Ha ez a logika érdemben
változik (pl. más szünet-hosszak, más darabolási szabály), ezt a
stringet kell megváltoztatni — ez automatikusan érvényteleníti a
korábbi gyorsítótár-bejegyzéseket, mert bekerül a cache-kulcsba."""


class AudioGenerator:
    """Egy `Book` fejezeteihez generál (vagy cache-ből ad vissza) hangfájlokat."""

    def __init__(
        self,
        tts: AbstractTTS,
        cache_manager: CacheManager,
        voice: VoiceSettings,
        *,
        split_on_commas: bool = False,
    ) -> None:
        """
        Args:
            tts: A használandó TTS motor.
            cache_manager: A gyorsítótár-kezelő.
            voice: A hang beállításai.
            split_on_commas: Lásd `ssml.fallback.build_chapter_segments`
                — finomabb szünet-vezérlés, de jelentősen több
                TTS-hívás (egy hosszú könyvnél akár tízszeres
                nagyságrendű generálási idő-növekedést is jelenthet).
                Alapból False.
        """
        self._tts = tts
        self._cache_manager = cache_manager
        self._voice = voice
        self._split_on_commas = split_on_commas

    @property
    def _engine_name(self) -> str:
        comma_suffix = "commas" if self._split_on_commas else "nocommas"
        return f"{type(self._tts).__name__}:{_SEGMENTATION_VERSION}:{comma_suffix}"

    def _synthesize_chapter(self, chapter: Chapter) -> AudioSegment:
        """A fejezetet szegmensekre bontva, külön-külön szintetizálja,
        majd a megfelelő szünetekkel összefűzi egyetlen hanggá."""
        speech_segments = build_chapter_segments(chapter, split_on_commas=self._split_on_commas)
        if not speech_segments:
            raise ValueError(f"A fejezetnek nincs felolvasható szövege: {chapter.title!r}")

        audio_pieces: list[AudioSegment] = []
        for speech_segment in speech_segments:
            audio = self._tts.synthesize(speech_segment.text, self._voice)
            audio_pieces.append(audio)
            if speech_segment.pause_after_ms > 0:
                audio_pieces.append(
                    generate_silence(
                        speech_segment.pause_after_ms,
                        sample_rate=audio.sample_rate,
                        sample_width=audio.sample_width,
                        channels=audio.channels,
                    )
                )

        return concatenate_audio_segments(audio_pieces)

    def generate_chapter(self, book: Book, chapter: Chapter) -> Path:
        """Egy fejezethez tartozó hangfájl elérési útját adja vissza.

        Ha van érvényes gyorsítótár-bejegyzés (a fejezet szövege és a
        hang beállításai nem változtak), azt adja vissza TTS-hívás
        nélkül. Egyébként szegmensenként szintetizál (lásd
        `_synthesize_chapter`), és a friss eredményt gyorsítótárba menti.
        """
        cache_key = self._cache_manager.compute_cache_key(chapter, self._voice, self._engine_name)
        cached_path = self._cache_manager.get_cached_path(book, chapter, cache_key)
        if cached_path is not None:
            logger.info("Gyorsítótárból: '%s' (%s)", chapter.title, cached_path.name)
            return cached_path

        logger.info("Hanggenerálás: '%s' (%d szó)", chapter.title, chapter.word_count)
        audio = self._synthesize_chapter(chapter)
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
