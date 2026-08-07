"""Lexikai heurisztika alapú érzelem-/hangsúly-felismerés.

Ez a modul NEM gépi tanulásos, kontextus-érzékeny érzelem-elemzést
végez (az egy jóval nagyobb, opcionálisan lokális LLM-et igénylő
feladat lenne — lásd az architektúra-terv eredeti "AI modul" pontját).
Ehelyett egy egyszerű, szótő-alapú kulcsszó-egyezést és néhány
tipográfiai jelet (felkiáltójel, csupa nagybetűs szó) használ, hogy a
`Sentence.emotion` mezőt egy hasznos, durva közelítéssel töltse fel.

Ismert korlátozások (tudatos kompromisszumok, nem hibák):

- A kulcsszó-egyezés nem veszi figyelembe a kontextust vagy a
  tagadást — "nem volt boldog" ugyanúgy "öröm"-ként azonosítaná,
  mint egy tagadás nélküli mondat.
- A magyar toldalékolás miatt a szótöveket prefix-egyezéssel
  közelítjük (pl. "dühös" töve elkapja a "dühösen" alakot is), ami
  ritkán hamis pozitívot is okozhat (pl. "nevetséges" a "nevet"
  tövére illeszkedne, holott gúnyos, nem örömteli jelentésű).
- A cél egy jobb-mint-semmi jelzés a szintézishez (11. iteráció),
  nem egy nyelvészeti szempontból tökéletes elemzés.
"""

from __future__ import annotations

import re

from hangoskonyv.core.document import Sentence
from hangoskonyv.core.enums import SentenceType

_JOY_STEMS = (
    "boldog", "örül", "öröm", "vidám", "mosoly", "nevet", "izgatott",
    "lelkes", "büszke",
)
_ANGER_STEMS = (
    "dühös", "harag", "üvölt", "kiabál", "ordít", "gyűlöl", "ideges",
    "bosszant",
)
_SADNESS_STEMS = (
    "szomor", "sír", "könny", "gyász", "bánat", "levert", "magány",
)
_FEAR_STEMS = (
    "retteg", "rettenet", "ijed", "pánik", "aggód", "szorong",
    "félelem", "riadt", "rémül",
)
_SURPRISE_STEMS = (
    "meglep", "megdöbben", "hihetetlen", "váratlan", "elképeszt", "ámul",
)

_EMOTION_STEMS: dict[str, tuple[str, ...]] = {
    "öröm": _JOY_STEMS,
    "harag": _ANGER_STEMS,
    "szomorúság": _SADNESS_STEMS,
    "félelem": _FEAR_STEMS,
    "meglepetés": _SURPRISE_STEMS,
}
"""A bejárás sorrendje egyben prioritási sorrend is: pontszám-egyenlőség
esetén a korábban szereplő kategória nyer."""

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


def _count_stem_matches(text_lower: str, stems: tuple[str, ...]) -> int:
    words = _WORD_RE.findall(text_lower)
    return sum(1 for word in words for stem in stems if word.startswith(stem))


def _has_all_caps_word(text: str) -> bool:
    """Igaz, ha van legalább egy 2+ betűs, csupa nagybetűs szó — ez a
    magyar szövegekben (a mondat eleji nagybetűtől eltérően) gyakran
    hangsúlyt/kiabálást jelez."""
    for word in _WORD_RE.findall(text):
        if len(word) >= 2 and word == word.upper() and word != word.lower():
            return True
    return False


def detect_emotion(sentence: Sentence) -> str | None:
    """A mondat érzelmi címkéjét állapítja meg egyszerű, szótő-alapú
    heurisztikával.

    Returns:
        Az érzelmi címke ("öröm", "harag", "szomorúság", "félelem",
        "meglepetés", vagy a felkiáltásokra/csupa nagybetűs szavakra
        alkalmazott generikus "izgatottság"), vagy None, ha nem
        sikerült egyértelmű érzelmet azonosítani. A None NEM
        feltétlenül jelenti, hogy a mondat "semleges" — csak azt,
        hogy ez a heurisztika nem tudta megállapítani.
    """
    text_lower = sentence.raw_text.lower()

    best_emotion: str | None = None
    best_score = 0
    for emotion, stems in _EMOTION_STEMS.items():
        score = _count_stem_matches(text_lower, stems)
        if score > best_score:
            best_score = score
            best_emotion = emotion

    if best_emotion is not None:
        return best_emotion

    if sentence.type is SentenceType.EXCLAMATION or _has_all_caps_word(sentence.raw_text):
        return "izgatottság"

    return None
