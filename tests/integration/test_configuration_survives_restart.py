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


async def _row_for(store: LLMCredentialStore, provider: LLMProvider) -> dict:
    """The status row for one provider.

    Never index ``list_status()`` by position. Storage is shared across this
    session, so which row lands at ``[0]`` depends on what other tests saved —
    an ordering dependency that passes locally and fails in CI, where the lane
    stops at the first failure and reaches this file earlier.
    """
    rows = [r for r in await store.list_status() if r["provider"] == provider.value]
    assert rows, f"no stored credential for {provider.value}"
    return rows[0]


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


async def test_a_credential_saved_under_other_encryption_reads_as_unusable(
    client, monkeypatch
):
    """The second production report: "anthropic [active]" beside "unavailable".

    Every field the Settings panel shows — provider, model, masked key,
    configured, is_active — is plaintext metadata stored beside the key, so all
    of it survives an encryption-material change that the key itself does not.
    The node then reports a credential as stored and active while the runtime
    can load nothing, and says so in neither the UI nor the logs.

    ``readable`` is the field that resolves the contradiction, and it is worth
    its decrypt because nothing cheaper can tell the two states apart.
    """
    store = await _store()
    await store.save(LLMProvider.ANTHROPIC, "sk-ant-under-the-old-key")
    await store.set_active(LLMProvider.ANTHROPIC)
    assert (await _row_for(store, LLMProvider.ANTHROPIC))["readable"] is True

    # The node comes back with different encryption material: a redeploy that
    # regenerated the secret, or a restore onto a host holding another one.
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "a-different-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "a-different-password")
    rotated = LLMCredentialStore(
        await StorageService.get_instance(), CredentialManager()
    )

    row = await _row_for(rotated, LLMProvider.ANTHROPIC)
    assert row["configured"] is True
    assert row["is_active"] is True
    assert row["readable"] is False, (
        "the panel must not be able to call a credential active without also "
        "saying it cannot be read"
    )

    # And the runtime genuinely has nothing, which is the half the operator saw.
    fresh = LLMService()
    await activate_stored_credentials(fresh, rotated)
    assert [p.value for p in await fresh.get_available_providers()] == []


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


async def test_applying_an_imported_rule_set_is_refused(client):
    """Rules ship with the image; an applied import could not survive (#457).

    `import_rule_set` ended in an in-memory dict assignment, so an applied
    import lived only in the worker that answered, was invisible to the others,
    and vanished on the next restart — while reporting success throughout.
    Refusing is the honest answer until rules have somewhere durable to live.
    """
    response = client.post(
        "/api/match/rules/import",
        json={
            "file_content": "domain: manufacturing\nrules: []\n",
            "file_format": "yaml",
            "dry_run": False,
        },
    )

    assert response.status_code == 501, response.text
    assert "shipped with the image" in response.json()["detail"]


async def test_a_dry_run_import_still_works(client):
    """Checking a rule set against a running node is the supported path."""
    response = client.post(
        "/api/match/rules/import",
        json={
            "file_content": "domain: manufacturing\nrules: []\n",
            "file_format": "yaml",
            "dry_run": True,
        },
    )

    # Whatever it concludes about the content, it must not be the refusal.
    assert response.status_code != 501, response.text


async def test_resetting_rules_is_refused(client):
    """It emptied one worker and told the caller everything was reset."""
    response = client.post("/api/match/rules/reset?confirm=true")

    assert response.status_code == 501, response.text
    assert "nothing to reset" in response.json()["detail"]


async def test_a_refused_reset_leaves_the_rules_loaded(client):
    """The failure mode being closed: no rules at all, in one process."""
    client.post("/api/match/rules/reset?confirm=true")

    listing = client.get("/api/match/rules/")

    assert listing.status_code == 200, listing.text
    assert listing.json()["data"]["total"] > 0
