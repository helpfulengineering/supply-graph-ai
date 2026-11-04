"""Record-level provenance (federated-identity Slice 3).

Who authored / published a record, and on whose behalf. Provenance is *content
trust* (about the record), distinct from the *transport trust* of the relaying
node. It is persisted in its own :class:`ProvenanceStore` keyed by record id —
deliberately *outside* the manifest so it never enters the design content hash —
and may be signed by the publisher for offline authorship verification.
The organisation named in ``on_behalf_of`` does not sign.
See ``notes/federated-identity-adr.md`` §4.3 / §4.3.1.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, Field, model_serializer, model_validator

from .capability import CapabilityGrant
from .space import SpaceClaim

# Manifests stash OHM-internal metadata under ``ohm_*`` keys so it never collides
# with OKH/OKW schema fields. ``to_dict()`` on those models is a whitelist, so these
# keys must be carried through create explicitly (see apply_ohm_metadata).
OHM_METADATA_PREFIX = "ohm_"
OHM_CREATED_BY_KEY = "ohm_created_by"
# The creator's subject DID. Record ownership keys on this (#403); the
# account id above is the fallback for env keys and pre-#403 records.
OHM_CREATED_BY_DID_KEY = "ohm_created_by_did"


class Credit(BaseModel):
    """Attribution to one contributor — a DID *or* a claimable external id.

    Exactly one of ``subject_did`` / ``external_id`` is set. An unclaimed
    ``external_id`` (e.g. ``orcid:0000-...``, ``name:Jane Doe``) can be claimed
    later by a real DID via an identity link (ADR §4.3.1).
    """

    subject_did: Optional[str] = None
    external_id: Optional[str] = None
    role: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one_identifier(self) -> "Credit":
        if bool(self.subject_did) == bool(self.external_id):
            raise ValueError(
                "exactly one of subject_did / external_id must be set on a Credit"
            )
        return self


class AttributionBody(BaseModel):
    """The organisation an existing record should be published for.

    ``None`` removes the attribution. Removing does not require a current grant.
    """

    on_behalf_of: Optional[str] = None


class BulkAttributionBody(BaseModel):
    """One organisation for many records the caller owns."""

    ids: list[UUID] = Field(..., min_length=1, max_length=500)
    on_behalf_of: Optional[str] = None


class BulkAttributionResult(BaseModel):
    """What happened to one id. ``on_behalf_of`` is set only when ``changed``."""

    id: UUID
    outcome: Literal["changed", "not_yours", "not_found"]
    on_behalf_of: Optional[str] = None


class BulkAttributionResponse(BaseModel):
    """One result per requested id, in request order."""

    results: list[BulkAttributionResult]


class RecordProvenance(BaseModel):
    """Authorship/publication facts attached to an OKH/OKW record."""

    authored_by: List[Credit] = Field(default_factory=list)
    published_by: Optional[str] = None  # publisher DID
    on_behalf_of: Optional[str] = None  # space DID a record is published for
    signed_by: Optional[str] = None  # DID whose key signed this provenance
    signed_at: Optional[datetime] = (
        None  # when the member signed; binds the grant window
    )
    signature: str = ""  # hex over signing_payload()
    # The affiliation that authorised on_behalf_of. Each object is signed by
    # its own key. Neither enters signing_payload, so the member's signature
    # stays over the claimed facts, and neither enters the content hash,
    # because provenance is stored in its own plane.
    space_claim: Optional[SpaceClaim] = None
    affiliation: Optional[CapabilityGrant] = None

    @model_serializer(mode="wrap")
    def _omit_absent_signing_time(self, handler, _info):
        # Records signed before the chain carried a time have no key. Dumping
        # null would change the catalog payload those nodes already signed.
        data = handler(self)
        if isinstance(data, dict) and data.get("signed_at") is None:
            data.pop("signed_at")
        return data

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload (the claimed facts only)."""
        payload = {
            "authored_by": [
                {
                    "subject_did": c.subject_did,
                    "external_id": c.external_id,
                    "role": c.role,
                }
                for c in self.authored_by
            ],
            "published_by": self.published_by,
            "on_behalf_of": self.on_behalf_of,
        }
        # Absent on records signed before the chain carried a time, so their
        # signatures still verify. Present, it is covered by the signature.
        if self.signed_at is not None:
            payload["signed_at"] = self.signed_at.isoformat()
        return payload


