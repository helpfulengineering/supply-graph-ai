"""Record-level provenance (federated-identity Slice 3).

Who authored / published a record, and on whose behalf. Provenance is *content
trust* (about the record), distinct from the *transport trust* of the relaying
node. It is persisted in its own :class:`ProvenanceStore` keyed by record id —
deliberately *outside* the manifest so it never enters the design content hash —
and may be signed by the author/space key for offline authorship verification.
See ``notes/federated-identity-adr.md`` §4.3 / §4.3.1.
"""

from typing import List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, Field, model_validator

# Manifests stash OHM-internal metadata under ``ohm_*`` keys so it never collides
# with OKH/OKW schema fields. ``to_dict()`` on those models is a whitelist, so these
# keys must be carried through create explicitly (see apply_ohm_metadata).
OHM_METADATA_PREFIX = "ohm_"
OHM_CREATED_BY_KEY = "ohm_created_by"


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


class RecordProvenance(BaseModel):
    """Authorship/publication facts attached to an OKH/OKW record."""

    authored_by: List[Credit] = Field(default_factory=list)
    published_by: Optional[str] = None  # publisher DID
    on_behalf_of: Optional[str] = None  # space DID a record is published for
    signed_by: Optional[str] = None  # DID whose key signed this provenance
    signature: str = ""  # hex over signing_payload()

    def signing_payload(self) -> dict:
        """Deterministic, signature-free payload (the claimed facts only)."""
        return {
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


def sign_provenance(
    provenance: RecordProvenance, private_key: Ed25519PrivateKey, signer_did: str
) -> RecordProvenance:
    """Sign a provenance claim with the author/space key (in place)."""
    # Imported lazily: federation/__init__ pulls in the service layer, which
    # imports the OKH/OKW services that import this module — a top-level import
    # here would form a cycle.
    from ..federation.identity import sign_payload

    provenance.signed_by = signer_did
    provenance.signature = sign_payload(private_key, provenance.signing_payload())
    return provenance


def verify_provenance(provenance: RecordProvenance) -> bool:
    """True iff the provenance is signed and the signature verifies offline."""
    from ..federation.identity import verify_payload

    if not provenance.signed_by or not provenance.signature:
        return False
    return verify_payload(
        provenance.signed_by, provenance.signing_payload(), provenance.signature
    )


def apply_ohm_metadata(
    payload: dict,
    source: Optional[object] = None,
    created_by: Optional[str] = None,
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
    return payload
