"""EPUB fájlok feldolgozása `Book` domain modellé.

Az EPUB lényegében egy ZIP-konténer, benne XHTML fájlokkal és
XML-alapú metaadat-/navigációs fájlokkal. Ez a modul nem a
`ebooklib` külső könyvtárra épít, hanem közvetlenül a szabványos
EPUB-belső fájlokat (`META-INF/container.xml`, a csomag-leíró OPF
fájl, valamint a `toc.ncx` navigációs fájl) dolgozza fel a beépített
`zipfile` és a már amúgy is használt `lxml`/`beautifulsoup4`
könyvtárakkal.

Ez a döntés (részletesen lásd a modul végén levő megjegyzést)
teljes kontrollt ad afölött, hogyan alakul át a nyers HTML a
strukturált dokumentummodellé — ami kritikus, mert pont ez a
későbbi (nlp, ssml) rétegek alapja.

Fő feldolgozási lépések:

1. `container.xml` -> a csomag-leíró (OPF) fájl helye
2. OPF fájl -> metaadatok (cím, szerző, nyelv), manifest (id -> href),
   spine (a fejezetek olvasási sorrendje)
3. `toc.ncx` -> fejezetcímek, a spine bejegyzésekhez rendelve
4. Minden, a toc.ncx-ben cím nélküli spine-bejegyzés (pl. címlap,
   fordítói jegyzet, kiadói ajánló) NEM válik fejezetté — ha egy
   tartalom nem szerepel a könyv saját navigációs szerkezetében,
   feltételezzük, hogy nem narratív tartalom.
5. A megmaradt fejezeteken lefut a `ChapterFilter`, ami a címben
   felismerhető (pl. "Borító", "Copyright") és az elhanyagolhatóan
   rövid (pl. rész-elválasztó oldalak, mint "ELSŐ RÉSZ") fejezeteket
   is kiszűri.
"""

from __future__ import annotations

import logging
import posixpath
import warnings
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from lxml import etree

# A valós EPUB-okban gyakori, hogy a fejezet-XHTML fájlok XML-deklarációval
# kezdődnek (<?xml version='1.0' ...?>), miközben a tartalmuk gyakorlatilag
# HTML-ként is jól feldolgozható (és sok "vadon élő" EPUB direkt HTML4/5
# szintaktikai hibákat is tartalmaz, amit egy szigorú XML parser elutasítana).
# Ezért szándékosan az "lxml" HTML parsert használjuk a `<p>` elemek
# kinyerésére, a BeautifulSoup ez esetben jogos, de itt irreleváns
# figyelmeztetését explicit módon elnémítjuk.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from hangoskonyv.core.document import Book, Chapter, Paragraph, Sentence
from hangoskonyv.core.exceptions import CorruptFileError
from hangoskonyv.parsers.base import AbstractParser
from hangoskonyv.parsers.chapter_filter import ChapterFilter
from hangoskonyv.utils.hashing import hash_file

logger = logging.getLogger(__name__)

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
_DC_NS = {"dc": "http://purl.org/dc/elements/1.1/"}
_NCX_NS = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}

_XHTML_MEDIA_TYPE = "application/xhtml+xml"


