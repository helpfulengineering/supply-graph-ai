"""Unit tests for space claim + peer/edge trust roots (Slice 5)."""

from uuid import uuid4

import pytest

from src.core.federation.identity import generate_identity
from src.core.federation.store import FederationStore
from src.core.models.capability import Scope
from src.core.models.identity import IdentityKind
from src.core.services.auth_service import AuthenticationService
from src.core.storage.grant_store import GrantStore
from src.core.storage.identity_key_store import IdentityKeyStore
from src.core.storage.space_claim_store import SpaceClaimStore


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def delete_object(self, key):
        self._objects.pop(key, None)

    async def list_objects(self, prefix=None):
        for key, data in list(self._objects.items()):
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.fixture
def service(tmp_path) -> AuthenticationService:
    backing = _FakeStorageService()
    svc = AuthenticationService()
    svc._grant_store = GrantStore(backing)
    svc._space_claim_store = SpaceClaimStore(backing)
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


@pytest.mark.asyncio
async def test_claim_space_tofu_and_admin_can_issue_space_grant(service):
    admin = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")

    claim = await service.claim_space(space.did, admin.did)
    assert claim.admin_did == admin.did
    assert claim.signature

    # Second claim fails (TOFU).
    other = await service.create_identity(uuid4(), IdentityKind.PERSON, "Bob")
    with pytest.raises(Exception) as exc:
        await service.claim_space(space.did, other.did)
    assert getattr(exc.value, "status_code", None) == 409

    space_scope = Scope(kind="space", target=space.did)
    await service.issue_grant(
        issuer_did=admin.did,
        subject_did=other.did,
        permissions=["publish"],
        scope=space_scope,
        coarse_floor=["read"],
    )
    perms = await service.resolve_capabilities(other.did, space_scope)
    assert "publish" in perms and "read" in perms


@pytest.mark.asyncio
async def test_non_admin_space_grant_is_not_trusted(service):
    admin = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")
    await service.claim_space(space.did, admin.did)

    interloper = await service.create_identity(uuid4(), IdentityKind.PERSON, "Eve")
    member = await service.create_identity(uuid4(), IdentityKind.PERSON, "Bob")
    space_scope = Scope(kind="space", target=space.did)
    await service.issue_grant(
        issuer_did=interloper.did,
        subject_did=member.did,
        permissions=["publish"],
        scope=space_scope,
        coarse_floor=["read"],
    )
    assert await service.resolve_capabilities(member.did, space_scope) == set()


@pytest.mark.asyncio
async def test_followed_peer_grant_is_trusted(service, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.core.services.auth_service.settings.OHM_FEDERATION_ENABLED", True
    )
    monkeypatch.setattr(
        "src.core.services.auth_service.settings.OHM_FEDERATION_DATA_DIR",
        str(tmp_path / "fed"),
    )
    peer = generate_identity("Peer")
    FederationStore(tmp_path / "fed").set_followed(peer.did, True)

    # Node holds the peer's key only for signing the test grant (simulates a
    # grant that arrived from that peer). Trust comes from the follow list.
    from src.core.models.identity import Identity

    service._identity_store.save(
        peer,
        Identity(did=peer.did, kind=IdentityKind.PERSON, display_name="Peer"),
    )

    subject = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    scope = Scope(kind="node", target=service._node_signing.did)
    await service.issue_grant(
        issuer_did=peer.did,
        subject_did=subject.did,
        permissions=["write"],
        scope=scope,
        coarse_floor=["read"],
    )
    perms = await service.resolve_capabilities(subject.did, scope)
    assert "write" in perms


@pytest.mark.asyncio
async def test_bootstrap_edge_grant_self_issues_on_local_node(service):
    edge = await service.create_identity(uuid4(), IdentityKind.PERSON, "Edge")
    grant = await service.bootstrap_edge_grant(edge.did)
    assert grant.issuer_did == edge.did == grant.subject_did
    scope = service.local_node_scope()
    perms = await service.resolve_capabilities(edge.did, scope)
    assert "write" in perms
