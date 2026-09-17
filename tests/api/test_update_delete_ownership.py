"""PUT/DELETE by-id have no ownership check across OKH, asset, and OKW (#518).

Found while fixing #514: `require_write` proves the caller holds *a*
credential, not that they may touch *this* record, so any credentialed
caller could update or delete any record on the node by id. #514 already
proved the fix primitive for two OKH routes (repair-doc merge) and made two
decisions explicit in its shipped code, extended here unchanged rather than
re-litigated:

- 403, not 404 — the caller already named this id, so there is nothing to
  hide; the honest answer is that they may not touch it.
- An unattributed record (no `ohm_*` stamp) refuses everyone, including
  whoever wrote it without one, rather than treating "nobody" as "anybody."
- Admin gets no bypass — `ViewerScope` grants admin nothing extra for reads
  either (ADR §9); writes follow the same rule.

One test module for all three domains since they share the same shape:
`get` the record, resolve `(created_by_did, created_by_account)` via each
service's own `owner_attribution`, and check `ViewerScope.owns`.
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

from src.core.models.asset import AssetRecord  # noqa: E402
from src.core.models.okw import (
    FacilityStatus,
    Location,
    ManufacturingFacility,
)  # noqa: E402

pytestmark = pytest.mark.contract

_OWNER_ACCOUNT = str(uuid4())
_STRANGER_ACCOUNT = str(uuid4())


def _app():
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _owner_user():
    from src.core.models.auth import AuthenticatedUser

    return AuthenticatedUser(
        key_id=uuid4(), name="owner", permissions=["write"], account_id=_OWNER_ACCOUNT
    )


# ---------------------------------------------------------------------------
# OKH: PUT/DELETE /api/okh/{id}
# ---------------------------------------------------------------------------


def _okh_manifest():
    m = MagicMock()
    m.to_dict.return_value = {
        "id": str(uuid4()),
        "title": "widget",
        "version": "1.0.0",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Test Author",
        "documentation_language": "en",
        "function": "A widget",
    }
    return m


_OKH_UPDATE_BODY = {
    "title": "widget v2",
    "version": "1.0.1",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Author",
    "documentation_language": "en",
    "function": "A widget",
}


def _okh_service(attribution):
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_okh_manifest())
    svc.owner_attribution = AsyncMock(return_value=attribution)
    svc.update = AsyncMock(return_value=_okh_manifest())
    svc.delete = AsyncMock(return_value=True)
    return svc


@pytest.mark.asyncio
async def test_update_okh_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = _okh_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okh/{manifest_id}", json=_OKH_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_okh_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = _okh_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okh/{manifest_id}", json=_OKH_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_okh_403s_for_an_unattributed_manifest():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = _okh_service((None, None))
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okh/{manifest_id}", json=_OKH_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_delete_okh_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = _okh_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/okh/{manifest_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_okh_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = _okh_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/okh/{manifest_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.delete.assert_awaited_once()


# ---------------------------------------------------------------------------
# Asset: PUT/DELETE /api/asset/{id}
# ---------------------------------------------------------------------------


def _asset_record():
    return AssetRecord(manifest_id=str(uuid4()), asset_tag="tag-1")


def _asset_service(attribution):
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_asset_record())
    svc.owner_attribution = AsyncMock(return_value=attribution)
    svc.update = AsyncMock(return_value=_asset_record())
    svc.delete = AsyncMock(return_value=True)
    return svc


@pytest.mark.asyncio
async def test_update_asset_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.asset import get_asset_service

    app, api_v1 = _app()
    svc = _asset_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_asset_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    asset_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/asset/{asset_id}", json={"location": "bin 4"})

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_asset_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.asset import get_asset_service

    app, api_v1 = _app()
    svc = _asset_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_asset_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    asset_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/asset/{asset_id}", json={"location": "bin 4"})

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_asset_403s_for_an_unattributed_record():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.asset import get_asset_service

    app, api_v1 = _app()
    svc = _asset_service((None, None))
    api_v1.dependency_overrides[get_asset_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    asset_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/asset/{asset_id}", json={"location": "bin 4"})

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_delete_asset_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.asset import get_asset_service

    app, api_v1 = _app()
    svc = _asset_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_asset_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    asset_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/asset/{asset_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_asset_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.asset import get_asset_service

    app, api_v1 = _app()
    svc = _asset_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_asset_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    asset_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/asset/{asset_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.delete.assert_awaited_once()


# ---------------------------------------------------------------------------
# OKW: PUT/DELETE /api/okw/{id}
# ---------------------------------------------------------------------------


def _okw_facility():
    return ManufacturingFacility(
        name="Fab", location=Location(), facility_status=FacilityStatus.ACTIVE
    )


_OKW_UPDATE_BODY = {"name": "Fab", "location": {}, "facility_status": "Active"}


def _okw_service(attribution):
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_okw_facility())
    svc.owner_attribution = AsyncMock(return_value=attribution)
    svc.update = AsyncMock(return_value=_okw_facility())
    svc.delete = AsyncMock(return_value=True)
    return svc


@pytest.mark.asyncio
async def test_update_okw_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = _okw_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    facility_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okw/{facility_id}", json=_OKW_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_okw_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = _okw_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    facility_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okw/{facility_id}", json=_OKW_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_okw_403s_for_an_unattributed_facility():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = _okw_service((None, None))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    facility_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.put(f"/v1/api/okw/{facility_id}", json=_OKW_UPDATE_BODY)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_delete_okw_403s_for_a_stranger():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = _okw_service((None, _STRANGER_ACCOUNT))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    facility_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/okw/{facility_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_okw_succeeds_for_the_owner():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = _okw_service((None, _OWNER_ACCOUNT))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    facility_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.delete(f"/v1/api/okw/{facility_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.delete.assert_awaited_once()
