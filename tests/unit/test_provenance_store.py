"""Unit tests for ProvenanceStore (Slice 3)."""

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.provenance import (
    Credit,
    RecordProvenance,
    sign_provenance,
)
from src.core.storage.provenance_store import ProvenanceStore


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.mark.asyncio
async def test_provenance_store_round_trip_preserves_signature():
    store = ProvenanceStore(_FakeStorageService())
    author = generate_identity("Ada")
    prov = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
        on_behalf_of="did:key:zSpace",
    )
    sign_provenance(prov, author.private_key, author.did)

    await store.save("record-1", prov)
    loaded = await store.load("record-1")

    assert loaded is not None
    assert loaded.published_by == author.did
    assert loaded.on_behalf_of == "did:key:zSpace"
    assert loaded.signed_by == author.did
    assert loaded.signature == prov.signature


@pytest.mark.asyncio
async def test_provenance_store_missing_returns_none():
    store = ProvenanceStore(_FakeStorageService())
    assert await store.load("nope") is None
