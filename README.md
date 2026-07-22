# hangoskonyv

Magyar nyelvű e-könyv felolvasó alkalmazás. A cél nem egy sima
text-to-speech eszköz, hanem egy olyan pipeline, amely a lehető
legtermészetesebben olvassa fel a magyar nyelvű könyveket.

## Fejlesztési státusz

**Fázis 1 – CLI MVP** (folyamatban)

- [x] **1. iteráció** – Core domain modell, exception hierarchia, logging
- [x] **2. iteráció** – EPUB parser
- [x] **3. iteráció** – Magyar nyelvi feldolgozás (nlp modul)
- [x] **4. iteráció** – Piper TTS integráció
- [x] **5. iteráció** – Audio cache és generátor
- [ ] 6. iteráció – CLI belépési pont

A GUI és a további formátumtámogatás (PDF, MOBI, TXT) csak a CLI
pipeline stabilizálása után következik.

## Projektstruktúra

```
src/hangoskonyv/
    core/           # Domain modell (Book -> Chapter -> Paragraph -> Sentence -> Token),
                     # saját exception hierarchia. Nincs külső függősége.
    parsers/         # Formátum-specifikus parserek (EPUB, később PDF/MOBI/TXT)
    nlp/             # Magyar nyelvi feldolgozás: mondatbontás, normalizálás
    ai/              # Opcionális AI elemzés (érzelem, szereplő-felismerés)
    ssml/            # SSML generálás / fallback szünet-időzítés
    tts/             # AbstractTTS és konkrét motorok (Piper, később XTTS, ElevenLabs)
    audio/           # Cache-elt hanggenerálás, lejátszó
    persistence/      # SQLite + SQLAlchemy réteg (könyvjelzők, állapotmentés)
    config/          # Konfiguráció betöltés/mentés (TOML)
    plugins/         # Bővíthetőségi réteg
    gui/             # PySide6 felület (Fázis 3)
    utils/           # Segédfunkciók (logging, hashing)
tests/
    unit/            # pytest unit tesztek
    fixtures/        # Teszt EPUB fájlok
```

## Fejlesztői környezet

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

A `pre-commit install` regisztrálja a `.pre-commit-config.yaml`-ban
leírt hook-okat: mostantól minden `git commit` előtt automatikusan
lefut a teljes teszt-csomag, és a commit megszakad, ha bármelyik
teszt elbukik.

## Tesztek futtatása

```bash
pytest tests/ -v
```

## Kódstílus

- Python 3.12+, type hint mindenhol
- PEP8, `ruff` linter
- `mypy --strict`
- Minden publikus osztály/függvény docstringet kap
