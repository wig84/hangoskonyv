"""Unit tesztek az audio.cache_manager modulhoz."""

from __future__ import annotations

from pathlib import Path

from hangoskonyv.audio.cache_manager import CacheManager
from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence
from hangoskonyv.tts.base import AudioSegment, VoiceSettings


def _book_with_chapter(text: str = "Ez a fejezet szövege.") -> tuple[Book, Chapter]:
    chapter = Chapter(
        title="Első fejezet",
        paragraphs=[Paragraph(sentences=[Sentence(raw_text=text)])],
        order=0,
    )
    book = Book(
        title="Teszt könyv",
        author="Teszt szerző",
        chapters=[chapter],
        content_hash="fake-book-hash-123",
    )
    return book, chapter


def _voice(tmp_path: Path, speed: float = 1.0) -> VoiceSettings:
    return VoiceSettings(voice_model_path=tmp_path / "hang.onnx", speed=speed)


class TestComputeCacheKey:
    def test_deterministic_for_same_inputs(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        _, chapter = _book_with_chapter()
        voice = _voice(tmp_path)

        key1 = cache.compute_cache_key(chapter, voice, "FakeTTS")
        key2 = cache.compute_cache_key(chapter, voice, "FakeTTS")
        assert key1 == key2

    def test_changes_with_chapter_text(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        _, chapter1 = _book_with_chapter("Első verzió.")
        _, chapter2 = _book_with_chapter("Módosított verzió.")
        voice = _voice(tmp_path)

        key1 = cache.compute_cache_key(chapter1, voice, "FakeTTS")
        key2 = cache.compute_cache_key(chapter2, voice, "FakeTTS")
        assert key1 != key2

    def test_changes_with_voice_speed(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        _, chapter = _book_with_chapter()

        key1 = cache.compute_cache_key(chapter, _voice(tmp_path, speed=1.0), "FakeTTS")
        key2 = cache.compute_cache_key(chapter, _voice(tmp_path, speed=1.5), "FakeTTS")
        assert key1 != key2

    def test_changes_with_engine_name(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        _, chapter = _book_with_chapter()
        voice = _voice(tmp_path)

        key1 = cache.compute_cache_key(chapter, voice, "PiperTTS")
        key2 = cache.compute_cache_key(chapter, voice, "XTTSTTS")
        assert key1 != key2


class TestGetCachedPath:
    def test_none_when_not_cached(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        book, chapter = _book_with_chapter()
        voice = _voice(tmp_path)
        key = cache.compute_cache_key(chapter, voice, "FakeTTS")

        assert cache.get_cached_path(book, chapter, key) is None

    def test_returns_path_after_store(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        book, chapter = _book_with_chapter()
        voice = _voice(tmp_path)
        key = cache.compute_cache_key(chapter, voice, "FakeTTS")
        audio = AudioSegment(audio_bytes=b"RIFF....WAVEfake", sample_rate=16000)

        stored_path = cache.store(book, chapter, key, audio)

        assert stored_path.exists()
        assert cache.get_cached_path(book, chapter, key) == stored_path

    def test_stored_content_matches(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        book, chapter = _book_with_chapter()
        voice = _voice(tmp_path)
        key = cache.compute_cache_key(chapter, voice, "FakeTTS")
        audio = AudioSegment(audio_bytes=b"pontosan-ez-a-tartalom", sample_rate=16000)

        stored_path = cache.store(book, chapter, key, audio)

        assert stored_path.read_bytes() == b"pontosan-ez-a-tartalom"


class TestInvalidateBook:
    def test_removes_all_cached_chapters(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        book, chapter = _book_with_chapter()
        voice = _voice(tmp_path)
        key = cache.compute_cache_key(chapter, voice, "FakeTTS")
        audio = AudioSegment(audio_bytes=b"x", sample_rate=16000)
        stored_path = cache.store(book, chapter, key, audio)
        assert stored_path.exists()

        cache.invalidate_book(book)

        assert not stored_path.exists()
        assert cache.get_cached_path(book, chapter, key) is None

    def test_invalidating_nonexistent_book_does_not_raise(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_root=tmp_path / "cache")
        book, _ = _book_with_chapter()
        cache.invalidate_book(book)  # nem szabad kivételt dobnia
