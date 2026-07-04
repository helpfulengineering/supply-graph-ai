"""Integration test for GET /api/okw/map (network map, review #1).

Runs the full ASGI app in-process. Uses include_mom=false so the endpoint stays
offline (no MoM SPARQL call); the MoM union + cache behaviour is unit-tested
separately in tests/unit/test_okw_map.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

pytestmark = pytest.mark.integration


def _facility_content() -> dict:
    data_dir = Path(__file__).resolve().parents[2] / "synthetic_data"
    facility_file = sorted(data_dir.glob("*okw*.json"))[0]
    return json.loads(facility_file.read_text(encoding="utf-8"))


def test_map_local_only_returns_source_labeled_points(client):
    created = client.post("/api/okw/create", json={"content": _facility_content()})
    assert created.status_code == 201, created.text

    resp = client.get("/api/okw/map", params={"include_mom": "false"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert data["mom_available"] is False
    assert data["mom_count"] == 0
    assert isinstance(data["points"], list)
    # The synthetic facility carries gps_coordinates, so it plots as a local point.
    assert data["local_count"] >= 1
    for p in data["points"]:
        assert p["source"] == "local"
        assert {"id", "name", "lat", "lon", "source"} <= set(p)
        assert isinstance(p["lat"], (int, float))
        assert isinstance(p["lon"], (int, float))
