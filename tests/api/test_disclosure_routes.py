"""Contract tests for GET/PUT /api/okw/{id}/disclosure."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.disclosure import (
    AudienceDisclosure,
    DisclosureGroup,
    DisclosureProfile,
    default_disclosure_profile,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okw_disclosure_defaults():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    facility_id = uuid4()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=MagicMock())
    svc.get_disclosure = AsyncMock(return_value=default_disclosure_profile())
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{facility_id}/disclosure")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == str(facility_id)
        assert body["disclosure"]["followers"]["groups"] == ["identity"]
        assert body["disclosure"]["public"]["groups"] == ["identity"]
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okw_disclosure_404_when_missing_record():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=None)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{uuid4()}/disclosure")
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_put_okw_disclosure_partial_merge():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    facility_id = uuid4()
    current = DisclosureProfile(
        followers=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
        public=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
    )
    updated = DisclosureProfile(
        followers=AudienceDisclosure(
            groups=[DisclosureGroup.IDENTITY, DisclosureGroup.LOCATION]
        ),
        public=AudienceDisclosure(groups=[DisclosureGroup.IDENTITY]),
    )
    svc = MagicMock()
    svc.get_disclosure = AsyncMock(return_value=current)
    svc.set_disclosure = AsyncMock(return_value=updated)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.put(
                f"/v1/api/okw/{facility_id}/disclosure",
                json={"followers": {"groups": ["identity", "location"]}},
            )
        assert resp.status_code == 200, resp.text
        assert "location" in resp.json()["disclosure"]["followers"]["groups"]
        # public left alone in merge (still identity-only in returned profile)
        assert resp.json()["disclosure"]["public"]["groups"] == ["identity"]
        svc.set_disclosure.assert_awaited_once()
        saved = svc.set_disclosure.await_args.args[1]
        assert DisclosureGroup.LOCATION in saved.followers.groups
        assert saved.public.groups == [DisclosureGroup.IDENTITY]
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_put_okw_disclosure_404_when_missing_record():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    facility_id = uuid4()
    svc = MagicMock()
    svc.get_disclosure = AsyncMock(return_value=default_disclosure_profile())
    svc.set_disclosure = AsyncMock(side_effect=LookupError("missing"))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.put(
                f"/v1/api/okw/{facility_id}/disclosure",
                json={"followers": {"groups": ["identity"]}},
            )
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_preview_okw_disclosure():
    from src.core.api.routes.okw import get_okw_service
    from src.core.models.disclosure import DisclosureAudience, DisclosureGroup

    app, api_v1 = _get_app()
    facility_id = uuid4()
    svc = MagicMock()
    svc.preview_disclosure = AsyncMock(
        return_value={
            "id": facility_id,
            "audience": DisclosureAudience.FOLLOWERS,
            "visibility": "private",
            "exported": False,
            "groups": [DisclosureGroup.IDENTITY],
            "facility": {"id": str(facility_id), "name": "Lab"},
        }
    )
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"/v1/api/okw/{facility_id}/disclosure/preview",
                params={"audience": "followers"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["exported"] is False
        assert body["visibility"] == "private"
        assert body["facility"]["name"] == "Lab"
        svc.preview_disclosure.assert_awaited_once()
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_preview_okw_disclosure_404():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.preview_disclosure = AsyncMock(side_effect=LookupError("missing"))
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okw/{uuid4()}/disclosure/preview")
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()
