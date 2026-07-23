"""Regression: Match UI sends MoM space IRIs as okw_ids; stubs must stay in the pool."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid5, NAMESPACE_URL

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MOM_IRI = "https://maps.ofmaking.org/space/harness-3dp-lab"


def _load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _patch_mom_cache(monkeypatch, spaces: list | None = None):
    import src.core.services.mom_bridge as mom

    payload = spaces if spaces is not None else _load_json("mom_spaces_3dp.json")

    async def fake_get(force_refresh=False):
        return (payload, True)

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)


@pytest.mark.asyncio
async def test_network_match_okw_ids_mom_iri_keeps_stub(monkeypatch):
    """Filtering by network space id (MoM IRI) must retain the MoM stub."""
    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(return_value=([], 0))
    _patch_mom_cache(monkeypatch)

    facilities = await svc.get_network_match_facilities(
        include_mom=True,
        require_coords=False,
        okw_ids=[MOM_IRI],
    )
    assert len(facilities) == 1
    assert facilities[0].name == "Harness MoM 3DP Lab"
    assert facilities[0].id == uuid5(NAMESPACE_URL, MOM_IRI)


@pytest.mark.asyncio
async def test_get_filtered_facilities_network_mom_iri(monkeypatch):
    """Match route network branch must pass MoM IRIs through to the pool."""
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities
    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(return_value=([], 0))
    _patch_mom_cache(monkeypatch)

    async def fake_get_instance():
        return svc

    monkeypatch.setattr(OKWService, "get_instance", staticmethod(fake_get_instance))

    request = MatchRequest.model_construct(
        network_filter={"include_mom": True},
        okw_ids=[MOM_IRI],
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={},
    )
    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=request,
        request_id="harness",
        domain="manufacturing",
    )
    assert len(facilities) == 1
    assert facilities[0].name == "Harness MoM 3DP Lab"


@pytest.mark.asyncio
async def test_mom_iri_okw_ids_yields_3dp_solution(monkeypatch):
    """End-to-end: 3DP-only design + MoM IRI selection → at least one solution."""
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService
    from src.core.services.okw_service import OKWService

    svc_okw = OKWService()
    svc_okw.list = AsyncMock(return_value=([], 0))
    _patch_mom_cache(monkeypatch)

    facilities = await svc_okw.get_network_match_facilities(
        include_mom=True,
        require_coords=False,
        okw_ids=[MOM_IRI],
    )
    assert facilities, "MoM IRI filter emptied the pool (id-alignment regression)"
    assert facilities[0].id == uuid5(NAMESPACE_URL, MOM_IRI)

    match_svc = MatchingService()
    await match_svc.initialize()
    okh = OKHManifest.from_dict(_load_json("okh_3dp_only.json"))
    solutions = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=facilities,
    )
    assert len(solutions) >= 1
