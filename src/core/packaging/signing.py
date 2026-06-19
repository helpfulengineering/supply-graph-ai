"""Cryptographic signing and verification for OKH packages."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..federation.identity import NodeIdentity, canonical_json_bytes, did_to_public_key


def _signature_path(package_path: Path) -> Path:
    return package_path / "metadata" / "package-signature.json"


def sign_package(package_path: Path, identity: NodeIdentity) -> dict:
    """Sign the package's file-manifest.json and write metadata/package-signature.json.

    Returns the signature record dict.
    """
    file_manifest_path = package_path / "metadata" / "file-manifest.json"
    with open(file_manifest_path, "r") as f:
        file_manifest = json.load(f)

    payload = canonical_json_bytes(file_manifest)
    sig_bytes = identity.sign_bytes(payload)

    record = {
        "signed_by": identity.did,
        "signature": sig_bytes.hex(),
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "ed25519",
    }

    with open(_signature_path(package_path), "w") as f:
        json.dump(record, f, indent=2)

    return record


def verify_package_signature(package_path: Path) -> bool:
    """Return True if the package-signature.json is valid against the file-manifest.json.

    Raises FileNotFoundError if either file is missing.
    Raises ValueError if the DID in the signature is malformed.
    Returns False if the signature is cryptographically invalid (tampered content).
    """
    sig_path = _signature_path(package_path)
    if not sig_path.exists():
        raise FileNotFoundError(f"No signature record at {sig_path}")

    with open(sig_path, "r") as f:
        record = json.load(f)

    file_manifest_path = package_path / "metadata" / "file-manifest.json"
    with open(file_manifest_path, "r") as f:
        file_manifest = json.load(f)

    payload = canonical_json_bytes(file_manifest)
    sig_bytes = bytes.fromhex(record["signature"])
    public_key = did_to_public_key(record["signed_by"])

    try:
        public_key.verify(sig_bytes, payload)
        return True
    except Exception:
        return False


def load_signature_record(package_path: Path) -> Optional[dict]:
    """Return the signature record dict if one exists, else None."""
    sig_path = _signature_path(package_path)
    if not sig_path.exists():
        return None
    with open(sig_path, "r") as f:
        return json.load(f)
