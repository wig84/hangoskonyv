"""Unit tesztek a logging konfigurációhoz."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from hangoskonyv.utils.logging_config import configure_logging


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Minden teszt után visszaállítja a root loggert, hogy a tesztek
    ne szennyezzék egymást (a logging modul globális állapotot tart)."""
    yield
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)


def test_configure_logging_sets_console_handler() -> None:
    configure_logging(level="INFO")
    root_logger = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)


def test_configure_logging_invalid_level_raises() -> None:
    with pytest.raises(ValueError, match="Érvénytelen log szint"):
        configure_logging(level="NEM_LETEZO_SZINT")


def test_configure_logging_with_file_creates_file_handler(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "hangoskonyv.log"
    configure_logging(level="DEBUG", log_file=log_file)

    logger = logging.getLogger("hangoskonyv.test")
    logger.debug("teszt üzenet")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_file.exists()
    assert "teszt üzenet" in log_file.read_text(encoding="utf-8")


def test_console_handler_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="WARNING")
    logger = logging.getLogger("hangoskonyv.test.level")

    logger.info("ez nem jelenik meg")
    logger.warning("ez megjelenik")

    captured = capsys.readouterr()
    assert "ez nem jelenik meg" not in captured.out
    assert "ez megjelenik" in captured.out


def test_third_party_loggers_silenced_by_default() -> None:
    configure_logging(level="DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
