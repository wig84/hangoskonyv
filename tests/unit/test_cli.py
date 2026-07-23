"""Tesztek a hangoskonyv CLI-hez.

Mivel a valódi Piper TTS motor nem áll rendelkezésre ebben a
fejlesztői környezetben, egy determinisztikus `CountingFakeTTS`
motort regisztrálunk a `TTSFactory`-ba "fake" néven — ez ugyanazt
a `synthesize`-hívásokat számoló mintát követi, mint a
`tests/unit/conftest.py`-beli `FakeTTS`, de osztályszintű
számlálóval, hogy a CLI két külön (alfolyamatszerű) hívása között
is meg tudjuk figyelni a cache-viselkedést.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest
from click.testing import CliRunner

import hangoskonyv.tts.factory as factory_module
from hangoskonyv.cli.main import cli
from hangoskonyv.tts.base import AbstractTTS, AudioSegment

FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "sample_books" / "Cixin_Liu_-_Gömbvillám.epub"
)


class CountingFakeTTS(AbstractTTS):
    call_count = 0

    @property
    def supports_ssml(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True

    def synthesize(self, content: str, voice) -> AudioSegment:
        type(self).call_count += 1
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 10)
        return AudioSegment(
            audio_bytes=buffer.getvalue(), sample_rate=16000, sample_width=2, channels=1
        )


@pytest.fixture(autouse=True)
def _register_fake_engine():
    """A "fake" motort regisztrálja minden teszt előtt, és nullázza a számlálót."""
    CountingFakeTTS.call_count = 0
    factory_module._ENGINES["fake"] = CountingFakeTTS
    yield
    del factory_module._ENGINES["fake"]


@pytest.fixture
def fake_model(tmp_path: Path) -> Path:
    model = tmp_path / "hang.onnx"
    model.write_bytes(b"nem valodi onnx tartalom")
    return model


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestConvertSuccess:
    def test_creates_output_files_for_every_chapter(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "kimenet"
        result = runner.invoke(
            cli,
            [
                "convert", str(FIXTURE_PATH),
                "--output", str(output_dir),
                "--voice-model", str(fake_model),
                "--engine", "fake",
                "--cache-dir", str(tmp_path / "cache"),
                "--log-level", "WARNING",
            ],
        )

        assert result.exit_code == 0
        output_files = sorted(output_dir.iterdir())
        assert len(output_files) == 35

    def test_filenames_start_with_zero_padded_index(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "kimenet"
        runner.invoke(
            cli,
            [
                "convert", str(FIXTURE_PATH),
                "--output", str(output_dir),
                "--voice-model", str(fake_model),
                "--engine", "fake",
                "--cache-dir", str(tmp_path / "cache"),
                "--log-level", "WARNING",
            ],
        )
        first_file = sorted(output_dir.iterdir())[0]
        assert first_file.name.startswith("01_")
        assert "ELŐSZÓ" in first_file.name

    def test_book_metadata_printed(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "convert", str(FIXTURE_PATH),
                "--output", str(tmp_path / "kimenet"),
                "--voice-model", str(fake_model),
                "--engine", "fake",
                "--cache-dir", str(tmp_path / "cache"),
                "--log-level", "WARNING",
            ],
        )
        assert "Gömbvillám" in result.output
        assert "Cixin Liu" in result.output


class TestConvertCaching:
    def test_second_run_does_not_resynthesize(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        args = [
            "convert", str(FIXTURE_PATH),
            "--output", str(tmp_path / "kimenet"),
            "--voice-model", str(fake_model),
            "--engine", "fake",
            "--cache-dir", str(tmp_path / "cache"),
            "--log-level", "WARNING",
        ]

        runner.invoke(cli, args)
        first_run_calls = CountingFakeTTS.call_count

        runner.invoke(cli, args)
        second_run_calls = CountingFakeTTS.call_count

        assert first_run_calls == 35
        assert second_run_calls == 35  # nem nőtt


class TestConvertErrorHandling:
    def test_unsupported_format_exits_nonzero(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        bad_file = tmp_path / "valami.mobi"
        bad_file.write_bytes(b"x")

        result = runner.invoke(
            cli, ["convert", str(bad_file), "--voice-model", str(fake_model), "--engine", "fake"]
        )

        assert result.exit_code != 0
        assert "Hiba" in result.output

    def test_unknown_engine_exits_nonzero(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "convert", str(FIXTURE_PATH),
                "--voice-model", str(fake_model),
                "--engine", "nemletezik",
                "--output", str(tmp_path / "kimenet"),
                "--cache-dir", str(tmp_path / "cache"),
            ],
        )

        assert result.exit_code != 0
        assert "Ismeretlen TTS motor" in result.output

    def test_missing_input_file_exits_nonzero(
        self, runner: CliRunner, fake_model: Path, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "convert", str(tmp_path / "nincs_ilyen.epub"),
                "--voice-model", str(fake_model),
                "--engine", "fake",
            ],
        )
        assert result.exit_code != 0

    def test_missing_voice_model_exits_nonzero(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            cli,
            [
                "convert", str(FIXTURE_PATH),
                "--voice-model", str(tmp_path / "nincs.onnx"),
                "--engine", "fake",
            ],
        )
        assert result.exit_code != 0


class TestCliHelp:
    def test_convert_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["convert", "--help"])
        assert result.exit_code == 0

    def test_top_level_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
