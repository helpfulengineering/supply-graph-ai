"""A node admin publishes a curated list a peer can verify offline (#580)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.core.federation.catalog import manifest_content_hash
from src.core.federation.identity import verify_payload
from src.core.federation.node_role import NodeRole, capabilities_for_role
from src.core.federation.service import FederationService
from src.core.federation.store import FederationStore
from src.core.models.auth import APIKeyCreate
from src.core.models.visibility import VisibilityLevel
from src.core.services.base import ServiceStatus
from tests.api.test_affiliation_required import MINIMAL, _ada, _auth, _client


class _Design:
    def __init__(self, data: dict, visibility: VisibilityLevel) -> None:
        self.id = UUID(data["id"])
        self.visibility = visibility
        self._data = data

    def to_dict(self) -> dict:
        return self._data


class _Designs:
    def __init__(self, designs: list[_Design]) -> None:
        self._designs = designs

    async def list(self, **_kwargs):
        return self._designs, len(self._designs)

    async def get_visibility(self, manifest_id):
        for design in self._designs:
            if design.id == manifest_id:
                return design.visibility
        raise KeyError(manifest_id)


def _federation(tmp_path) -> FederationService:
    service = FederationService()
    service.status = ServiceStatus.ACTIVE
    service.store = FederationStore(tmp_path / "federation")
    service.role = NodeRole.PEER
    service.capabilities = capabilities_for_role(NodeRole.PEER)
    from src.core.federation.identity import generate_identity

    service.identity = generate_identity("List Node")
    return service


def _payload(body: dict) -> dict:
    entries = []
    for entry in body["entries"]:
        item = {"content_hash": entry["content_hash"]}
        if entry.get("supersedes"):
            item["supersedes"] = entry["supersedes"]
        entries.append(item)
    return {
        "list_id": body["list_id"],
        "name": body["name"],
        "publisher_did": body["publisher_did"],
        "sequence": body["sequence"],
        "entries": entries,
    }


@pytest.mark.asyncio
async def test_a_node_admin_publishes_a_list_a_peer_can_verify(tmp_path, monkeypatch):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service, get_okh_for_lists

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    federation = _federation(tmp_path)
    design = _Design(dict(MINIMAL), VisibilityLevel.FOLLOWERS)
    content_hash = manifest_content_hash(design.to_dict())

    async with _client(
        monkeypatch,
        auth,
        overrides={
            get_federation_service: lambda: federation,
            get_okh_for_lists: lambda: _Designs([design]),
        },
    ) as client:
        published = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {admin.token}"},
            json={"name": "Field designs", "entries": [{"content_hash": content_hash}]},
        )
        assert published.status_code == 201, published.text
        body = published.json()
        fetched = await client.get(f"/v1/api/federation/lists/{body['list_id']}")
        listed = await client.get("/v1/api/federation/lists")

    assert fetched.status_code == 200, fetched.text
    assert listed.status_code == 200, listed.text
    assert [item["list_id"] for item in listed.json()] == [body["list_id"]]
    document = fetched.json()
    assert document["name"] == "Field designs"
    assert document["publisher_did"] == federation.identity.did
    assert document["sequence"] == 1
    assert document["entries"] == [{"content_hash": content_hash}]
    assert verify_payload(
        document["publisher_did"], _payload(document), document["signature"]
    )
    tampered = _payload(document)
    tampered["name"] = "Something else"
    assert not verify_payload(
        document["publisher_did"], tampered, document["signature"]
    )


@pytest.mark.asyncio
async def test_a_member_cannot_publish_a_list(tmp_path, monkeypatch):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service, get_okh_for_lists

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    member = await auth.create_api_key(
        APIKeyCreate(name="member", permissions=["write"], account_id=uuid4())
    )
    design = _Design(dict(MINIMAL), VisibilityLevel.FOLLOWERS)

    async with _client(
        monkeypatch,
        auth,
        overrides={
            get_federation_service: lambda: _federation(tmp_path),
            get_okh_for_lists: lambda: _Designs([design]),
        },
    ) as client:
        refused = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {member.token}"},
            json={
                "name": "Field designs",
                "entries": [{"content_hash": manifest_content_hash(design.to_dict())}],
            },
        )

    assert refused.status_code == 403, refused.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "visibility", [VisibilityLevel.PRIVATE, VisibilityLevel.MEMBERS]
)
async def test_a_list_does_not_publish_a_design_peers_cannot_fetch(
    tmp_path, monkeypatch, visibility
):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service, get_okh_for_lists

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    hidden = _Design(dict(MINIMAL), visibility)
    hidden_hash = manifest_content_hash(hidden.to_dict())

    async with _client(
        monkeypatch,
        auth,
        overrides={
            get_federation_service: lambda: _federation(tmp_path),
            get_okh_for_lists: lambda: _Designs([hidden]),
        },
    ) as client:
        refused = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {admin.token}"},
            json={"name": "Field designs", "entries": [{"content_hash": hidden_hash}]},
        )

    assert refused.status_code == 400, refused.text
    assert hidden_hash in refused.text


def _design(title: str, visibility: VisibilityLevel) -> _Design:
    data = dict(MINIMAL)
    data["id"] = str(uuid4())
    data["title"] = title
    return _Design(data, visibility)


@pytest.mark.asyncio
async def test_an_edit_bumps_adds_and_removes_and_the_sequence_counts(
    tmp_path, monkeypatch
):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service, get_okh_for_lists

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    federation = _federation(tmp_path)
    first = _design("First", VisibilityLevel.FOLLOWERS)
    bumped = _design("Bumped", VisibilityLevel.FOLLOWERS)
    added = _design("Added", VisibilityLevel.PUBLIC)
    first_hash = manifest_content_hash(first.to_dict())
    bumped_hash = manifest_content_hash(bumped.to_dict())
    added_hash = manifest_content_hash(added.to_dict())
    headers = {"Authorization": f"Bearer {admin.token}"}

    async with _client(
        monkeypatch,
        auth,
        overrides={
            get_federation_service: lambda: federation,
            get_okh_for_lists: lambda: _Designs([first, bumped, added]),
        },
    ) as client:
        created = await client.post(
            "/v1/api/federation/lists",
            headers=headers,
            json={"name": "Field designs", "entries": [{"content_hash": first_hash}]},
        )
        assert created.status_code == 201, created.text
        list_id = created.json()["list_id"]
        edited = await client.put(
            f"/v1/api/federation/lists/{list_id}",
            headers=headers,
            json={
                "name": "Field designs",
                "entries": [
                    {"content_hash": added_hash},
                    {"content_hash": bumped_hash, "supersedes": first_hash},
                ],
            },
        )
        removed = await client.put(
            f"/v1/api/federation/lists/{list_id}",
            headers=headers,
            json={"name": "Field designs", "entries": [{"content_hash": bumped_hash}]},
        )

    assert edited.status_code == 200, edited.text
    document = edited.json()
    assert document["sequence"] == 2
    assert [entry["content_hash"] for entry in document["entries"]] == sorted(
        [bumped_hash, added_hash]
    )
    replacement = next(
        entry for entry in document["entries"] if entry["content_hash"] == bumped_hash
    )
    assert replacement["supersedes"] == first_hash
    assert first_hash not in {entry["content_hash"] for entry in document["entries"]}
    assert verify_payload(
        document["publisher_did"], _payload(document), document["signature"]
    )

    assert removed.status_code == 200, removed.text
    current = removed.json()
    assert current["sequence"] == 3
    assert current["entries"] == [{"content_hash": bumped_hash}]
    assert verify_payload(
        current["publisher_did"], _payload(current), current["signature"]
    )


@pytest.mark.asyncio
async def test_an_organisation_admin_publishes_a_list_signed_by_the_space_key(
    tmp_path, monkeypatch
):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service, get_okh_for_lists

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    ada, grace, space, ada_key = await _ada(auth)
    grace_key = await auth.create_api_key(
        APIKeyCreate(
            name="grace",
            permissions=["write"],
            account_id=UUID(grace.account_id),
        )
    )
    node_admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    federation = _federation(tmp_path)
    design = _design("Field", VisibilityLevel.FOLLOWERS)
    content_hash = manifest_content_hash(design.to_dict())
    body = {
        "name": "Field designs",
        "publisher_did": space.did,
        "entries": [{"content_hash": content_hash}],
    }

    async with _client(
        monkeypatch,
        auth,
        overrides={
            get_federation_service: lambda: federation,
            get_okh_for_lists: lambda: _Designs([design]),
        },
    ) as client:
        published = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {grace_key.token}"},
            json=body,
        )
        assert published.status_code == 201, published.text
        document = published.json()
        member = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {ada_key.token}"},
            json=body,
        )
        node = await client.post(
            "/v1/api/federation/lists",
            headers={"Authorization": f"Bearer {node_admin.token}"},
            json=body,
        )
        edited = await client.put(
            f"/v1/api/federation/lists/{document['list_id']}",
            headers={"Authorization": f"Bearer {grace_key.token}"},
            json={"name": "Field designs", "entries": [{"content_hash": content_hash}]},
        )

    assert document["publisher_did"] == space.did
    assert document["publisher_did"] != federation.identity.did
    assert verify_payload(space.did, _payload(document), document["signature"])
    assert member.status_code == 403, member.text
    assert node.status_code == 403, node.text
    assert edited.status_code == 200, edited.text
    assert edited.json()["sequence"] == 2
    assert verify_payload(
        space.did, _payload(edited.json()), edited.json()["signature"]
    )
