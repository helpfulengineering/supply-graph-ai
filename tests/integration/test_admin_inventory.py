"""An operator enumerates and deletes without reading (#405).

The ratified boundary is that an admin's record scope is identical to any other
authenticated user's — they do not read private records. That is only survivable
if operators get a replacement, and this is it. The test that matters most is
the negative one: no field here may be derived from manifest content, because a
title states intent and intent is most of what a private draft is.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration

GOLDEN = Path(__file__).resolve().parents[1] / "api" / "golden" / "inventory_row.json"

#: Anything a manifest supplies. If one of these ever appears in a row, the
#: surface has become a browse surface.
CONTENT_FIELDS = {
    "title",
    "description",
    "name",
    "repo",
    "function",
    "license",
    "licensor",
    "manifest",
    "content",
    "keywords",
}


def _register(client) -> tuple[dict, str]:
    resp = client.post(
        "/api/identity/register", json={"display_name": "Inventory Fixture"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"Authorization": f"Bearer {body['key']['token']}"}, body["did"]


def test_inventory_reports_metadata_and_no_content(client):
    auth, did = _register(client)
    created = client.post(
        "/api/okh/create",
        json={"content": okh_manifest_dict()},
        headers=auth,
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["okh"]["id"]

    resp = client.get("/api/okh/inventory", headers=auth)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    row = next(r for r in data["rows"] if r["id"] == record_id)

    # What an operator needs.
    assert row["visibility"] == "private"
    assert row["created_by_did"] == did
    assert row["created_by_account"]
    assert row["size_bytes"] and row["size_bytes"] > 0

    # And what they must not get. Checked against the row's own keys rather
    # than a fixed list, so a field added later has to be considered.
    assert not (CONTENT_FIELDS & set(row)), f"content leaked into the row: {row}"
    assert okh_manifest_dict()["title"] not in json.dumps(data)

    # The count an operator actually reasons about.
    assert data["private_total"] >= 1
    assert data["total"] >= data["private_total"]


def test_inventory_covers_facilities_too(client):
    auth, _ = _register(client)
    created = client.post(
        "/api/okw/create", json={"content": okw_facility_dict()}, headers=auth
    )
    assert created.status_code == 201, created.text
    facility_id = created.json()["okw"]["id"]

    rows = client.get("/api/okw/inventory", headers=auth).json()["data"]["rows"]
    row = next(r for r in rows if r["id"] == facility_id)

    assert row["visibility"] == "private"
    assert not (CONTENT_FIELDS & set(row))
    assert okw_facility_dict()["name"] not in json.dumps(rows)


def test_an_admin_can_delete_what_they_cannot_read(client):
    """The whole point: takedown works on an id."""
    auth, _ = _register(client)
    created = client.post(
        "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
    )
    record_id = created.json()["okh"]["id"]

    listed = client.get("/api/okh/inventory", headers=auth).json()["data"]["rows"]
    assert record_id in [r["id"] for r in listed]

    deleted = client.delete(f"/api/okh/{record_id}", headers=auth)
    assert deleted.status_code in (200, 204), deleted.text

    after = client.get("/api/okh/inventory", headers=auth).json()["data"]["rows"]
    assert record_id not in [r["id"] for r in after]


def test_inventory_row_shape_is_frozen(client):
    """A golden over the row's key set.

    Values are not frozen — sizes and timestamps vary per run, and the id and
    owner come from a fresh registration. Keys are what a response_model can
    drop and what a caller depends on, so keys are what this locks.
    """
    auth, _ = _register(client)
    client.post("/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth)

    rows = client.get("/api/okh/inventory", headers=auth).json()["data"]["rows"]
    assert rows, "fixture produced no rows, so this would freeze nothing"
    shape = sorted(rows[0].keys())

    if os.getenv("BLESS_INVENTORY_CONTRACT"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(shape, indent=2) + "\n")
        pytest.skip("golden re-blessed")

    assert (
        GOLDEN.exists()
    ), f"No golden at {GOLDEN}. Capture one with BLESS_INVENTORY_CONTRACT=1."
    assert shape == json.loads(GOLDEN.read_text()), (
        "The inventory row changed shape. If a field was added, confirm it is "
        "not derived from manifest content before re-blessing."
    )
