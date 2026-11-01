"""Visibility and disclosure writes need ownership; visibility reads hide private ids (#590).

The three routes that change who may see a record checked `require_write`
only — any credentialed caller (every self-registered account) could make
another user's private record public, or loosen a facility's disclosure.
They now follow the update/delete rule from #518: `require_ownership`, 403.

`GET …/visibility` answered for any existing id, confirming a private record
exists to an anonymous caller that `GET /{id}` would 404. It now applies the
same rule as `GET /{id}`.
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

from src.core.models.disclosure import DisclosureProfile  # noqa: E402
from src.core.models.visibility import VisibilityLevel  # noqa: E402

pytestmark = pytest.mark.contract

_OWNER_ACCOUNT = str(uuid4())
_STRANGER_ACCOUNT = str(uuid4())


def _caller():
    from src.core.models.auth import AuthenticatedUser

    return AuthenticatedUser(
        key_id=uuid4(), name="caller", permissions=["write"], account_id=_OWNER_ACCOUNT
    )


def _service(attribution, visibility=VisibilityLevel.PRIVATE):
    svc = MagicMock()
    svc.get = AsyncMock(return_value=MagicMock())
    svc.owner_attribution = AsyncMock(return_value=attribution)
    svc.get_visibility = AsyncMock(return_value=visibility)
    svc.set_visibility = AsyncMock(return_value=VisibilityLevel.PUBLIC)
    svc.get_disclosure = AsyncMock(return_value=DisclosureProfile())
    svc.set_disclosure = AsyncMock(return_value=DisclosureProfile())
    return svc


async def _call(domain, svc, method, path, overrides, json=None):
    from src.core.api.routes.okh import get_okh_service
    from src.core.api.routes.okw import get_okw_service
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    service = {"okh": get_okh_service, "okw": get_okw_service}[domain]
    api_v1.dependency_overrides[service] = lambda: svc
    api_v1.dependency_overrides.update(overrides)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as client:
            return await client.request(
                method, f"/v1/api/{domain}/{uuid4()}/{path}", json=json
            )
    finally:
        api_v1.dependency_overrides.clear()


_WRITES = [
    ("okh", "visibility", {"visibility": "public"}, "set_visibility"),
    ("okw", "visibility", {"visibility": "public"}, "set_visibility"),
    ("okw", "disclosure", {"public": {"groups": []}}, "set_disclosure"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("domain,path,body,setter", _WRITES)
async def test_a_stranger_cannot_change_who_sees_a_record(domain, path, body, setter):
    from src.core.api.dependencies import require_write

    svc = _service((None, _STRANGER_ACCOUNT))
    resp = await _call(domain, svc, "PUT", path, {require_write: _caller}, json=body)

    assert resp.status_code == 403, resp.text
    getattr(svc, setter).assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("domain,path,body,setter", _WRITES)
async def test_the_owner_can_change_who_sees_a_record(domain, path, body, setter):
    from src.core.api.dependencies import require_write

    svc = _service((None, _OWNER_ACCOUNT))
    resp = await _call(domain, svc, "PUT", path, {require_write: _caller}, json=body)

    assert resp.status_code == 200, resp.text
    getattr(svc, setter).assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["okh", "okw"])
@pytest.mark.parametrize(
    "viewer,owner,visibility,expected",
    [
        (None, _STRANGER_ACCOUNT, VisibilityLevel.PRIVATE, 404),
        (None, _STRANGER_ACCOUNT, VisibilityLevel.FOLLOWERS, 200),
        (_caller, _STRANGER_ACCOUNT, VisibilityLevel.PRIVATE, 404),
        (_caller, _OWNER_ACCOUNT, VisibilityLevel.PRIVATE, 200),
    ],
    ids=[
        "anonymous-private",
        "anonymous-shareable",
        "stranger-private",
        "owner-private",
    ],
)
async def test_visibility_read_matches_get_by_id(
    domain, viewer, owner, visibility, expected
):
    from src.core.api.dependencies import get_viewer

    svc = _service((None, owner), visibility)
    resolve = viewer or (lambda: None)
    resp = await _call(domain, svc, "GET", "visibility", {get_viewer: resolve})

    assert resp.status_code == expected, resp.text
