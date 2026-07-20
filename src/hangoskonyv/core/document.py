"""Hierarchikus dokumentummodell egy felolvasandó könyvhöz.

A modell szándékosan nem egyetlen hosszú karakterláncot ábrázol,
hanem egy réteges szerkezetet:

    Book
        Chapter
            Paragraph
                Sentence
                    Token

Ez teszi lehetővé, hogy a pipeline későbbi lépései (nlp, ai, ssml)
strukturált metaadatokkal (mondattípus, szereplő, hangsúly, kiejtési
javaslat) bővítsék a szöveget anélkül, hogy a nyers karakterláncot
kellene újra és újra feldolgozniuk.

A parserek (pl. EpubParser) egyelőre csak a Paragraph/Sentence szintig
töltik fel a modellt `raw_text`-tel; a Token-szintű bontást az nlp
modul végzi el egy külön feldolgozási lépésben. Ez a késleltetett
tokenizálás elkerüli, hogy a parser réteg nyelvi feltevéseket kelljen
hogy tegyen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hangoskonyv.core.enums import SentenceType, TokenType


@dataclass(slots=True)
class Token:
    """A legkisebb feldolgozási egység: egy szó, szám vagy írásjel.

    A Token-eket az nlp modul hozza létre a Sentence nyers szövegéből.
    Amíg egy Sentence-t nem dolgozott fel az nlp pipeline, a `tokens`
    listája üres marad.
    """

    text: str
    type: TokenType = TokenType.WORD
    pronunciation_hint: str | None = None
    """Kiejtési javaslat (pl. normalizált szám -> kiejtett alak).

    Ha None, a TTS a `text` mezőt olvassa fel változtatás nélkül.
    """


@dataclass(slots=True)
class Sentence:
    """Egy mondat a nyers szövegével és (opcionális) tokenjeivel."""

    raw_text: str
    type: SentenceType = SentenceType.STATEMENT
    speaker: str | None = None
    """A mondatot mondó szereplő neve, ha párbeszédről van szó."""

    emotion: str | None = None
    """Érzelmi címke (pl. 'düh', 'öröm'), az AI modul tölti ki."""

    tokens: list[Token] = field(default_factory=list)
    """Token-szintű bontás. Üres, amíg az nlp modul fel nem dolgozza."""

    def __post_init__(self) -> None:
        if not self.raw_text.strip():
            raise ValueError("A Sentence.raw_text nem lehet üres.")

    @property
    def word_count(self) -> int:
        """A mondat szószáma egyszerű whitespace-alapú becsléssel."""
        return len(self.raw_text.split())


@dataclass(slots=True)
class Paragraph:
    """Egy bekezdés, egy vagy több mondatból összeállítva."""

    sentences: list[Sentence] = field(default_factory=list)
    is_dialogue_block: bool = False
    """Igaz, ha a bekezdés túlnyomó része párbeszéd."""

    @property
    def text(self) -> str:
        """A bekezdés teljes szövege a mondatok összefűzésével."""
        return " ".join(sentence.raw_text for sentence in self.sentences)

    @property
    def word_count(self) -> int:
        return sum(sentence.word_count for sentence in self.sentences)


@dataclass(slots=True)
class Chapter:
    """Egy fejezet, bekezdésekből felépítve."""

    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    order: int = 0
    """A fejezet sorrendi pozíciója a könyvön belül (0-tól indexelve)."""

    def __post_init__(self) -> None:
        if self.order < 0:
            raise ValueError("A Chapter.order nem lehet negatív.")

    @property
    def text(self) -> str:
        """A fejezet teljes szövege, bekezdésenként új sorral elválasztva."""
        return "\n\n".join(paragraph.text for paragraph in self.paragraphs)

    @property
    def word_count(self) -> int:
        return sum(paragraph.word_count for paragraph in self.paragraphs)

    @property
    def is_empty(self) -> bool:
        """Igaz, ha a fejezetnek nincs felolvasható tartalma."""
        return self.word_count == 0


@dataclass(slots=True)
class Book:
    """A teljes könyv: metaadatok és a fejezetek listája."""

    title: str
    author: str
    chapters: list[Chapter] = field(default_factory=list)
    language: str = "hu"
    cover_image: bytes | None = None
    content_hash: str = ""
    """A könyv tartalmának hash-e; a CacheManager használja fejezetenkénti
    cache-kulcs képzéséhez (lásd audio/cache_manager.py)."""

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def total_word_count(self) -> int:
        return sum(chapter.word_count for chapter in self.chapters)

    def chapters_sorted(self) -> list[Chapter]:
        """A fejezetek `order` szerint rendezve.

        A parserek nem garantálják, hogy a `chapters` lista már
        a végleges sorrendben áll össze (pl. párhuzamos feldolgozás
        esetén), ezért ezt a rendezett nézetet kell használni minden
        olyan helyen, ahol a felolvasási sorrend számít (audio
        generálás, lejátszó, GUI könyvtár nézet).
        """
        return sorted(self.chapters, key=lambda chapter: chapter.order)
