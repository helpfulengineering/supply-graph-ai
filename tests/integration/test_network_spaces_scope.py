"""GET /api/okw/spaces lists only facilities the caller may see.

The browse surface built its local half without a viewer, so a private facility
appeared on every visitor's map and facility list.
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def _space_ids(client, headers):
    resp = client.get("/api/okw/spaces?include_mom=false", headers=headers)
    assert resp.status_code == 200, resp.text
    return {s["id"] for s in resp.json()["spaces"]}


def test_the_network_view_follows_each_facilitys_visibility(client):
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    facility_id = str(uuid4())
    created = client.post(
        "/api/okw/create",
        json={"content": {**okw_facility_dict(), "id": facility_id}},
        headers=alice,
    )
    assert created.status_code == 201, created.text
    try:
        assert facility_id in _space_ids(client, alice)
        assert facility_id not in _space_ids(client, bob)
        assert facility_id not in _space_ids(client, {})

        shared = client.put(
            f"/api/okw/{facility_id}/visibility",
            json={"visibility": "members"},
            headers=alice,
        )
        assert shared.status_code == 200, shared.text
        assert facility_id in _space_ids(client, bob)
        assert facility_id not in _space_ids(client, {})
    finally:
        client.delete(f"/api/okw/{facility_id}", headers=alice)
