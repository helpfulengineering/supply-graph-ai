"""`mine=true` lists only the caller's own records, shared or not (#576).

The account page needs this to offer bulk visibility change: a shared record of
yours is otherwise indistinguishable from anyone else's in a list.
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


def _mine(client, path, headers):
    resp = client.get(path, params={"mine": "true", "page_size": 100}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = body.get("items") or body.get("results") or []
    return {str(r["id"]) for r in rows}


@pytest.mark.asyncio
@pytest.mark.parametrize("service", ["okh", "okw"])
async def test_mine_without_a_viewer_refuses_rather_than_listing_everything(service):
    from src.core.services.okh_service import OKHService
    from src.core.services.okw_service import OKWService

    svc = (OKHService if service == "okh" else OKWService)()
    with pytest.raises(ValueError, match="viewer"):
        await svc.list(mine=True)


@pytest.mark.parametrize(
    "kind,content,path",
    [
        ("okh", okh_manifest_dict, "/api/okh"),
        ("okw", okw_facility_dict, "/api/okw"),
        ("okw", okw_facility_dict, "/api/okw/search"),
    ],
)
def test_mine_lists_the_callers_records_whatever_their_visibility(
    client, kind, content, path
):
    alice, bob = _register(client, "Alice"), _register(client, "Bob")
    private = _create(client, kind, content, alice)
    shared = _create(client, kind, content, alice, visibility="public")
    bobs = _create(client, kind, content, bob, visibility="public")
    try:
        assert _mine(client, path, alice) >= {private, shared}
        assert bobs not in _mine(client, path, alice)
        assert _mine(client, path, bob) & {private, shared} == set()
        assert bobs in _mine(client, path, bob)
    finally:
        client.delete(f"/api/{kind}/{private}", headers=alice)
        client.delete(f"/api/{kind}/{shared}", headers=alice)
        client.delete(f"/api/{kind}/{bobs}", headers=bob)
