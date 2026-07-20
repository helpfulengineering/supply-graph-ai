"""Node-local identity key store (federated-identity Slice 2).

Private keys are **secret and never federated**, so they live as plaintext files
under ``OHM_FEDERATION_DATA_DIR/identities/<did>.json`` (peacetime; encryption-at-rest
is on the roadmap) — the same node-local plane as the node's own ``identity.json``,
distinct from the object store used for OKH/OKW/API keys.

Each file bundles the Ed25519 keypair (hex) with the public :class:`Identity`
record (kind, links, account binding) for convenience; only this node reads it.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..federation.identity import NodeIdentity
from ..models.identity import Identity, IdentityKind, IdentityLink


class IdentityKeyStore:
    """Filesystem store for person/space signing keys + public identity records."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir).expanduser() / "identities"

    def _path(self, did: str) -> Path:
        # did:key:z... contains no path separators, but slashes are impossible in
        # base58 anyway; guard defensively.
        safe = did.replace("/", "_")
        return self._dir / f"{safe}.json"

    def save(self, signing_key: NodeIdentity, identity: Identity) -> None:
        """Persist a keypair + its public identity record."""
        self._dir.mkdir(parents=True, exist_ok=True)
        data = signing_key.to_identity_file()
        data.update(
            {
                "kind": identity.kind.value,
                "created_at": identity.created_at.isoformat(),
                "account_id": identity.account_id,
                "custodial": identity.custodial,
                "links_in": [
                    {**link.signing_payload(), "signature": link.signature}
                    for link in identity.links_in
                ],
            }
        )
        self._path(identity.did).write_text(json.dumps(data, indent=2), "utf-8")

    def load_signing_key(self, did: str) -> Optional[NodeIdentity]:
        """Load the Ed25519 keypair for ``did`` (for signing), or None."""
        path = self._path(did)
        if not path.is_file():
            return None
        return NodeIdentity.from_identity_file(json.loads(path.read_text("utf-8")))

    def load_identity(self, did: str) -> Optional[Identity]:
        """Load the public :class:`Identity` record for ``did``, or None."""
        path = self._path(did)
        if not path.is_file():
            return None
        return self._deserialize(json.loads(path.read_text("utf-8")))

    def list_identities(self) -> List[Identity]:
        """List all public identity records held by this node."""
        if not self._dir.is_dir():
            return []
        out: List[Identity] = []
        for path in sorted(self._dir.glob("*.json")):
            out.append(self._deserialize(json.loads(path.read_text("utf-8"))))
        return out

    def find_primary_did(self, account_id: str) -> Optional[str]:
        """Return the (single, for now) DID bound to ``account_id``."""
        for identity in self.list_identities():
            if identity.account_id == account_id:
                return identity.did
        return None

    @staticmethod
    def _deserialize(data: dict) -> Identity:
        return Identity(
            did=data["did"],
            kind=IdentityKind(data.get("kind", "person")),
            display_name=str(data.get("display_name", "")),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.utcnow()
            ),
            account_id=data.get("account_id"),
            custodial=bool(data.get("custodial", False)),
            links_in=[
                IdentityLink(
                    from_did=link["from_did"],
                    to_did=link["to_did"],
                    reason=link["reason"],
                    signed_by=link["signed_by"],
                    signature=link["signature"],
                    created_at=datetime.fromisoformat(link["created_at"]),
                )
                for link in data.get("links_in", [])
            ],
        )
