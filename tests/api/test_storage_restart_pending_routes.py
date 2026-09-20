"""The `runtime` block on `GET /storage/config`, and the pending refusal (#545).

`node` mirrors what `main.py`'s own lifespan does at boot — configure storage,
save that as the persisted configuration, and start the liveness marker — so
these tests exercise the same shape a real API process has, not one where an
inline switch's `refresh_backend()` is a no-op because nothing ever started a
marker (that shape is the CLI's, covered elsewhere).
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from src.core.api.dependencies import require_admin_strict
from src.core.api.routes.storage import get_storage_service
from src.core.main import api_v1, app
from src.core.models.auth import AuthenticatedUser
from src.core.services import storage_liveness as sl
from src.core.services.storage_config_store import load_config, save_config
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig

pytestmark = [pytest.mark.contract, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def node(tmp_path, monkeypatch):
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_STORAGE_MARKER_PATH", str(tmp_path / "api-live.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "restart-pending-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "restart-pending-password")

    old = tmp_path / "old"
    old.mkdir()

    service = StorageService()
    await service.configure(StorageConfig(provider="local", bucket_name=str(old)))
    assert service._configured
    save_config(StorageConfig(provider="local", bucket_name=str(old)))
    sl.start("local", str(old))

    admin = AuthenticatedUser(
        key_id=uuid4(), name="admin", permissions=["admin"], account_id=uuid4()
    )
    api_v1.dependency_overrides[require_admin_strict] = lambda: admin
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client, service, old, tmp_path
    finally:
        api_v1.dependency_overrides.clear()
        await sl.stop()


async def test_not_pending_right_after_boot(node):
    client, *_ = node

    resp = await client.get("/v1/api/storage/config")

    assert resp.status_code == 200, resp.text
    runtime = resp.json()["data"]["runtime"]
    assert runtime["restart_required"] is False
    assert runtime["live_bucket"] == runtime["saved_bucket"]


async def test_get_config_reports_restart_required_when_pending(node):
    """The shape a CLI switch, from a separate process, leaves behind: the
    marker still names the backend the API booted with, the saved config has
    already moved on."""
    client, _service, old, tmp_path = node
    diverged = tmp_path / "diverged"

    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    resp = await client.get("/v1/api/storage/config")

    assert resp.status_code == 200, resp.text
    runtime = resp.json()["data"]["runtime"]
    assert runtime["restart_required"] is True
    assert runtime["live_bucket"] == str(old)
    assert runtime["saved_bucket"] == str(diverged)
    assert runtime["since"] is not None


async def test_post_config_is_refused_while_pending(node):
    client, service, old, tmp_path = node
    diverged = tmp_path / "diverged"
    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    resp = await client.post(
        "/v1/api/storage/config",
        json={"provider": "local", "bucket": str(tmp_path / "third")},
    )

    assert resp.status_code == 400, resp.text
    assert "restart is already pending" in resp.json()["detail"]
    # Untouched by the refused attempt: still `diverged` (from the setup
    # above, standing in for the earlier switch), not `third`.
    assert load_config().bucket_name == str(diverged)
    assert service.manager.config.bucket_name == str(old)


async def test_health_reports_restart_required_too(node):
    """#545 scope: `/health`'s storage block gains `restart_required` — a
    public endpoint, unlike `/storage/config`, so an operator's monitoring
    doesn't need admin credentials to see it."""
    client, _service, _old, tmp_path = node
    diverged = tmp_path / "diverged"
    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    resp = await client.get("/health")

    assert resp.status_code == 200, resp.text
    assert resp.json()["storage"]["restart_required"] is True


async def test_an_inline_switch_updates_the_marker_and_leaves_nothing_pending(node):
    """#545 AC4: an inline switch applies to this process and its marker at
    once, so it never creates a pending state of its own."""
    client, service, old, tmp_path = node
    new = tmp_path / "new"

    resp = await client.post(
        "/v1/api/storage/config", json={"provider": "local", "bucket": str(new)}
    )
    assert resp.status_code == 200, resp.text

    follow_up = await client.get("/v1/api/storage/config")
    runtime = follow_up.json()["data"]["runtime"]
    assert runtime["restart_required"] is False
    assert runtime["live_bucket"] == str(new)
    assert runtime["saved_bucket"] == str(new)
    assert service.manager.config.bucket_name == str(new)
