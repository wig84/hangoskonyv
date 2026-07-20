"""Nem-narratív fejezetek (borító, copyright, impresszum stb.) kiszűrése.

Ez a komponens szándékosan formátum-független: bármelyik parser
(EPUB, később PDF/MOBI/TXT) ugyanazt a `ChapterFilter`-t használhatja,
mert kizárólag a már felépített `Chapter` objektumon dolgozik, nem a
formátum-specifikus nyers adatokon.

A szűrés két rétegű:

1. Beépített, alapértelmezett címlista (`DEFAULT_SKIP_TITLES`) —
   ez fedi a leggyakoribb eseteket kézi konfiguráció nélkül is.
2. A `settings.toml`-ból felülírható/bővíthető lista (lásd a
   `config` modult) — ha egy adott könyvnél a beépített heurisztika
   tévedne.

Szándékosan NEM alkalmazunk alapértelmezetten szószám-alapú
heurisztikát (pl. "50 szónál rövidebb fejezetek kiszűrése"), mert ez
könnyen kiszűrhetne valódi, csak rövid fejezeteket (pl. egy rövid
epilógust). A szószám-küszöb opcionálisan bekapcsolható, de alapból
kikapcsolt állapotban van.
"""

from __future__ import annotations

import unicodedata

from hangoskonyv.core.document import Chapter

DEFAULT_SKIP_TITLES: frozenset[str] = frozenset(
    {
        "borító",
        "copyright",
        "tartalom",
        "tartalomjegyzék",
        "impresszum",
        "jogi nyilatkozat",
        "kolofon",
        "hátsó borító",
        "cover",
    }
)
"""Alapértelmezetten kiszűrt fejezetcímek, kis/nagybetű- és
ékezet-független összehasonlítással."""


def _normalize_title(title: str) -> str:
    """Kisbetűsít és eltávolítja az ékezeteket az összehasonlításhoz.

    Ékezet-független összehasonlítás azért kell, mert a valós
    EPUB-okban a fejezetcímek helyesírása (pl. "COPYRIGHT" vs.
    "Copyright") és néha az ékezethasználat is eltérhet.
    """
    normalized = unicodedata.normalize("NFKD", title.strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


class ChapterFilter:
    """Eldönti, hogy egy fejezetet fel kell-e olvasni, vagy ki kell hagyni."""

    def __init__(
        self,
        skip_titles: frozenset[str] | None = None,
        min_word_count: int | None = None,
    ) -> None:
        """
        Args:
            skip_titles: Kiszűrendő fejezetcímek halmaza. Ha None,
                a `DEFAULT_SKIP_TITLES`-t használja.
            min_word_count: Ha meg van adva, az ennél kevesebb szót
                tartalmazó fejezetek is kiszűrésre kerülnek. Alapból
                None (kikapcsolva), lásd a modul docstring indoklását.
        """
        titles = skip_titles if skip_titles is not None else DEFAULT_SKIP_TITLES
        self._skip_titles = {_normalize_title(title) for title in titles}
        self._min_word_count = min_word_count

    def should_skip(self, chapter: Chapter) -> bool:
        """Igazat ad vissza, ha a fejezetet ki kell hagyni a felolvasásból."""
        if _normalize_title(chapter.title) in self._skip_titles:
            return True

        if chapter.is_empty:
            return True

        if self._min_word_count is not None and chapter.word_count < self._min_word_count:
            return True

        return False

    def filter_chapters(self, chapters: list[Chapter]) -> list[Chapter]:
        """A megadott fejezetlistából eltávolítja a kiszűrendőket."""
        return [chapter for chapter in chapters if not self.should_skip(chapter)]
