"""Regression: match API must route to MoM SPARQL when OKW_SOURCE=mom (no inline OKWs,
no MATCHING_LOCAL_OKW_JSON_DIR) and must not touch blob storage in that case."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.mark.asyncio
async def test_get_filtered_facilities_uses_mom_when_okw_source_mom(monkeypatch):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes import match as match_mod
    from src.core.models.okh import License, OKHManifest
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility
    from src.core.services import okw_service as okw_mod

    monkeypatch.setenv("OKW_SOURCE", "mom")
    monkeypatch.setattr(match_mod, "_resolve_matching_local_okw_json_dir", lambda: None)

    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("OKWService must not load when OKW_SOURCE=mom")
        ),
    )

    mom_facility = ManufacturingFacility(
        name="Fab Lab Berlin",
        location=Location(gps_coordinates="52.52, 13.4"),
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=["laser_cutting"],
    )

    mock_fetch = AsyncMock(return_value=[mom_facility])
    monkeypatch.setattr(
        "src.core.services.mom_bridge.fetch_mom_facilities_for_manifest", mock_fetch
    )

    manifest = OKHManifest(
        title="Test Manifest",
        version="1.0.0",
        license=License(hardware="CERN-OHL-S-2.0"),
        licensor="Test Licensor",
        documentation_language="en",
        function="Test function",
        manufacturing_processes=["laser_cutting"],
    )
    req = MatchRequest.model_construct(okw_facilities=None)

    facilities = await match_mod._get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
        okh_manifest=manifest,
    )

    assert facilities == [mom_facility]
    mock_fetch.assert_awaited_once()
    assert mock_fetch.call_args.args[0] is manifest


@pytest.mark.asyncio
async def test_get_filtered_facilities_mom_wins_over_local_json_dir(
    tmp_path, monkeypatch
):
    """Regression: OKW_SOURCE=mom must win over MATCHING_LOCAL_OKW_JSON_DIR.

    Previously the API checked MATCHING_LOCAL_OKW_JSON_DIR before OKW_SOURCE,
    so a dev-convenience env var silently overrode an explicit mom request —
    a divergence from the CLI, where --okw-source mom always reaches MoM.
    See docs/runbooks/mom-integration-e2e-validation.md (Troubleshooting).
    """
    import json

    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes import match as match_mod
    from src.core.models.okh import License, OKHManifest
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility
    from src.core.services import okw_service as okw_mod

    monkeypatch.setenv("OKW_SOURCE", "mom")

    local_facility = {
        "name": "Local JSON Facility",
        "location": {"gps_coordinates": "0.0, 0.0"},
        "facility_status": "Active",
        "manufacturing_processes": ["laser_cutting"],
    }
    (tmp_path / "facility.json").write_text(json.dumps(local_facility))
    monkeypatch.setattr(
        "src.config.settings.MATCHING_LOCAL_OKW_JSON_DIR", str(tmp_path)
    )

    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("OKWService must not load when OKW_SOURCE=mom")
        ),
    )

    mom_facility = ManufacturingFacility(
        name="Fab Lab Berlin",
        location=Location(gps_coordinates="52.52, 13.4"),
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=["laser_cutting"],
    )
    mock_fetch = AsyncMock(return_value=[mom_facility])
    monkeypatch.setattr(
        "src.core.services.mom_bridge.fetch_mom_facilities_for_manifest", mock_fetch
    )

    manifest = OKHManifest(
        title="Test Manifest",
        version="1.0.0",
        license=License(hardware="CERN-OHL-S-2.0"),
        licensor="Test Licensor",
        documentation_language="en",
        function="Test function",
        manufacturing_processes=["laser_cutting"],
    )
    req = MatchRequest.model_construct(okw_facilities=None)

    facilities = await match_mod._get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
        okh_manifest=manifest,
    )

    assert facilities == [mom_facility]
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_filtered_facilities_ignores_mom_without_okh_manifest(monkeypatch):
    """get_okw_source()=='mom' is only honored when an OKH manifest is available
    to derive required processes from; otherwise falls through to blob storage."""
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes import match as match_mod
    from src.core.services import okw_service as okw_mod

    monkeypatch.setenv("OKW_SOURCE", "mom")
    monkeypatch.setattr(match_mod, "_resolve_matching_local_okw_json_dir", lambda: None)

    mock_get_instance = AsyncMock()
    mock_okw_service = AsyncMock()
    mock_okw_service.list.return_value = ([], 0)
    mock_get_instance.return_value = mock_okw_service
    monkeypatch.setattr(okw_mod.OKWService, "get_instance", mock_get_instance)

    req = MatchRequest.model_construct(okw_facilities=None)

    await match_mod._get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
        okh_manifest=None,
    )

    mock_get_instance.assert_awaited()
