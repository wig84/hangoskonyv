"""Magyar nyelvi feldolgozás: mondatbontás, típus-/beszélő-felismerés,
szám-/dátum-/mértékegység-normalizálás."""

from hangoskonyv.nlp.dialogue_detector import detect_sentence_type, extract_speaker
from hangoskonyv.nlp.normalizer import tokenize_and_normalize
from hangoskonyv.nlp.numbers import cardinal_to_words, ordinal_to_words
from hangoskonyv.nlp.preprocessor import Preprocessor
from hangoskonyv.nlp.roman_numerals import is_roman_numeral, roman_to_int
from hangoskonyv.nlp.sentence_splitter import split_sentences

__all__ = [
    "Preprocessor",
    "split_sentences",
    "detect_sentence_type",
    "extract_speaker",
    "tokenize_and_normalize",
    "cardinal_to_words",
    "ordinal_to_words",
    "is_roman_numeral",
    "roman_to_int",
]
