"""Formátum-specifikus parserek: könyvfájl -> `Book` domain modell."""

from hangoskonyv.parsers.base import AbstractParser
from hangoskonyv.parsers.chapter_filter import ChapterFilter
from hangoskonyv.parsers.epub_parser import EpubParser
from hangoskonyv.parsers.factory import ParserFactory

__all__ = ["AbstractParser", "ChapterFilter", "EpubParser", "ParserFactory"]
