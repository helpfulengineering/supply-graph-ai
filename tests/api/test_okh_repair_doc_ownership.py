"""POST /okh/extract-repair-docs and POST /okh/import-repair-doc must not
merge into a manifest the caller doesn't own (#514).

Both accept an optional `manifest_id` and, when given one, patch that
manifest — with no check the caller has any relationship to it beyond
holding *some* write-permitted credential (`require_write`, #485). Any
credentialed caller could patch any manifest on the node by id.

`_require_manifest_ownership` (`okh.py`) now checks `ViewerScope.owns` —
the same primitive `visible_to` already uses for read-scoping — against
`OKHService.owner_attribution`. These drive both real routes end-to-end,
with `RepairDocExtractor` running for real against a small throwaway text
file (nothing under test here depends on what it extracts) and only
`OKHService` mocked, since attribution and the ownership decision are the
only things in question.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

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
        key_id=uuid4(),
        name="owner",
        permissions=["write"],
        account_id=_OWNER_ACCOUNT,
    )


def _existing_manifest():
    m = MagicMock()
    m.to_dict.return_value = {
        "id": str(uuid4()),
        "title": "widget",
        "version": "1.0.0",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Test Author",
        "documentation_language": "en",
        "function": "A widget",
        "components": [],
        "repair_guides": [],
    }
    m.components = []
    m.repair_guides = []
    m.id = uuid4()
    return m


def _files():
    return [("files", ("manual.txt", b"a repair manual", "text/plain"))]


@pytest.mark.asyncio
async def test_extract_repair_docs_403s_when_caller_does_not_own_the_manifest():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_existing_manifest())
    svc.owner_attribution = AsyncMock(return_value=(None, _STRANGER_ACCOUNT))
    svc.update = AsyncMock(return_value=_existing_manifest())
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    import httpx

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/extract-repair-docs",
            data={"manifest_id": manifest_id},
            files=_files(),
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.update.assert_not_called()


@pytest.mark.asyncio
async def test_extract_repair_docs_succeeds_when_caller_owns_the_manifest():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_existing_manifest())
    svc.owner_attribution = AsyncMock(return_value=(None, _OWNER_ACCOUNT))
    svc.update = AsyncMock(return_value=_existing_manifest())
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    import httpx

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/extract-repair-docs",
            data={"manifest_id": manifest_id},
            files=_files(),
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_repair_docs_403s_for_an_unattributed_manifest():
    """Nobody owns a legacy/never-stamped record — refuses everyone rather
    than treating "nobody" as "anybody"."""
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_existing_manifest())
    svc.owner_attribution = AsyncMock(return_value=(None, None))
    svc.update = AsyncMock(return_value=_existing_manifest())
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    import httpx

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/extract-repair-docs",
            data={"manifest_id": manifest_id},
            files=_files(),
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_import_repair_doc_403s_when_caller_does_not_own_the_manifest():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_existing_manifest())
    svc.owner_attribution = AsyncMock(return_value=(None, _STRANGER_ACCOUNT))
    svc.import_repair_doc = AsyncMock(return_value=_existing_manifest())
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    import httpx

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/import-repair-doc",
            data={"manifest_id": manifest_id},
            files=_files(),
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 403, resp.text
    svc.import_repair_doc.assert_not_called()


@pytest.mark.asyncio
async def test_import_repair_doc_succeeds_when_caller_owns_the_manifest():
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_existing_manifest())
    svc.owner_attribution = AsyncMock(return_value=(None, _OWNER_ACCOUNT))
    svc.import_repair_doc = AsyncMock(return_value=_existing_manifest())
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: _owner_user()

    import httpx

    manifest_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/import-repair-doc",
            data={"manifest_id": manifest_id},
            files=_files(),
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    svc.import_repair_doc.assert_awaited_once()
