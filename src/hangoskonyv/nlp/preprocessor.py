"""A teljes NLP előfeldolgozási lánc összefogása.

A parser (2. iteráció) minden bekezdést egyetlen, naiv `Sentence`-be
tesz (a teljes bekezdés-szöveggel). A `Preprocessor` ezt dolgozza át:
minden bekezdést valódi, magyar nyelvi szabályok szerint bontott
mondatokra oszt, minden mondathoz típust (kérdés/felkiáltás/párbeszéd/
idézet), — párbeszéd esetén, ha felismerhető — beszélőt, és egy
durva érzelmi címkét rendel (lásd `ai.emotion_analyzer`), majd
token-szintre bontja és normalizálja a szöveget.
"""

from __future__ import annotations

import logging

from hangoskonyv.ai.emotion_analyzer import detect_emotion
from hangoskonyv.core.document import Book, Paragraph, Sentence
from hangoskonyv.core.enums import SentenceType
from hangoskonyv.nlp.dialogue_detector import detect_sentence_type, extract_speaker
from hangoskonyv.nlp.normalizer import tokenize_and_normalize
from hangoskonyv.nlp.sentence_splitter import split_sentences

logger = logging.getLogger(__name__)


class Preprocessor:
    """A parser által adott naiv `Book`-ot nyelvileg feldolgozott
    `Book`-ká alakítja (mondatbontás, típus/beszélő-felismerés,
    token-szintű normalizálás).

    Ismert korlátozás: mivel a "!"/"?" mindig mondatvéget jelent, egy
    "– Szia! – mondta Éva." mintázatú bekezdés két külön `Sentence`-re
    bomlik ("– Szia!" és "– mondta Éva."). A felismert beszélő ("Éva")
    csak a tag-mondathoz (a másodikhoz) kerül hozzárendelésre, az idézet
    saját mondata beszélő nélkül marad. Ennek pontosabb kezelése (a
    beszélő visszaterjesztése az idézet-mondatra) egy későbbi finomítás
    tárgya lehet.
    """

    def process_book(self, book: Book) -> Book:
        """A könyv minden bekezdését feldolgozza, a helyben módosított
        `book`-ot adja vissza (kényelmi célból, a hívási lánc miatt).
        """
        logger.info("NLP előfeldolgozás indul: '%s' (%d fejezet)", book.title, book.chapter_count)
        for chapter in book.chapters:
            for paragraph in chapter.paragraphs:
                self._process_paragraph(paragraph)
        logger.info("NLP előfeldolgozás kész: '%s'", book.title)
        return book

    def _process_paragraph(self, paragraph: Paragraph) -> None:
        raw_text = paragraph.text
        sentence_texts = split_sentences(raw_text)

        new_sentences: list[Sentence] = []
        for sentence_text in sentence_texts:
            sentence_type = detect_sentence_type(sentence_text)
            speaker = (
                extract_speaker(sentence_text) if sentence_type == SentenceType.DIALOGUE else None
            )
            tokens = tokenize_and_normalize(sentence_text)
            new_sentence = Sentence(
                raw_text=sentence_text,
                type=sentence_type,
                speaker=speaker,
                tokens=tokens,
            )
            new_sentence.emotion = detect_emotion(new_sentence)
            new_sentences.append(new_sentence)

        paragraph.sentences = new_sentences
        paragraph.is_dialogue_block = any(
            sentence.type == SentenceType.DIALOGUE for sentence in new_sentences
        )
