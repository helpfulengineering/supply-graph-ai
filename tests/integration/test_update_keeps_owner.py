"""Updating a record keeps its owner.

``update`` stored ``to_dict()``, a whitelist that drops ``ohm_*`` keys, so the
first edit erased ``ohm_created_by``: a private record then belonged to no
one, and its owner could no longer read, edit or list it.
"""

from uuid import uuid4

import pytest

from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration


def _register(client, name):
    resp = client.post("/api/identity/register", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


@pytest.mark.parametrize(
    "kind,content,name_field",
    [("okh", okh_manifest_dict, "title"), ("okw", okw_facility_dict, "name")],
)
def test_the_owner_keeps_a_private_record_after_updating_it(
    client, kind, content, name_field
):
    owner, stranger = _register(client, "Owner"), _register(client, "Stranger")
    record_id = str(uuid4())
    created = client.post(
        f"/api/{kind}/create",
        json={"content": {**content(), "id": record_id}},
        headers=owner,
    )
    assert created.status_code == 201, created.text
    path = f"/api/{kind}/{record_id}"
    try:
        record = client.get(path, headers=owner).json()
        for name in ("Renamed", "Renamed twice"):
            updated = client.put(path, json={**record, name_field: name}, headers=owner)
            assert updated.status_code == 200, updated.text
            after = client.get(path, headers=owner)
            assert after.status_code == 200, f"owner lost the record: {after.text}"
            assert after.json()[name_field] == name
            record = after.json()

        mine = client.get(f"/api/{kind}", params={"mine": "true"}, headers=owner)
        assert record_id in mine.text

        assert client.get(path, headers=stranger).status_code == 404
        overwrite = client.put(
            path, json={**record, name_field: "Hijacked"}, headers=stranger
        )
        assert overwrite.status_code in (403, 404), overwrite.text
    finally:
        client.delete(path, headers=owner)
