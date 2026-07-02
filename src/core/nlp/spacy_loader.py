"""
Load spaCy English pipelines with predictable fallbacks.

Environment
-----------
``OHM_SPACY_MODELS``
    Comma-separated list of model names to try, in order.
    Default: ``en_core_web_sm,en_core_web_md,en_core_web_lg``

If no model loads, returns ``None``; callers should disable NLP features without
printing to stdout (use logging at debug level).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_spacy_import_failed_logged = False
_no_model_logged = False


def _model_candidates() -> List[str]:
    raw = os.environ.get(
        "OHM_SPACY_MODELS", "en_core_web_sm,en_core_web_md,en_core_web_lg"
    )
    return [p.strip() for p in raw.split(",") if p.strip()]


@lru_cache(maxsize=1)
def load_spacy_english() -> Optional[Any]:
    """
    Return a loaded ``spacy.Language`` for English, or ``None`` if unavailable.

    Cached for the process so repeated service initializations do not re-try
    every model or spam logs.
    """
    global _spacy_import_failed_logged, _no_model_logged

    try:
        import spacy
    except ImportError:
        if not _spacy_import_failed_logged:
            logger.debug(
                "spaCy is not installed; NLP features that need it are disabled. "
                "Install the `spacy` package if you need the NLP generation layer."
            )
            _spacy_import_failed_logged = True
        return None

    for name in _model_candidates():
        try:
            nlp = spacy.load(name)
            logger.debug("Loaded spaCy model %r", name)
            return nlp
        except OSError:
            logger.debug("spaCy model %r not installed or not loadable", name)

    if not _no_model_logged:
        logger.warning(
            "No spaCy English model could be loaded (tried: %s). "
            "NLP-based generation/matching will use regex fallbacks. "
            "To enable full NLP: python -m spacy download en_core_web_sm "
            "(or set OHM_SPACY_MODELS to a comma-separated list of installed model names).",
            ", ".join(_model_candidates()),
        )
        _no_model_logged = True
    return None


def clear_spacy_cache_for_tests() -> None:
    """Drop the process cache (tests only)."""
    load_spacy_english.cache_clear()
