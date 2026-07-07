"""OKW_SOURCE=mom routing under the unified resolver (#240).

Since the union-default change, all sources route through
``OKWService.get_network_match_facilities`` (the network surface), not the
per-manifest ``fetch_mom_facilities_for_manifest`` path. ``OKW_SOURCE=mom`` still
means "MoM only" and still wins over ``MATCHING_LOCAL_OKW_JSON_DIR``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _mock_network(monkeypatch, return_value):
    """Patch OKWService.get_instance so get_network_match_facilities is captured."""
    from src.core.services import okw_service as okw_mod

    svc = AsyncMock()
    svc.get_network_match_facilities = AsyncMock(return_value=return_value)
    monkeypatch.setattr(okw_mod.OKWService, "get_instance", AsyncMock(return_value=svc))
    return svc


@pytest.mark.asyncio
async def test_mom_routes_through_network_path_only(monkeypatch):
    from src.core.services.okw_service import resolve_match_facilities
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    mom_fac = ManufacturingFacility(
        name="Fab Lab Berlin",
        location=Location(gps_coordinates="52.52, 13.4"),
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=["laser_cutting"],
    )
    svc = _mock_network(monkeypatch, [mom_fac])

    # The requirement-aware per-manifest MoM fetch must NOT be used any more.
    fetch = AsyncMock()
    monkeypatch.setattr(
        "src.core.services.mom_bridge.fetch_mom_facilities_for_manifest", fetch
    )

    result = await resolve_match_facilities(effective_source="mom")

    assert result == [mom_fac]
    fetch.assert_not_awaited()
    svc.get_network_match_facilities.assert_awaited_once()
    kwargs = svc.get_network_match_facilities.await_args.kwargs
    assert kwargs["include_mom"] is True
    assert kwargs["source"] == "mom"
    assert kwargs["require_coords"] is False


@pytest.mark.asyncio
async def test_mom_wins_over_local_json_dir(tmp_path, monkeypatch):
    """OKW_SOURCE=mom is explicit; it must beat MATCHING_LOCAL_OKW_JSON_DIR."""
    import json

    from src.core.services import okw_service as okw_mod
    from src.core.services.okw_service import resolve_match_facilities
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    (tmp_path / "facility.json").write_text(
        json.dumps(
            {
                "name": "Local JSON Facility",
                "location": {"gps_coordinates": "0.0, 0.0"},
                "facility_status": "Active",
                "manufacturing_processes": ["laser_cutting"],
            }
        )
    )
    monkeypatch.setattr(
        "src.config.settings.MATCHING_LOCAL_OKW_JSON_DIR", str(tmp_path)
    )

    # If the local-dir loader were reached, this would fire the assertion.
    monkeypatch.setattr(
        okw_mod,
        "load_facilities_from_local_okw_json_dir",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("local dir must not be read when OKW_SOURCE=mom")
        ),
    )

    mom_fac = ManufacturingFacility(
        name="Fab Lab Berlin",
        location=Location(gps_coordinates="52.52, 13.4"),
        facility_status=FacilityStatus.ACTIVE,
    )
    _mock_network(monkeypatch, [mom_fac])

    result = await resolve_match_facilities(effective_source="mom")
    assert result == [mom_fac]
