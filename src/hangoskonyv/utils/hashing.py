"""Hash-elési segédfunkciók.

Ezeket használja a parser réteg (a `Book.content_hash` feltöltésére)
és a későbbi `audio.cache_manager` (fejezetenkénti cache-kulcs
képzésére). A cél mindkét helyen ugyanaz: eldönteni, hogy egy adott
tartalom változott-e a legutóbbi feldolgozás óta, hogy elkerüljük a
felesleges (és költséges) TTS-újragenerálást.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    """A megadott bájtsorozat SHA-256 hash-e, hexadecimális stringként."""
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    """A megadott szöveg SHA-256 hash-e (UTF-8 kódolással)."""
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: Path) -> str:
    """Egy fájl teljes tartalmának SHA-256 hash-e.

    Nagy fájloknál (pl. egy több MB-os EPUB) darabokban olvassa be
    a tartalmat, hogy ne kelljen az egész fájlt egyszerre memóriába
    tölteni.
    """
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
