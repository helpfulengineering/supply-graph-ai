"""OKH/OKW create persists provenance to its own plane (Slice 3).

Provenance is written to the ProvenanceStore keyed by record id — NOT embedded
in the manifest — so it stays out of the design content hash. Account attribution
(ohm_created_by) still rides the manifest and survives an ingest round-trip.
"""

import json
from unittest.mock import AsyncMock

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.provenance import OHM_CREATED_BY_KEY, Credit, RecordProvenance
from src.core.services.okh_service import OKHService
from src.core.services.okw_service import OKWService

MINIMAL_OKH = {
    "okhv": "1.0",
    "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
    "title": "Test Design",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "testing",
}

FACILITY_ID = "b2c9f0a1-0000-4000-8000-000000000001"
MINIMAL_OKW = {
    "id": FACILITY_ID,
    "name": "Community Lab",
    "location": {"address": {"country": "US"}},
    "facility_status": "Active",
}


class _CapturingManager:
    def __init__(self) -> None:
        self.written: dict[str, bytes] = {}

    async def put_object(self, key, data, *args, **kwargs):
        self.written[key] = data


class _FakeStorage:
    def __init__(self) -> None:
        self.manager = _CapturingManager()


def _stub_service(service):
    service.storage = _FakeStorage()
    service.ensure_initialized = AsyncMock()
    return service.storage.manager


def _load(manager, key) -> dict:
    return json.loads(manager.written[key].decode("utf-8"))


@pytest.mark.asyncio
async def test_okh_create_persists_provenance_to_store_not_manifest():
    svc = OKHService()
    manager = _stub_service(svc)
    author = generate_identity("Ada")
    prov = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
    )
    await svc.create(dict(MINIMAL_OKH), created_by="acct-1", provenance=prov)

    # Provenance is stored in its own plane, keyed by record id.
    prov_key = f"provenance/{MINIMAL_OKH['id']}.json"
    assert prov_key in manager.written
    assert _load(manager, prov_key)["published_by"] == author.did

    # The manifest carries attribution but NOT provenance (keeps content hash clean).
    manifest_key = next(k for k in manager.written if k.startswith("okh/"))
    manifest = _load(manager, manifest_key)
    assert manifest[OHM_CREATED_BY_KEY] == "acct-1"
    assert "ohm_provenance" not in manifest


@pytest.mark.asyncio
async def test_okh_create_without_provenance_writes_no_provenance_object():
    svc = OKHService()
    manager = _stub_service(svc)
    await svc.create(dict(MINIMAL_OKH), created_by="acct-1")
    assert not any(k.startswith("provenance/") for k in manager.written)


@pytest.mark.asyncio
async def test_okh_create_preserves_incoming_created_by_on_ingest():
    # Ingest round-trip: manifest already carries ohm_created_by; create preserves
    # it even without an explicit created_by argument.
    svc = OKHService()
    manager = _stub_service(svc)
    incoming = dict(MINIMAL_OKH)
    incoming[OHM_CREATED_BY_KEY] = "acct-origin"
    await svc.create(incoming)

    manifest_key = next(k for k in manager.written if k.startswith("okh/"))
    assert _load(manager, manifest_key)[OHM_CREATED_BY_KEY] == "acct-origin"


@pytest.mark.asyncio
async def test_okw_create_persists_provenance_to_store():
    svc = OKWService()
    manager = _stub_service(svc)
    prov = RecordProvenance(
        published_by="did:key:zSpace", on_behalf_of="did:key:zSpace"
    )
    await svc.create(dict(MINIMAL_OKW), created_by="acct-2", provenance=prov)

    prov_key = f"provenance/{FACILITY_ID}.json"
    assert prov_key in manager.written
    assert _load(manager, prov_key)["on_behalf_of"] == "did:key:zSpace"
