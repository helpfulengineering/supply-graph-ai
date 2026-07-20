"""OKH/OKW create stamps + preserves ohm provenance metadata (Slice 3).

Proves the federation-survival mechanism at the service layer: provenance passed
to create is written under ohm_provenance, and ohm_* metadata already present on
an incoming record (the ingest round-trip) is preserved even though to_dict() is
a whitelist that would otherwise drop it.
"""

import json
from unittest.mock import AsyncMock

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.provenance import (
    OHM_CREATED_BY_KEY,
    OHM_PROVENANCE_KEY,
    Credit,
    RecordProvenance,
)
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


def _only_written_payload(manager) -> dict:
    assert len(manager.written) == 1
    return json.loads(next(iter(manager.written.values())).decode("utf-8"))


@pytest.mark.asyncio
async def test_okh_create_stamps_provenance():
    svc = OKHService()
    manager = _stub_service(svc)
    author = generate_identity("Ada")
    prov = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
    )
    await svc.create(dict(MINIMAL_OKH), created_by="acct-1", provenance=prov)

    payload = _only_written_payload(manager)
    assert payload[OHM_CREATED_BY_KEY] == "acct-1"
    assert payload[OHM_PROVENANCE_KEY]["published_by"] == author.did
    assert payload[OHM_PROVENANCE_KEY]["authored_by"][0]["subject_did"] == author.did


@pytest.mark.asyncio
async def test_okh_create_preserves_incoming_provenance_on_ingest():
    # Simulate ingest: the manifest already carries ohm_* metadata; create must
    # preserve it even without explicit created_by/provenance arguments.
    svc = OKHService()
    manager = _stub_service(svc)
    incoming = dict(MINIMAL_OKH)
    incoming[OHM_CREATED_BY_KEY] = "acct-origin"
    incoming[OHM_PROVENANCE_KEY] = {
        "authored_by": [{"subject_did": "did:key:zAuthor", "role": "author"}],
        "published_by": "did:key:zAuthor",
        "on_behalf_of": None,
    }
    await svc.create(incoming)

    payload = _only_written_payload(manager)
    assert payload[OHM_CREATED_BY_KEY] == "acct-origin"
    assert payload[OHM_PROVENANCE_KEY]["published_by"] == "did:key:zAuthor"


@pytest.mark.asyncio
async def test_okw_create_stamps_provenance():
    svc = OKWService()
    manager = _stub_service(svc)
    prov = RecordProvenance(
        published_by="did:key:zSpace", on_behalf_of="did:key:zSpace"
    )
    facility = {
        "id": "b2c9f0a1-0000-4000-8000-000000000001",
        "name": "Community Lab",
        "location": {"address": {"country": "US"}},
        "facility_status": "Active",
    }
    await svc.create(facility, created_by="acct-2", provenance=prov)

    payload = _only_written_payload(manager)
    assert payload[OHM_CREATED_BY_KEY] == "acct-2"
    assert payload[OHM_PROVENANCE_KEY]["on_behalf_of"] == "did:key:zSpace"
