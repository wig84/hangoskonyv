"""Mondattípus és (heurisztikus) beszélő-felismerés.

A típus-felismerés egyszerű, írásjel- és tipográfia-alapú
heurisztika. A beszélő (speaker) felismerése egy még egyszerűbb,
mintaillesztés-alapú becslés — a pontos szereplő-azonosítás
(pl. névmások feloldása, kontextusból következtetés) az opcionális
`ai` modul feladata lesz egy későbbi iterációban.

Prioritási sorrend típus-felismerésnél: DIALOGUE > QUOTE > QUESTION >
EXCLAMATION > STATEMENT. Ha egy párbeszéd-mondat egyben kérdő mondat
is (pl. "– Hogy vagy?"), a `type` mezőben DIALOGUE lesz rögzítve, de
ez nem veszíti el a kérdő jelleget: az SSML-generáló (későbbi
iteráció) a `raw_text` tényleges írásjeleit is megvizsgálhatja a
pontos hanglejtéshez. A `type` mező tehát egy durvább, szerkezeti
kategória, nem a teljes pragmatikai információ kizárólagos hordozója.

Ismert korlátozás: a beszélő-felismerés legfeljebb kétszavas nevet
ismer fel közvetlenül a beszéd-ige után (pl. "mondta Csao Jü"). Ha a
szereplő neve három vagy több elemből áll, vagy a mondatszerkezet
eltér ettől a mintától, a felismerés None-t ad — ez a heurisztika
tudatosan konzervatív a hamis pozitívok elkerülése érdekében.
"""

from __future__ import annotations

import re

from hangoskonyv.core.enums import SentenceType

_DIALOGUE_DASH_PREFIXES = ("–", "—", "-")
_OPENING_QUOTES = ("„", "»")
_CLOSING_QUOTES = ("”", "«")

_SPEECH_VERBS = (
    "mondta", "kérdezte", "válaszolta", "kiáltotta", "suttogta",
    "felelte", "dünnyögte", "motyogta", "szólt", "dörmögte",
    "vágta rá", "tette hozzá",
)
_SPEAKER_PATTERN = re.compile(
    r"(?:" + "|".join(_SPEECH_VERBS) + r")\s+"
    r"([A-ZÁÉÍÓÖŐÚÜŰ][\wáéíóöőúüű]*(?:\s[A-ZÁÉÍÓÖŐÚÜŰ][\wáéíóöőúüű]*)?)"
)


def detect_sentence_type(text: str) -> SentenceType:
    """A mondat szerkezeti típusát állapítja meg írásjelek/tipográfia alapján."""
    stripped = text.strip()
    if not stripped:
        return SentenceType.STATEMENT

    if stripped.startswith(_DIALOGUE_DASH_PREFIXES):
        return SentenceType.DIALOGUE

    if stripped.startswith(_OPENING_QUOTES) or stripped.endswith(_CLOSING_QUOTES):
        return SentenceType.QUOTE

    ending = stripped.rstrip("\"”»›'")
    if ending.endswith("?"):
        return SentenceType.QUESTION
    if ending.endswith("!"):
        return SentenceType.EXCLAMATION

    return SentenceType.STATEMENT


def extract_speaker(text: str) -> str | None:
    """Megpróbálja kinyerni a beszélő nevét egy párbeszéd-mondatból.

    Kizárólag a "– ... – mondta Éva."-típusú, explicit beszéd-igés
    mintákat ismeri fel. Ha nincs ilyen minta, None-t ad vissza —
    ez nem jelenti azt, hogy nincs beszélő, csak azt, hogy ez az
    egyszerű heurisztika nem tudta megállapítani.
    """
    match = _SPEAKER_PATTERN.search(text)
    return match.group(1) if match else None
