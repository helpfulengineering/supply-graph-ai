"""Regression: match API must honor MatchRequest.okw_facilities (avoid blocking storage list)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.mark.asyncio
async def test_get_filtered_facilities_inline_manufacturing_skips_okw_service(
    monkeypatch,
):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities
    from src.core.services import okw_service as okw_mod

    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("OKWService must not load when inline OKWs")
        ),
    )

    okw_path = (
        _REPO_ROOT / "synthetic_data" / "additive-manufacturing-center-015-okw.json"
    )
    facility_dict = json.loads(okw_path.read_text(encoding="utf-8"))

    req = MatchRequest.model_construct(okw_facilities=[facility_dict])

    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
    )
    assert len(facilities) == 1
    assert getattr(facilities[0], "name", None) == "Additive Manufacturing Center"


@pytest.mark.asyncio
async def test_get_filtered_facilities_inline_empty_returns_empty_manufacturing(
    monkeypatch,
):
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes.match import _get_filtered_facilities
    from src.core.services import okw_service as okw_mod

    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("OKWService must not load when inline OKWs")
        ),
    )

    req = MatchRequest.model_construct(okw_facilities=[])

    facilities = await _get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
    )
    assert facilities == []


@pytest.mark.asyncio
async def test_get_filtered_facilities_local_json_dir_skips_okw_service(
    tmp_path,
    monkeypatch,
):
    """MATCHING_LOCAL_OKW_JSON_DIR avoids OKWService.list() when inline OKWs absent."""
    from src.core.api.models.match.request import MatchRequest
    from src.core.api.routes import match as match_mod
    from src.core.services import okw_service as okw_mod

    sample = (
        _REPO_ROOT / "synthetic_data" / "additive-manufacturing-center-015-okw.json"
    )
    dest = tmp_path / "fac.json"
    dest.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(
        "src.config.settings.MATCHING_LOCAL_OKW_JSON_DIR",
        str(tmp_path),
    )

    monkeypatch.setattr(
        okw_mod.OKWService,
        "get_instance",
        AsyncMock(
            side_effect=AssertionError("OKWService must not list remote storage")
        ),
    )

    req = MatchRequest.model_construct(okw_facilities=None)

    facilities = await match_mod._get_filtered_facilities(
        storage_service=None,
        request=req,
        request_id="unit-test",
        domain="manufacturing",
    )
    assert len(facilities) == 1
    assert getattr(facilities[0], "name", None) == "Additive Manufacturing Center"