class EpubParser(AbstractParser):
    """EPUB (.epub) fájlokat dolgoz fel `Book` domain modellé."""

    def __init__(self, chapter_filter: ChapterFilter | None = None) -> None:
        """
        Args:
            chapter_filter: A fejezetszűréshez használt `ChapterFilter`.
                Ha None, egy alapértelmezett szűrőt hoz létre, amely a
                cím alapján felismerhető nem-narratív tartalmakon
                (Borító, Copyright stb.) felül az 5 szónál rövidebb
                "fejezeteket" (pl. rész-elválasztó oldalak, mint az
                "ELSŐ RÉSZ" önmagában) is kiszűri. Ez utóbbi küszöb
                jóval a valós, akár rövid fejezetek hossza alatt van,
                így valódi tartalmat gyakorlatilag nem szűr ki.
        """
        self._chapter_filter = chapter_filter or ChapterFilter(min_word_count=5)

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".epub"

    def parse(self, path: Path) -> Book:
        logger.info("EPUB feldolgozás indul: %s", path)
        try:
            with zipfile.ZipFile(path) as archive:
                self._validate_mimetype(archive, path)
                opf_path = self._read_container(archive, path)
                opf_root = self._read_xml(archive, opf_path, path)

                title, author, language = self._read_metadata(opf_root)
                manifest = self._read_manifest(opf_root)
                spine_hrefs = self._read_spine(opf_root, manifest, opf_path)
                toc_map = self._read_toc(archive, opf_root, manifest, opf_path)
                cover_image = self._read_cover(archive, opf_root, manifest, opf_path)

                chapters = self._build_chapters(archive, spine_hrefs, toc_map)
        except zipfile.BadZipFile as exc:
            raise CorruptFileError(f"A fájl nem érvényes ZIP/EPUB: {path}") from exc

        chapters = self._chapter_filter.filter_chapters(chapters)
        chapters = self._renumber(chapters)

        book = Book(
            title=title,
            author=author,
            chapters=chapters,
            language=language,
            cover_image=cover_image,
            content_hash=hash_file(path),
        )
        logger.info(
            "EPUB feldolgozva: '%s' — %d fejezet, %d szó összesen",
            book.title,
            book.chapter_count,
            book.total_word_count,
        )
        return book

    # -- Belső feldolgozási lépések ----------------------------------------

    @staticmethod
    def _validate_mimetype(archive: zipfile.ZipFile, path: Path) -> None:
        """Ellenőrzi, hogy a ZIP valóban EPUB-e (mimetype bejegyzés)."""
        try:
            mimetype = archive.read("mimetype").decode("ascii").strip()
        except KeyError as exc:
            raise CorruptFileError(
                f"Hiányzó 'mimetype' bejegyzés, nem valódi EPUB: {path}"
            ) from exc
        if mimetype != "application/epub+zip":
            raise CorruptFileError(
                f"Váratlan mimetype ('{mimetype}'), nem valódi EPUB: {path}"
            )

    @staticmethod
    def _read_container(archive: zipfile.ZipFile, path: Path) -> str:
        """A META-INF/container.xml-ből kiolvassa az OPF fájl elérési útját."""
        try:
            container_xml = archive.read("META-INF/container.xml")
        except KeyError as exc:
            raise CorruptFileError(
                f"Hiányzó META-INF/container.xml: {path}"
            ) from exc

        root = etree.fromstring(container_xml)
        rootfile = root.find(".//c:rootfile", _CONTAINER_NS)
        if rootfile is None or not rootfile.get("full-path"):
            raise CorruptFileError(
                f"Nem található rootfile hivatkozás a container.xml-ben: {path}"
            )
        return rootfile.get("full-path")

    @staticmethod
    def _read_xml(archive: zipfile.ZipFile, member_path: str, path: Path) -> etree._Element:
        try:
            data = archive.read(member_path)
        except KeyError as exc:
            raise CorruptFileError(f"Hiányzó fájl az EPUB-on belül: {member_path}") from exc
        try:
            return etree.fromstring(data)
        except etree.XMLSyntaxError as exc:
            raise CorruptFileError(f"Érvénytelen XML: {member_path} ({path})") from exc

    @staticmethod
    def _read_metadata(opf_root: etree._Element) -> tuple[str, str, str]:
        title_el = opf_root.find(".//dc:title", _DC_NS)
        creator_el = opf_root.find(".//dc:creator", _DC_NS)
        language_el = opf_root.find(".//dc:language", _DC_NS)

        title = (title_el.text or "").strip() if title_el is not None else "Ismeretlen cím"
        author = (
            (creator_el.text or "").strip() if creator_el is not None else "Ismeretlen szerző"
        )
        language = (language_el.text or "hu").strip() if language_el is not None else "hu"
        return title, author, language

    @staticmethod
    def _read_manifest(opf_root: etree._Element) -> dict[str, dict[str, str]]:
        """Az OPF manifest bejegyzéseit adja vissza: id -> {href, media_type}."""
        manifest: dict[str, dict[str, str]] = {}
        for item in opf_root.findall(".//opf:manifest/opf:item", _OPF_NS):
            item_id = item.get("id")
            if item_id is None:
                continue
            manifest[item_id] = {
                "href": item.get("href", ""),
                "media_type": item.get("media-type", ""),
                "properties": item.get("properties", ""),
            }
        return manifest

    @staticmethod
    def _resolve(base_member_path: str, relative_href: str) -> str:
        """Egy relatív hivatkozást az EPUB-on belüli abszolút (ZIP-belső)
        elérési úttá alakít, a `base_member_path` könyvtárához képest."""
        relative_href = relative_href.split("#", maxsplit=1)[0]
        base_dir = posixpath.dirname(base_member_path)
        return posixpath.normpath(posixpath.join(base_dir, relative_href))

    def _read_spine(
        self,
        opf_root: etree._Element,
        manifest: dict[str, dict[str, str]],
        opf_path: str,
    ) -> list[str]:
        """A spine (olvasási sorrend) alapján a XHTML fejezetfájlok
        ZIP-belső, normalizált elérési útjainak listája, sorrendben."""
        hrefs: list[str] = []
        for itemref in opf_root.findall(".//opf:spine/opf:itemref", _OPF_NS):
            idref = itemref.get("idref")
            item = manifest.get(idref or "")
            if item is None:
                continue
            if item["media_type"] != _XHTML_MEDIA_TYPE:
                continue
            hrefs.append(self._resolve(opf_path, item["href"]))
        return hrefs

    def _read_toc(
        self,
        archive: zipfile.ZipFile,
        opf_root: etree._Element,
        manifest: dict[str, dict[str, str]],
        opf_path: str,
    ) -> dict[str, str]:
        """A toc.ncx navigációs fájlból fejezetcím-térképet épít:
        ZIP-belső, normalizált elérési út -> fejezetcím.

        Üres dict-et ad vissza, ha a könyvben nincs toc.ncx (pl. tisztán
        EPUB3, nav.xhtml alapú navigációjú könyvek — ez egy ismert
        korlátozás, lásd a modul végi megjegyzést).
        """
        spine_el = opf_root.find(".//opf:spine", _OPF_NS)
        ncx_id = spine_el.get("toc") if spine_el is not None else None
        ncx_item = manifest.get(ncx_id or "")
        if ncx_item is None:
            logger.warning("Nem található toc.ncx hivatkozás, fejezetcímek üresek maradnak.")
            return {}

        ncx_path = self._resolve(opf_path, ncx_item["href"])
        try:
            ncx_data = archive.read(ncx_path)
        except KeyError:
            logger.warning("A hivatkozott toc.ncx nem található: %s", ncx_path)
            return {}

        ncx_root = etree.fromstring(ncx_data)
        toc_map: dict[str, str] = {}
        for nav_point in ncx_root.findall(".//ncx:navPoint", _NCX_NS):
            label_el = nav_point.find("./ncx:navLabel/ncx:text", _NCX_NS)
            content_el = nav_point.find("./ncx:content", _NCX_NS)
            if label_el is None or content_el is None or not content_el.get("src"):
                continue
            title = (label_el.text or "").strip()
            resolved_path = self._resolve(ncx_path, content_el.get("src"))
            toc_map.setdefault(resolved_path, title)
        return toc_map

    def _read_cover(
        self,
        archive: zipfile.ZipFile,
        opf_root: etree._Element,
        manifest: dict[str, dict[str, str]],
        opf_path: str,
    ) -> bytes | None:
        """A borítókép bájtjait olvassa ki, ha van ilyen hivatkozás."""
        cover_id = None

        cover_meta = opf_root.find(".//opf:metadata/opf:meta[@name='cover']", _OPF_NS)
        if cover_meta is not None:
            cover_id = cover_meta.get("content")

        if cover_id is None:
            for item_id, item in manifest.items():
                if "cover-image" in item.get("properties", ""):
                    cover_id = item_id
                    break

        cover_item = manifest.get(cover_id or "")
        if cover_item is None:
            return None

        cover_path = self._resolve(opf_path, cover_item["href"])
        try:
            return archive.read(cover_path)
        except KeyError:
            logger.warning("A hivatkozott borítókép nem található: %s", cover_path)
            return None

    def _build_chapters(
        self,
        archive: zipfile.ZipFile,
        spine_hrefs: list[str],
        toc_map: dict[str, str],
    ) -> list[Chapter]:
        """Fejezeteket épít a spine sorrendből, csak azokból a
        fájlokból, amikhez tartozik a toc.ncx-ben cím.

        A tervezési döntést (miért csak a toc-ban szereplő fájlok
        válnak fejezetté) lásd a modul docstringjében.
        """
        chapters: list[Chapter] = []
        for order, href in enumerate(spine_hrefs):
            title = toc_map.get(href)
            if title is None:
                logger.debug("Kihagyva (nincs toc-cím): %s", href)
                continue

            html_bytes = archive.read(href)
            paragraphs = self._extract_paragraphs(html_bytes)
            chapters.append(Chapter(title=title, paragraphs=paragraphs, order=order))
        return chapters

    @staticmethod
    def _extract_paragraphs(html_bytes: bytes) -> list[Paragraph]:
        """A `<p>` elemek szövegéből építi fel a bekezdéseket.

        Szándékosan csak a `<p>` elemeket vesszük figyelembe, a
        címsorokat (`<h1>`-`<h6>`) nem: ezek jellemzően megismétlik a
        fejezetcímet (amit már a toc.ncx-ből megkaptunk), a
        felolvasásban pedig duplikációt okoznának.

        Minden bekezdés egyelőre egyetlen (naiv) `Sentence`-ként kerül
        tárolásra a teljes bekezdés-szöveggel; a valódi, magyar nyelvi
        szabályokat alkalmazó mondatbontást az `nlp` modul végzi majd
        el egy külön feldolgozási lépésben (3. iteráció).
        """
        soup = BeautifulSoup(html_bytes, "lxml")
        paragraphs: list[Paragraph] = []
        for p_tag in soup.find_all("p"):
            text = " ".join(p_tag.get_text(separator=" ", strip=True).split())
            if not text:
                continue
            paragraphs.append(Paragraph(sentences=[Sentence(raw_text=text)]))
        return paragraphs

    @staticmethod
    def _renumber(chapters: list[Chapter]) -> list[Chapter]:
        """A szűrés után a fejezeteket 0-tól induló, folytonos sorrendbe
        rendezi újra, hogy a downstream komponensek (audio generátor,
        lejátszó) egyszerű, hézagmentes indexeléssel dolgozhassanak."""
        renumbered = []
        for new_order, chapter in enumerate(chapters):
            chapter.order = new_order
            renumbered.append(chapter)
        return renumbered


