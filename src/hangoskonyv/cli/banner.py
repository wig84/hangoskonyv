"""ASCII "banner" a CLI paraméter nélküli indításához.

A cél: ha valaki csak beírja, hogy `hangoskonyv` (alparancs nélkül),
ne a nyers `click` hibaüzenetet vagy a tömör alap-help-et lássa, hanem
egy barátságos, gyors áttekintést a legfontosabb parancsokról és
kapcsolókról, példákkal. A részletes, technikai referenciát (minden
kapcsoló, típus, alapérték) továbbra is a `--help` adja.

A doboz szélét és a tartalom igazítását programmatikusan (nem kézzel
beírt szóközökkel) építjük fel — ez kizárja az elgépelt/elcsúszott
szegély kockázatát, függetlenül attól, hogy a szöveg pontosan hány
karakter hosszú.
"""

from __future__ import annotations

_BOX_WIDTH = 78
_CONTENT_WIDTH = _BOX_WIDTH - 4  # "│ " + tartalom + " │"


def _box(lines: list[str]) -> str:
    horizontal = "─" * (_BOX_WIDTH - 2)
    top = f"┌{horizontal}┐"
    bottom = f"└{horizontal}┘"
    body_lines = []
    for line in lines:
        if len(line) > _CONTENT_WIDTH:
            raise ValueError(
                f"A banner sora túl hosszú ({len(line)} > {_CONTENT_WIDTH}): {line!r}"
            )
        body_lines.append(f"│ {line.ljust(_CONTENT_WIDTH)} │")
    return "\n".join([top, *body_lines, bottom])


def render_banner() -> str:
    """Az indító képernyőn megjelenő ASCII doboz teljes szövege."""
    lines = [
        "",
        "  ▁▂▃▅▇█  H A N G O S K Ö N Y V  █▇▅▃▂▁",
        "  Magyar nyelvű e-könyv felolvasó — EPUB-ból hangoskönyv",
        "",
        "  Gyors kezdés",
        "  ────────────",
        "",
        "  Alap konvertálás:",
        "    hangoskonyv convert konyv.epub --voice-model hang.onnx",
        "",
        "  Egyéni kimeneti mappa:",
        "    hangoskonyv convert konyv.epub --voice-model hang.onnx -o ./hangok",
        "",
        "  Természetesebb szünetek vesszőknél (lassabb generálás):",
        "    hangoskonyv convert konyv.epub --voice-model hang.onnx --comma-pauses",
        "",
        "  Gyorsabb/lassabb felolvasás (1.0 = normál):",
        "    hangoskonyv convert konyv.epub --voice-model hang.onnx --speed 1.2",
        "",
        "  Hangmodell letöltése (Piper, ha még nincs):",
        "    python3 -m piper.download_voices hu_HU-anna-medium",
        "",
        "  Gyors teszt egyetlen fejezeten (nem kell az egészet generálni):",
        "    hangoskonyv chapters konyv.epub",
        "    hangoskonyv convert konyv.epub --voice-model hang.onnx --chapter 3",
        "",
        "  Részletes súgó (minden kapcsoló):",
        "    hangoskonyv convert --help",
        "",
    ]
    return _box(lines)


def render_cheatsheet() -> str:
    """Rejtett (nem dokumentált) puska: a leggyakrabban elfelejtett
    git/teszt parancsok, egy helyen.

    Elérése: `hangoskonyv --cheatsheet` — szándékosan nem jelenik meg
    a `--help`-ben (ez egy személyes, kényelmi gyorsreferencia, nem a
    hivatalos API része).
    """
    lines = [
        "",
        "  hangoskonyv — parancs-puska",
        "",
        "  Bundle behozása (a Claude-tól kapott .bundle fájlból):",
        "    cd ~/Projects/hangoskonyv",
        "    git pull <bundle_fájl_elérési_útja> main",
        "",
        "  Feltöltés GitHub-ra (kód + tag-ek):",
        "    git push",
        "    git push --tags",
        "",
        "  Saját változtatás mentése:",
        "    git add -A",
        "    git commit -m \"üzenet\"",
        "",
        "  Mit tartalmaz az utolsó commit:",
        "    git log -1 -p",
        "",
        "  Tesztek futtatása:",
        "    pytest tests/ -v",
        "",
        "  pre-commit hook telepítése (egyszer, klónozás után):",
        "    pre-commit install",
        "",
        "  Fejezetek listázása / egy fejezet tesztelése:",
        "    hangoskonyv chapters konyv.epub",
        "    hangoskonyv convert konyv.epub --voice-model h.onnx --chapter 3",
        "",
    ]
    return _box(lines)
