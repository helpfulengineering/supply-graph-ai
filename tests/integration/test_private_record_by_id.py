"""A private record is readable by id by its owner only, not by every signed-in account.

Lists were scoped per viewer in #403; the by-id reads kept an anonymous-only
check, so any account on the node could fetch another's private record by id.
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
    "kind,content",
    [("okh", okh_manifest_dict), ("okw", okw_facility_dict)],
)
def test_only_the_owner_reads_a_private_record_by_id(client, kind, content):
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    record_id = str(uuid4())
    created = client.post(
        f"/api/{kind}/create",
        json={"content": {**content(), "id": record_id}},
        headers=alice,
    )
    assert created.status_code == 201, created.text
    try:
        for path in (f"/api/{kind}/{record_id}", f"/api/{kind}/{record_id}/visibility"):
            assert client.get(path, headers=alice).status_code == 200, path
            assert client.get(path, headers=bob).status_code == 404, path

        for path, body in _OTHER_READS[kind](record_id):
            resp = client.post(path, json=body, headers=bob)
            assert resp.status_code == 404, f"{path}: {resp.status_code} {resp.text}"
    finally:
        client.delete(f"/api/{kind}/{record_id}", headers=alice)


_OTHER_READS = {
    "okh": lambda rid: [
        ("/api/okh/from-storage", {"manifest_id": rid}),
        ("/api/okh/harvest-parts", {"manifest_ids": [rid]}),
        (f"/api/package/build/{rid}", None),
        ("/api/match", {"okh_id": rid}),
    ],
    "okw": lambda rid: [("/api/match/facility", {"okw_id": rid})],
}
