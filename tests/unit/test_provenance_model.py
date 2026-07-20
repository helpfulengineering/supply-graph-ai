"""Unit tests for the provenance model, signing, and ohm-metadata helper (Slice 3)."""

import pytest

from src.core.federation.identity import generate_identity
from src.core.models.provenance import (
    OHM_CREATED_BY_KEY,
    OHM_PROVENANCE_KEY,
    Credit,
    RecordProvenance,
    apply_ohm_metadata,
    sign_provenance,
    verify_provenance,
)


def test_credit_requires_exactly_one_identifier():
    Credit(subject_did="did:key:zA", role="author")
    Credit(external_id="orcid:0000-0001", role="author")
    with pytest.raises(ValueError):
        Credit(role="author")  # neither
    with pytest.raises(ValueError):
        Credit(subject_did="did:key:zA", external_id="orcid:0000-0001")  # both


def test_provenance_sign_and_verify_round_trip():
    author = generate_identity("Ada")
    prov = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
    )
    sign_provenance(prov, author.private_key, author.did)
    assert prov.signed_by == author.did
    assert verify_provenance(prov)


def test_unsigned_provenance_does_not_verify():
    prov = RecordProvenance(authored_by=[Credit(external_id="name:Jane")])
    assert not verify_provenance(prov)


def test_tampered_provenance_fails_verification():
    author = generate_identity("Ada")
    prov = RecordProvenance(authored_by=[Credit(subject_did=author.did)])
    sign_provenance(prov, author.private_key, author.did)
    prov.on_behalf_of = "did:key:zEvilSpace"  # tamper after signing
    assert not verify_provenance(prov)


def test_apply_ohm_metadata_stamps_created_by_and_provenance():
    prov = RecordProvenance(published_by="did:key:zPub")
    payload = apply_ohm_metadata(
        {"title": "Widget"}, source=None, created_by="acct-1", provenance=prov
    )
    assert payload[OHM_CREATED_BY_KEY] == "acct-1"
    assert payload[OHM_PROVENANCE_KEY]["published_by"] == "did:key:zPub"


def test_apply_ohm_metadata_carries_ohm_keys_through_round_trip():
    # Simulates ingest: a manifest arrives already carrying ohm_* metadata, but
    # to_dict() (a whitelist) dropped it. The helper re-attaches it from source.
    incoming = {
        "title": "Widget",
        OHM_CREATED_BY_KEY: "acct-orig",
        OHM_PROVENANCE_KEY: {"published_by": "did:key:zPub", "authored_by": []},
        "ohm_future_field": {"x": 1},
    }
    rebuilt = apply_ohm_metadata({"title": "Widget"}, source=incoming)
    assert rebuilt[OHM_CREATED_BY_KEY] == "acct-orig"
    assert rebuilt[OHM_PROVENANCE_KEY]["published_by"] == "did:key:zPub"
    assert rebuilt["ohm_future_field"] == {"x": 1}  # forward-compatible passthrough


def test_apply_ohm_metadata_explicit_args_override_source():
    incoming = {OHM_CREATED_BY_KEY: "acct-orig"}
    rebuilt = apply_ohm_metadata({}, source=incoming, created_by="acct-new")
    assert rebuilt[OHM_CREATED_BY_KEY] == "acct-new"
