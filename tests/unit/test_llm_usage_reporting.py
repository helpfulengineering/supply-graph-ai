"""A run must say whether an LLM contributed, and why not when it did not.

Generation degrades to direct + heuristic + NLP whenever no LLM is usable, and
that was invisible outside the logs — a reviewer could not tell a thin manifest
from a missing provider. Declared availability is not proof either: a stored key
can be expired, a named local model can be down. So this reports what HAPPENED.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.generation.models import LayerConfig
from src.core.generation.quality import (
    LLMUsageStatus,
    llm_usage_recommendation,
    summarize_llm_usage,
)
from src.core.llm.availability import LLMAvailability, LLMUnavailableReason

pytestmark = pytest.mark.unit


def _available(provider="anthropic"):
    return LayerConfig.for_generate_from_url().with_llm_availability(
        LLMAvailability(available=True, provider=provider)
    )


def _unavailable(reason):
    return LayerConfig.for_generate_from_url().with_llm_availability(
        LLMAvailability.unavailable(reason)
    )


# --- What actually happened --------------------------------------------------


def test_a_run_that_used_the_llm_says_so_and_names_the_provider():
    summary = summarize_llm_usage(_available("openai"), {"llm": 1}, {})

    assert summary["llm_used"] is True
    assert summary["llm_status"] == LLMUsageStatus.USED
    assert summary["llm_provider"] == "openai"


def test_no_provider_configured_is_reported_as_such():
    summary = summarize_llm_usage(
        _unavailable(LLMUnavailableReason.NOT_CONFIGURED), {"direct": 1}, {}
    )

    assert summary["llm_used"] is False
    assert summary["llm_status"] == LLMUsageStatus.NOT_CONFIGURED


def test_the_kill_switch_is_distinguished_from_a_missing_credential():
    """'Disabled' and 'not configured' need different fixes."""
    summary = summarize_llm_usage(
        _unavailable(LLMUnavailableReason.DISABLED), {"direct": 1}, {}
    )

    assert summary["llm_status"] == LLMUsageStatus.DISABLED


def test_opting_out_is_not_reported_as_a_problem():
    summary = summarize_llm_usage(
        LayerConfig.for_generate_from_url(no_llm=True), {"direct": 1}, {}
    )

    assert summary["llm_status"] == LLMUsageStatus.NOT_REQUESTED


def test_a_configured_provider_that_failed_is_distinguished_from_one_never_reached():
    """Neither leaves a usage count, so the engine's error count separates them.

    A stored key can be expired and a local model can be down; reporting that as
    'not configured' would send someone to fix the wrong thing.
    """
    failed = summarize_llm_usage(_available(), {"direct": 1}, {"llm": 1})
    skipped = summarize_llm_usage(_available(), {"direct": 1}, {})

    assert failed["llm_status"] == LLMUsageStatus.FAILED
    assert skipped["llm_status"] == LLMUsageStatus.SKIPPED
    assert failed["llm_used"] is False and skipped["llm_used"] is False


def test_the_provider_is_not_claimed_for_a_run_that_did_not_use_it():
    summary = summarize_llm_usage(_available("anthropic"), {"direct": 1}, {"llm": 1})

    assert summary["llm_provider"] is None


# --- What the reviewer sees --------------------------------------------------


def test_a_degraded_run_explains_itself_in_plain_language():
    summary = summarize_llm_usage(
        _unavailable(LLMUnavailableReason.NOT_CONFIGURED), {"direct": 1}, {}
    )
    note = llm_usage_recommendation(summary)

    assert note is not None
    assert "without an LLM" in note
    assert "function" in note  # the field this actually costs the user


def test_a_failed_provider_is_told_to_check_the_credential_not_to_add_one():
    note = llm_usage_recommendation(
        summarize_llm_usage(_available(), {"direct": 1}, {"llm": 1})
    )

    assert note is not None and "could not be reached" in note


def test_a_successful_run_says_nothing():
    assert (
        llm_usage_recommendation(summarize_llm_usage(_available(), {"llm": 1}, {}))
        is None
    )


def test_deliberate_choices_are_not_nagged_about():
    """Telling someone who passed no_llm that they got no LLM is noise; so is
    reporting progressive enhancement stopping early, which is a success."""
    opted_out = summarize_llm_usage(
        LayerConfig.for_generate_from_url(no_llm=True), {"direct": 1}, {}
    )
    stopped_early = summarize_llm_usage(_available(), {"direct": 1}, {})

    assert llm_usage_recommendation(opted_out) is None
    assert llm_usage_recommendation(stopped_early) is None


def test_the_kill_switch_gets_its_own_explanation():
    note = llm_usage_recommendation(
        summarize_llm_usage(
            _unavailable(LLMUnavailableReason.DISABLED), {"direct": 1}, {}
        )
    )

    assert note is not None and "LLM_ENABLED" in note


# --- The engine supplies the evidence ----------------------------------------


@pytest.mark.asyncio
async def test_the_engine_records_a_layer_that_raised():
    """Without this evidence, 'failed' and 'skipped' are indistinguishable.

    Exercises the real loop with a matcher that raises, rather than asserting
    the recording code merely exists.
    """
    from unittest.mock import AsyncMock

    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import GenerationLayer

    engine = GenerationEngine(config=_available())
    exploding = AsyncMock(side_effect=RuntimeError("provider unreachable"))
    engine._matchers = {GenerationLayer.LLM: AsyncMock(process=exploding)}

    await engine._progressive_enhancement_async(object(), {}, {}, [])

    metrics = engine.get_metrics()
    assert metrics.error_counts.get("llm") == 1
    assert metrics.layer_usage_counts.get("llm", 0) == 0

    # And that evidence produces the FAILED status rather than SKIPPED.
    summary = summarize_llm_usage(
        _available(), metrics.layer_usage_counts, metrics.error_counts
    )
    assert summary["llm_status"] == LLMUsageStatus.FAILED
