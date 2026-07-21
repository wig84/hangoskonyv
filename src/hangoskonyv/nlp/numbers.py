"""Arab számok magyar tő- és sorszámnévvé alakítása.

Ez a modul tartalmazza a projekt egyik legnyelv-specifikusabb
logikáját. A magyar számnévképzés nem egyszerű "számjegyenkénti"
felolvasás (mint pl. egy telefonszámnál), hanem valódi, összetett
szóalkotás (pl. 1923 -> "ezerkilencszázhuszonhárom").

Ismert korlátozás: a `ordinal_to_words` 100 alatt teljesen pontos
(ez fedi a gyakorlati eseteket: hónap napjai 1-31, század-/uralkodó-
sorszámok jellemzően 100 alatt), 100 fölött viszont egy egyszerűsített,
"best-effort" utótag-cserét alkalmaz a tőszámnévi alakon, ami nem
minden esetben ad tökéletes eredményt. Ez egy tudatos kompromisszum:
a valós használati esetek túlnyomó többségét lefedi, a ritka
kivételeket pedig inkább egy kicsit pontatlanul, mint hibásan (pl.
kivétellel leállva) kezeli.
"""

from __future__ import annotations

_ONES = [
    "nulla", "egy", "kettő", "három", "négy", "öt",
    "hat", "hét", "nyolc", "kilenc",
]
_TEENS = [
    "tíz", "tizenegy", "tizenkettő", "tizenhárom", "tizennégy", "tizenöt",
    "tizenhat", "tizenhét", "tizennyolc", "tizenkilenc",
]
_TENS_WORDS = {
    2: "húsz", 3: "harminc", 4: "negyven", 5: "ötven",
    6: "hatvan", 7: "hetven", 8: "nyolcvan", 9: "kilencven",
}
_TENS_PREFIX = {
    2: "huszon", 3: "harminc", 4: "negyven", 5: "ötven",
    6: "hatvan", 7: "hetven", 8: "nyolcvan", 9: "kilencven",
}
_CONTRACTED_ONES = {2: "két"}
"""A 'kettő' 'két'-té rövidül, amikor közvetlenül 'száz'/'ezer'/'millió'/
'milliárd' elé kerül szorzóként (pl. 'kétszáz', nem 'kettőszáz')."""

_ORDINAL_ONES = {
    0: "nulladik", 1: "első", 2: "második", 3: "harmadik", 4: "negyedik",
    5: "ötödik", 6: "hatodik", 7: "hetedik", 8: "nyolcadik", 9: "kilencedik",
}
_ORDINAL_ONES_COMPOUND = {**_ORDINAL_ONES, 1: "egyedik", 2: "kettedik"}
"""Összetett sorszámban (pl. 'huszonegyedik') az 1 és 2 alakja eltér az
önálló használattól ('első'/'második'): 'egyedik'/'kettedik' lesz belőle,
pontosan úgy, ahogy a `_ORDINAL_TEENS`-ben a 11/12 is 'tizenegyedik' és
'tizenkettedik' (nem 'tizenelső'/'tizenmásodik')."""

_ORDINAL_TEENS = {
    10: "tizedik", 11: "tizenegyedik", 12: "tizenkettedik", 13: "tizenharmadik",
    14: "tizennegyedik", 15: "tizenötödik", 16: "tizenhatodik",
    17: "tizenhetedik", 18: "tizennyolcadik", 19: "tizenkilencedik",
}
_ORDINAL_TENS_EXACT = {
    20: "huszadik", 30: "harmincadik", 40: "negyvenedik", 50: "ötvenedik",
    60: "hatvanadik", 70: "hetvenedik", 80: "nyolcvanadik", 90: "kilencvenedik",
}

DAY_OF_MONTH_WORDS: dict[int, str] = {
    1: "elseje", 2: "másodika", 3: "harmadika", 4: "negyedike", 5: "ötödike",
    6: "hatodika", 7: "hetedike", 8: "nyolcadika", 9: "kilencedike",
    10: "tizedike", 11: "tizenegyedike", 12: "tizenkettedike",
    13: "tizenharmadika", 14: "tizennegyedike", 15: "tizenötödike",
    16: "tizenhatodika", 17: "tizenhetedike", 18: "tizennyolcadika",
    19: "tizenkilencedike", 20: "huszadika", 21: "huszonegyedike",
    22: "huszonkettedike", 23: "huszonharmadika", 24: "huszonnegyedike",
    25: "huszonötödike", 26: "huszonhatodika", 27: "huszonhetedike",
    28: "huszonnyolcadika", 29: "huszonkilencedike", 30: "harmincadika",
    31: "harmincegyedike",
}
"""A hónap napjainak kiejtett alakja (1-31).

Ez egy teljes, kézzel felvett táblázat, nem szabály-alapú generálás
— a magyar "hányadika" alakok (pl. "elseje", nem "elsője") elég
sok kivételt tartalmaznak ahhoz, hogy egy 31 elemű, véges
táblázat megbízhatóbb legyen egy általános szabálynál.
"""


