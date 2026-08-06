# hangoskonyv

Magyar nyelvű e-könyv felolvasó alkalmazás. A cél nem egy sima
text-to-speech eszköz, hanem egy olyan pipeline, amely a lehető
legtermészetesebben olvassa fel a magyar nyelvű könyveket.

## Fejlesztési státusz

**Fázis 1 – CLI MVP** ✅ **kész**

- [x] **1. iteráció** – Core domain modell, exception hierarchia, logging
- [x] **2. iteráció** – EPUB parser
- [x] **3. iteráció** – Magyar nyelvi feldolgozás (nlp modul)
- [x] **4. iteráció** – Piper TTS integráció
- [x] **5. iteráció** – Audio cache és generátor
- [x] **6. iteráció** – CLI belépési pont
- [x] **7. iteráció** – SSML fallback (szünet-finomhangolás, hármaspont-javítás)
- [x] **8. iteráció** – SQLite perzisztencia réteg (könyvtár, könyvjelzők, lejátszási állapot)

**Fázis 2 – Természetesebb hangsúlyozás** (folyamatban; a projekt tudatosan
**CLI-only** marad, nincs tervezett GUI)

- [x] **9. iteráció** – CLI ASCII banner (paraméter nélküli indításkor gyors
  áttekintés a legfontosabb kapcsolókról, példákkal)
- [ ] 10. iteráció – Érzelem-/hangsúly-felismerés (`ai` modul) — a már meglévő,
  eddig kihasználatlan `Sentence.emotion` mező tényleges feltöltése
- [ ] 11. iteráció – A felismerés bekötése a szintézisbe (Piper
  `noise_scale`/`noise_w_scale`/`length_scale` mondatonkénti finomhangolása)

**Fázis 3+ – további bővítés** (később)

- PDF/MOBI/TXT parserek, plugin rendszer, XTTS (hangklónozás), ElevenLabs

## Használat

```bash
pip install -e ".[dev]"

# Piper hangmodell letöltése (magyar hang, ha elérhető; a pontos
# elnevezés a Piper hangkatalógusától függ, ellenőrizd a
# python3 -m piper.download_voices --help kimenetét):
python3 -m piper.download_voices hu_HU-imre-medium

hangoskonyv convert konyv.epub --voice-model hu_HU-imre-medium.onnx -o ./hangok
```

Ismételt futtatáskor a változatlan fejezetek a gyorsítótárból
(`./cache`) érkeznek, nem generálódnak újra.

### Tesztelés egyetlen fejezeten

Mielőtt egy egész könyvet legenerálnál (ami hosszú percekig/órákig is
eltarthat), érdemes egyetlen fejezeten kipróbálni egy hangbeállítást:

```bash
hangoskonyv chapters konyv.epub                 # fejezetek listája, sorszámmal
hangoskonyv convert konyv.epub --voice-model hang.onnx --chapter 3
```

### MP3 export

Alapból WAV-ot ad ki; MP3-hoz add meg a `--format mp3` kapcsolót
(ehhez az `ffmpeg` parancssori eszköz szükséges a rendszeren —
Ubuntu/Debianon: `sudo apt install ffmpeg`):

```bash
hangoskonyv convert konyv.epub --voice-model hang.onnx --format mp3
```

### Szünet-finomhangolás (SSML fallback)

Mivel a Piper nem támogat SSML-t, a rendszer mondat-szinten
szegmentálja a szöveget, és a darabok közé explicit csendet szúr be
(lásd `ssml/fallback.py`). Ez orvosolja, hogy a hármaspontot ("...")
a Piper szó szerint, "pont pont pont"-ként olvasná fel — helyette
hosszabb szünet lesz a helyén —, és hogy mondatvégeken/kérdéseknél
kicsit hosszabb, természetesebb szünet legyen.

A `--comma-pauses` kapcsolóval a vesszőknél is extra szünet
kérhető, de ez **jelentősen megnöveli a TTS-hívások számát**
(egy átlagos regénynél nagyságrendekkel), ami a generálási időt is
arányosan megnyújthatja. Érdemes előbb egy rövid fejezeten
kipróbálni, mielőtt egy egész könyvre bekapcsolod:

```bash
hangoskonyv convert konyv.epub --voice-model hang.onnx -o ./teszt --comma-pauses
```

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
    persistence/      # SQLite (stdlib sqlite3) réteg: könyvtár, könyvjelzők, állapotmentés
    config/          # Konfiguráció betöltés/mentés (TOML)
    plugins/         # Bővíthetőségi réteg
    gui/             # NEM tervezett — a projekt tudatosan CLI-only marad
    cli/             # Parancssori belépési pont (click alapú)
    utils/           # Segédfunkciók (logging, hashing, fájlnév-tisztítás)
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
