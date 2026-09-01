"""One mechanism decides which LLM provider is used, for every caller.

Two used to. Generation read the encrypted credential store first, then the
environment. The `ohm llm` CLI read the environment only, probed ollama over the
network against a hardcoded localhost address, and fell through to auto-detection
when an explicit choice was unavailable.

So a credential stored through Settings reached generation but was invisible to
the CLI: `ohm llm` reported no provider on a node that was generating happily
with one. That is the same one-concept-two-surfaces defect the LLM work set out
to remove, relocated rather than fixed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.llm.availability import LLMAvailability, LLMUnavailableReason
from src.core.llm.providers.base import LLMProviderType
from src.core.llm.provider_selection import (
    create_llm_service_with_selection,
    get_provider_selector,
)

pytestmark = pytest.mark.unit


def _resolves_to(availability):
    return patch(
        "src.core.llm.availability.resolve_llm_availability",
        AsyncMock(return_value=availability),
    )


def _stored(mapping):
    return patch(
        "src.core.llm.availability._stored_key",
        AsyncMock(side_effect=lambda provider: mapping.get(provider)),
    )


@pytest.fixture(autouse=True)
def _no_real_service():
    """The subject is the decision, not constructing a live provider client."""
    with patch("src.core.llm.service.LLMService.initialize", AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def _no_recorded_provider():
    """No provider chosen in Settings unless a test says so.

    Resolution consults the credential store for the recorded active provider,
    which on a developer machine is a real directory (``LOCAL_STORAGE_PATH``
    from ``.env``). Left alone, these tests read whatever that node happens to
    have chosen — and a recorded choice is tried ALONE, so one stray record
    changes what every test here resolves.
    """
    with patch(
        "src.core.llm.availability._recorded_active_provider",
        AsyncMock(return_value=None),
    ):
        yield


def _recorded(provider):
    """Patch the provider an operator chose in Settings."""
    return patch(
        "src.core.llm.availability._recorded_active_provider",
        AsyncMock(return_value=provider),
    )


# --- The CLI now sees what generation sees -----------------------------------


@pytest.mark.asyncio
async def test_the_cli_uses_a_credential_stored_through_settings():
    """THE fix. This path previously read process environment variables only."""
    with _stored({"anthropic": "sk-from-settings"}):
        service = await create_llm_service_with_selection(verbose=False)

    assert service.config.default_provider is LLMProviderType.ANTHROPIC


@pytest.mark.asyncio
async def test_an_explicit_provider_is_never_silently_replaced():
    """It used to fall through to auto-detection, so asking for one provider
    could quietly bill another."""
    with _stored({"anthropic": "sk-anthropic"}):
        with pytest.raises(RuntimeError, match="openai"):
            await create_llm_service_with_selection(
                cli_provider="openai", verbose=False
            )


@pytest.mark.asyncio
async def test_the_kill_switch_is_honoured_here_too():
    with _resolves_to(LLMAvailability.unavailable(LLMUnavailableReason.DISABLED)):
        with pytest.raises(RuntimeError, match="LLM_ENABLED"):
            await create_llm_service_with_selection(verbose=False)


@pytest.mark.asyncio
async def test_no_provider_says_what_to_do_about_it():
    with _resolves_to(LLMAvailability.unavailable(LLMUnavailableReason.NOT_CONFIGURED)):
        with pytest.raises(RuntimeError) as raised:
            await create_llm_service_with_selection(verbose=False)

    message = str(raised.value)
    assert "Settings" in message
    assert "LLM_DEFAULT_PROVIDER=local" in message  # the no-cloud-key option


@pytest.mark.asyncio
async def test_an_explicit_model_still_wins():
    with _stored({"anthropic": "sk-anthropic"}):
        service = await create_llm_service_with_selection(
            cli_model="claude-3-haiku", verbose=False
        )

    assert service.config.default_model == "claude-3-haiku"


@pytest.mark.asyncio
async def test_a_default_model_is_chosen_for_the_resolved_provider():
    """Model defaults are the selector's own business and stay there."""
    with _stored({"openai": "sk-openai"}):
        service = await create_llm_service_with_selection(verbose=False)

    assert service.config.default_provider is LLMProviderType.OPENAI
    assert service.config.default_model


# --- Ollama is answered the same way on both paths ---------------------------


def test_ollama_is_not_reported_available_merely_because_it_could_be(monkeypatch):
    """The listing used to probe a hardcoded localhost address and, when it
    could not check — which is always, inside a running event loop — report
    available anyway. Every node claimed a local model it did not have."""
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "")

    selector = get_provider_selector()
    selector.invalidate_availability_cache()

    assert selector._is_provider_available(LLMProviderType.LOCAL) is False


def test_ollama_is_available_once_opted_into(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box.local:11434")

    selector = get_provider_selector()
    selector.invalidate_availability_cache()

    assert selector._is_provider_available(LLMProviderType.LOCAL) is True


def test_the_listing_never_opens_a_network_connection(monkeypatch):
    """A provider listing should not depend on reaching anything."""
    import socket

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    def _forbidden(*args, **kwargs):
        raise AssertionError("provider availability must not use the network")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)

    selector = get_provider_selector()
    selector.invalidate_availability_cache()
    selector._is_provider_available(LLMProviderType.LOCAL)


@pytest.mark.asyncio
async def test_the_cli_uses_the_provider_chosen_in_settings():
    """The recorded choice reaches the CLI, not just the web app.

    Records openai while both credentials exist, because preference order
    would pick anthropic on its own — so passing this cannot be explained by
    the fallback path.
    """
    with _recorded("openai"), _stored({"anthropic": "sk-a", "openai": "sk-o"}):
        service = await create_llm_service_with_selection(verbose=False)

    assert service.config.default_provider is LLMProviderType.OPENAI
