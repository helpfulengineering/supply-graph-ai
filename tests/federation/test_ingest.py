"""Unit tests for federation manifest ingest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uuid import UUID

from src.core.federation.catalog import manifest_content_hash
from src.core.federation.identity import generate_identity
from src.core.federation.ingest import (
    IngestError,
    verify_and_store,
    verify_signed_record,
)
from src.core.federation.models import CatalogRecord, SignedManifestRecord, utc_now
from src.core.federation.store import FederationStore
from tests.federation.test_catalog import MINIMAL_MANIFEST


def _signed_record(publisher=None, provenance=None) -> SignedManifestRecord:
    identity = publisher or generate_identity("Publisher")
    content_hash = manifest_content_hash(MINIMAL_MANIFEST)
    updated_at = utc_now()
    record = CatalogRecord(
        manifest_id=UUID(MINIMAL_MANIFEST["id"]),
        content_hash=content_hash,
        title=MINIMAL_MANIFEST["title"],
        version=MINIMAL_MANIFEST["version"],
        updated_at=updated_at,
        publisher_did=identity.did,
        provenance=provenance,
        signature="",
    )
    # Sign the canonical payload (which includes provenance when present).
    record = record.model_copy(
        update={"signature": identity.sign_json(record.record_payload()).hex()}
    )
    return SignedManifestRecord(
        catalog_record=record,
        manifest=MINIMAL_MANIFEST,
        manifest_signature=identity.sign_json(MINIMAL_MANIFEST).hex(),
    )


@pytest.mark.unit
def test_verify_signed_record_accepts_valid() -> None:
    signed = _signed_record()
    verify_signed_record(signed)


@pytest.mark.unit
def test_verify_signed_record_rejects_bad_manifest_sig() -> None:
    signed = _signed_record()
    bad = signed.model_copy(update={"manifest_signature": "00" * 64})
    with pytest.raises(IngestError, match="manifest signature"):
        verify_signed_record(bad)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_rejects_unfollowed(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    okh_service = AsyncMock()

    with pytest.raises(IngestError, match="not followed"):
        await verify_and_store(
            signed,
            publisher_did=signed.catalog_record.publisher_did,
            store=store,
            okh_service=okh_service,
            local_content_hashes=set(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_persists_followed_record(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    store.set_followed(signed.catalog_record.publisher_did, True)
    okh_service = AsyncMock()
    okh_service.create = AsyncMock(return_value=MagicMock())

    with patch(
        "src.core.federation.ingest.validate_okh_manifest",
        return_value=MagicMock(valid=True, errors=[]),
    ):
        result = await verify_and_store(
            signed,
            publisher_did=signed.catalog_record.publisher_did,
            store=store,
            okh_service=okh_service,
            local_content_hashes=set(),
        )

    assert result.action == "stored"
    okh_service.create.assert_awaited_once()


def _signed_provenance():
    from src.core.models.provenance import Credit, RecordProvenance, sign_provenance

    author = generate_identity("Ada")
    prov = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
    )
    sign_provenance(prov, author.private_key, author.did)
    return author, prov


@pytest.mark.unit
def test_verify_signed_record_accepts_valid_provenance() -> None:
    _, prov = _signed_provenance()
    verify_signed_record(_signed_record(provenance=prov))


@pytest.mark.unit
def test_verify_signed_record_rejects_tampered_provenance() -> None:
    _, prov = _signed_provenance()
    publisher = generate_identity("Publisher")
    signed = _signed_record(publisher=publisher, provenance=prov)
    # Tamper the provenance after the node signed the record. Re-sign the record
    # with the SAME node key so the node signature still passes and only the
    # author's provenance signature is broken.
    tampered = signed.catalog_record.model_copy(deep=True)
    tampered.provenance.on_behalf_of = "did:key:zEvilSpace"
    tampered = tampered.model_copy(
        update={"signature": publisher.sign_json(tampered.record_payload()).hex()}
    )
    bad = signed.model_copy(update={"catalog_record": tampered})
    with pytest.raises(IngestError, match="provenance signature"):
        verify_signed_record(bad)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provenance_survives_catalog_to_ingest_round_trip(tmp_path) -> None:
    """Acceptance (Slice 3): a design authored at node A shows its author at node B."""
    from src.core.federation.catalog import build_catalog_index

    node_a = generate_identity("Node A")
    author, prov = _signed_provenance()

    manifest = MagicMock()
    manifest.id = UUID(MINIMAL_MANIFEST["id"])
    manifest.title = MINIMAL_MANIFEST["title"]
    manifest.version = MINIMAL_MANIFEST["version"]
    manifest.version_date = None
    manifest.to_dict.return_value = dict(MINIMAL_MANIFEST)

    # Node A publishes the design it holds provenance for.
    from src.core.models.visibility import VisibilityLevel

    okh_a = AsyncMock()
    okh_a.list.return_value = ([manifest], 1)
    okh_a.get_provenance.return_value = prov
    okh_a.get_visibility.return_value = VisibilityLevel.PUBLIC
    auth = AsyncMock()
    auth.list_attestations_for_catalog = AsyncMock(return_value=[])
    with patch(
        "src.core.services.auth_service.AuthenticationService.get_instance",
        new_callable=AsyncMock,
        return_value=auth,
    ):
        index = await build_catalog_index(okh_a, node_a)
    signed = index.get_signed_record(index.records[0].content_hash)

    # Node B follows A and ingests; provenance is re-stamped into B's own plane.
    store = FederationStore(tmp_path)
    store.set_followed(node_a.did, True)
    okh_b = AsyncMock()
    okh_b.create = AsyncMock(return_value=MagicMock())
    with patch(
        "src.core.federation.ingest.validate_okh_manifest",
        return_value=MagicMock(valid=True, errors=[]),
    ):
        result = await verify_and_store(
            signed,
            publisher_did=node_a.did,
            store=store,
            okh_service=okh_b,
            local_content_hashes=set(),
        )

    assert result.action == "stored"
    _, kwargs = okh_b.create.call_args
    assert kwargs["provenance"].authored_by[0].subject_did == author.did


@pytest.mark.unit
def test_verify_signed_record_rejects_bad_attestation() -> None:
    from src.core.models.attestation import Attestation

    publisher = generate_identity("Publisher")
    att = Attestation(
        type="certified",
        issuer_did="did:key:zFake",
        subject_did="did:key:zFirm",
        content_hash="sha256:bundle",
        claim={"version": "1.0.0"},
        signature="00" * 64,
    )
    signed = _signed_record(publisher=publisher)
    catalog = signed.catalog_record.model_copy(update={"attestations": [att]})
    catalog = catalog.model_copy(
        update={"signature": publisher.sign_json(catalog.record_payload()).hex()}
    )
    bad = signed.model_copy(update={"catalog_record": catalog})
    with pytest.raises(IngestError, match="attestation signature"):
        verify_signed_record(bad)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_attestations_survive_ingest(tmp_path) -> None:
    from src.core.federation.identity import sign_payload
    from src.core.models.attestation import Attestation

    publisher = generate_identity("Publisher")
    issuer = generate_identity("Issuer")
    att = Attestation(
        type="certified",
        issuer_did=issuer.did,
        subject_did=issuer.did,
        content_hash="sha256:bundle",
        claim={"version": "1.0.0"},
    )
    att.signature = sign_payload(issuer.private_key, att.signing_payload())

    signed = _signed_record(publisher=publisher)
    catalog = signed.catalog_record.model_copy(update={"attestations": [att]})
    catalog = catalog.model_copy(
        update={"signature": publisher.sign_json(catalog.record_payload()).hex()}
    )
    signed = signed.model_copy(update={"catalog_record": catalog})

    store = FederationStore(tmp_path)
    store.set_followed(publisher.did, True)
    okh_service = AsyncMock()
    okh_service.create = AsyncMock(return_value=MagicMock())
    auth = AsyncMock()
    auth.save_attestation = AsyncMock()

    with (
        patch(
            "src.core.federation.ingest.validate_okh_manifest",
            return_value=MagicMock(valid=True, errors=[]),
        ),
        patch(
            "src.core.services.auth_service.AuthenticationService.get_instance",
            new_callable=AsyncMock,
            return_value=auth,
        ),
    ):
        result = await verify_and_store(
            signed,
            publisher_did=publisher.did,
            store=store,
            okh_service=okh_service,
            local_content_hashes=set(),
        )

    assert result.action == "stored"
    auth.save_attestation.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_skips_existing_hash(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    store.set_followed(signed.catalog_record.publisher_did, True)
    okh_service = AsyncMock()

    result = await verify_and_store(
        signed,
        publisher_did=signed.catalog_record.publisher_did,
        store=store,
        okh_service=okh_service,
        local_content_hashes={signed.catalog_record.content_hash},
    )

    assert result.action == "skipped"
    okh_service.create.assert_not_called()
