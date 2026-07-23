"""Opt-in live MoM SPARQL smoke — skipped unless MOM_LIVE=1."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_3DP_CANONICAL = {
    "3d_printing",
    "3d_printing_fdm",
    "3d_printing_sla",
    "3d_printing_sls",
    "3d_printing_dlp",
}


def _mom_live_enabled() -> bool:
    return os.environ.get("MOM_LIVE", "").strip() in {"1", "true", "TRUE", "yes"}


pytestmark = [
    pytest.mark.mom_live,
    pytest.mark.allow_network,
    pytest.mark.skipif(
        not _mom_live_enabled(), reason="Set MOM_LIVE=1 to run live MoM smoke"
    ),
]


@pytest.mark.asyncio
async def test_live_mom_pool_has_3dp_capable_space():
    from src.core.services.mom_bridge import mom_spaces_cache
    from src.core.taxonomy import taxonomy

    spaces, available = await mom_spaces_cache.get(force_refresh=True)
    assert available, "Live MoM cache reported unavailable"
    assert spaces, "Live MoM returned no spaces"

    def claims_3dp(space: dict) -> bool:
        for p in space.get("processes") or []:
            cid = taxonomy.normalize(p) or p
            if cid in _3DP_CANONICAL or cid == "3DP":
                return True
            ancestors = taxonomy.get_ancestors(cid) or []
            if "3d_printing" in ancestors or cid == "3d_printing":
                return True
        return False

    assert any(
        claims_3dp(s) for s in spaces
    ), "No live MoM space normalized to a 3D-printing process"


@pytest.mark.asyncio
async def test_live_network_match_facility_count_positive():
    """Soft match: 3DP-only harness OKH against live network (no okw_ids)."""
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities
    from src.core.models.okh import OKHManifest
    from src.core.services.matching_service import MatchingService
    from src.core.services.okw_service import OKWService

    okh = OKHManifest.from_dict(
        json.loads((FIXTURES / "okh_3dp_only.json").read_text(encoding="utf-8"))
    )
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
        request_id="mom-live",
        domain="manufacturing",
    )
    assert len(facilities) > 0, "Live network match pool was empty"

    match_svc = MatchingService()
    await match_svc.initialize()
    # Soft: pool non-empty is the release gate; solutions depend on live MoM tags.
    _ = await match_svc.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=facilities[:50],
    )
