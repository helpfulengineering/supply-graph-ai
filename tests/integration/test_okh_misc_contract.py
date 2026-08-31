"""Capture the real responses before modelling them (#373).

The procedure from #370, which exists because a response_model silently filters
any field it does not declare: freeze the payload the route actually returns,
add the model, then prove the payload is unchanged. Deriving a model by reading
the handler is how #369's two bugs got in.

Frozen structurally — keys kept, leaves reduced to a mark — because the
integration client is session-scoped and values depend on what other tests
created.

    BLESS_OKH_MISC=1 .venv/bin/python -m pytest \
        tests/integration/test_okh_misc_contract.py
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from tests.contract_shape import assert_shape
from tests.record_fixtures import okh_manifest_dict

pytestmark = pytest.mark.integration

BLESS = "BLESS_OKH_MISC"


@pytest.fixture
def a_design(client):
    created: list[str] = []

    def make() -> str:
        resp = client.post("/api/okh/create", json={"content": okh_manifest_dict()})
        assert resp.status_code == 201, resp.text
        record_id = resp.json()["okh"]["id"]
        created.append(record_id)
        # Shared, or an anonymous export sees nothing: the collection routes
        # list as the caller, and a fresh record is private.
        shared = client.put(
            f"/api/okh/{record_id}/visibility", json={"visibility": "public"}
        )
        assert shared.status_code == 200, shared.text
        return record_id

    yield make
    for record_id in created:
        client.delete(f"/api/okh/{record_id}")


def test_security_policy_shape(client):
    resp = client.get("/api/identity/security-policy")
    assert resp.status_code == 200, resp.text
    assert_shape(resp.json(), "identity_security_policy", BLESS)


def test_okh_template_shape(client):
    resp = client.get("/api/okh/template")
    assert resp.status_code == 200, resp.text
    assert_shape(resp.json(), "okh_template", BLESS)


def test_okh_export_collection_is_an_archive(client, a_design):
    """Not JSON: this streams a zip, which is why it never had a model."""
    a_design()
    resp = client.get("/api/okh/export-collection")

    assert resp.status_code == 200, resp.text
    assert zipfile.is_zipfile(io.BytesIO(resp.content)), "not a zip archive"


def test_okh_diff_collection_shape(client, a_design):
    """Captured with a NON-EMPTY list.

    An empty list freezes the envelope and says nothing about the item, which
    is what a client actually reads — the same trap that left `designs`
    untypable for two releases (#402). Exporting and then deleting the record
    puts it in the archive and not locally, which is what populates
    `only_in_archive`.
    """
    record_id = a_design()
    archive = client.get("/api/okh/export-collection").content
    client.delete(f"/api/okh/{record_id}")

    resp = client.post(
        "/api/okh/diff-collection",
        files={"file": ("collection.zip", archive, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["only_in_archive"], f"nothing to freeze an item shape from: {body}"
    assert_shape(body, "okh_diff_collection", BLESS)


def test_okh_import_collection_shape(client, a_design):
    """Both a `new` item and a `duplicate` item, for the same reason."""
    kept = a_design()
    archive_with_both = client.get("/api/okh/export-collection").content
    # Deleting one makes it new-to-this-node while the other stays a duplicate.
    client.delete(f"/api/okh/{kept}")

    resp = client.post(
        "/api/okh/import-collection?dry_run=true",
        files={"file": ("collection.zip", archive_with_both, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (
        body["new"] or body["duplicate"]
    ), f"no classified item to freeze a shape from: {body}"
    assert_shape(body, "okh_import_collection", BLESS)
