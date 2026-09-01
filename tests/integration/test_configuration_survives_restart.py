"""Configuration written through the API must survive the process that wrote it.

The shape this guards against, which has now bitten twice:

    a write mutates a process-local singleton, and nothing re-establishes
    that state at boot

It fails only in production, which is what makes it expensive. A dev box runs
one process, so the worker that handled the write is the worker that answers
the next read and everything looks fine. Production runs several gunicorn
workers behind several replicas, so the write lands in one and the read lands
in another — and the operator is told their key saved and then told the LLM is
unavailable.

The test is deliberately shaped as *write through the API, then read through a
FRESH service instance*, because that second half is the part unit tests skip
and single-process manual testing cannot see.
"""

from __future__ import annotations

import pytest

from src.config.llm_config import CredentialManager, LLMProvider
from src.core.llm.credentials import activate_stored_credentials
from src.core.llm.service import LLMService
from src.core.services.storage_service import StorageService
from src.core.storage.llm_credential_store import LLMCredentialStore

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def minted_encryption(monkeypatch):
    """Credential storage refuses to operate under the default keys."""
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "restart-suite-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "restart-suite-password")
    # A provider key in the environment is picked up independently of the
    # store and masks the whole failure — which is exactly why this went
    # unnoticed on developer machines.
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_AI_API_KEY",
        "AZURE_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


async def _store() -> LLMCredentialStore:
    return LLMCredentialStore(await StorageService.get_instance(), CredentialManager())


async def test_a_stored_llm_credential_is_live_in_a_fresh_process(client):
    """The production report: saved through Settings, still "unavailable"."""
    store = await _store()
    await store.save(LLMProvider.ANTHROPIC, "sk-ant-restart", model="claude-x")

    # A process that did not handle the write — a second worker, or this one
    # after a restart.
    fresh = LLMService()
    assert [p.value for p in await fresh.get_available_providers()] == []

    await activate_stored_credentials(fresh, store)

    assert "anthropic" in [p.value for p in await fresh.get_available_providers()]


async def test_the_active_provider_choice_survives_a_restart(client):
    """Which provider is used must be a recorded fact, not the last writer."""
    store = await _store()
    await store.save(LLMProvider.ANTHROPIC, "sk-ant-restart", model="claude-x")
    await store.save(LLMProvider.OPENAI, "sk-oai-restart", model="gpt-x")
    await store.set_active(LLMProvider.OPENAI)

    fresh = LLMService()
    await activate_stored_credentials(fresh, store)

    assert fresh._active_provider is not None
    assert fresh._active_provider.value == "openai"


async def test_the_listing_says_which_provider_is_active(client):
    """An operator should not have to infer it from row order."""
    store = await _store()
    await store.save(LLMProvider.ANTHROPIC, "sk-ant-restart")
    await store.save(LLMProvider.OPENAI, "sk-oai-restart")
    await store.set_active(LLMProvider.ANTHROPIC)

    rows = {r["provider"]: r["is_active"] for r in await store.list_status()}

    assert rows["anthropic"] is True
    assert rows["openai"] is False


async def test_storage_configuration_survives_a_restart(client, tmp_path, monkeypatch):
    """The same property for storage, which gets it right by a different route.

    Storage never had the bug — it persists to a file read at boot rather than
    hot-swapping a singleton — and this pins that, so the two surfaces cannot
    drift apart into one durable and one not.
    """
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))

    from src.core.services.storage_config_store import load_config, save_config
    from src.core.storage.base import StorageConfig

    save_config(StorageConfig(provider="local", bucket_name=str(tmp_path / "chosen")))

    # What boot reads, in a process that did not perform the write.
    reloaded = load_config()

    assert reloaded is not None
    assert reloaded.bucket_name == str(tmp_path / "chosen")
