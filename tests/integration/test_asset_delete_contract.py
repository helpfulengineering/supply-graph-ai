"""Capture the delete response before modelling it (#373).

The last of the small rows: ``DELETE /api/asset/{id}`` returned a bare dict
with no model, so the generated schema said nothing about it and a client had
to guess.

    BLESS_ASSET_DELETE=1 .venv/bin/python -m pytest \
        tests/integration/test_asset_delete_contract.py
"""

from __future__ import annotations

import pytest

from tests.contract_shape import assert_shape

pytestmark = pytest.mark.integration

BLESS = "BLESS_ASSET_DELETE"

_MANIFEST = {
    "title": "Asset Delete Contract Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for the asset delete contract test",
}


@pytest.fixture
def an_asset(client):
    """One asset, owned by a registered caller, ready to be deleted."""
    registration = client.post(
        "/api/identity/register", json={"display_name": "Asset Delete Fixture"}
    )
    assert registration.status_code == 201, registration.text
    auth = {"Authorization": f"Bearer {registration.json()['key']['token']}"}

    manifest = client.post("/api/okh/manifests/", json=_MANIFEST, headers=auth)
    assert manifest.status_code == 201, manifest.text

    asset = client.post(
        "/api/asset/",
        json={"manifest_id": manifest.json()["id"], "asset_tag": "SN-CONTRACT-01"},
        headers=auth,
    )
    assert asset.status_code == 201, asset.text
    return auth, asset.json()["id"]


def test_asset_delete_shape(client, an_asset):
    auth, asset_id = an_asset
    response = client.delete(f"/api/asset/{asset_id}", headers=auth)
    assert response.status_code == 200, response.text
    assert_shape(response.json(), "asset_delete", BLESS)
