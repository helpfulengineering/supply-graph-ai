"""Integration tests for POST /api/match/facility (reverse matching, review #7).

Runs the full ASGI app in-process (TestClient + local storage from conftest).
The ranking logic is unit-tested separately; here we verify the endpoint is
wired end-to-end: unknown facilities 404, and a real facility returns the
documented response envelope.
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def test_reverse_match_unknown_facility_returns_404(client):
    resp = client.post("/api/match/facility", json={"okw_id": str(uuid4())})
    assert resp.status_code == 404, resp.text


def test_reverse_match_returns_ranked_envelope(client, matchable_design):
    """The design has to be one matching can see, or this asserts nothing.

    It used to create no design at all, so the loop below ran zero times and
    the endpoint's item shape was never checked — the test passed for years
    without exercising the thing it names. Records are created ``private`` and
    an anonymous list returns only shareable ones, which is why the fixture
    shares it first.
    """
    matchable_design(okh_manifest_dict())
    created = client.post("/api/okw/create", json={"content": okw_facility_dict()})
    assert created.status_code == 201, created.text
    okw_id = created.json()["okw"]["id"]

    resp = client.post(
        "/api/match/facility",
        json={"okw_id": okw_id, "min_confidence": 0.1, "max_results": 5},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["okw_id"] == okw_id
    assert data["total_designs"] == len(data["designs"])
    assert (
        data["designs_considered"] >= 1
    ), "matching examined no designs, so the assertions below check nothing"
    assert data["designs"], "no design matched, so the item shape is unchecked"
    # Each returned design carries a friendly identity + ranking.
    for d in data["designs"]:
        assert {"okh_id", "okh_title", "confidence", "rank"} <= set(d)
