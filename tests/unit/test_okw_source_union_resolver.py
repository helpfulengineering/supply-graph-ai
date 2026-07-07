"""#240 — OKW_SOURCE union default + shared facility-pool resolver.

Covers the tri-state (union|storage|mom), env-restricts-request-narrows
precedence, MATCHING_LOCAL_OKW_JSON_DIR (storage-only, never unioned),
MoM-down graceful degradation, coordinate-less retention for matching, and
API↔CLI parity on the single shared resolver.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def clean_env(monkeypatch):
    for key in ("OKW_SOURCE", "MATCHING_LOCAL_OKW_JSON_DIR"):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


# ---------------------------------------------------------------------------
# Precedence: env sets the universe; request narrows within it, never broadens.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "env, request_source, expected",
    [
        (None, None, "union"),  # unset → union
        (None, "storage", "storage"),  # union narrows to storage
        (None, "mom", "mom"),  # union narrows to mom
        ("storage", None, "storage"),
        ("storage", "mom", "storage"),  # cannot broaden storage → mom
        ("storage", "union", "storage"),  # cannot broaden back to union
        ("mom", None, "mom"),
        ("mom", "storage", "mom"),  # mom is absolute
        ("union", "storage", "storage"),
        ("union", None, "union"),
    ],
)
def test_resolve_effective_source(clean_env, env, request_source, expected):
    from src.config.storage_config import resolve_effective_source

    if env is not None:
        clean_env.setenv("OKW_SOURCE", env)
    assert resolve_effective_source(request_source) == expected


# ---------------------------------------------------------------------------
# Resolver routing: each source maps to the right network-path call.
# ---------------------------------------------------------------------------


def _mock_network(monkeypatch, return_value=None):
    from src.core.services import okw_service as okw_mod

    svc = AsyncMock()
    svc.get_network_match_facilities = AsyncMock(return_value=return_value or [])
    monkeypatch.setattr(okw_mod.OKWService, "get_instance", AsyncMock(return_value=svc))
    # Ensure no stray local dir interferes.
    monkeypatch.setattr(okw_mod, "resolve_matching_local_okw_json_dir", lambda: None)
    return svc


@pytest.mark.asyncio
async def test_union_includes_mom(clean_env, monkeypatch):
    from src.core.services.okw_service import resolve_match_facilities

    svc = _mock_network(monkeypatch)
    await resolve_match_facilities(effective_source="union")
    kwargs = svc.get_network_match_facilities.await_args.kwargs
    assert kwargs["include_mom"] is True
    assert kwargs.get("source") is None
    assert kwargs["require_coords"] is False


@pytest.mark.asyncio
async def test_storage_excludes_mom(clean_env, monkeypatch):
    from src.core.services.okw_service import resolve_match_facilities

    svc = _mock_network(monkeypatch)
    await resolve_match_facilities(effective_source="storage")
    kwargs = svc.get_network_match_facilities.await_args.kwargs
    assert kwargs["include_mom"] is False


# ---------------------------------------------------------------------------
# MATCHING_LOCAL_OKW_JSON_DIR: storage-only, never unioned.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_dir_is_storage_only_never_unioned(clean_env, monkeypatch):
    from src.core.services import okw_service as okw_mod
    from src.core.services.okw_service import resolve_match_facilities

    sentinel = ["local-only"]
    monkeypatch.setattr(
        okw_mod, "resolve_matching_local_okw_json_dir", lambda: "/some/dir"
    )
    monkeypatch.setattr(
        okw_mod,
        "load_facilities_from_local_okw_json_dir",
        lambda *a, **k: list(sentinel),
    )
    # If the network path were taken, this would fail the test.
    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("must not touch storage/MoM for local dir")
        ),
    )

    # Even with the union default, a local dir is never unioned with MoM.
    result = await resolve_match_facilities(effective_source="union")
    assert result == sentinel


# ---------------------------------------------------------------------------
# Coordinate-less facilities: dropped for browse, retained for matching.
# ---------------------------------------------------------------------------


def _facility_without_coords():
    from src.core.models.okw import FacilityStatus, Location, ManufacturingFacility

    return ManufacturingFacility(
        name="No-Coords Fab",
        location=Location(city="Nowhere"),  # no gps_coordinates
        facility_status=FacilityStatus.ACTIVE,
        manufacturing_processes=["cnc_milling"],
    )


def test_coordless_dropped_when_require_coords_true():
    from src.core.services.okw_service import _local_facility_to_space

    assert _local_facility_to_space(_facility_without_coords()) is None


def test_coordless_retained_when_require_coords_false():
    from src.core.services.okw_service import _local_facility_to_space

    space = _local_facility_to_space(_facility_without_coords(), require_coords=False)
    assert space is not None
    assert space["lat"] is None and space["lon"] is None
    assert space["source"] == "local"


# ---------------------------------------------------------------------------
# MoM-down graceful degradation: union still returns storage facilities.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_union_degrades_to_storage_when_mom_unavailable(clean_env, monkeypatch):
    from src.core.services import okw_service as okw_mod

    local = _facility_without_coords()

    async def _one_page(self, *, page, page_size):
        return ([local], 1) if page == 1 else ([], 0)

    monkeypatch.setattr(okw_mod.OKWService, "list", _one_page)
    # MoM cache reports unavailable (network down) → no MoM candidates added.
    from src.core.services import mom_bridge

    monkeypatch.setattr(
        mom_bridge.mom_spaces_cache,
        "get",
        AsyncMock(return_value=([], False)),
    )

    svc = await okw_mod.OKWService.get_instance()
    facilities = await svc.get_network_match_facilities(
        include_mom=True, require_coords=False
    )
    assert facilities == [local]


# ---------------------------------------------------------------------------
# API ↔ CLI parity: both use the one shared resolver object.
# ---------------------------------------------------------------------------


def test_api_and_service_share_one_resolver():
    import src.core.api.routes.match as match_mod
    from src.core.services import okw_service as okw_mod

    assert match_mod.resolve_match_facilities is okw_mod.resolve_match_facilities