# --- Tervezési döntés: miért nem `ebooklib` -----------------------------
#
# A `ebooklib` a facto sztenderd választás lenne EPUB-hoz Pythonban,
# viszont ebben a fejlesztői környezetben (ahol ez a kód íródott)
# nincs hálózati hozzáférés, így a könyvtár nem telepíthető és nem
# tesztelhető. Emellett a saját, `zipfile` + `lxml`/`beautifulsoup4`
# alapú megoldásnak van egy tartalmi előnye is: pontosan szabályozza,
# mi számít "fejezetnek" (pl. a toc.ncx-ben nem szereplő, nem-narratív
# fájlok automatikus kihagyása), ami a strukturált dokumentummodell
# szempontjából amúgy is szükséges lett volna egy vékony `ebooklib`
# wrapper felett.
#
# Ismert korlátozás: ez a parser a `toc.ncx`-et (EPUB2 navigáció)
# várja. Tisztán EPUB3 `nav.xhtml`-t használó könyveknél a fejezetcím-
# feloldás üres eredményt ad, és minden fejezet kimarad. Ezt egy
# következő iterációban a `nav.xhtml` (EPUB3) feldolgozásának
# hozzáadásával oldjuk majd fel — a `_read_toc` metódus erre a célra
# könnyen bővíthető, mert csak a visszaadott `toc_map`
# szerkezetét kell megőrizni.
