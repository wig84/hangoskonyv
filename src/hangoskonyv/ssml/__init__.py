"""SSML réteg: natív SSML-generálás (jövőbeli, SSML-t támogató motorokhoz)
és fallback szünet-közelítés (jelenleg a Piperhez)."""

from hangoskonyv.ssml.fallback import (
    COMMA_PAUSE_MS,
    ELLIPSIS_PAUSE_MS,
    PARAGRAPH_PAUSE_MS,
    QUESTION_EXCLAMATION_PAUSE_MS,
    SENTENCE_PAUSE_MS,
    SpeechSegment,
    build_chapter_segments,
)

__all__ = [
    "SpeechSegment",
    "build_chapter_segments",
    "COMMA_PAUSE_MS",
    "SENTENCE_PAUSE_MS",
    "QUESTION_EXCLAMATION_PAUSE_MS",
    "ELLIPSIS_PAUSE_MS",
    "PARAGRAPH_PAUSE_MS",
]
