"""Magyar nyelvi szabályok és konstansok.

Ez a modul kizárólag statikus adatokat (listákat, szótárakat) és
egyszerű, adat-alapú segédfüggvényeket tartalmaz — nincs benne
"algoritmikus" logika (az a `sentence_splitter`, `normalizer` stb.
modulokban van). Ez teszi lehetővé, hogy a nyelvi szabályokat
(pl. új rövidítés hozzáadása) kód-módosítás nélkül, egyetlen helyen
bővítsük.
"""

from __future__ import annotations

ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "pl.", "stb.", "kb.", "vö.", "ún.", "ill.", "ti.", "köt.", "évf.",
        "sz.", "o.", "l.", "min.", "max.", "dr.", "prof.", "id.", "ifj.",
        "p.", "kif.", "átv.", "gyak.", "kül.", "tel.", "fax.", "vsz.",
        "kr.", "e.", "u.", "i.", "n.", "m.", "cca.", "kb",
        # hónap-rövidítések (dátumformátumokhoz)
        "jan.", "febr.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.",
        "szept.", "okt.", "nov.", "dec.",
    }
)
"""Rövidítések, amik utáni pont NEM zárja le a mondatot.

Megjegyzés: néhány egybetűs bejegyzés (pl. "e.", "u.", "i.") a
"Kr. e.", "Kr. u.", "i. sz." típusú, két szóból álló rövidítések
második tagját fedi le. Ez egy tudatos egyszerűsítés: ezek a
karakterláncok elvileg más kontextusban is előfordulhatnának, de a
valós magyar szövegekben ez a kockázat elhanyagolható a haszonhoz
képest (lásd a sentence_splitter modul teszteit).
"""

MONTH_NAMES: dict[int, str] = {
    1: "január", 2: "február", 3: "március", 4: "április",
    5: "május", 6: "június", 7: "július", 8: "augusztus",
    9: "szeptember", 10: "október", 11: "november", 12: "december",
}

ABBREVIATION_EXPANSIONS: dict[str, str] = {
    "pl.": "például",
    "stb.": "és a többi",
    "kb.": "körülbelül",
    "ill.": "illetve",
    "ún.": "úgynevezett",
    "vö.": "vesd össze",
    "dr.": "doktor",
    "prof.": "professzor",
}
"""Kiejtési javaslatok néhány gyakori rövidítéshez.

Nem minden `ABBREVIATIONS`-beli elem szerepel itt: csak azokat
vettük fel, amikhez egyértelmű, kontextustól független kiejtés
rendelhető. A többinél a TTS a rövidítést betűzve olvassa fel,
ami nem ideális, de biztonságosabb egy rossz feloldásnál.
"""

UNIT_ABBREVIATIONS: dict[str, str] = {
    "km": "kilométer", "cm": "centiméter", "mm": "milliméter", "m": "méter",
    "kg": "kilogramm", "g": "gramm", "dkg": "dekagramm",
    "l": "liter", "ml": "milliliter", "dl": "deciliter",
    "%": "százalék",
}
"""Mértékegység-rövidítések kiejtett alakja.

Csak akkor alkalmazzuk, ha a rövidítés közvetlenül egy szám után
áll (lásd `normalizer.py`), hogy elkerüljük a hamis pozitívokat
(pl. az "m" mint önálló szó vagy névelő-szerű előfordulás esetén).
"""
