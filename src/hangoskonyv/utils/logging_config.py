"""Központi logging konfiguráció.

A projekt egyetlen pontból állítja be a Python `logging` modult,
hogy minden alrendszer (parser, nlp, tts, audio, gui) konzisztens
formátummal és szinttel naplózzon. Sehol a kódbázisban nem
használunk `print()`-et diagnosztikai célra.

Használat a belépési pontokon (pl. cli/main.py):

    from hangoskonyv.utils.logging_config import configure_logging
    configure_logging(level="INFO")

Minden más modulban:

    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Fejezet feldolgozása: %s", chapter.title)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    *,
    verbose_third_party: bool = False,
) -> None:
    """Beállítja a root loggert a projekt egész futása idejére.

    Args:
        level: A konzolra írt üzenetek minimum szintje
            (pl. "DEBUG", "INFO", "WARNING", "ERROR").
        log_file: Ha meg van adva, a naplóüzenetek DEBUG szinttől
            fájlba is íródnak (a konzol szintjétől függetlenül),
            hogy hiba esetén részletes utólagos diagnosztika
            legyen elérhető.
        verbose_third_party: Ha False (alapértelmezett), a zajos
            harmadik féltől származó könyvtárak (pl. httpx, PySide6
            belső loggerei) szintje WARNING-ra van korlátozva, hogy
            ne nyomják el a projekt saját üzeneteit.

    Raises:
        ValueError: Ha `level` nem érvényes logging szint név.
    """
    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        raise ValueError(f"Érvénytelen log szint: {level!r}")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(
        logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATE_FORMAT)
    )
    root_logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)

    if not verbose_third_party:
        for noisy_logger_name in ("httpx", "httpcore", "PySide6"):
            logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)
