"""Matching against this node's member facilities only (#575).

The facility without a key is attributed to the dev-local account, which no
account store holds — the same shape as a synced facility, whose attribution
names an account on its origin node.
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def _create_facility(client, headers):
    facility_id = str(uuid4())
    created = client.post(
        "/api/okw/create",
        json={
            "content": {**okw_facility_dict(), "id": facility_id, "name": facility_id}
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return facility_id


def _matched_facility_ids(client, design_id, network_filter):
    resp = client.post(
        "/api/match",
        json={
            "okh_id": design_id,
            "min_confidence": 0.0,
            "network_filter": network_filter,
        },
    )
    assert resp.status_code == 200, resp.text
    return {
        str((s.get("facility") or {}).get("id"))
        for s in resp.json()["data"]["solutions"]
    }


def test_the_member_filter_matches_only_facilities_by_members(client):
    alice = _register(client, "Alice")
    members = _create_facility(client, alice)
    shared = client.put(
        f"/api/okw/{members}/visibility",
        json={"visibility": "public"},
        headers=alice,
    )
    assert shared.status_code == 200, shared.text
    not_a_member = _create_facility(client, {})
    design = client.post("/api/okh/create", json={"content": okh_manifest_dict()})
    assert design.status_code == 201, design.text
    design_id = design.json()["okh"]["id"]
    try:
        everyone = _matched_facility_ids(client, design_id, {"include_mom": False})
        assert members in everyone
        assert not_a_member in everyone

        only_members = _matched_facility_ids(client, design_id, {"members_only": True})
        assert members in only_members
        assert not_a_member not in only_members
    finally:
        client.delete(f"/api/okh/{design_id}")
        client.delete(f"/api/okw/{not_a_member}")
        client.delete(f"/api/okw/{members}", headers=alice)
