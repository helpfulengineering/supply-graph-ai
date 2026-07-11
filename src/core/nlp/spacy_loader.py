"""
Load spaCy English pipelines with predictable fallbacks.

Environment
-----------
``OHM_SPACY_MODELS``
    Comma-separated list of model names to try, in order.
    Default: ``en_core_web_md,en_core_web_lg,en_core_web_sm``

    Prefer ``en_core_web_md`` (bundled word vectors). ``en_core_web_sm`` has no
    vectors and is only a last-resort fallback.

If no model loads, returns ``None``; callers should disable NLP features without
printing to stdout (use logging).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODELS = "en_core_web_md,en_core_web_lg,en_core_web_sm"
_spacy_import_failed_logged = False
_no_model_logged = False


def _model_candidates() -> List[str]:
    raw = os.environ.get("OHM_SPACY_MODELS", _DEFAULT_MODELS)
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
            "Preferred model is en_core_web_md (with word vectors), installed via "
            "`uv sync` / the project lockfile. "
            "Or set OHM_SPACY_MODELS to a comma-separated list of installed model names.",
            ", ".join(_model_candidates()),
        )
        _no_model_logged = True
    return None


def clear_spacy_cache_for_tests() -> None:
    """Drop the process cache (tests only)."""
    load_spacy_english.cache_clear()
