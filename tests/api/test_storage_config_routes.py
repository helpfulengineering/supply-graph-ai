"""Storage configuration over the API (#377).

Two things this must get right, and they are the reason the endpoints exist
rather than a direct call to ``StorageService.configure``:

- **A bad configuration must change nothing.** ``configure`` swallows
  connection failures so the app can boot degraded, and it replaces the active
  manager before connecting. Called naively from a handler, a mistyped
  credential would return success and leave the instance with no working
  storage — and no route back, because the endpoint that would fix it needs
  storage-backed admin credentials to authenticate.
- **Admin that development mode cannot relax.** An endpoint that repoints an
  instance's storage is not something to leave open, the same reasoning that
  put LLM credential management behind ``require_admin_strict``.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _admin():
    from src.core.models.auth import AuthenticatedUser

    return AuthenticatedUser(
        key_id=uuid4(), name="admin", permissions=["admin"], account_id=uuid4()
    )


async def _request(app, method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize(
    "method,payload",
    [("GET", None), ("POST", {"provider": "local", "bucket": "/tmp/x"})],
)
async def test_endpoints_reject_anonymous_in_development(monkeypatch, method, payload):
    """require_admin would relax here; require_admin_strict must not."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    app, _ = _get_app()

    kwargs = {"json": payload} if payload else {}
    resp = await _request(app, method, "/v1/api/storage/config", **kwargs)

    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_read_reports_configuration_without_credential_values(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))

    from src.core.api.dependencies import require_admin_strict
    from src.core.api.routes.storage import get_storage_service
    from src.core.storage.base import StorageConfig

    service = MagicMock()
    service.manager = MagicMock()
    service.manager.config = StorageConfig(
        provider="azure_blob",
        bucket_name="production",
        credentials={"account_name": "acct", "account_key": "SUPER-SECRET"},
    )
    service._configured = True
    service.get_config_fingerprint = AsyncMock(
        return_value={
            "provider": "azure_blob",
            "account": "acct",
            "container": "production",
            "okh_count": 3,
            "okw_count": 4,
        }
    )

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[require_admin_strict] = _admin
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        resp = await _request(app, "GET", "/v1/api/storage/config")
    finally:
        api_v1.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    config = body["data"]["config"]

    assert config["provider"] == "azure_blob"
    assert config["credential_names"] == ["account_key", "account_name"]
    assert body["data"]["fingerprint"]["okh_count"] == 3

    # The whole payload, not just that field: a credential must not reach the
    # client anywhere in the response.
    assert "SUPER-SECRET" not in resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_a_rejected_configuration_leaves_the_instance_alone(
    monkeypatch, tmp_path
):
    """The regression this endpoint exists to avoid."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "test-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "test-password")

    from src.core.api.dependencies import require_admin_strict
    from src.core.api.routes.storage import get_storage_service
    from src.core.services.storage_service import StorageService
    from src.core.storage.base import StorageConfig

    working = tmp_path / "working"
    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(working)))
    assert service._configured

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[require_admin_strict] = _admin
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        resp = await _request(
            app,
            "POST",
            "/v1/api/storage/config",
            json={"provider": "local", "bucket": "/dev/null/not-a-directory"},
        )
    finally:
        api_v1.dependency_overrides.clear()

    assert resp.status_code == 400, resp.text
    assert "still serving" in resp.json()["detail"]

    # Still pointed at, and connected to, the backend it started on.
    assert service._configured is True
    assert service.manager.config.bucket_name == str(working)
    # And nothing was written to the config file.
    assert not (tmp_path / "cfg.json").exists()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_a_good_configuration_is_committed_and_persisted(monkeypatch, tmp_path):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "test-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "test-password")

    from src.core.api.dependencies import require_admin_strict
    from src.core.api.routes.storage import get_storage_service
    from src.core.services.storage_config_store import load_config
    from src.core.services.storage_service import StorageService
    from src.core.storage.base import StorageConfig

    before = tmp_path / "before"
    after = tmp_path / "after"
    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(before)))

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[require_admin_strict] = _admin
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        resp = await _request(
            app,
            "POST",
            "/v1/api/storage/config",
            json={"provider": "local", "bucket": str(after)},
        )
    finally:
        api_v1.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["verified"] is True
    # Setup is part of configuration, not a step after it.
    assert sorted(data["prefixes_created"]) == [
        "okh/",
        "okw/",
        "packages/",
        "supply-trees/",
    ]
    assert data["previous_bucket"] == str(before)

    # The live service moved, and the choice survives this process.
    assert service.manager.config.bucket_name == str(after)
    assert load_config().bucket_name == str(after)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_an_unknown_credential_name_is_rejected(monkeypatch, tmp_path):
    """A misspelled credential should fail here, not authenticate badly later."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))

    from src.core.api.dependencies import require_admin_strict
    from src.core.api.routes.storage import get_storage_service
    from src.core.services.storage_service import StorageService

    service = await StorageService.get_instance()

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[require_admin_strict] = _admin
    api_v1.dependency_overrides[get_storage_service] = lambda: service
    try:
        resp = await _request(
            app,
            "POST",
            "/v1/api/storage/config",
            json={
                "provider": "azure_blob",
                "bucket": "container",
                "credentials": {"acount_name": "typo"},
            },
        )
    finally:
        api_v1.dependency_overrides.clear()

    assert resp.status_code == 400, resp.text
    assert "acount_name" in resp.json()["detail"]
