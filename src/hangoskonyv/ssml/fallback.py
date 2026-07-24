"""SSML fallback mód — szünet-időzítés közelítése szegmentálással.

A Piper (és sok más TTS motor) nem támogat SSML-t (`AbstractTTS.
supports_ssml == False`), tehát nem tudunk `<break time="500ms"/>`
jellegű jelölést használni a szünetek vezérlésére. Ehelyett ez a
modul a mondatot/bekezdést kisebb szövegdarabokra (`SpeechSegment`)
bontja, mindegyikhez egy "utána tartandó csend" időtartamot rendelve.
A hívó kód (`audio.generator.AudioGenerator`) minden darabot külön
szintetizál, majd a darabok közé a megadott hosszúságú digitális
csendet szúrja be, mielőtt összefűzné őket egy teljes fejezetnyi
hanggá.

Ez két problémát old meg egyszerre:

1. **Finomhangolható szünetek**: mivel mi magunk generáljuk a
   csendet, pontosan szabályozható, mennyi szünet legyen egy vessző,
   egy mondatvég, vagy egy bekezdésváltás után — függetlenül attól,
   mit "gondol" erről maga a TTS motor.
2. **A hármaspont ("...") hibás felolvasásának elkerülése**: a Piper
   ezt szó szerint, "pont pont pont"-ként olvassa fel, ha a
   karakterek bekerülnek a szintetizálandó szövegbe. Ehelyett a
   hármaspontot a szövegből eltávolítjuk, és helyette egy hosszabb
   csendet illesztünk be — ez adja vissza a szándékolt "elgondolkodó
   szünet" hatást, hibás kiejtés nélkül.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hangoskonyv.core.document import Chapter, Paragraph, Sentence
from hangoskonyv.core.enums import SentenceType

COMMA_PAUSE_MS = 150
"""Extra szünet vessző után (a Piper saját, beépített vessző-szünete fölött)."""

SENTENCE_PAUSE_MS = 450
"""Extra szünet kijelentő/párbeszéd-mondat vége után."""

QUESTION_EXCLAMATION_PAUSE_MS = 500
"""Extra szünet kérdő/felkiáltó mondat vége után (kicsit hosszabb, mint
egy sima kijelentésé, hogy a hanglejtés-változásnak legyen ideje "leülni")."""

ELLIPSIS_PAUSE_MS = 700
"""Szünet hármaspont ("...", "…") helyén — a karakterek eltávolítása
mellett, hogy a TTS ne olvassa fel szó szerint."""

PARAGRAPH_PAUSE_MS = 700
"""Minimum szünet egy bekezdés utolsó mondata után (bekezdésváltás)."""

_TRAILING_ELLIPSIS_RE = re.compile(r"(?:\.\.\.|…)+\s*$")
_COMMA_SPLIT_RE = re.compile(r",")


@dataclass(slots=True)
class SpeechSegment:
    """Egy önállóan szintetizálandó szövegdarab, a felolvasás után
    tartandó csend hosszával."""

    text: str
    pause_after_ms: int


def _strip_trailing_ellipsis(text: str) -> tuple[str, bool]:
    """Eltávolítja a mondat végi hármaspontot, ha van ilyen.

    Returns:
        (a hármaspont nélküli szöveg, volt-e hármaspont).
    """
    match = _TRAILING_ELLIPSIS_RE.search(text)
    if match:
        return text[: match.start()].rstrip(), True
    return text, False


def _split_on_commas(text: str) -> list[str]:
    """A szöveget vesszőknél darabolja, a vesszőt az előző darab
    végén megtartva (hogy a TTS a vessző saját hanglejtését/szünetét
    is megkapja — mi csak *ráadás* csendet adunk hozzá)."""
    positions = [m.end() for m in _COMMA_SPLIT_RE.finditer(text)]
    if not positions:
        return [text] if text.strip() else []

    chunks: list[str] = []
    start = 0
    for pos in positions:
        chunk = text[start:pos].strip()
        if chunk:
            chunks.append(chunk)
        start = pos
    remainder = text[start:].strip()
    if remainder:
        chunks.append(remainder)
    return chunks


def _build_sentence_segments(sentence: Sentence, *, split_on_commas: bool) -> list[SpeechSegment]:
    text, had_ellipsis = _strip_trailing_ellipsis(sentence.raw_text)
    if not text:
        return []

    if had_ellipsis:
        end_pause = ELLIPSIS_PAUSE_MS
    elif sentence.type in (SentenceType.QUESTION, SentenceType.EXCLAMATION):
        end_pause = QUESTION_EXCLAMATION_PAUSE_MS
    else:
        end_pause = SENTENCE_PAUSE_MS

    if not split_on_commas:
        return [SpeechSegment(text=text, pause_after_ms=end_pause)]

    comma_chunks = _split_on_commas(text)
    if not comma_chunks:
        return []

    segments = [
        SpeechSegment(text=chunk, pause_after_ms=COMMA_PAUSE_MS) for chunk in comma_chunks[:-1]
    ]
    segments.append(SpeechSegment(text=comma_chunks[-1], pause_after_ms=end_pause))
    return segments


def _build_paragraph_segments(paragraph: Paragraph, *, split_on_commas: bool) -> list[SpeechSegment]:
    segments: list[SpeechSegment] = []
    for sentence in paragraph.sentences:
        segments.extend(_build_sentence_segments(sentence, split_on_commas=split_on_commas))
    return segments


def build_chapter_segments(chapter: Chapter, *, split_on_commas: bool = False) -> list[SpeechSegment]:
    """Egy fejezet teljes szövegét `SpeechSegment`-ekre bontja.

    Minden bekezdés utolsó szegmensének szünetét legalább
    `PARAGRAPH_PAUSE_MS`-re emeli, hogy a bekezdésváltás érzékelhető
    maradjon a felolvasásban.

    Args:
        chapter: A szegmentálandó fejezet.
        split_on_commas: Ha True, a mondatokon belül a vesszőknél is
            külön szegmenst képez (finomabb szünet-vezérlés, de
            jelentősen több TTS-hívást igényel — egy hosszabb
            könyvnél ez a hívásszám többszöröződését jelentheti,
            ami a teljes generálási időt is arányosan megnövelheti).
            Alapból False: csak mondat-szinten szegmentálunk, ami a
            leggyakoribb panaszt (rövid mondatvégi szünet, hibásan
            felolvasott hármaspont) már megoldja, jóval kisebb
            teljesítmény-hatással.
    """
    all_segments: list[SpeechSegment] = []
    for paragraph in chapter.paragraphs:
        paragraph_segments = _build_paragraph_segments(paragraph, split_on_commas=split_on_commas)
        if not paragraph_segments:
            continue
        paragraph_segments[-1].pause_after_ms = max(
            paragraph_segments[-1].pause_after_ms, PARAGRAPH_PAUSE_MS
        )
        all_segments.extend(paragraph_segments)
    return all_segments
