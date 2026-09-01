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
    # Explicit, because MagicMock auto-creates attributes as truthy — leaving
    # this to getattr() would make every "has it loaded yet" check say yes.
    service._stored_credentials_loaded = False
    service.config = MagicMock(
        default_model="a-model", default_provider=default_provider
    )
    service.add_provider = AsyncMock(return_value=True)
    service.remove_provider = AsyncMock()
    service.set_active_provider = AsyncMock(return_value=True)
    return service


def _store(statuses, key="sk-stored", active=None):
    store = MagicMock()
    store.list_status = AsyncMock(return_value=statuses)
    store.load = AsyncMock(return_value=key)
    # `active` is the recorded choice; None means a node that has never made
    # one, which is a real state rather than an error.
    store.get_active = AsyncMock(return_value=active)
    store.set_active = AsyncMock()
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


async def test_the_recorded_active_provider_wins():
    """The point of recording it: the node uses what was chosen, not a guess."""
    service = _service(default_provider=LLMProvider.ANTHROPIC)
    store = _store(
        [
            {"provider": "anthropic", "model": None},
            {"provider": "openai", "model": None},
        ],
        active=LLMProvider.OPENAI,
    )

    await activate_stored_credentials(service, store)

    # Chosen over the configured default, because someone chose it.
    assert service.set_active_provider.await_args.args[0].value == "openai"


async def test_a_recorded_provider_that_is_gone_falls_back():
    """Deleting the active credential must not leave the node with none."""
    service = _service(default_provider=None)
    store = _store(
        [{"provider": "anthropic", "model": None}], active=LLMProvider.OPENAI
    )

    activated = await activate_stored_credentials(service, store)

    assert activated == ["anthropic"]
    assert service.set_active_provider.await_args.args[0].value == "anthropic"


async def test_the_configured_default_wins_when_nothing_was_recorded():
    """Only when there is no record does the configured preference decide."""
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


# --- Recovery from a failed startup load ---------------------------------
#
# Startup activation ends in `provider.connect()`, a network call. A worker
# that starts before egress is ready gets False back, logs it, and — before
# this — never tried again: the node reported "unavailable" for a credential
# sitting valid in storage, and only re-saving the key fixed it, for one
# worker.


async def test_a_failed_startup_load_is_retried_on_the_next_request():
    """The regression: a transient boot failure used to be permanent."""
    from src.core.llm.credentials import ensure_stored_credentials_loaded

    service = _service()
    store = _store([{"provider": "anthropic", "model": None}])
    service.add_provider = AsyncMock(return_value=False)

    await activate_stored_credentials(service, store)
    assert service._providers == {}

    # Network is fine now, as it is by the time a request arrives.
    async def _adds(config):
        service._providers[config.provider_type] = object()
        return True

    service.add_provider = AsyncMock(side_effect=_adds)
    await ensure_stored_credentials_loaded(service, store)

    assert service._providers != {}


async def test_a_service_that_already_has_providers_does_not_touch_storage():
    """The common path is a flag check, not a read."""
    from src.core.llm.credentials import ensure_stored_credentials_loaded

    service = _service()
    service._providers = {"anthropic": object()}
    store = _store([{"provider": "anthropic", "model": None}])

    await ensure_stored_credentials_loaded(service, store)

    store.list_status.assert_not_awaited()


async def test_nothing_stored_is_a_settled_answer_not_a_retry():
    """A node with no credential must not read storage on every request."""
    from src.core.llm.credentials import ensure_stored_credentials_loaded

    service = _service()
    store = _store([])

    await ensure_stored_credentials_loaded(service, store)
    await ensure_stored_credentials_loaded(service, store)

    assert store.list_status.await_count == 1


async def test_a_failed_load_keeps_retrying():
    """Not setting the flag on failure is the point: that case is retryable."""
    from src.core.llm.credentials import ensure_stored_credentials_loaded

    service = _service()
    store = _store([{"provider": "anthropic", "model": None}])
    service.add_provider = AsyncMock(return_value=False)

    await ensure_stored_credentials_loaded(service, store)
    await ensure_stored_credentials_loaded(service, store)

    assert store.list_status.await_count == 2
