"""Integration test for GET /api/okw/spaces (unified network surface, #230).

Runs the full ASGI app in-process. Uses include_mom=false so the endpoint stays
offline (no MoM SPARQL call); the MoM union, cache, and filter behaviour are
unit-tested in tests/unit/test_okw_spaces.py.
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


def test_spaces_local_only_returns_unified_shape(client):
    created = client.post("/api/okw/create", json={"content": _facility_content()})
    assert created.status_code == 201, created.text

    resp = client.get("/api/okw/spaces", params={"include_mom": "false"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert data["mom_available"] is False and data["mom_count"] == 0
    assert isinstance(data["spaces"], list) and data["local_count"] >= 1
    assert data["total"] == len(data["spaces"])
    for s in data["spaces"]:
        assert s["source"] == "local"
        assert {
            "id",
            "name",
            "lat",
            "lon",
            "city",
            "region",
            "country",
            "source",
            "status",
            "processes",
            "url",
        } <= set(s)
        assert isinstance(s["lat"], (int, float)) and isinstance(s["processes"], list)


def test_spaces_source_filter_excludes_local(client):
    client.post("/api/okw/create", json={"content": _facility_content()})
    # Filtering to MoM only, with MoM disabled, yields an empty set (no local leak).
    resp = client.get(
        "/api/okw/spaces", params={"include_mom": "false", "source": "mom"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["spaces"] == []
