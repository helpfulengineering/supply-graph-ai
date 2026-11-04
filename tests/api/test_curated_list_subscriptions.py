"""A node admin subscribes to one peer's curated list (#581)."""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
import pytest

from src.core.federation.identity import generate_identity
from src.core.federation.lists import sign_curated_list
from src.core.federation.models import CuratedList, CuratedListEntry
from src.core.federation.node_role import NodeRole, capabilities_for_role
from src.core.federation.service import FederationService
from src.core.federation.store import FederationStore
from src.core.models.auth import APIKeyCreate
from src.core.services.base import ServiceStatus
from tests.api.test_affiliation_required import _auth, _client


def _federation(tmp_path) -> FederationService:
    service = FederationService()
    service.status = ServiceStatus.ACTIVE
    service.store = FederationStore(tmp_path / "federation")
    service.role = NodeRole.PEER
    service.capabilities = capabilities_for_role(NodeRole.PEER)
    service.identity = generate_identity("Subscriber")
    return service


def _signed_list() -> tuple[object, dict]:
    publisher = generate_identity("Publisher")
    document = sign_curated_list(
        publisher,
        CuratedList(
            list_id="field-designs",
            name="Field designs",
            publisher_did=publisher.did,
            sequence=1,
            entries=[CuratedListEntry(content_hash="sha256:abc")],
        ),
    )
    return publisher, document.model_dump(mode="json", exclude_none=True)


@pytest.mark.asyncio
async def test_a_node_admin_subscribes_to_a_peers_signed_list(tmp_path, monkeypatch):
    from unittest.mock import patch

    from src.config import settings
    from src.core.api.routes.federation import get_federation_service

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    publisher, document = _signed_list()
    federation = _federation(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/api/federation/lists/field-designs":
            return httpx.Response(200, json=document)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    headers = {"Authorization": f"Bearer {admin.token}"}

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: federation},
    ) as client:
        with patch(
            "src.core.federation.subscriptions.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            subscribed = await client.post(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                json={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            listed = await client.get(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
            )

    assert subscribed.status_code == 201, subscribed.text
    body = subscribed.json()
    assert body["list_id"] == "field-designs"
    assert body["name"] == "Field designs"
    assert body["publisher_did"] == publisher.did
    assert body["peer_url"] == "http://peer.example"
    assert listed.status_code == 200, listed.text
    assert listed.json() == [body]


@pytest.mark.asyncio
async def test_a_list_with_a_bad_signature_is_not_subscribed(tmp_path, monkeypatch):
    from unittest.mock import patch

    from src.config import settings
    from src.core.api.routes.federation import get_federation_service

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    _publisher, document = _signed_list()
    document["signature"] = "00" * 64
    headers = {"Authorization": f"Bearer {admin.token}"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=document)

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: _federation(tmp_path)},
    ) as client:
        with patch(
            "src.core.federation.subscriptions.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            refused = await client.post(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                json={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            listed = await client.get(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
            )

    assert refused.status_code == 400, refused.text
    assert listed.status_code == 200, listed.text
    assert listed.json() == []


@pytest.mark.asyncio
async def test_a_member_cannot_subscribe(tmp_path, monkeypatch):
    from src.config import settings
    from src.core.api.routes.federation import get_federation_service

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    member = await auth.create_api_key(
        APIKeyCreate(name="member", permissions=["write"], account_id=uuid4())
    )

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: _federation(tmp_path)},
    ) as client:
        refused = await client.post(
            "/v1/api/federation/lists/subscriptions",
            headers={"Authorization": f"Bearer {member.token}"},
            json={"peer_url": "http://peer.example", "list_id": "field-designs"},
        )

    assert refused.status_code == 403, refused.text


