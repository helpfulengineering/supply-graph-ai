"""A manifest the catalogue skips still belongs to whoever created it (#590).

The catalogue drops manifests that are not "minimal", like this one, but
``get`` still finds them by scanning storage. Ownership must find them the same
way, or the creator is refused their own record as if it were unattributed.
"""

INCOMPLETE = {
    "title": "Incomplete Widget",
    "repo": "https://github.com/example/widget",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Author",
    "function": "A widget",
}


def test_the_creator_can_share_a_manifest_the_catalogue_skips(client):
    created = client.post("/api/okh/manifests/", json=INCOMPLETE)
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    try:
        shared = client.put(
            f"/api/okh/{record_id}/visibility", json={"visibility": "public"}
        )
        assert shared.status_code == 200, shared.text
    finally:
        client.delete(f"/api/okh/{record_id}")
