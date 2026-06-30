"""Unit tests for the MoM SPARQL bridge (src/core/services/mom_bridge.py)."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.models.okw import ManufacturingFacility
from src.core.services import mom_bridge


def _sparql_response(bindings):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"results": {"bindings": bindings}}
    return response


def _binding(space, name, lat, lon):
    return {
        "space": {"value": space},
        "name": {"value": name},
        "lat": {"value": str(lat)},
        "lon": {"value": str(lon)},
    }


@pytest.mark.asyncio
async def test_query_mom_spaces_for_process_no_qid_short_circuits():
    """Unrecognized/unmapped canonical IDs must not issue a network call."""
    with patch.object(mom_bridge.httpx, "AsyncClient") as mock_client_cls:
        result = await mom_bridge.query_mom_spaces_for_process("not_a_real_process")

    assert result == []
    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_query_mom_spaces_for_process_parses_bindings():
    bindings = [_binding("https://mom.example/space/1", "Fab Lab Berlin", 52.52, 13.40)]

    mock_client = AsyncMock()
    mock_client.post.return_value = _sparql_response(bindings)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch.object(mom_bridge.httpx, "AsyncClient", return_value=mock_client):
        result = await mom_bridge.query_mom_spaces_for_process("laser_cutting")

    assert result == [
        {
            "space": "https://mom.example/space/1",
            "name": "Fab Lab Berlin",
            "lat": 52.52,
            "lon": 13.40,
        }
    ]
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == mom_bridge.MOM_SPARQL_ENDPOINT
    assert "Q3062349" in kwargs["data"]["query"]


@pytest.mark.asyncio
async def test_query_mom_spaces_for_process_empty_results():
    mock_client = AsyncMock()
    mock_client.post.return_value = _sparql_response([])
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch.object(mom_bridge.httpx, "AsyncClient", return_value=mock_client):
        result = await mom_bridge.query_mom_spaces_for_process("laser_cutting")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_mom_facilities_for_manifest_no_processes_returns_empty():
    manifest = MagicMock()
    manifest.manufacturing_processes = []
    manifest.extract_requirements.return_value = []

    result = await mom_bridge.fetch_mom_facilities_for_manifest(manifest)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_mom_facilities_for_manifest_dedupes_and_merges_processes():
    """A space matching two requested processes is returned once, with both processes listed."""
    manifest = MagicMock()
    manifest.manufacturing_processes = ["laser_cutting", "cnc_machining"]
    manifest.extract_requirements.return_value = []

    space = {
        "space": "https://mom.example/space/1",
        "name": "Fab Lab Berlin",
        "lat": 52.52,
        "lon": 13.40,
    }

    async def fake_query(
        canonical_id, endpoint=mom_bridge.MOM_SPARQL_ENDPOINT, timeout=10.0
    ):
        return [space]

    with patch.object(
        mom_bridge, "query_mom_spaces_for_process", side_effect=fake_query
    ):
        result = await mom_bridge.fetch_mom_facilities_for_manifest(manifest)

    assert len(result) == 1
    facility = result[0]
    assert isinstance(facility, ManufacturingFacility)
    assert facility.name == "Fab Lab Berlin"
    assert facility.manufacturing_processes == ["laser_cutting", "cnc_machining"]
    assert facility.location.gps_coordinates == "52.52, 13.4"


@pytest.mark.asyncio
async def test_fetch_mom_facilities_for_manifest_skips_unrecognized_process_names():
    manifest = MagicMock()
    manifest.manufacturing_processes = ["not_a_real_process"]
    manifest.extract_requirements.return_value = []

    with patch.object(
        mom_bridge, "query_mom_spaces_for_process", new=AsyncMock()
    ) as mock_query:
        result = await mom_bridge.fetch_mom_facilities_for_manifest(manifest)

    assert result == []
    mock_query.assert_not_called()
