"""The API refuses the two storage-switch modes that were retired (#543, #539).

`abandon_and_wipe` switched the API's own process and then erased the old backend.
Fine for a lone API process; not fine for anything else still using that backend, and
the same combined step run from the CLI erased storage a *running* API was serving
from (its design count went 1 -> 0). `migrate` over the API enqueued a worker job
that never configured its own storage, so it stopped with "There is no current
storage to migrate from" every time, and it carried the destination's credentials
through Redis as cleartext JSON.

Both now answer 400 with what to do instead, and change nothing. The values stay in
the request enum on purpose: a clear message reaches a caller who followed the old
docs, where removing them would hand back a generic 422.

The default mode is the control: it must keep working, and it shows the refusals are
about the two modes, not about the endpoint.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from uuid import uuid4

from src.config import settings  # noqa: F401  (imported before the app, as elsewhere)
from src.core.api.dependencies import require_admin_strict
from src.core.api.routes.storage import get_storage_service
from src.core.main import api_v1, app
from src.core.models.auth import AuthenticatedUser
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig

pytestmark = [pytest.mark.contract, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def node(tmp_path, monkeypatch):
    """A node serving from `old/`, holding one design, with the storage routes mounted."""
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "retired-modes-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "retired-modes-password")

    old, new = tmp_path / "old", tmp_path / "new"
    (old / "okh").mkdir(parents=True)
    (old / "okh" / "users-design-okh.json").write_text('{"title": "a user\'s data"}')

    service = StorageService()
    await service.configure(StorageConfig(provider="local", bucket_name=str(old)))
    assert service._configured

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
            yield client, service, old, new, tmp_path / "cfg.json"
    finally:
        api_v1.dependency_overrides.clear()


def _design_survives(old) -> bool:
    return (old / "okh" / "users-design-okh.json").exists()


async def test_abandon_and_wipe_is_refused_and_nothing_is_erased(node) -> None:
    client, service, old, new, cfg = node

    response = await client.post(
        "/v1/api/storage/config",
        json={
            "provider": "local",
            "bucket": str(new),
            "mode": "abandon_and_wipe",
            "wipe_confirm": str(old),
        },
    )

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert "retired" in detail, detail
    assert _design_survives(old), "the retired mode erased the old backend"
    assert service.manager.config.bucket_name == str(old), "and it switched"
    assert not cfg.exists(), "and it persisted a configuration"


async def test_a_legacy_wipe_request_gets_the_same_answer(node) -> None:
    """A client following the old docs also sends `dry_run`; it must not 422."""
    client, _, old, new, _ = node

    response = await client.post(
        "/v1/api/storage/config",
        json={
            "provider": "local",
            "bucket": str(new),
            "mode": "abandon_and_wipe",
            "wipe_confirm": str(old),
            "dry_run": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "retired" in response.json()["detail"]


async def test_migrate_over_the_api_is_refused_and_points_at_the_cli(node) -> None:
    client, service, old, new, cfg = node

    response = await client.post(
        "/v1/api/storage/config",
        json={"provider": "local", "bucket": str(new), "mode": "migrate"},
    )

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert "retired" in detail and "ohm storage config set" in detail, detail
    assert service.manager.config.bucket_name == str(old)
    assert not cfg.exists()


async def test_the_migration_status_route_is_gone(node) -> None:
    client, *_ = node

    response = await client.get("/v1/api/storage/migration/some-job-id")
    assert response.status_code == 404, response.text

    spec = (await client.get("/v1/openapi.json")).json()
    leftovers = [p for p in spec["paths"] if "migration" in p and "storage" in p]
    assert not leftovers, leftovers


async def test_the_default_switch_still_works(node) -> None:
    """The control: the endpoint itself is fine, and a switch leaves the old data."""
    client, service, old, new, cfg = node

    response = await client.post(
        "/v1/api/storage/config", json={"provider": "local", "bucket": str(new)}
    )

    assert response.status_code == 200, response.text
    assert service.manager.config.bucket_name == str(new)
    assert _design_survives(old), "a plain switch must leave the old data in place"
    assert cfg.exists()