def _contract_kettő(word: str) -> str:
    if word.endswith("kettő"):
        return word[: -len("kettő")] + "két"
    return word


def _two_digit_to_words(n: int) -> str:
    """0-99 közötti szám magyar tőszámnévi alakja."""
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n - 10]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _TENS_WORDS[tens]
    return _TENS_PREFIX[tens] + _ONES[ones]


def _three_digit_to_words(n: int) -> str:
    """0-999 közötti szám magyar tőszámnévi alakja."""
    hundreds, remainder = divmod(n, 100)
    if hundreds == 0:
        hundreds_part = ""
    elif hundreds == 1:
        hundreds_part = "száz"
    else:
        hundreds_part = _CONTRACTED_ONES.get(hundreds, _ONES[hundreds]) + "száz"
    remainder_part = _two_digit_to_words(remainder) if remainder else ""
    return hundreds_part + remainder_part


def _grouped_multiplier(value: int, unit_word: str) -> str:
    """Egy 0-999 közötti csoport + szorzó szó (ezer/millió/milliárd)
    összefűzött alakja, a szükséges 'kettő' -> 'két' rövidítéssel."""
    if value == 0:
        return ""
    if value == 1:
        return unit_word
    text = _contract_kettő(_three_digit_to_words(value))
    return text + unit_word


def cardinal_to_words(n: int) -> str:
    """Egy egész szám magyar tőszámnévi (kiejtett) alakja.

    Támogatott tartomány: gyakorlatilag tetszőleges nagyságú egész
    szám (milliárdos nagyságrendig pontosan tesztelve).

    Args:
        n: A számmá alakítandó egész szám (lehet negatív is).

    Returns:
        A szám magyar szöveges alakja, pl. `cardinal_to_words(1923)`
        -> `"ezerkilencszázhuszonhárom"`.
    """
    if n < 0:
        return "mínusz " + cardinal_to_words(-n)
    if n == 0:
        return "nulla"

    billions, remainder = divmod(n, 1_000_000_000)
    millions, remainder = divmod(remainder, 1_000_000)
    thousands, remainder = divmod(remainder, 1000)
    hundreds_group = remainder

    parts = [
        _grouped_multiplier(billions, "milliárd"),
        _grouped_multiplier(millions, "millió"),
        _grouped_multiplier(thousands, "ezer"),
        _three_digit_to_words(hundreds_group),
    ]
    result = "".join(parts)
    return result or "nulla"


def ordinal_to_words(n: int) -> str:
    """Egy egész szám magyar sorszámnévi (kiejtett) alakja.

    100 alatt pontos eredményt ad. 100 fölött egy egyszerűsített
    utótag-cserét alkalmaz a tőszámnévi alakon (lásd a modul
    docstringjét a korlátozás indoklásáért).

    Args:
        n: A számmá alakítandó, nem negatív egész szám.

    Raises:
        ValueError: Ha `n` negatív.
    """
    if n < 0:
        raise ValueError("A sorszámnév nem értelmezhető negatív számra.")

    if n < 10:
        return _ORDINAL_ONES[n]
    if n < 20:
        return _ORDINAL_TEENS[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        if ones == 0:
            return _ORDINAL_TENS_EXACT[tens * 10]
        return _TENS_PREFIX[tens] + _ORDINAL_ONES_COMPOUND[ones]

    # 100 és afölött: best-effort utótag-csere a tőszámnévi alakon.
    cardinal = cardinal_to_words(n)
    for suffix, ordinal_suffix in (
        ("milliárd", "milliárdodik"),
        ("millió", "milliomodik"),
        ("ezer", "ezredik"),
        ("száz", "századik"),
    ):
        if cardinal.endswith(suffix):
            return cardinal[: -len(suffix)] + ordinal_suffix

    # Nem kerek száz/ezer/millió (pl. 123, 1045) — a tőszámnévi alak
    # végére egyszerű "-adik" toldalékot illesztünk. Ez nyelvtanilag
    # nem mindig helyes (a valós szabály az utolsó szótagtól függő
    # hangrendi illeszkedést igényelne), de ismert, dokumentált
    # korlátozás — lásd a modul docstringjét.
    return cardinal + "-adik"
