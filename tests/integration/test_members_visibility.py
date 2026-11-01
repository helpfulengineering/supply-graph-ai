"""`members` records are visible to anyone signed in to the node, and nobody else (#574).

The driving case: a volunteer shares their home printer with the relief
organisation running the node without publishing it to anonymous visitors.
Catalogue exclusion is pinned in tests/federation/test_catalog.py and
test_okw_catalog.py.
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def _listed_ids(client, kind, headers):
    resp = client.get(f"/api/{kind}?page_size=100", headers=headers)
    assert resp.status_code == 200, resp.text
    return {str(item["id"]) for item in resp.json()["items"]}


@pytest.mark.parametrize(
    "kind,content",
    [("okh", okh_manifest_dict), ("okw", okw_facility_dict)],
)
def test_members_records_are_seen_by_members_only(client, kind, content):
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    record_id = str(uuid4())
    created = client.post(
        f"/api/{kind}/create",
        json={"content": {**content(), "id": record_id}},
        headers=alice,
    )
    assert created.status_code == 201, created.text
    try:
        set_level = client.put(
            f"/api/{kind}/{record_id}/visibility",
            json={"visibility": "members"},
            headers=alice,
        )
        assert set_level.status_code == 200, set_level.text
        assert set_level.json()["visibility"] == "members"

        assert record_id in _listed_ids(client, kind, bob)
        assert client.get(f"/api/{kind}/{record_id}", headers=bob).status_code == 200

        assert record_id not in _listed_ids(client, kind, {})
        assert client.get(f"/api/{kind}/{record_id}").status_code == 404
    finally:
        client.delete(f"/api/{kind}/{record_id}", headers=alice)
