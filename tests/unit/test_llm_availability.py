"""A key stored via Settings must actually reach generation.

Generation used to answer "is an LLM configured?" twice, differently: the gate
that admits the LLM layer read process environment variables only, while the
service that would have run it reads the encrypted credential store first. The
gate wins, so a credential set through Settings → LLM providers caused the layer
to be dropped BEFORE the service was ever constructed. The store worked;
nothing reached it.

These tests pin the single resolved answer, and the two independent bugs found
alongside it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.generation.models import LayerConfig
from src.core.llm.availability import (
    LLMAvailability,
    LLMUnavailableReason,
    resolve_llm_availability,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _no_ambient_keys(monkeypatch):
    """Tests must not depend on the developer's real .env."""
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AWS_BEDROCK_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")


def _stored(mapping):
    """Patch the credential store to return keys from `mapping`."""
    return patch(
        "src.core.llm.availability._stored_key",
        AsyncMock(side_effect=lambda provider: mapping.get(provider)),
    )


def _nothing_stored():
    return _stored({})


# --- The bug this issue exists to fix ----------------------------------------


@pytest.mark.asyncio
async def test_a_credential_stored_via_settings_makes_the_llm_available():
    """THE regression. Previously the gate never consulted the store at all."""
    with _stored({"anthropic": "sk-from-the-settings-ui"}):
        availability = await resolve_llm_availability()

    assert availability.available is True
    assert availability.provider == "anthropic"
    assert availability.source == "credential_store"


@pytest.mark.asyncio
async def test_a_stored_credential_reaches_the_generation_gate():
    """End to end through the object generation actually consults."""
    with _stored({"anthropic": "sk-stored"}):
        availability = await resolve_llm_availability()

    config = LayerConfig.for_generate_from_url().with_llm_availability(availability)

    assert config.is_llm_configured() is True
    assert config.llm_provider == "anthropic"


@pytest.mark.asyncio
async def test_an_environment_key_still_works_unchanged(monkeypatch):
    """The local `.env` workflow must not regress — Settings ALSO works now."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")

    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is True
    assert availability.source == "environment"


@pytest.mark.asyncio
async def test_the_store_wins_over_the_environment(monkeypatch):
    """An admin rotating a key through Settings should take effect."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-stale-env")

    with _stored({"anthropic": "sk-current"}):
        availability = await resolve_llm_availability()

    assert availability.source == "credential_store"


# --- Nothing configured ------------------------------------------------------


@pytest.mark.asyncio
async def test_no_credential_anywhere_means_no_llm():
    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_opting_out_short_circuits_before_touching_the_store():
    """`no_llm=true` must not pay for a storage read it cannot use."""
    store = AsyncMock()
    with patch("src.core.llm.availability._stored_key", store):
        availability = await resolve_llm_availability(requested=False)

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_REQUESTED
    store.assert_not_awaited()


# --- The master switch -------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_enabled_false_overrides_a_stored_credential(monkeypatch):
    """A kill switch: turn the LLM off without deleting credentials."""
    monkeypatch.setenv("LLM_ENABLED", "false")

    with _stored({"anthropic": "sk-still-there"}):
        availability = await resolve_llm_availability()

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.DISABLED


@pytest.mark.asyncio
async def test_llm_is_on_by_default_when_a_credential_exists(monkeypatch):
    """Configuring a provider is the enable action; the flag only disables."""
    monkeypatch.delenv("LLM_ENABLED", raising=False)

    with _stored({"anthropic": "sk-configured"}):
        availability = await resolve_llm_availability()

    assert availability.available is True


def test_the_schema_default_is_a_kill_switch_not_an_enable_switch():
    from src.config.schema import Settings

    assert Settings().llm_enabled is True


# --- Provider selection ------------------------------------------------------


@pytest.mark.asyncio
async def test_preference_order_picks_the_configured_provider():
    """With only OpenAI configured, generation must not insist on Anthropic."""
    with _stored({"openai": "sk-openai"}):
        availability = await resolve_llm_availability()

    assert availability.provider == "openai"


@pytest.mark.asyncio
async def test_an_explicitly_chosen_provider_is_never_silently_swapped():
    """A CLI `--provider openai` must not fall back to a stored Anthropic key."""
    with _stored({"anthropic": "sk-anthropic", "openai": None}):
        availability = await resolve_llm_availability(preferred_provider="openai")

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_ollama_is_not_assumed_available():
    """It defaults to localhost, so presence-based detection would claim every
    node has a local model. Explicit opt-in is a separate change."""
    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.provider != "local"


# --- The layer uses the resolved provider ------------------------------------


def test_the_generation_layer_builds_a_service_for_the_resolved_provider():
    """It hardcoded Anthropic, so a configured OpenAI key was ignored even once
    the gate let the layer run."""
    from src.core.generation.layers.llm import LLMGenerationLayer

    config = LayerConfig(use_llm=True).with_llm_availability(
        LLMAvailability(available=True, provider="openai", source="credential_store")
    )
    layer = LLMGenerationLayer(layer_config=config)

    assert layer.llm_service.config.default_provider.value == "openai"


def test_an_unknown_resolved_provider_falls_back_rather_than_crashing():
    from src.core.generation.layers.llm import LLMGenerationLayer

    config = LayerConfig(use_llm=True).with_llm_availability(
        LLMAvailability(available=True, provider="not-a-provider")
    )
    layer = LLMGenerationLayer(layer_config=config)

    assert layer.llm_service.config.default_provider.value == "anthropic"


# --- The stack cannot disagree with itself -----------------------------------


def test_an_unresolved_config_runs_without_an_llm():
    """Fail closed: a caller that never resolved must not silently get an LLM."""
    config = LayerConfig.for_generate_from_url()

    assert config.llm_available is False
    assert config.is_llm_configured() is False


def test_the_gate_and_the_enabled_layer_stack_agree():
    """Progress stages are built from the same answer the engine acts on."""
    from src.core.generation.models import GenerationLayer

    available = LayerConfig.for_generate_from_url().with_llm_availability(
        LLMAvailability(available=True, provider="anthropic")
    )
    unavailable = LayerConfig.for_generate_from_url().with_llm_availability(
        LLMAvailability.unavailable(LLMUnavailableReason.NOT_CONFIGURED)
    )

    assert available.is_llm_configured() is True
    assert GenerationLayer.LLM in available.get_enabled_layers()

    assert unavailable.is_llm_configured() is False
    assert GenerationLayer.LLM not in unavailable.get_enabled_layers()
