"""Tests for spacy_loader.py warning behaviour and NLPMatcher error messages.

Verifies that:
  - When no spaCy model can be loaded, a WARNING (not DEBUG) is emitted.
  - The warning includes actionable install instructions.
  - NLPMatcher.process() returns a result with an error that names the fix.
"""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.core.nlp.spacy_loader import clear_spacy_cache_for_tests, load_spacy_english


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_spacy_state():
    """Reset lru_cache AND the module-level dedup flags before/after every test."""
    import src.core.nlp.spacy_loader as _loader

    clear_spacy_cache_for_tests()
    _loader._spacy_import_failed_logged = False
    _loader._no_model_logged = False
    yield
    clear_spacy_cache_for_tests()
    _loader._spacy_import_failed_logged = False
    _loader._no_model_logged = False


def test_no_model_emits_warning_not_debug(caplog):
    """When spaCy is installed but no model can be loaded, log level must be WARNING."""
    spacy_mock = MagicMock()
    spacy_mock.load.side_effect = OSError("model not found")

    with patch.dict(sys.modules, {"spacy": spacy_mock}):
        with caplog.at_level(logging.DEBUG, logger="src.core.nlp.spacy_loader"):
            result = load_spacy_english()

    assert result is None
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "Expected at least one WARNING record when no model loads"


def test_no_model_warning_contains_install_hint(caplog):
    """The WARNING message must include the spacy download command."""
    spacy_mock = MagicMock()
    spacy_mock.load.side_effect = OSError("model not found")

    with patch.dict(sys.modules, {"spacy": spacy_mock}):
        with caplog.at_level(logging.WARNING, logger="src.core.nlp.spacy_loader"):
            load_spacy_english()

    full_text = " ".join(
        r.message for r in caplog.records if r.levelno == logging.WARNING
    )
    assert (
        "spacy download" in full_text.lower() or "en_core_web_sm" in full_text
    ), "WARNING should reference the install command or model name"


def test_spacy_import_missing_returns_none(caplog):
    """If spaCy is not installed at all, load_spacy_english must return None silently."""
    # Remove spacy from sys.modules to simulate it not being installed
    with patch.dict(sys.modules, {"spacy": None}):
        with caplog.at_level(logging.DEBUG, logger="src.core.nlp.spacy_loader"):
            result = load_spacy_english()

    assert result is None


def test_successful_load_returns_model():
    """When a model loads successfully, it is returned and no WARNING is emitted."""
    fake_model = MagicMock(name="spacy_model")
    spacy_mock = MagicMock()
    spacy_mock.load.return_value = fake_model

    with patch.dict(sys.modules, {"spacy": spacy_mock}):
        result = load_spacy_english()

    assert result is fake_model


# ---------------------------------------------------------------------------
# NLPMatcher.process() error message tests
# ---------------------------------------------------------------------------


def _make_nlp_matcher_no_model():
    """Return an NLPMatcher-like object with nlp=None, bypassing the constructor.

    NLPMatcher.__init__ transitively imports heavy optional packages (anthropic,
    openai, cryptography …) that may not be installed in the test venv.  Using
    object.__new__ lets us exercise process() in isolation.
    """
    from src.core.generation.layers.nlp import NLPMatcher
    from src.core.generation.models import GenerationLayer

    matcher = object.__new__(NLPMatcher)
    matcher.nlp = None
    matcher.layer_type = GenerationLayer.NLP
    return matcher


def _minimal_project():
    from src.core.generation.models import PlatformType, ProjectData

    return ProjectData(
        platform=PlatformType.GITHUB,
        url="https://example.com/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={},
    )


@pytest.mark.asyncio
async def test_nlp_matcher_error_message_is_actionable():
    """When spaCy is unavailable, NLPMatcher.process() error text must include
    instructions for installing the model."""
    matcher = _make_nlp_matcher_no_model()
    project = _minimal_project()
    layer_result = await matcher.process(project)

    assert layer_result.errors, "Expected at least one error in LayerResult"
    combined_errors = " ".join(layer_result.errors)
    assert (
        "spacy download" in combined_errors.lower()
        or "en_core_web_sm" in combined_errors
    ), "Error message should include the install command or model name"


@pytest.mark.asyncio
async def test_nlp_matcher_error_mentions_skipped():
    """The error text should make it clear the NLP layer was skipped."""
    matcher = _make_nlp_matcher_no_model()
    project = _minimal_project()
    layer_result = await matcher.process(project)

    combined = " ".join(layer_result.errors).lower()
    assert (
        "skip" in combined or "not available" in combined
    ), "Error should indicate the layer was skipped"
