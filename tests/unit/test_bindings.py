"""Unit tests for domain/OAuth bindings + directory (Slice 7)."""

from uuid import uuid4

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.binding import (
    domain_external_id,
    oauth_external_id,
    well_known_document,
    well_known_url,
)
from src.core.models.identity import IdentityKind
from src.core.services.auth_service import AuthenticationService
from src.core.storage.attestation_store import AttestationStore
from src.core.storage.binding_store import BindingStore, DirectoryStore
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
    svc._attestation_store = AttestationStore(backing)
    svc._binding_store = BindingStore(backing)
    svc._directory_store = DirectoryStore(backing)
    svc._identity_store = IdentityKeyStore(tmp_path)
    svc._node_signing = generate_identity("test-node")
    svc._initialized = True
    return svc


def test_domain_external_id_normalizes_host():
    assert domain_external_id("https://Example.ORG/path") == "domain:example.org"
    assert well_known_url("example.org").endswith("/.well-known/ohm-did.json")


def test_oauth_external_id():
    assert oauth_external_id("GitHub", "ada") == "oauth:github:ada"


@pytest.mark.asyncio
async def test_domain_bind_start_and_verify_with_fetcher(service):
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")
    started = await service.start_domain_binding(space.did, "fablab.example")
    binding = started["binding"]
    assert binding.verified is False
    assert binding.challenge
    doc = started["well_known_document"]
    assert doc == well_known_document(space.did, binding.challenge)

    async def fake_fetch(url: str):
        assert "fablab.example" in url
        return doc

    verified = await service.verify_domain_binding(
        space.did, "fablab.example", fetcher=fake_fetch
    )
    assert verified.verified is True
    assert verified.challenge is None

    # Reputation carries domain_bound attestation; directory auto-refreshed.
    rep = await service.list_reputation(space.did)
    assert any(a.type == "domain_bound" for a in rep)
    directory = await service.list_directory()
    assert any(e.did == space.did and e.domain == "fablab.example" for e in directory)


@pytest.mark.asyncio
async def test_domain_verify_rejects_bad_challenge(service):
    space = await service.create_identity(uuid4(), IdentityKind.SPACE, "FabLab")
    await service.start_domain_binding(space.did, "bad.example")

    async def fake_fetch(_url: str):
        return {"did": space.did, "challenge": "wrong", "method": "ohm-domain-bind-v1"}

    with pytest.raises(Exception) as exc:
        await service.verify_domain_binding(
            space.did, "bad.example", fetcher=fake_fetch
        )
    assert getattr(exc.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_oauth_bind_and_list(service):
    person = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    binding = await service.bind_oauth(
        subject_did=person.did,
        provider="github",
        external_subject="ada-lovelace",
        evidence={"login": "ada-lovelace"},
    )
    assert binding.verified
    assert binding.external_id == "oauth:github:ada-lovelace"

    listed = await service.list_bindings(subject_did=person.did)
    assert len(listed) == 1
    rep = await service.list_reputation(person.did)
    assert any(a.type == "oauth_bound" for a in rep)


@pytest.mark.asyncio
async def test_directory_publish(service):
    person = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    entry = await service.publish_directory_entry(
        did=person.did,
        display_name="Ada",
        base_url="http://localhost:8001",
    )
    assert entry.did == person.did
    assert entry.display_name == "Ada"
    assert len(await service.list_directory()) == 1


@pytest.mark.asyncio
async def test_directory_ca_pinned_filters_unbound(service, monkeypatch):
    from src.config.security_policy import get_security_policy

    person = await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    await service.publish_directory_entry(did=person.did, display_name="Ada")
    monkeypatch.setattr(
        "src.core.services.auth_service.get_security_policy",
        lambda: get_security_policy("shielded"),
    )
    assert await service.list_directory() == []


@pytest.mark.asyncio
async def test_create_identity_blocked_when_custodial_disallowed(service, monkeypatch):
    from src.config.security_policy import get_security_policy

    monkeypatch.setattr(
        "src.core.services.auth_service.get_security_policy",
        lambda: get_security_policy("shielded"),
    )
    with pytest.raises(Exception) as exc:
        await service.create_identity(uuid4(), IdentityKind.PERSON, "Ada")
    assert getattr(exc.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_domain_bind_requires_held_key(service):
    with pytest.raises(Exception) as exc:
        await service.start_domain_binding("did:key:zNotHeld", "example.org")
    assert getattr(exc.value, "status_code", None) == 403
