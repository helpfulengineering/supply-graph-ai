"""Offline + live taxonomy coverage across processes.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.matching.taxonomy_coverage import (
    build_coverage_report,
    format_coverage_table,
    write_coverage_json,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def _mom_live_enabled() -> bool:
    return os.environ.get("MOM_LIVE", "").strip() in {"1", "true", "TRUE", "yes"}


@pytest.mark.asyncio
async def test_taxonomy_coverage_offline_mocked_mom(monkeypatch, capsys):
    """Reporter works offline: mocked MoM 3DP space → only 3DP family matchable."""
    from src.core.models.okw import ManufacturingFacility
    from src.core.services import okw_service as okw_mod
    from src.core.services.matching_service import MatchingService
    import src.core.services.mom_bridge as mom

    local = ManufacturingFacility.from_dict(
        json.loads((FIXTURES / "okw_additive_local.json").read_text(encoding="utf-8"))
    )
    mom_spaces = json.loads(
        (FIXTURES / "mom_spaces_3dp.json").read_text(encoding="utf-8")
    )

    async def list_local(self, page=1, page_size=50, **kwargs):
        return ([local], 1) if page == 1 else ([], 0)

    async def fake_get(force_refresh=False):
        return (mom_spaces, True)

    monkeypatch.setattr(okw_mod.OKWService, "list", list_local)
    monkeypatch.setattr(mom.mom_spaces_cache, "get", fake_get)

    svc = okw_mod.OKWService()
    facilities = await svc.get_network_match_facilities(
        include_mom=True, require_coords=False
    )
    match_svc = MatchingService()
    await match_svc.initialize()

    rows = await build_coverage_report(
        facilities,
        matching_service=match_svc,
        verify_match=True,
    )
    table = format_coverage_table(rows)
    print("\n" + table)
    write_coverage_json(rows, ARTIFACTS / "taxonomy_coverage_offline.json")

    by_id = {r.canonical_id: r for r in rows}
    assert by_id["3d_printing"].matched
    assert by_id["laser_cutting"].matched  # MoM laser-only fixture
    assert not by_id["welding"].matched
    assert not by_id["cnc_machining"].matched
    # Smoke: we scanned the full taxonomy.
    assert len(rows) >= 40


@pytest.mark.asyncio
@pytest.mark.mom_live
@pytest.mark.allow_network
@pytest.mark.skipif(
    not _mom_live_enabled(), reason="Set MOM_LIVE=1 to run live taxonomy coverage"
)
async def test_taxonomy_coverage_live_mom(capsys):
    """Report matchability of every processes.yaml id against live MoM∪local.

    Informational: does not fail when processes lack MoM coverage. Fails only
    if MoM is unavailable or the scan itself errors.
    """
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities
    from src.core.services.matching_service import MatchingService
    from src.core.services.okw_service import OKWService

    request = MatchRequest.model_construct(
        network_filter={"include_mom": True, "force_refresh": True},
        okw_ids=None,
        okw_facilities=None,
        access_type=None,
        facility_status=None,
        location=None,
        okw_filters={},
    )
    okw_service = await OKWService.get_instance()
    facilities = await _get_filtered_facilities(
        storage_service=okw_service,
        request=request,
        request_id="taxonomy-coverage",
        domain="manufacturing",
    )
    assert facilities, "Live network pool empty — cannot score taxonomy coverage"

    match_svc = MatchingService()
    await match_svc.initialize()
    rows = await build_coverage_report(
        facilities,
        matching_service=match_svc,
        verify_match=True,
        max_candidates=25,
    )
    table = format_coverage_table(rows)
    print("\n" + table)
    out = ARTIFACTS / "taxonomy_coverage_live.json"
    write_coverage_json(rows, out)
    print(f"\nWrote {out}")

    # Soft gate: at least one process in the taxonomy is matchable live.
    assert any(r.matched for r in rows), "No taxonomy process matched against live pool"
