"""A stored LLM credential must survive the process that saved it.

Saving a credential and activating it had different lifetimes. The key
persisted to storage; the activation only ever touched the **in-process**
``LLMService``, and ``/api/llm/health`` reports in-process state. So a key saved
through Settings was live in the one worker that handled the request, and every
other worker — and every process after a restart — reported "unavailable" with
a perfectly good credential sitting in storage.

It reproduced only in production because a dev machine runs one process, and
usually has ``ANTHROPIC_API_KEY`` in its .env, which the service picks up
independently of the store and masks the whole thing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.llm_config import LLMProvider
from src.core.llm.credentials import activate_stored_credentials

pytestmark = pytest.mark.asyncio


def _service(default_provider=None):
    service = MagicMock()
    service._providers = {}
    service.config = MagicMock(
        default_model="a-model", default_provider=default_provider
    )
    service.add_provider = AsyncMock(return_value=True)
    service.remove_provider = AsyncMock()
    service.set_active_provider = AsyncMock(return_value=True)
    return service


def _store(statuses, key="sk-stored"):
    store = MagicMock()
    store.list_status = AsyncMock(return_value=statuses)
    store.load = AsyncMock(return_value=key)
    return store


async def test_a_stored_credential_is_activated_at_startup():
    """The regression: this is what a fresh worker used to skip entirely."""
    service = _service()
    store = _store([{"provider": "anthropic", "model": "claude-x"}])

    activated = await activate_stored_credentials(service, store)

    assert activated == ["anthropic"]
    service.add_provider.assert_awaited()
    service.set_active_provider.assert_awaited()


async def test_nothing_stored_activates_nothing_and_does_not_raise():
    service = _service()
    store = _store([])

    assert await activate_stored_credentials(service, store) == []
    service.set_active_provider.assert_not_awaited()


async def test_the_configured_default_wins_when_several_are_stored():
    """Which one is active is a choice, so it is a stated and tested one."""
    service = _service(default_provider=LLMProvider.OPENAI)
    store = _store(
        [
            {"provider": "anthropic", "model": None},
            {"provider": "openai", "model": None},
        ]
    )

    activated = await activate_stored_credentials(service, store)

    assert set(activated) == {"anthropic", "openai"}
    chosen = service.set_active_provider.await_args.args[0]
    assert chosen.value == "openai"


async def test_without_a_configured_default_the_choice_is_stable():
    """Alphabetical, so two workers reading the same store agree."""
    service = _service(default_provider=None)
    store = _store(
        [
            {"provider": "openai", "model": None},
            {"provider": "anthropic", "model": None},
        ]
    )

    await activate_stored_credentials(service, store)

    assert service.set_active_provider.await_args.args[0].value == "anthropic"


async def test_one_bad_credential_does_not_stop_the_others():
    service = _service()
    store = _store(
        [
            {"provider": "anthropic", "model": None},
            {"provider": "openai", "model": None},
        ]
    )
    service.add_provider = AsyncMock(side_effect=[RuntimeError("revoked"), True])

    activated = await activate_stored_credentials(service, store)

    assert activated == ["openai"]


async def test_an_unreadable_store_is_logged_not_raised():
    """Startup calls this. An LLM is optional; a node that will not boot is not."""
    service = _service()
    store = MagicMock()
    store.list_status = AsyncMock(side_effect=OSError("storage unreachable"))

    assert await activate_stored_credentials(service, store) == []


async def test_an_unknown_provider_name_is_skipped():
    """A credential written by a newer version must not break an older one."""
    service = _service()
    store = _store([{"provider": "a-provider-from-the-future", "model": None}])

    assert await activate_stored_credentials(service, store) == []
