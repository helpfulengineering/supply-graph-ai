"""Build signed federation catalog from local OKH manifests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from ..models.visibility import is_shareable
from .identity import NodeIdentity, canonical_json_bytes
from .merkle import merkle_root
from .models import CatalogRecord, SignedManifestRecord, utc_now

if TYPE_CHECKING:
    from ..services.okh_service import OKHService


@dataclass
class CatalogIndex:
    """In-memory catalog snapshot for API responses."""

    records: list[CatalogRecord]
    signed_by_hash: dict[str, SignedManifestRecord] = field(default_factory=dict)
    merkle_root: str = ""
    record_count: int = 0

    def get_signed_record(self, content_hash: str) -> SignedManifestRecord | None:
        return self.signed_by_hash.get(content_hash)


def manifest_content_hash(manifest: dict[str, Any]) -> str:
    """Stable content address for a manifest dict."""
    digest = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    return f"sha256:{digest}"


def _manifest_updated_at(manifest_dict: dict[str, Any]) -> datetime:
    raw = manifest_dict.get("version_date")
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return datetime.combine(raw, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return utc_now()


def _sign_catalog_record(
    identity: NodeIdentity, record: CatalogRecord
) -> CatalogRecord:
    signature = identity.sign_json(record.record_payload()).hex()
    return record.model_copy(update={"signature": signature})


async def _catalog_attestations(content_hash: str) -> list[Any]:
    """Load attestations for a catalog leaf (isolated for tests)."""
    from ..services.auth_service import AuthenticationService

    auth = await AuthenticationService.get_instance()
    return await auth.list_attestations_for_catalog(content_hash) or []


async def _shareable_leaves(
    okh_service: OKHService,
    page_size: int,
) -> list[tuple[Any, dict, str]]:
    """Select the manifests that may leave this node, with their content hashes.

    Membership, order and hashing all live here so the full index and the cheap
    summary cannot drift: a merkle root computed by one has to equal the other's,
    or a peer's digest comparison silently disagrees with our own catalog.
    """
    manifests, _total = await okh_service.list(page=1, page_size=page_size)
    leaves: list[tuple[Any, dict, str]] = []
    for manifest in manifests:
        visibility = await okh_service.get_visibility(manifest.id)
        if not is_shareable(visibility):
            continue
        manifest_dict = manifest.to_dict()
        leaves.append((manifest, manifest_dict, manifest_content_hash(manifest_dict)))
    return leaves


async def build_catalog_summary(
    okh_service: OKHService,
    *,
    page_size: int = 10_000,
) -> tuple[int, str]:
    """Return ``(record_count, merkle_root)`` without signing anything.

    /status reports these two numbers and discards the rest of the index, but
    building the full index costs two blob reads, an attestation lookup, a
    package-pointer resolve and two Ed25519 signatures PER MANIFEST. That is the
    most expensive call in the router on the one endpoint the dashboard polls,
    so it gets the cheap path instead of a cache — no staleness to reason about.
    """
    leaves = await _shareable_leaves(okh_service, page_size)
    return len(leaves), merkle_root([content_hash for _m, _d, content_hash in leaves])


async def build_catalog_index(
    okh_service: OKHService,
    identity: NodeIdentity,
    *,
    page_size: int = 10_000,
) -> CatalogIndex:
    """List OKH manifests from storage and build signed catalog entries.

    Only records with shareable visibility (``followers`` / ``public``) are
    included — ``private`` (the create default) never leaves the node.
    """
    records: list[CatalogRecord] = []
    signed_by_hash: dict[str, SignedManifestRecord] = {}

    for manifest, manifest_dict, content_hash in await _shareable_leaves(
        okh_service, page_size
    ):
        # Provenance rides the catalog record (its own plane), so it is signed by
        # the node in transit but stays out of the design content hash.
        provenance = await okh_service.get_provenance(manifest.id)
        # Attestations ride the catalog record the same way provenance does —
        # out of the design content hash, inside the node-signed payload.
        attestations = await _catalog_attestations(content_hash)
        # Package pointer rides the catalog (out of design content hash) when a
        # local package exists — bytes move on a separate CAS channel.
        from .package_pointer import resolve_package_pointer

        package_ptr = resolve_package_pointer(manifest.id)
        record = CatalogRecord(
            manifest_id=manifest.id,
            content_hash=content_hash,
            title=manifest.title,
            version=manifest.version,
            updated_at=_manifest_updated_at(manifest_dict),
            publisher_did=identity.did,
            provenance=provenance,
            attestations=attestations or None,
            package=package_ptr,
            signature="",
        )
        signed_record = _sign_catalog_record(identity, record)
        manifest_sig = identity.sign_json(manifest_dict).hex()
        records.append(signed_record)
        signed_by_hash[content_hash] = SignedManifestRecord(
            catalog_record=signed_record,
            manifest=manifest_dict,
            manifest_signature=manifest_sig,
        )

    leaf_hashes = [r.content_hash for r in records]
    root = merkle_root(leaf_hashes)
    return CatalogIndex(
        records=records,
        signed_by_hash=signed_by_hash,
        merkle_root=root,
        record_count=len(records),
    )
