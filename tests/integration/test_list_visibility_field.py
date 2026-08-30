"""List items carry their visibility, so the UI can find what is not yet shared.

Post-#403 a caller sees shareable records plus their own, so a non-shareable
row in a list is necessarily one of the caller's own. That is the signal the
web UI uses to surface "you made this and nobody else can see it" — the list
payload is otherwise silent about visibility, because ``to_dict()`` is a
whitelist.
"""

from __future__ import annotations

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client) -> dict:
    resp = client.post(
        "/api/identity/register", json={"display_name": "Visibility Fixture"}
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def test_okh_list_reports_visibility_and_hides_it_from_others(client):
    auth = _register(client)
    created = client.post(
        "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["okh"]["id"]

    mine = client.get("/api/okh?page_size=100", headers=auth).json()["items"]
    row = next(r for r in mine if r["id"] == record_id)
    # Create stamps private, and the creator is the only one who can see it.
    assert row["visibility"] == "private"

    anonymous = client.get("/api/okh?page_size=100").json()["items"]
    assert record_id not in [r["id"] for r in anonymous]

    # Sharing it moves the row into everyone's list, still reporting its level.
    promoted = client.put(
        f"/api/okh/{record_id}/visibility",
        json={"visibility": "public"},
        headers=auth,
    )
    assert promoted.status_code == 200, promoted.text

    now_public = client.get("/api/okh?page_size=100").json()["items"]
    shared_row = next(r for r in now_public if r["id"] == record_id)
    assert shared_row["visibility"] == "public"


def test_okw_list_reports_visibility(client):
    auth = _register(client)
    created = client.post(
        "/api/okw/create", json={"content": okw_facility_dict()}, headers=auth
    )
    assert created.status_code == 201, created.text
    facility_id = created.json()["okw"]["id"]

    rows = client.get("/api/okw?page_size=100", headers=auth).json()["items"]
    assert next(r for r in rows if r["id"] == facility_id)["visibility"] == "private"

    anonymous = client.get("/api/okw?page_size=100").json()["items"]
    assert facility_id not in [r["id"] for r in anonymous]

    # /api/okw/search is what the web UI actually lists from, and it has its own
    # envelope and its own response model, so it needs its own assertion.
    found = client.get("/api/okw/search?page_size=100", headers=auth).json()["results"]
    assert next(r for r in found if r["id"] == facility_id)["visibility"] == "private"
