"""Unit tesztek az audio.generator modulhoz."""

from __future__ import annotations

from pathlib import Path

from hangoskonyv.audio.cache_manager import CacheManager
from hangoskonyv.audio.generator import AudioGenerator
from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence
from hangoskonyv.tts.base import VoiceSettings


def _book_with_chapters(count: int = 3) -> Book:
    chapters = [
        Chapter(
            title=f"Fejezet {i}",
            paragraphs=[Paragraph(sentences=[Sentence(raw_text=f"Ez a(z) {i}. fejezet szövege.")])],
            order=i,
        )
        for i in range(count)
    ]
    return Book(
        title="Teszt könyv", author="Teszt szerző", chapters=chapters, content_hash="hash-abc"
    )


def _generator(fake_tts, tmp_path: Path) -> AudioGenerator:
    cache = CacheManager(cache_root=tmp_path / "cache")
    voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")
    return AudioGenerator(tts=fake_tts, cache_manager=cache, voice=voice)


class TestGenerateChapter:
    def test_calls_synthesize_once_for_new_chapter(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(1)
        generator = _generator(fake_tts, tmp_path)

        generator.generate_chapter(book, book.chapters[0])

        assert fake_tts.synthesize_call_count == 1

    def test_second_call_uses_cache_not_synthesize(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(1)
        generator = _generator(fake_tts, tmp_path)

        path1 = generator.generate_chapter(book, book.chapters[0])
        path2 = generator.generate_chapter(book, book.chapters[0])

        assert fake_tts.synthesize_call_count == 1
        assert path1 == path2

    def test_returns_valid_file_path(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(1)
        generator = _generator(fake_tts, tmp_path)

        path = generator.generate_chapter(book, book.chapters[0])

        assert path.exists()
        assert path.suffix == ".wav"

    def test_resynthesizes_when_chapter_text_changes(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(1)
        generator = _generator(fake_tts, tmp_path)
        generator.generate_chapter(book, book.chapters[0])

        # A fejezet szövegét "kézzel" módosítjuk (mintha egy új parser-futás
        # más tartalmat adott volna).
        book.chapters[0].paragraphs[0].sentences[0].raw_text = "Teljesen más szöveg."

        generator.generate_chapter(book, book.chapters[0])

        assert fake_tts.synthesize_call_count == 2


class TestSegmentedSynthesis:
    def test_comma_sentence_produces_multiple_calls_when_enabled(
        self, fake_tts, tmp_path: Path
    ) -> None:
        chapter = Chapter(
            title="Fejezet",
            paragraphs=[
                Paragraph(
                    sentences=[Sentence(raw_text="Bementem a boltba, vettem kenyeret, és hazamentem.")]
                )
            ],
            order=0,
        )
        book = Book(title="Könyv", author="Szerző", chapters=[chapter], content_hash="h1")
        cache = CacheManager(cache_root=tmp_path / "cache")
        voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")
        generator = AudioGenerator(tts=fake_tts, cache_manager=cache, voice=voice, split_on_commas=True)

        generator.generate_chapter(book, chapter)

        assert fake_tts.synthesize_call_count == 3

    def test_comma_sentence_produces_single_call_by_default(
        self, fake_tts, tmp_path: Path
    ) -> None:
        chapter = Chapter(
            title="Fejezet",
            paragraphs=[
                Paragraph(
                    sentences=[Sentence(raw_text="Bementem a boltba, vettem kenyeret, és hazamentem.")]
                )
            ],
            order=0,
        )
        book = Book(title="Könyv", author="Szerző", chapters=[chapter], content_hash="h1")
        cache = CacheManager(cache_root=tmp_path / "cache")
        voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")
        generator = AudioGenerator(tts=fake_tts, cache_manager=cache, voice=voice)

        generator.generate_chapter(book, chapter)

        assert fake_tts.synthesize_call_count == 1

    def test_switching_split_on_commas_invalidates_cache(self, fake_tts, tmp_path: Path) -> None:
        chapter = Chapter(
            title="Fejezet",
            paragraphs=[Paragraph(sentences=[Sentence(raw_text="Egy, kettő, három.")])],
            order=0,
        )
        book = Book(title="Könyv", author="Szerző", chapters=[chapter], content_hash="h1")
        cache = CacheManager(cache_root=tmp_path / "cache")
        voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")

        generator_off = AudioGenerator(tts=fake_tts, cache_manager=cache, voice=voice)
        generator_off.generate_chapter(book, chapter)
        assert fake_tts.synthesize_call_count == 1

        generator_on = AudioGenerator(
            tts=fake_tts, cache_manager=cache, voice=voice, split_on_commas=True
        )
        generator_on.generate_chapter(book, chapter)
        # Nem cache-találat, mert más a szegmentálási konfiguráció -> új hívások.
        assert fake_tts.synthesize_call_count == 4  # 1 (előző) + 3 (új, vesszős)

    def test_ellipsis_text_not_sent_to_tts(self, fake_tts, tmp_path: Path) -> None:
        chapter = Chapter(
            title="Fejezet",
            paragraphs=[Paragraph(sentences=[Sentence(raw_text="Talán majd...")])],
            order=0,
        )
        book = Book(title="Könyv", author="Szerző", chapters=[chapter], content_hash="h1")
        cache = CacheManager(cache_root=tmp_path / "cache")
        voice = VoiceSettings(voice_model_path=tmp_path / "hang.onnx")
        generator = AudioGenerator(tts=fake_tts, cache_manager=cache, voice=voice)

        generator.generate_chapter(book, chapter)

        assert fake_tts.synthesized_texts == ["Talán majd"]
    def test_returns_path_for_every_chapter(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(3)
        generator = _generator(fake_tts, tmp_path)

        paths = generator.generate_book(book)

        assert len(paths) == 3
        assert all(path.exists() for path in paths)

    def test_paths_follow_chapter_order(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(3)
        generator = _generator(fake_tts, tmp_path)

        paths = generator.generate_book(book)

        # A fájlnevek a fejezet sorszámával kezdődnek (lásd CacheManager),
        # így a lexikografikus sorrend is a fejezet-sorrendet tükrözi.
        assert [p.name[:3] for p in paths] == ["000", "001", "002"]

    def test_second_run_does_not_resynthesize(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(3)
        generator = _generator(fake_tts, tmp_path)

        generator.generate_book(book)
        assert fake_tts.synthesize_call_count == 3

        generator.generate_book(book)
        assert fake_tts.synthesize_call_count == 3  # nem nőtt

    def test_progress_callback_called_for_each_chapter(self, fake_tts, tmp_path: Path) -> None:
        book = _book_with_chapters(2)
        generator = _generator(fake_tts, tmp_path)
        calls: list[tuple[int, int, str, str]] = []

        def callback(index, total, chapter, status):
            calls.append((index, total, chapter.title, status))

        generator.generate_book(book, progress_callback=callback)

        # Minden fejezethez 2 hívás várt: egy a feldolgozás elején
        # (cache_hit vagy generating), egy a végén (done).
        assert len(calls) == 4
        assert calls[0] == (0, 2, "Fejezet 0", "generating")
        assert calls[1] == (0, 2, "Fejezet 0", "done")
        assert calls[2] == (1, 2, "Fejezet 1", "generating")
        assert calls[3] == (1, 2, "Fejezet 1", "done")

    def test_progress_callback_reports_cache_hit_on_second_run(
        self, fake_tts, tmp_path: Path
    ) -> None:
        book = _book_with_chapters(1)
        generator = _generator(fake_tts, tmp_path)
        generator.generate_book(book)

        calls: list[str] = []
        generator.generate_book(
            book, progress_callback=lambda i, t, ch, status: calls.append(status)
        )

        assert calls == ["cache_hit", "done"]
