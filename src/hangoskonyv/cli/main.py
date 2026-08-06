"""A hangoskonyv parancssori (CLI) belépési pontja.

Ez az iteráció köti össze a teljes eddig megépített láncot:

    EPUB fájl
        -> ParserFactory / EpubParser        (2. iteráció)
        -> Preprocessor (nlp)                (3. iteráció)
        -> TTSFactory / PiperTTS             (4. iteráció)
        -> CacheManager / AudioGenerator     (5. iteráció, majd
           ssml.fallback szünet-finomhangolással bővítve)
        -> fejezetenkénti hangfájlok a kimeneti könyvtárban

A `click`-et választottuk CLI-keretrendszernek a `typer` helyett —
az indoklást lásd a `pyproject.toml` megjegyzésében: a `typer`
(és amire épül, a `rich`) nem volt telepíthető/tesztelhető ebben a
fejlesztői sandboxban, a `click` viszont igen, és beépített
progress bar-t ad külön függőség nélkül.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from hangoskonyv.audio.cache_manager import CacheManager
from hangoskonyv.audio.generator import AudioGenerator
from hangoskonyv.cli.banner import render_banner, render_cheatsheet
from hangoskonyv.core.exceptions import HangoskonyvError
from hangoskonyv.nlp.preprocessor import Preprocessor
from hangoskonyv.parsers.factory import ParserFactory
from hangoskonyv.tts.base import VoiceSettings
from hangoskonyv.tts.factory import TTSFactory
from hangoskonyv.utils.filenames import sanitize_filename
from hangoskonyv.utils.logging_config import configure_logging
from hangoskonyv.utils.mp3_export import convert_wav_to_mp3

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.version_option(package_name="hangoskonyv")
@click.option("--cheatsheet", is_flag=True, hidden=True)
@click.pass_context
def cli(ctx: click.Context, cheatsheet: bool) -> None:
    """hangoskonyv — magyar nyelvű e-könyv felolvasó, parancssori eszköz."""
    if cheatsheet:
        click.echo(render_cheatsheet())
        ctx.exit()
    if ctx.invoked_subcommand is None:
        click.echo(render_banner())


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output", "-o", "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./kimenet"), show_default=True,
    help="A legenerált hangfájlok célkönyvtára.",
)
@click.option(
    "--voice-model",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="A TTS hangmodell fájl elérési útja (Pipernél egy .onnx fájl).",
)
@click.option("--engine", default="piper", show_default=True, help="A használandó TTS motor neve.")
@click.option("--speed", type=float, default=1.0, show_default=True, help="Felolvasási sebesség szorzó.")
@click.option("--volume", type=float, default=1.0, show_default=True, help="Hangerő szorzó.")
@click.option(
    "--speaker-id", type=int, default=None,
    help="Beszélő azonosítója (több beszélős hangmodelleknél).",
)
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./cache"), show_default=True,
    help="A gyorsítótár könyvtára — ismételt futtatásnál a változatlan fejezeteket nem generálja újra.",
)
@click.option(
    "--comma-pauses/--no-comma-pauses",
    default=False,
    show_default=True,
    help=(
        "Extra szünet vesszőknél is (nem csak mondatvégeken). Finomabb "
        "szünet-vezérlés, de a mondaton belüli darabolás miatt jelentősen "
        "több TTS-hívást igényel — hosszabb könyveknél ez a generálási "
        "időt is érdemben megnövelheti. Próbáld ki előbb egy rövid "
        "fejezeten, mielőtt egy egész könyvre bekapcsolod."
    ),
)
@click.option(
    "--chapter", "chapter_number", type=int, default=None,
    help=(
        "Ha meg van adva, csak ennyiedik fejezetet konvertálja (1-től "
        "indexelve, a `hangoskonyv chapters` paranccsal listázott "
        "sorszám szerint) — az egész könyv helyett. Hasznos gyors "
        "teszteléshez egy hangbeállítás vagy szünet-finomhangolás "
        "kipróbálásakor, mielőtt az egész könyvet legenerálnád."
    ),
)
@click.option(
    "--format", "output_format", type=click.Choice(["wav", "mp3"]), default="wav",
    show_default=True,
    help="A kimeneti fájlok formátuma. Az mp3-hoz az 'ffmpeg' szükséges a rendszeren.",
)
@click.option("--log-level", default="INFO", show_default=True, help="Naplózási szint.")
@click.option(
    "--log-file", type=click.Path(dir_okay=False, path_type=Path), default=None,
    help="Ha meg van adva, a részletes (DEBUG szintű) napló ide is íródik.",
)
def convert(
    input_path: Path,
    output_dir: Path,
    voice_model: Path,
    engine: str,
    speed: float,
    volume: float,
    speaker_id: int | None,
    cache_dir: Path,
    comma_pauses: bool,
    chapter_number: int | None,
    output_format: str,
    log_level: str,
    log_file: Path | None,
) -> None:
    """A megadott e-könyvet (jelenleg: EPUB) fejezetenkénti hangfájlokká alakítja.

    Példa:

        hangoskonyv convert konyv.epub --voice-model hu_HU-voice.onnx -o ./hangok

    Egyetlen fejezet teszteléshez:

        hangoskonyv chapters konyv.epub
        hangoskonyv convert konyv.epub --voice-model hu_HU-voice.onnx --chapter 3
    """
    configure_logging(level=log_level, log_file=log_file)

    try:
        click.echo(f"Feldolgozás: {input_path}")
        parser = ParserFactory().get_parser(input_path)
        book = parser.parse(input_path)
        click.echo(f"'{book.title}' — {book.author} ({book.chapter_count} fejezet, {book.total_word_count} szó)")

        click.echo("Nyelvi előfeldolgozás (mondatbontás, normalizálás)...")
        Preprocessor().process_book(book)

        tts_engine = TTSFactory().get_engine(engine)
        voice = VoiceSettings(
            voice_model_path=voice_model, speed=speed, volume=volume, speaker_id=speaker_id
        )
        cache_manager = CacheManager(cache_root=cache_dir)
        generator = AudioGenerator(
            tts=tts_engine,
            cache_manager=cache_manager,
            voice=voice,
            split_on_commas=comma_pauses,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        chapters = book.chapters_sorted()

        if chapter_number is not None:
            if not (1 <= chapter_number <= len(chapters)):
                raise click.BadParameter(
                    f"Nincs {chapter_number}. fejezet — a könyvben {len(chapters)} "
                    f"fejezet van (1–{len(chapters)}). A fejezetek listázásához: "
                    f"hangoskonyv chapters {input_path}",
                    param_hint="'--chapter'",
                )
            selected = chapters[chapter_number - 1]
            chapters = [selected]
            click.echo(f"Csak a(z) {chapter_number}. fejezet: '{selected.title}'")

        with click.progressbar(
            chapters, length=len(chapters), label="Hanggenerálás", show_pos=True
        ) as progress:
            for chapter in progress:
                cached_path = generator.generate_chapter(book, chapter)
                base_name = f"{chapter.order + 1:02d}_{sanitize_filename(chapter.title)}"
                wav_path = output_dir / f"{base_name}{cached_path.suffix}"
                shutil.copyfile(cached_path, wav_path)

                if output_format == "mp3":
                    mp3_path = output_dir / f"{base_name}.mp3"
                    convert_wav_to_mp3(wav_path, mp3_path)
                    wav_path.unlink()

        click.secho(
            f"Kész! {len(chapters)} fejezet mentve ide: {output_dir}", fg="green"
        )

    except HangoskonyvError as exc:
        click.secho(f"Hiba: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc


@cli.command(name="chapters")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def list_chapters(input_path: Path) -> None:
    """Kilistázza egy könyv fejezeteit (sorszám, cím, szószám) — TTS nélkül, gyorsan.

    A sorszámok a `convert --chapter N` kapcsolóhoz igazodnak, tehát ha
    csak egyetlen fejezetet szeretnél tesztelni, itt nézd meg, melyik
    számot add meg.

    Példa:

        hangoskonyv chapters konyv.epub
    """
    try:
        book = ParserFactory().get_parser(input_path).parse(input_path)
    except HangoskonyvError as exc:
        click.secho(f"Hiba: {exc}", fg="red", err=True)
        raise SystemExit(1) from exc

    click.echo(f"'{book.title}' — {book.author} ({book.chapter_count} fejezet)\n")
    for chapter in book.chapters_sorted():
        click.echo(f"  {chapter.order + 1:3d}. {chapter.title}  ({chapter.word_count} szó)")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
