"""WAV -> MP3 konverzió az `ffmpeg` parancssori eszközzel.

Nem célunk saját MP3 kódolót írni — az `ffmpeg` (libmp3lame) ezt már
megbízhatóan, gyorsan csinálja. Ha nincs telepítve, világos, magyar
hibaüzenetet adunk, nem egy nehezen értelmezhető subprocess kivételt.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hangoskonyv.core.exceptions import HangoskonyvError


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path, *, quality: int = 2) -> None:
    """Egy WAV fájlt MP3-má konvertál.

    Args:
        wav_path: A forrás WAV fájl.
        mp3_path: A célhely.
        quality: Az ffmpeg `libmp3lame` `-qscale:a` értéke (0 = legjobb/
            legnagyobb fájl, 9 = legrosszabb/legkisebb). Alapértelmezett: 2
            (jó minőség, ésszerű fájlméret — nagyjából ~190 kbps VBR-nek
            felel meg).

    Raises:
        HangoskonyvError: Ha az `ffmpeg` nem található, vagy a konverzió
            sikertelen volt.
    """
    if not is_ffmpeg_available():
        raise HangoskonyvError(
            "Az mp3 formátumhoz az 'ffmpeg' parancssori eszköz szükséges, "
            "de nem található a rendszeren. Telepítés Ubuntu/Debianon: "
            "sudo apt install ffmpeg"
        )

    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-qscale:a", str(quality),
            str(mp3_path),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        stderr_text = result.stderr.decode(errors="replace").strip()
        raise HangoskonyvError(f"Az ffmpeg mp3 konverzió sikertelen volt: {stderr_text}")
