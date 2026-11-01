"""A plain match must not draw on another member's private facility (#595).

#503 scoped the ``network_filter`` branch of the match pool; a match without one
still listed every facility on the node, and returned a private one as a
solution to anyone who asked.
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def _matched_facility_ids(client, auth):
    design = client.post(
        "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
    )
    assert design.status_code == 201, design.text
    design_id = design.json()["okh"]["id"]
    try:
        resp = client.post(
            "/api/match",
            json={"okh_id": design_id, "min_confidence": 0.0},
            headers=auth,
        )
        assert resp.status_code == 200, resp.text
        return {
            str((s.get("facility") or {}).get("id"))
            for s in resp.json()["data"]["solutions"]
        }
    finally:
        client.delete(f"/api/okh/{design_id}", headers=auth)


def test_only_the_owner_matches_against_a_private_facility(client, monkeypatch):
    monkeypatch.setenv("OKW_SOURCE", "storage")
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    facility_id = str(uuid4())
    created = client.post(
        "/api/okw/create",
        json={"content": {**okw_facility_dict(), "id": facility_id}},
        headers=alice,
    )
    assert created.status_code == 201, created.text
    try:
        assert facility_id not in _matched_facility_ids(client, bob)
        assert facility_id in _matched_facility_ids(client, alice)
    finally:
        client.delete(f"/api/okw/{facility_id}", headers=alice)
