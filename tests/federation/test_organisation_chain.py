"""A receiving node checks an organisation's evidence chain offline."""

from datetime import datetime, timedelta

import pytest

from src.core.federation.identity import generate_identity, sign_payload
from src.core.models.capability import CapabilityGrant, Scope
from src.core.models.provenance import (
    Credit,
    RecordProvenance,
    organisation_verified,
    sign_provenance,
    verify_provenance,
)
from src.core.models.space import SpaceClaim


def _chain(
    *,
    signed_at: datetime | None = None,
    expires_at: datetime | None = None,
    grant_issuer=None,
    tamper_claim: bool = False,
) -> RecordProvenance:
    member = generate_identity("Ada")
    admin = generate_identity("Grace")
    space = generate_identity("FabLab")
    when = signed_at or datetime.utcnow()
    claim = SpaceClaim(space_did=space.did, admin_did=admin.did, claimed_at=when)
    claim.signature = sign_payload(space.private_key, claim.signing_payload())
    if tamper_claim:
        claim.admin_did = generate_identity("Other").did
    issuer = grant_issuer or admin
    grant = CapabilityGrant(
        issuer_did=issuer.did,
        subject_did=member.did,
        permissions=["publish"],
        scope=Scope(kind="space", target=space.did),
        issued_at=when - timedelta(days=1),
        expires_at=expires_at or (when + timedelta(days=90)),
    )
    grant.signature = sign_payload(issuer.private_key, grant.signing_payload())
    provenance = RecordProvenance(
        authored_by=[Credit(subject_did=member.did, role="author")],
        published_by=member.did,
        on_behalf_of=space.did,
        signed_at=when,
        space_claim=claim,
        affiliation=grant,
    )
    sign_provenance(provenance, member.private_key, member.did)
    return provenance


def test_a_valid_chain_shows_the_organisation_as_verified() -> None:
    assert organisation_verified(_chain())


def test_a_grant_that_has_since_lapsed_stays_verified() -> None:
    signed_at = datetime.utcnow() - timedelta(days=100)
    assert organisation_verified(
        _chain(signed_at=signed_at, expires_at=signed_at + timedelta(days=90))
    )


def test_a_chain_expired_at_signing_is_unverified() -> None:
    signed_at = datetime.utcnow()
    assert not organisation_verified(
        _chain(signed_at=signed_at, expires_at=signed_at - timedelta(days=1))
    )


def test_a_tampered_claim_is_unverified() -> None:
    assert not organisation_verified(_chain(tamper_claim=True))


def test_an_issuer_who_is_not_the_claimed_admin_is_unverified() -> None:
    assert not organisation_verified(_chain(grant_issuer=generate_identity("Stranger")))


@pytest.mark.asyncio
async def test_a_synced_record_with_a_broken_chain_is_kept(tmp_path) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.core.federation.ingest import verify_and_store
    from src.core.federation.store import FederationStore
    from tests.federation.test_ingest import _signed_record

    provenance = _chain(tamper_claim=True)
    signed = _signed_record(provenance=provenance)
    store = FederationStore(tmp_path)
    store.set_followed(signed.catalog_record.publisher_did, True)
    okh = AsyncMock()
    okh.create = AsyncMock(return_value=MagicMock())
    okh.get = AsyncMock(return_value=None)
    with patch(
        "src.core.federation.ingest.validate_okh_manifest",
        return_value=MagicMock(valid=True, errors=[]),
    ):
        result = await verify_and_store(
            signed,
            publisher_did=signed.catalog_record.publisher_did,
            store=store,
            okh_service=okh,
            local_content_hashes=set(),
        )
    assert result.action == "stored"
    stored = okh.create.call_args.kwargs["provenance"]
    assert stored.on_behalf_of
    assert not organisation_verified(stored)


def test_a_catalog_signed_before_the_chain_carried_a_time_still_verifies() -> None:
    from src.core.federation.ingest import verify_signed_record
    from tests.federation.test_ingest import _signed_record

    author = generate_identity("Ada")
    publisher = generate_identity("Publisher")
    provenance = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
        signed_by=author.did,
    )
    provenance.signature = sign_payload(
        author.private_key,
        {
            "authored_by": [
                {"subject_did": author.did, "external_id": None, "role": "author"}
            ],
            "published_by": author.did,
            "on_behalf_of": None,
        },
    )
    assert verify_provenance(provenance)
    signed = _signed_record(publisher=publisher, provenance=provenance)
    payload = signed.catalog_record.record_payload()
    payload["provenance"].pop("signed_at", None)
    catalog = signed.catalog_record.model_copy(
        update={"signature": publisher.sign_json(payload).hex()}
    )
    verify_signed_record(signed.model_copy(update={"catalog_record": catalog}))


def test_a_named_organisation_with_no_chain_is_unverified() -> None:
    member = generate_identity("Ada")
    provenance = RecordProvenance(
        authored_by=[Credit(subject_did=member.did, role="author")],
        published_by=member.did,
        on_behalf_of="did:key:zLegacy",
    )
    sign_provenance(provenance, member.private_key, member.did)
    assert not organisation_verified(provenance)
