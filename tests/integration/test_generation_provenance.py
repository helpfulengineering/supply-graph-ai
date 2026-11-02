"""A generated design can be saved, and the run stays out of its content hash."""

import pytest

from src.core.federation.catalog import manifest_content_hash
from tests.record_fixtures import okh_manifest_dict

pytestmark = pytest.mark.integration

_RECORD = {
    "schema": "ohm-generation-provenance/v1",
    "source_url": "https://github.com/example/widget",
    "stages": [{"seq": 1, "stage": "extract", "fraction": 1}],
    "fields": {
        "title": {
            "layer": "direct",
            "method": "metadata_name",
            "confidence": 0.9,
            "source": "metadata.name",
        }
    },
}


def _design(body: dict) -> dict:
    """The manifest, without the response envelope that changes per request."""
    drop = {"request_id", "timestamp", "status", "message", "success"}
    return {key: value for key, value in body.items() if key not in drop}


def test_saving_the_run_leaves_the_manifest_and_its_hash_alone(client):
    content = okh_manifest_dict()
    created = client.post("/api/okh/create", json={"content": content})
    assert created.status_code == 201, created.text
    record_id = created.json()["okh"]["id"]

    before = client.get(f"/api/okh/{record_id}")
    assert before.status_code == 200, before.text
    visibility = client.get(f"/api/okh/{record_id}/visibility")
    assert visibility.status_code == 200, visibility.text
    assert visibility.json()["visibility"] == "private"

    stored = client.put(f"/api/okh/{record_id}/generation-provenance", json=_RECORD)
    assert stored.status_code == 200, stored.text
    after = client.get(f"/api/okh/{record_id}")
    assert _design(after.json()) == _design(before.json())
    assert manifest_content_hash(_design(after.json())) == manifest_content_hash(
        _design(before.json())
    )
    assert "ohm-generation-provenance" not in after.text

    fetched = client.get(f"/api/okh/{record_id}/generation-provenance")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["schema"] == _RECORD["schema"]
    assert fetched.json()["source_url"] == _RECORD["source_url"]

    client.delete(f"/api/okh/{record_id}")