@pytest.mark.asyncio
async def test_a_node_admin_can_unsubscribe(tmp_path, monkeypatch):
    from unittest.mock import patch

    from src.config import settings
    from src.core.api.routes.federation import get_federation_service

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    _publisher, document = _signed_list()
    headers = {"Authorization": f"Bearer {admin.token}"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=document)

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: _federation(tmp_path)},
    ) as client:
        with patch(
            "src.core.federation.subscriptions.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            subscribed = await client.post(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                json={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            assert subscribed.status_code == 201, subscribed.text
            removed = await client.delete(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                params={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            listed = await client.get(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
            )

    assert removed.status_code == 200, removed.text
    assert listed.status_code == 200, listed.text
    assert listed.json() == []


class _Held:
    def __init__(self, data: dict) -> None:
        self.id = UUID(data["id"])
        self._data = data

    def to_dict(self) -> dict:
        return self._data


class _EmptyDesigns:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def list(self, **_kwargs):
        held = [_Held(item) for item in self.created]
        return held, len(held)

    async def get(self, manifest_id):
        for item in self.created:
            if item["id"] == str(manifest_id):
                return _Held(item)
        return None

    async def get_visibility(self, _manifest_id):
        from src.core.models.visibility import VisibilityLevel

        return VisibilityLevel.FOLLOWERS

    async def create(self, manifest, provenance=None, verbatim=False):
        self.created.append(manifest)
        return manifest


def _signed_record(publisher, manifest: dict):
    from src.core.federation.catalog import manifest_content_hash
    from src.core.federation.models import CatalogRecord, SignedManifestRecord, utc_now

    content_hash = manifest_content_hash(manifest)
    record = CatalogRecord(
        manifest_id=UUID(manifest["id"]),
        content_hash=content_hash,
        title=manifest["title"],
        version=manifest["version"],
        updated_at=utc_now(),
        publisher_did=publisher.did,
        signature="",
    )
    record = record.model_copy(
        update={"signature": publisher.sign_json(record.record_payload()).hex()}
    )
    signed = SignedManifestRecord(
        catalog_record=record,
        manifest=manifest,
        manifest_signature=publisher.sign_json(manifest).hex(),
    )
    return content_hash, signed.model_dump(mode="json")


@pytest.mark.asyncio
async def test_sync_pulls_the_lists_designs_and_nothing_else(tmp_path, monkeypatch):
    from unittest.mock import patch

    from src.config import settings
    from src.core.api.routes.federation import get_federation_service
    from src.core.services.okh_service import OKHService
    from tests.api.test_affiliation_required import MINIMAL

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    publisher = generate_identity("Publisher")
    manifest = dict(MINIMAL)
    listed_hash, record = _signed_record(publisher, manifest)
    other_hash = "sha256:" + "cd" * 32
    document = sign_curated_list(
        publisher,
        CuratedList(
            list_id="field-designs",
            name="Field designs",
            publisher_did=publisher.did,
            sequence=1,
            entries=[CuratedListEntry(content_hash=listed_hash)],
        ),
    ).model_dump(mode="json", exclude_none=True)
    designs = _EmptyDesigns()

    async def get_instance(cls):
        return designs

    monkeypatch.setattr(OKHService, "get_instance", classmethod(get_instance))
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/v1/api/federation/lists/field-designs":
            return httpx.Response(200, json=document)
        if listed_hash in request.url.path:
            return httpx.Response(200, json=record)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    headers = {"Authorization": f"Bearer {admin.token}"}

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: _federation(tmp_path)},
    ) as client:
        with patch(
            "src.core.federation.subscriptions.httpx.AsyncClient",
            side_effect=lambda *args, **kwargs: real_client(transport=transport),
        ):
            subscribed = await client.post(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                json={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            assert subscribed.status_code == 201, subscribed.text
            synced = await client.post(
                "/v1/api/federation/sync/run",
                headers=headers,
            )

    assert synced.status_code == 200, synced.text
    assert synced.json()["total_pulled"] == 1, synced.text
    assert designs.created == [manifest]
    assert any(listed_hash in path for path in requested)
    assert all(other_hash not in path for path in requested)
    assert all("sync/digest" not in path for path in requested)


@pytest.mark.asyncio
async def test_an_entry_the_publisher_adds_arrives_on_the_next_sync(
    tmp_path, monkeypatch
):
    from unittest.mock import patch

    from src.config import settings
    from src.core.api.routes.federation import get_federation_service
    from src.core.services.okh_service import OKHService
    from tests.api.test_affiliation_required import MINIMAL

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    auth = _auth(tmp_path)
    admin = await auth.create_api_key(
        APIKeyCreate(name="admin", permissions=["admin"], account_id=uuid4())
    )
    publisher = generate_identity("Publisher")
    first = dict(MINIMAL)
    first_hash, first_record = _signed_record(publisher, first)
    added = dict(MINIMAL)
    added["id"] = str(uuid4())
    added["title"] = "Added later"
    added_hash, added_record = _signed_record(publisher, added)
    records = {first_hash: first_record, added_hash: added_record}
    versions = [
        sign_curated_list(
            publisher,
            CuratedList(
                list_id="field-designs",
                name="Field designs",
                publisher_did=publisher.did,
                sequence=1,
                entries=[CuratedListEntry(content_hash=first_hash)],
            ),
        ).model_dump(mode="json", exclude_none=True)
    ]
    versions.append(
        sign_curated_list(
            publisher,
            CuratedList(
                list_id="field-designs",
                name="Field designs",
                publisher_did=publisher.did,
                sequence=2,
                entries=[
                    CuratedListEntry(content_hash=first_hash),
                    CuratedListEntry(content_hash=added_hash),
                ],
            ),
        ).model_dump(mode="json", exclude_none=True)
    )
    designs = _EmptyDesigns()

    async def get_instance(cls):
        return designs

    monkeypatch.setattr(OKHService, "get_instance", classmethod(get_instance))
    served = {"document": versions[0]}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/api/federation/lists/field-designs":
            return httpx.Response(200, json=served["document"])
        for content_hash, record in records.items():
            if content_hash in request.url.path:
                return httpx.Response(200, json=record)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    headers = {"Authorization": f"Bearer {admin.token}"}

    async with _client(
        monkeypatch,
        auth,
        overrides={get_federation_service: lambda: _federation(tmp_path)},
    ) as client:
        with patch(
            "src.core.federation.subscriptions.httpx.AsyncClient",
            side_effect=lambda *args, **kwargs: real_client(transport=transport),
        ):
            subscribed = await client.post(
                "/v1/api/federation/lists/subscriptions",
                headers=headers,
                json={"peer_url": "http://peer.example", "list_id": "field-designs"},
            )
            assert subscribed.status_code == 201, subscribed.text
            first_sync = await client.post(
                "/v1/api/federation/sync/run", headers=headers
            )
            served["document"] = versions[1]
            second_sync = await client.post(
                "/v1/api/federation/sync/run", headers=headers
            )

    assert first_sync.status_code == 200, first_sync.text
    assert first_sync.json()["total_pulled"] == 1, first_sync.text
    assert second_sync.status_code == 200, second_sync.text
    assert second_sync.json()["total_pulled"] == 1, second_sync.text
    assert designs.created == [first, added]
