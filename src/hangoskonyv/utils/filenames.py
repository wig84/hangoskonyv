"""Fájlnév-tisztító segédfüggvény.

Fejezetcímekből (pl. "KÜLÖNÖS JELENSÉGEK (I.)") biztonságos, a
fájlrendszer által elfogadott fájlnevet készít. Az ékezetes magyar
karaktereket megtartja (ezek Linuxon és a modern fájlrendszereken
problémamentesek), csak a ténylegesen tiltott/problémás karaktereket
távolítja el.
"""

from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")


def sanitize_filename(name: str, *, max_length: int = 100, fallback: str = "fejezet") -> str:
    """A megadott szöveget biztonságos fájlnév-résszé alakítja.

    Args:
        name: A tisztítandó szöveg (pl. egy fejezetcím).
        max_length: A visszaadott string maximális hossza.
        fallback: Ha a tisztítás után üres string maradna, ezt adja
            vissza helyette.

    Returns:
        A tisztított, fájlnévként biztonságosan használható string.
    """
    cleaned = _INVALID_CHARS.sub("", name)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    if not cleaned:
        return fallback
    return cleaned[:max_length]
