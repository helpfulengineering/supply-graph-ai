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
from src.core.llm.availability import (
    _recorded_active_provider as _real_recorded_active_provider,  # noqa: E402
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _no_ambient_keys(monkeypatch):
    """Tests must not depend on the developer's real .env."""
    # LLM_DEFAULT_PROVIDER especially: a developer's .env commonly sets it, and
    # an explicit choice is tried ALONE, so leaving it set would silently change
    # what every test in this file is exercising.
    for name in (
        "LLM_DEFAULT_PROVIDER",
        "OLLAMA_BASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AWS_BEDROCK_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")
    # No recorded active provider unless a test sets one. Without this the
    # lookup reaches real storage, and these tests would pass only because it
    # happens to be unconfigured on this machine.
    monkeypatch.setattr(
        "src.core.llm.availability._recorded_active_provider",
        AsyncMock(return_value=None),
    )


def _recorded(provider):
    """Patch the provider an operator chose in Settings."""
    return patch(
        "src.core.llm.availability._recorded_active_provider",
        AsyncMock(return_value=provider),
    )


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


# --- Declaring the provider on the config surface ----------------------------


@pytest.mark.asyncio
async def test_the_configured_default_provider_wins_over_preference_order(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openai")

    with _stored({"anthropic": "sk-anthropic", "openai": "sk-openai"}):
        availability = await resolve_llm_availability()

    assert availability.provider == "openai"


@pytest.mark.asyncio
async def test_a_configured_default_is_tried_alone(monkeypatch):
    """Falling back would silently serve a provider the operator did not choose."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openai")

    with _stored({"anthropic": "sk-anthropic"}):
        availability = await resolve_llm_availability()

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_a_call_site_choice_beats_the_configured_default(monkeypatch):
    """`ohm llm --provider ...` must win over the deployment's default."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "anthropic")

    with _stored({"openai": "sk-openai"}):
        availability = await resolve_llm_availability(preferred_provider="openai")

    assert availability.provider == "openai"


# --- Ollama is opt-in, never assumed -----------------------------------------


@pytest.mark.asyncio
async def test_ollama_is_usable_when_named_as_the_default(monkeypatch):
    """It has no credential to detect, so naming it IS the opt-in."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "local")

    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is True
    assert availability.provider == "local"
    assert availability.source == "ollama"


@pytest.mark.asyncio
async def test_ollama_is_usable_when_its_base_url_is_set(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "local")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box.local:11434")

    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is True


@pytest.mark.asyncio
async def test_ollama_needs_no_api_key(monkeypatch):
    """The whole point of the local path: run a model with no cloud key anywhere."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "local")

    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is True


@pytest.mark.asyncio
async def test_ollama_is_never_reached_by_preference_order():
    """Its client falls back to localhost, so auto-selecting it would make every
    node claim a local model and send every request to a dead endpoint."""
    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_setting_the_base_url_alone_opts_you_in(monkeypatch):
    """Setting it is itself a deliberate act, so it counts as opting in — but
    only the SET value ever does; the client's localhost default never has."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box.local:11434")

    with _nothing_stored():
        availability = await resolve_llm_availability()

    assert availability.available is True
    assert availability.provider == "local"


@pytest.mark.asyncio
async def test_a_cloud_credential_still_wins_over_an_available_ollama(monkeypatch):
    """Ollama joins the end of preference order, so it is the fallback, not the
    default — a node with both keeps using its configured cloud provider."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box.local:11434")

    with _stored({"anthropic": "sk-anthropic"}):
        availability = await resolve_llm_availability()

    assert availability.provider == "anthropic"


# --- The recorded active provider must reach generation ----------------------


@pytest.mark.asyncio
async def test_the_recorded_choice_beats_a_stale_default_provider(monkeypatch):
    """The third report of one bug: Settings said active, generation did not.

    An operator picked anthropic in Settings while the deployment still set
    LLM_DEFAULT_PROVIDER=openai. Because an explicit choice is tried alone and
    generation never read the recorded choice, it looked for an openai key it
    did not have and reported `not_configured` — beside a panel correctly
    showing anthropic as the active provider.
    """
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openai")

    with _recorded("anthropic"), _stored({"anthropic": "sk-anthropic"}):
        availability = await resolve_llm_availability()

    assert availability.available is True
    assert availability.provider == "anthropic"
    assert availability.source == "credential_store"


@pytest.mark.asyncio
async def test_the_environment_still_decides_when_nothing_is_recorded(monkeypatch):
    """LLM_DEFAULT_PROVIDER keeps working for deployment-configured nodes."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openai")

    with _stored({"openai": "sk-openai", "anthropic": "sk-anthropic"}):
        availability = await resolve_llm_availability()

    assert availability.provider == "openai"


@pytest.mark.asyncio
async def test_an_explicit_request_still_outranks_the_recorded_choice():
    """A per-request provider is the most specific intent there is."""
    with _recorded("anthropic"), _stored({"openai": "sk-openai"}):
        availability = await resolve_llm_availability(preferred_provider="openai")

    assert availability.provider == "openai"


@pytest.mark.asyncio
async def test_a_recorded_choice_is_tried_alone():
    """It is an explicit choice, so it gets explicit-choice semantics.

    Silently generating with a provider the operator did not pick — and billing
    them for it — is worse than reporting that the one they did pick is unusable.
    """
    with _recorded("openai"), _stored({"anthropic": "sk-anthropic"}):
        availability = await resolve_llm_availability()

    assert availability.available is False
    assert availability.reason == LLMUnavailableReason.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_unreachable_storage_yields_no_recorded_choice():
    """The lookup is best-effort, so a node with no storage still generates.

    Patching the lookup itself would replace the very try/except under test, so
    the failure has to come from storage.
    """
    broken = AsyncMock(side_effect=RuntimeError("storage down"))
    with patch("src.core.services.storage_service.StorageService.get_instance", broken):
        assert await _real_recorded_active_provider() is None
