"""Optional NLP utilities (spaCy loading, etc.)."""

from .spacy_loader import clear_spacy_cache_for_tests, load_spacy_english

__all__ = ["load_spacy_english", "clear_spacy_cache_for_tests"]
