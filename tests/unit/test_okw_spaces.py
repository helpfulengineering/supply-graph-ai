"""Unit tests for the unified network surface (GET /api/okw/spaces, issue #230).

Covers the enriched MoM fetch (city/country/status/url/processes), the TTL
cache, `OKWService.get_network_spaces` union, and the pure
`filter_network_spaces` (cross-source hard filters + local-only soft filters
with ambiguous flag + ranking). All network + storage is mocked.
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
# fetch_all_mom_spaces — enriched SPARQL parsing + process normalization
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


def _row(
    space, name, lat, lon, city=None, country=None, state=None, url=None, tags=None
):
    row = {
        "space": {"value": space},
        "name": {"value": name},
        "lat": {"value": str(lat)},
        "lon": {"value": str(lon)},
    }
    for key, val in (
        ("city", city),
        ("country", country),
        ("state", state),
        ("url", url),
        ("tags", tags),
    ):
        if val is not None:
            row[key] = {"value": val}
    return row


@pytest.mark.asyncio
async def test_fetch_enriches_and_normalizes_processes(monkeypatch):
    import src.core.services.mom_bridge as mom

    payload = {
        "results": {
            "bindings": [
                _row(
                    "urn:a",
                    "Space A",
                    41.9,
                    12.5,
                    city="Rome",
                    country="IT",
                    state="confirmed",
                    url="https://a",
                    tags="laser|cnc",
                ),
            ]
        }
    }
    monkeypatch.setattr(mom.httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))

    [s] = await mom.fetch_all_mom_spaces()
    assert s["city"] == "Rome" and s["country"] == "IT"
    assert s["status"] == "confirmed" and s["url"] == "https://a"
    # MoM slugs normalized to canonical OHM process ids.
    assert s["processes"] == ["laser_cutting", "cnc_machining"]


@pytest.mark.asyncio
async def test_fetch_skips_malformed_and_tolerates_missing_optionals(monkeypatch):
    import src.core.services.mom_bridge as mom

    payload = {
        "results": {
            "bindings": [
                _row("urn:ok", "OK", 1.0, 2.0),  # no optionals at all
                {
                    "space": {"value": "bad"},
                    "name": {"value": "B"},
                    "lat": {"value": "x"},
                    "lon": {"value": "2"},
                },
            ]
        }
    }
    monkeypatch.setattr(mom.httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))

    spaces = await mom.fetch_all_mom_spaces()
    assert [s["space"] for s in spaces] == ["urn:ok"]
    assert spaces[0]["city"] is None and spaces[0]["processes"] == []


# ---------------------------------------------------------------------------
# MoMSpacesCache — TTL, refresh hook, invalidate, graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_serves_fresh_then_refresh_and_invalidate(monkeypatch):
    from src.core.services.mom_bridge import MoMSpacesCache

    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0, "processes": []}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=1000)
    _, avail = await cache.get()
    await cache.get()
    assert avail and calls["n"] == 1  # second served from cache
    assert await cache.refresh() is True and calls["n"] == 2  # hook forces refetch
    cache.invalidate()
    await cache.get()
    assert calls["n"] == 3  # invalidate forced a refetch


@pytest.mark.asyncio
async def test_cache_keeps_stale_on_failure_and_unavailable_when_never_fetched(
    monkeypatch,
):
    from src.core.services.mom_bridge import MoMSpacesCache

    state = {"fail": True}

    async def fake_fetch():
        if state["fail"]:
            raise RuntimeError("MoM down")
        return [{"space": "x", "name": "X", "lat": 1.0, "lon": 2.0, "processes": []}]

    monkeypatch.setattr("src.core.services.mom_bridge.fetch_all_mom_spaces", fake_fetch)

    cache = MoMSpacesCache(ttl_seconds=0)
    spaces, avail = await cache.get()  # never succeeded
    assert spaces == [] and avail is False
    state["fail"] = False
    good, avail2 = await cache.get()
    assert good and avail2 is True
    state["fail"] = True
    stale, avail3 = await cache.get()  # refetch fails → keep stale
    assert stale == good and avail3 is True


# ---------------------------------------------------------------------------
# filter_network_spaces — pure cross-source + soft local-only filtering
# ---------------------------------------------------------------------------


def _spaces():
    return [
        {
            "id": "a",
            "name": "Local A",
            "lat": 1,
            "lon": 1,
            "city": "Austin",
            "region": "TX",
            "country": "US",
            "source": "local",
            "status": "active",
            "processes": ["laser_cutting"],
            "access_type": "Public",
            "url": None,
        },
        {
            "id": "b",
            "name": "MoM B",
            "lat": 2,
            "lon": 2,
            "city": "Seoul",
            "region": None,
            "country": "KR",
            "source": "mom",
            "status": "active",
            "processes": ["cnc_machining"],
            "access_type": None,
            "url": "x",
        },
    ]


def test_cross_source_filters_hard_exclude():
    from src.core.services.okw_service import filter_network_spaces

    assert [
        s["id"] for s in filter_network_spaces(_spaces(), process="laser_cutting")
    ] == ["a"]
    assert [s["id"] for s in filter_network_spaces(_spaces(), country="kr")] == ["b"]
    assert [s["id"] for s in filter_network_spaces(_spaces(), city="seo")] == ["b"]
    assert [s["id"] for s in filter_network_spaces(_spaces(), source="mom")] == ["b"]


def test_local_only_axis_keeps_ambiguous_and_ranks_last():
    from src.core.services.okw_service import filter_network_spaces

    result = filter_network_spaces(_spaces(), access_type="Public")
    # Both kept; the MoM space that can't express access_type is flagged + last.
    assert [(s["id"], s["ambiguous"]) for s in result] == [("a", False), ("b", True)]


def test_local_only_axis_excludes_definite_non_match_keeps_ambiguous():
    from src.core.services.okw_service import filter_network_spaces

    # region=CA: local A has region TX (definite non-match → excluded); MoM B
    # can't express region (ambiguous → kept).
    result = filter_network_spaces(_spaces(), region="CA")
    assert [(s["id"], s["ambiguous"]) for s in result] == [("b", True)]


# ---------------------------------------------------------------------------
# OKWService.get_network_spaces — union + counts + filter wiring
# ---------------------------------------------------------------------------


def _facility(fid, name, gps, processes):
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    return ManufacturingFacility(
        name=name,
        location=Location(gps_coordinates=gps),
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=processes,
        id=fid,
    )


@pytest.mark.asyncio
async def test_get_network_spaces_unions_and_counts(monkeypatch):
    from uuid import uuid4
    from src.core.services.okw_service import OKWService
    import src.core.services.mom_bridge as mom

    svc = OKWService()
    with_coords = _facility(uuid4(), "Local A", "40.0, -70.0", [])
    without = _facility(uuid4(), "Local B", None, [])
    svc.list = AsyncMock(return_value=([with_coords, without], 2))

    async def fake_get(force_refresh=False):
        return (
            [
                {
                    "space": "urn:z",
                    "name": "MoM Z",
                    "lat": 1.0,
                    "lon": 2.0,
                    "city": None,
                    "country": None,
                    "status": None,
                    "url": None,
                    "processes": [],
                }
            ],
            True,
        )

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    result = await svc.get_network_spaces()
    assert result["total"] == 2
    assert result["local_count"] == 1 and result["mom_count"] == 1
    assert result["dropped_no_coords"] == 1 and result["mom_available"] is True
    assert {s["source"] for s in result["spaces"]} == {"local", "mom"}


@pytest.mark.asyncio
async def test_get_network_spaces_applies_source_filter(monkeypatch):
    from uuid import uuid4
    from src.core.services.okw_service import OKWService
    import src.core.services.mom_bridge as mom

    svc = OKWService()
    svc.list = AsyncMock(
        return_value=([_facility(uuid4(), "Local A", "40.0, -70.0", [])], 1)
    )

    async def fake_get(force_refresh=False):
        return (
            [
                {
                    "space": "urn:z",
                    "name": "MoM Z",
                    "lat": 1.0,
                    "lon": 2.0,
                    "processes": [],
                }
            ],
            True,
        )

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    result = await svc.get_network_spaces(source="local")
    assert result["mom_count"] == 0
    assert all(s["source"] == "local" for s in result["spaces"])


@pytest.mark.asyncio
async def test_get_network_match_facilities_returns_facilities(monkeypatch):
    from uuid import uuid4
    from src.core.services.okw_service import OKWService
    from src.core.models.okw import ManufacturingFacility
    import src.core.services.mom_bridge as mom

    svc = OKWService()
    svc.list = AsyncMock(
        return_value=([_facility(uuid4(), "Local A", "40.0, -70.0", [])], 1)
    )

    async def fake_get(force_refresh=False):
        return (
            [
                {
                    "space": "urn:z",
                    "name": "MoM Z",
                    "lat": 1.0,
                    "lon": 2.0,
                    "city": "Rome",
                    "country": "IT",
                    "status": "confirmed",
                    "url": None,
                    "processes": ["laser_cutting"],
                }
            ],
            True,
        )

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    # Full network → both local + MoM as matchable ManufacturingFacility objects.
    facilities = await svc.get_network_match_facilities()
    assert all(isinstance(f, ManufacturingFacility) for f in facilities)
    assert {f.name for f in facilities} == {"Local A", "MoM Z"}
    # The MoM stub carries its canonical processes for process-level matching.
    mom_stub = next(f for f in facilities if f.name == "MoM Z")
    assert mom_stub.manufacturing_processes == ["laser_cutting"]

    # source=local drops MoM from the candidate pool.
    local_only = await svc.get_network_match_facilities(source="local")
    assert [f.name for f in local_only] == ["Local A"]


@pytest.mark.asyncio
async def test_get_network_match_facilities_filters_by_space_id(monkeypatch):
    """okw_ids matches network space id (MoM IRI), not the stub UUID5."""
    from uuid import NAMESPACE_URL, uuid4, uuid5

    from src.core.services.okw_service import OKWService
    import src.core.services.mom_bridge as mom

    svc = OKWService()
    svc.list = AsyncMock(
        return_value=([_facility(uuid4(), "Local A", "40.0, -70.0", [])], 1)
    )
    mom_iri = "urn:mom:space-z"

    async def fake_get(force_refresh=False):
        return (
            [
                {
                    "space": mom_iri,
                    "name": "MoM Z",
                    "lat": 1.0,
                    "lon": 2.0,
                    "city": "Rome",
                    "country": "IT",
                    "status": "confirmed",
                    "url": None,
                    "processes": ["laser_cutting"],
                }
            ],
            True,
        )

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    facilities = await svc.get_network_match_facilities(
        include_mom=True, okw_ids=[mom_iri]
    )
    assert len(facilities) == 1
    assert facilities[0].name == "MoM Z"
    assert facilities[0].id == uuid5(NAMESPACE_URL, mom_iri)
