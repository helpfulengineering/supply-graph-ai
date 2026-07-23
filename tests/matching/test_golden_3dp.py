"""Golden matching cases: simple 3DP designs must find facilities (mocked MoM)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MOM_3DP_IRI = "https://maps.ofmaking.org/space/harness-3dp-lab"


def _load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _local_facility():
    from src.core.models.okw import ManufacturingFacility

    return ManufacturingFacility.from_dict(_load_json("okw_additive_local.json"))


def _patch_mom(monkeypatch, spaces=None):
    import src.core.services.mom_bridge as mom

    payload = spaces if spaces is not None else _load_json("mom_spaces_3dp.json")

    async def fake_get(force_refresh=False):
        return (payload, True)

    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)


@pytest.mark.asyncio
async def test_local_direct_3dp_finds_facility():
    """3DP-only OKH against a local additive OKW → ≥1 solution."""
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService

    match_svc = MatchingService()
    await match_svc.initialize()
    okh = OKHManifest.from_dict(_load_json("okh_3dp_only.json"))
    solutions = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=[_local_facility()],
    )
    assert len(solutions) >= 1


@pytest.mark.asyncio
async def test_mom_mock_iri_3dp_finds_facility(monkeypatch):
    """3DP-only OKH + mocked MoM with okw_ids=[IRI] → ≥1 solution."""
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService
    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(return_value=([], 0))
    _patch_mom(monkeypatch)

    facilities = await svc.get_network_match_facilities(
        include_mom=True,
        require_coords=False,
        okw_ids=[MOM_3DP_IRI],
    )
    assert len(facilities) == 1

    match_svc = MatchingService()
    await match_svc.initialize()
    okh = OKHManifest.from_dict(_load_json("okh_3dp_only.json"))
    solutions = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=facilities,
    )
    assert len(solutions) >= 1


@pytest.mark.asyncio
async def test_union_all_3dp_finds_facility(monkeypatch):
    """3DP-only OKH against local ∪ MoM mock with no okw_ids → ≥1 solution."""
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService
    from src.core.services import okw_service as okw_mod

    local = _local_facility()

    async def list_local(self, page=1, page_size=50, **kwargs):
        return ([local], 1) if page == 1 else ([], 0)

    monkeypatch.setattr(okw_mod.OKWService, "list", list_local)
    _patch_mom(monkeypatch)

    svc = okw_mod.OKWService()
    facilities = await svc.get_network_match_facilities(
        include_mom=True,
        require_coords=False,
    )
    names = {f.name for f in facilities}
    assert "Harness Additive Lab" in names
    assert "Harness MoM 3DP Lab" in names

    match_svc = MatchingService()
    await match_svc.initialize()
    okh = OKHManifest.from_dict(_load_json("okh_3dp_only.json"))
    solutions = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=facilities,
    )
    assert len(solutions) >= 1


@pytest.mark.asyncio
async def test_multi_req_negative_against_3dp_only_mom(monkeypatch):
    """Multi-process OKH vs 3DP-only MoM stub → 0 solutions (combinations off)."""
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService
    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(return_value=([], 0))
    _patch_mom(monkeypatch)

    facilities = await svc.get_network_match_facilities(
        include_mom=True,
        require_coords=False,
        okw_ids=[MOM_3DP_IRI],
    )
    assert len(facilities) == 1

    match_svc = MatchingService()
    await match_svc.initialize()
    okh = OKHManifest.from_dict(_load_json("okh_multi_process.json"))
    solutions = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=facilities,
    )
    assert len(solutions) == 0


@pytest.mark.asyncio
async def test_mom_stub_id_is_stable_uuid5(monkeypatch):
    from uuid import NAMESPACE_URL, uuid5

    from src.core.services.okw_service import OKWService

    svc = OKWService()
    svc.list = AsyncMock(return_value=([], 0))
    _patch_mom(monkeypatch)

    a = await svc.get_network_match_facilities(
        include_mom=True, require_coords=False, okw_ids=[MOM_3DP_IRI]
    )
    b = await svc.get_network_match_facilities(
        include_mom=True, require_coords=False, okw_ids=[MOM_3DP_IRI]
    )
    assert a[0].id == b[0].id == uuid5(NAMESPACE_URL, MOM_3DP_IRI)
    assert isinstance(a[0].id, UUID)
