"""Private records must not be served to unauthenticated callers.

docs-site/docs/guides/who-can-see-your-data.md promises "Private | The record
stays on this instance. Nothing is exported to anyone", and ``private`` is the
create default. The federation plane honoured that (build_catalog_index filters
on is_shareable); the REST plane did not, so a record the API itself reported as
private was readable — address included — by anyone.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.visibility import VisibilityLevel  # noqa: E402

PRIVATE_ID = UUID("11111111-1111-4111-8111-111111111111")
SHAREABLE_ID = UUID("22222222-2222-4222-8222-222222222222")


def _app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _record(record_id: UUID, name: str) -> MagicMock:
    record = MagicMock()
    record.id = record_id
    record.name = name
    record.title = name
    record.to_dict.return_value = {"id": str(record_id), "name": name, "title": name}
    return record


def _visibility_side_effect(record_id: UUID) -> VisibilityLevel:
    return (
        VisibilityLevel.PRIVATE if record_id == PRIVATE_ID else VisibilityLevel.PUBLIC
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_okh_list_hides_private_from_anonymous_callers() -> None:
    """The filter belongs to the service so `total` and the page agree."""
    from src.core.services.okh_service import OKHService

    service = OKHService.__new__(OKHService)
    service.get_visibility = AsyncMock(side_effect=_visibility_side_effect)

    kept = await OKHService.filter_shareable(
        service,
        [_record(PRIVATE_ID, "Secret"), _record(SHAREABLE_ID, "Shared")],
    )
    assert [r.id for r in kept] == [SHAREABLE_ID]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_okw_filter_shareable_drops_private() -> None:
    from src.core.services.okw_service import OKWService

    service = OKWService.__new__(OKWService)
    service.get_visibility = AsyncMock(side_effect=_visibility_side_effect)

    kept = await OKWService.filter_shareable(
        service,
        [_record(PRIVATE_ID, "Secret Workshop"), _record(SHAREABLE_ID, "Open Shop")],
    )
    assert [r.id for r in kept] == [SHAREABLE_ID]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_okw_get_404s_for_anonymous_when_private() -> None:
    """404 rather than 403 — the response must not confirm the id exists."""
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_record(PRIVATE_ID, "Secret Workshop"))
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{PRIVATE_ID}")
        assert resp.status_code == 404, resp.text
        assert "Secret Workshop" not in resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_okh_get_404s_for_anonymous_when_private() -> None:
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_record(PRIVATE_ID, "Secret Design"))
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okh/{PRIVATE_ID}")
        assert resp.status_code == 404, resp.text
        assert "Secret Design" not in resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_shareable_record_still_served_anonymously() -> None:
    """Closing the leak must not make public records unreadable.

    A real facility rather than a mock: the route builds a response model from
    concrete attributes, so a MagicMock proves nothing about the happy path.
    """
    from src.core.api.routes.okw import get_okw_service
    from src.core.models.okw import ManufacturingFacility

    facility = ManufacturingFacility.from_dict(
        {
            "id": str(SHAREABLE_ID),
            "name": "Open Shop",
            "location": {"address": {"city": "Somewhere", "country": "GB"}},
            "facility_status": "Active",
        }
    )

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=facility)
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PUBLIC)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{SHAREABLE_ID}")
        assert resp.status_code == 200, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_stale_token_reads_as_anonymous_rather_than_401() -> None:
    """A read endpoint that was public must not start 401ing on a bad token.

    get_viewer degrades an unusable credential to anonymous; get_optional_user
    would reject it, turning one expired key into a site-wide read outage.
    """
    from src.core.api.dependencies import get_viewer

    assert await get_viewer(auth_header=None) is None
    assert await get_viewer(auth_header="Bearer definitely-not-a-real-key") is None


@pytest.mark.asyncio
@pytest.mark.contract
async def test_unknown_id_still_404s() -> None:
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=None)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{uuid4()}")
        assert resp.status_code == 404
    finally:
        api_v1.dependency_overrides.clear()
