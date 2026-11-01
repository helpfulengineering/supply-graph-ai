"""POST /api/{okh,okw}/visibility changes many records, one result per id (#576).

Each id gets the single-record rule: the caller must own it, and a record they
cannot read answers not_found rather than confirming it exists (#606).
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def _create(client, kind, content, headers, visibility=None):
    record_id = str(uuid4())
    created = client.post(
        f"/api/{kind}/create",
        json={"content": {**content(), "id": record_id}},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    if visibility:
        shared = client.put(
            f"/api/{kind}/{record_id}/visibility",
            json={"visibility": visibility},
            headers=headers,
        )
        assert shared.status_code == 200, shared.text
    return record_id


def _level(client, kind, record_id, headers):
    resp = client.get(f"/api/{kind}/{record_id}/visibility", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["visibility"]


@pytest.mark.parametrize(
    "kind,content", [("okh", okh_manifest_dict), ("okw", okw_facility_dict)]
)
def test_bulk_visibility_reports_each_id_and_changes_only_the_callers(
    client, kind, content
):
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    first = _create(client, kind, content, alice)
    second = _create(client, kind, content, alice)
    bobs_private = _create(client, kind, content, bob)
    bobs_public = _create(client, kind, content, bob, visibility="public")
    missing = str(uuid4())
    try:
        resp = client.post(
            f"/api/{kind}/visibility",
            json={
                "ids": [first, second, bobs_private, bobs_public, missing],
                "visibility": "members",
            },
            headers=alice,
        )
        assert resp.status_code == 200, resp.text
        outcomes = {r["id"]: r["outcome"] for r in resp.json()["results"]}
        assert outcomes == {
            first: "changed",
            second: "changed",
            bobs_private: "not_found",
            bobs_public: "not_yours",
            missing: "not_found",
        }
        assert _level(client, kind, first, alice) == "members"
        assert _level(client, kind, second, alice) == "members"
        assert _level(client, kind, bobs_private, bob) == "private"
        assert _level(client, kind, bobs_public, bob) == "public"
    finally:
        for record_id in (first, second):
            client.delete(f"/api/{kind}/{record_id}", headers=alice)
        for record_id in (bobs_private, bobs_public):
            client.delete(f"/api/{kind}/{record_id}", headers=bob)