def sign_provenance(
    provenance: RecordProvenance, private_key: Ed25519PrivateKey, signer_did: str
) -> RecordProvenance:
    """Sign a provenance claim with the given key (in place)."""
    # Imported lazily: federation/__init__ pulls in the service layer, which
    # imports the OKH/OKW services that import this module — a top-level import
    # here would form a cycle.
    from ..federation.identity import sign_payload

    if provenance.signed_at is None:
        provenance.signed_at = datetime.utcnow()
    provenance.signed_by = signer_did
    provenance.signature = sign_payload(private_key, provenance.signing_payload())
    return provenance


def organisation_verified(provenance: RecordProvenance) -> bool:
    """True when the embedded chain shows this organisation authorised the record.

    Offline: signatures only, against the keys named in the chain, at the time
    the member signed. A grant that has since lapsed still holds. A missing or
    broken chain does not.
    """
    from ..federation.identity import verify_payload

    claim = provenance.space_claim
    grant = provenance.affiliation
    signed_at = provenance.signed_at
    if (
        not provenance.on_behalf_of
        or claim is None
        or grant is None
        or signed_at is None
        or not verify_provenance(provenance)
    ):
        return False
    if (
        claim.space_did != provenance.on_behalf_of
        or grant.issuer_did != claim.admin_did
    ):
        return False
    if not verify_payload(claim.space_did, claim.signing_payload(), claim.signature):
        return False
    if (
        grant.subject_did != provenance.signed_by
        or grant.scope.kind != "space"
        or grant.scope.target != provenance.on_behalf_of
        or "publish" not in grant.permissions
    ):
        return False
    if not verify_payload(grant.issuer_did, grant.signing_payload(), grant.signature):
        return False
    if grant.not_before and signed_at < grant.not_before:
        return False
    return signed_at < grant.expires_at


class ProvenanceResponse(RecordProvenance):
    """Provenance plus this node's verdict. The verdict is computed, never stored."""

    organisation_verified: bool = False


def present_provenance(provenance: RecordProvenance) -> ProvenanceResponse:
    return ProvenanceResponse(
        **provenance.model_dump(),
        organisation_verified=organisation_verified(provenance),
    )


def verify_provenance(provenance: RecordProvenance) -> bool:
    """True iff the provenance is signed and the signature verifies offline."""
    from ..federation.identity import verify_payload

    if not provenance.signed_by or not provenance.signature:
        return False
    return verify_payload(
        provenance.signed_by, provenance.signing_payload(), provenance.signature
    )


def record_attribution(record: dict) -> tuple[Optional[str], Optional[str]]:
    """The ``(creator DID, creator account)`` a stored record was stamped with.

    Read from the raw dict rather than a parsed model: ``to_dict()`` is a
    whitelist that drops ``ohm_*``, so the attribution is gone by the time a
    record is an ``OKHManifest`` or a ``ManufacturingFacility``.
    """
    return record.get(OHM_CREATED_BY_DID_KEY), record.get(OHM_CREATED_BY_KEY)


def apply_ohm_metadata(
    payload: dict,
    source: Optional[object] = None,
    created_by: Optional[str] = None,
    created_by_did: Optional[str] = None,
) -> dict:
    """Attach OHM-namespaced metadata to a serialized manifest ``payload``.

    Because model ``to_dict()`` is a whitelist, any ``ohm_*`` keys already present
    on a dict ``source`` (e.g. a manifest received over federation) are carried
    through verbatim first — this is what lets account attribution survive an
    ingest round-trip. An explicit ``created_by`` then takes precedence.

    Note: record *provenance* (authorship/publication) lives in its own store
    (:class:`ProvenanceStore`), not in the manifest, so it stays out of the design
    content hash.
    """
    if isinstance(source, dict):
        for key, value in source.items():
            if key.startswith(OHM_METADATA_PREFIX):
                payload[key] = value
    if created_by:
        payload[OHM_CREATED_BY_KEY] = created_by
    if created_by_did:
        payload[OHM_CREATED_BY_DID_KEY] = created_by_did
    return payload
