"""A match must not surface a facility the caller cannot see (#503).

Visibility is applied inside `OKWService.list()`, and only when a viewer is
supplied — its docstring says `None` means unscoped, "for trusted internal
callers only". The match path never supplied one and structurally could not:
neither `get_network_match_facilities` nor `_load_network_candidates` took the
parameter, so a private facility was matchable by anyone, and the match response
carries `facility.to_dict()` — the whole record, contact details included.

The gate that exists for this class missed it. `test_viewer_scope_ratchet.py`
parses route files for unscoped `list()` calls; here the call was two frames
below the handler, inside the service.

These tests work at the service boundary, where the scoping lives. The route's
job is only to hand a scope down, which `test_match_passes_the_callers_scope`
asserts directly.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.visibility import ANONYMOUS_SCOPE, ViewerScope  # noqa: E402

pytestmark = pytest.mark.contract

OWNER = ViewerScope(account_id="acct-owner")
FACILITY_ID = uuid4()


def _service():
    from src.core.services.okw_service import OKWService

    return OKWService.__new__(OKWService)


@pytest.mark.asyncio
async def test_the_candidate_pool_is_scoped_to_the_viewer():
    """Whatever scope arrives must reach `list()`, which is where visibility is."""
    from src.core.services.okw_service import OKWService

    service = _service()
    seen = {}

    async def fake_list(*, page, page_size, viewer=None):
        seen["viewer"] = viewer
        return [], 0

    with patch.object(service, "list", new=fake_list):
        await OKWService._load_network_candidates(
            service, include_mom=False, force_refresh=False, viewer=OWNER
        )
    assert seen["viewer"] is OWNER


@pytest.mark.asyncio
async def test_an_anonymous_scope_reaches_list_rather_than_being_dropped():
    """Calibration: the test above would pass if every scope became None.

    An anonymous scope is a real scope — it owns nothing and sees only what is
    shareable — and it must arrive as itself, not as the unscoped `None` that
    means "trusted internal caller".
    """
    from src.core.services.okw_service import OKWService

    service = _service()
    seen = {}

    async def fake_list(*, page, page_size, viewer=None):
        seen["viewer"] = viewer
        return [], 0

    with patch.object(service, "list", new=fake_list):
        await OKWService._load_network_candidates(
            service, include_mom=False, force_refresh=False, viewer=ANONYMOUS_SCOPE
        )
    assert seen["viewer"] is ANONYMOUS_SCOPE
    assert seen["viewer"] is not None


@pytest.mark.asyncio
async def test_match_facilities_carries_the_scope_through():
    """The public entry point the match route calls."""
    from src.core.services.okw_service import OKWService

    service = _service()
    seen = {}

    async def fake_candidates(*, include_mom, force_refresh, require_coords, viewer):
        seen["viewer"] = viewer
        return [], 0, False

    with patch.object(service, "_load_network_candidates", new=fake_candidates):
        await OKWService.get_network_match_facilities(service, viewer=OWNER)
    assert seen["viewer"] is OWNER


@pytest.mark.asyncio
async def test_match_hands_the_callers_scope_to_the_candidate_pool(monkeypatch):
    """End to end through the route.

    The defect was not a wrong scope, it was **no** scope: the handler resolved
    a caller for attribution and never used it for this. So the assertion is
    that a scope arrives at all, and that an anonymous caller arrives as the
    anonymous scope rather than as the unscoped `None`.
    """
    import httpx
    from fastapi import FastAPI

    # Production posture: outside it an unauthenticated caller resolves to the
    # dev-local identity (#494), which is correct there and would obscure what
    # this asserts — that a stranger gets the scope that owns nothing.
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    from src.core.api.routes import match as match_routes
    from src.core.main import api_v1

    seen = {}

    async def fake_filtered(*args, **kwargs):
        seen["viewer"] = kwargs.get("viewer", "NOT PASSED")
        return []

    app = FastAPI()
    app.mount("/v1", api_v1)
    # Inline manifest, so the request reaches the facility fetch without a
    # design lookup — the scope hand-off is what is under test, not resolution.
    payload = {
        "max_depth": 0,
        "okh_manifest": {
            "title": "Probe",
            "repo": "https://example.com/probe",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Someone",
            "documentation_language": "en",
            "function": "probe",
        },
    }

    with patch.object(match_routes, "_get_filtered_facilities", new=fake_filtered):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            await client.post("/v1/api/match", json=payload)

    assert seen.get("viewer") != "NOT PASSED", "the route passed no scope at all"
    assert seen["viewer"] == ANONYMOUS_SCOPE


@pytest.mark.asyncio
async def test_a_private_facility_is_not_reverse_matchable(monkeypatch):
    """Knowing the id must not be enough to ask what it can make.

    The answer would confirm the facility exists and describe its capabilities,
    which is most of what the record says. 404, not 403, so the response does
    not confirm the id either.
    """
    import httpx
    from fastapi import FastAPI
    from unittest.mock import MagicMock

    from src.core.api.routes.match import get_okw_service
    from src.core.main import api_v1
    from src.core.models.visibility import VisibilityLevel

    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    # `MagicMock(name=...)` names the mock, it does not set `.name` — the
    # attribute has to be assigned, or the route renders a Mock repr.
    facility = MagicMock(id=str(FACILITY_ID))
    facility.name = "Secret Workshop"
    svc = MagicMock()
    svc.get = AsyncMock(return_value=facility)
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)

    app = FastAPI()
    app.mount("/v1", api_v1)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/match/facility", json={"okw_id": str(FACILITY_ID)}
            )
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_a_shareable_facility_is_still_reverse_matchable(monkeypatch):
    """Calibration: without this, a route that 404'd on everything would pass."""
    import httpx
    from fastapi import FastAPI
    from unittest.mock import MagicMock

    from src.core.api.routes.match import get_okw_service
    from src.core.main import api_v1
    from src.core.models.visibility import VisibilityLevel

    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    facility = MagicMock(id=str(FACILITY_ID))
    facility.name = "Open Shop"
    svc = MagicMock()
    svc.get = AsyncMock(return_value=facility)
    svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PUBLIC)

    app = FastAPI()
    app.mount("/v1", api_v1)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/match/facility", json={"okw_id": str(FACILITY_ID)}
            )
        assert resp.status_code != 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()
