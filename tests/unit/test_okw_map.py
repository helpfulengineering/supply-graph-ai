"""Unit tests for the OKW network map: MoM all-spaces fetch, TTL cache, union.

Covers `fetch_all_mom_spaces` parsing, `MoMSpacesCache` freshness/refresh/
invalidate/graceful-degradation, and `OKWService.get_map_points` unioning local
facilities with MoM points. All network + storage is mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# fetch_all_mom_spaces — SPARQL JSON parsing
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse(self._payload)


def _bindings(*rows):
    return {
        "results": {
            "bindings": [
                {
                    "space": {"value": s},
                    "name": {"value": n},
                    "lat": {"value": str(lat)},
                    "lon": {"value": str(lon)},
                }
                for (s, n, lat, lon) in rows
            ]
        }
    }


@pytest.mark.asyncio
async def test_fetch_all_mom_spaces_parses_rows(monkeypatch):
    import src.core.services.mom_bridge as mom

    payload = _bindings(
        ("urn:mak:space/a", "Space A", 41.89, 12.51),
        ("urn:mak:space/b", "Space B", 49.65, 11.03),
    )
    monkeypatch.setattr(mom.httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))

    spaces = await mom.fetch_all_mom_spaces()
    assert spaces == [
        {"space": "urn:mak:space/a", "name": "Space A", "lat": 41.89, "lon": 12.51},
        {"space": "urn:mak:space/b", "name": "Space B", "lat": 49.65, "lon": 11.03},
    ]


@pytest.mark.asyncio
async def test_fetch_all_mom_spaces_skips_malformed_rows(monkeypatch):
    import src.core.services.mom_bridge as mom

    payload = {
        "results": {
            "bindings": [
                {
                    "space": {"value": "ok"},
                    "name": {"value": "N"},
                    "lat": {"value": "1.0"},
                    "lon": {"value": "2.0"},
                },
                {
                    "space": {"value": "bad"},
                    "name": {"value": "N"},
                    "lat": {"value": "not-a-number"},
                    "lon": {"value": "2.0"},
                },
                {
                    "space": {"value": "missing-lon"},
                    "name": {"value": "N"},
                    "lat": {"value": "1.0"},
                },
            ]
        }
    }
    monkeypatch.setattr(mom.httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))

    spaces = await mom.fetch_all_mom_spaces()
    assert [s["space"] for s in spaces] == ["ok"]


# ---------------------------------------------------------------------------
# MoMSpacesCache — TTL, refresh hook, invalidate, graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_serves_fresh_without_refetching(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=1000)
    spaces1, avail1 = await cache.get()
    spaces2, avail2 = await cache.get()
    assert avail1 and avail2
    assert spaces1 == spaces2
    assert calls["n"] == 1  # second get served from cache


@pytest.mark.asyncio
async def test_cache_refetches_when_stale(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=0)  # everything is immediately stale
    await cache.get()
    await cache.get()
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_refresh_hook_forces_fetch_and_invalidate_clears(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=1000)
    await cache.get()
    assert calls["n"] == 1
    assert await cache.refresh() is True  # hook forces refetch despite fresh TTL
    assert calls["n"] == 2
    cache.invalidate()
    await cache.get()
    assert calls["n"] == 3  # invalidate forced a refetch


@pytest.mark.asyncio
async def test_cache_keeps_stale_data_on_failure(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    state = {"fail": False}

    async def fake_fetch():
        if state["fail"]:
            raise RuntimeError("MoM down")
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=0)
    good, avail = await cache.get()
    assert avail and good
    state["fail"] = True
    stale, avail2 = await cache.get()  # refetch fails → keep stale, still available
    assert stale == good
    assert avail2 is True


@pytest.mark.asyncio
async def test_cache_unavailable_when_never_fetched(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    async def fake_fetch():
        raise RuntimeError("MoM down")

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=0)
    spaces, avail = await cache.get()
    assert spaces == []
    assert avail is False


# ---------------------------------------------------------------------------
# OKWService.get_map_points — union + source labels + dropped count
# ---------------------------------------------------------------------------


def _facility(fid, name, gps):
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    return ManufacturingFacility(
        name=name,
        location=Location(gps_coordinates=gps),
        facility_status=FacilityStatus.ACTIVE,
        id=fid,
    )


@pytest.mark.asyncio
async def test_get_map_points_unions_local_and_mom(monkeypatch):
    from uuid import uuid4
    from src.core.services.okw_service import OKWService
    import src.core.services.mom_bridge as mom

    svc = OKWService()
    a_id, b_id = uuid4(), uuid4()
    with_coords = _facility(a_id, "Local A", "40.0, -70.0")
    without = _facility(b_id, "Local B", None)
    svc.list = AsyncMock(return_value=([with_coords, without], 2))

    async def fake_get(force_refresh=False):
        return (
            [{"space": "urn:mak:space/z", "name": "MoM Z", "lat": 1.0, "lon": 2.0}],
            True,
        )

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    result = await svc.get_map_points()
    assert result["local_count"] == 1
    assert result["mom_count"] == 1
    assert result["dropped_no_coords"] == 1
    assert result["mom_available"] is True
    sources = {p["source"] for p in result["points"]}
    assert sources == {"local", "mom"}


@pytest.mark.asyncio
async def test_get_map_points_local_only_skips_mom(monkeypatch):
    from uuid import uuid4
    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(
        return_value=([_facility(uuid4(), "Local A", "40.0, -70.0")], 1)
    )

    result = await svc.get_map_points(include_mom=False)
    assert result["mom_count"] == 0
    assert result["mom_available"] is False
    assert all(p["source"] == "local" for p in result["points"])
