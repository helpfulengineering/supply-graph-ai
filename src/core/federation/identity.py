"""Node identity: Ed25519 keypair and did:key encoding."""

from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

# multicodec ed25519-pub
_ED25519_PUB_MULTICODEC = bytes([0xED, 0x01])
_BASE58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58_encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    encoded = bytearray()
    while num > 0:
        num, rem = divmod(num, 58)
        encoded.append(_BASE58_ALPHABET[rem])
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
    prefix = _BASE58_ALPHABET[0:1] * pad
    return (prefix + encoded[::-1]).decode("ascii")


def _base58_decode(text: str) -> bytes:
    num = 0
    for char in text.encode("ascii"):
        num = num * 58 + _BASE58_ALPHABET.index(char)
    combined = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = 0
    for char in text:
        if char == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + combined


def public_key_to_did(public_key: Ed25519PublicKey) -> str:
    """Encode an Ed25519 public key as did:key."""
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    multicodec = _ED25519_PUB_MULTICODEC + raw
    return f"did:key:z{_base58_encode(multicodec)}"


def did_to_public_key(did: str) -> Ed25519PublicKey:
    """Resolve did:key to an Ed25519 public key."""
    if not did.startswith("did:key:z"):
        raise ValueError(f"Unsupported DID method: {did[:32]}...")
    decoded = _base58_decode(did[len("did:key:z") :])
    if len(decoded) < 2 or decoded[:2] != _ED25519_PUB_MULTICODEC:
        raise ValueError("did:key does not contain ed25519-pub multicodec prefix")
    raw = decoded[2:]
    if len(raw) != 32:
        raise ValueError(f"Expected 32-byte Ed25519 public key, got {len(raw)}")
    return Ed25519PublicKey.from_public_bytes(raw)


@dataclass
class NodeIdentity:
    """Signing identity for a federation node."""

    did: str
    display_name: str
    private_key: Ed25519PrivateKey

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self.private_key.public_key()

    def sign_bytes(self, payload: bytes) -> bytes:
        return self.private_key.sign(payload)

    def sign_json(self, data: dict[str, Any]) -> bytes:
        return self.sign_bytes(canonical_json_bytes(data))

    def verify_bytes(
        self,
        payload: bytes,
        signature: bytes,
        *,
        public_key: Ed25519PublicKey | None = None,
    ) -> bool:
        key = public_key or self.public_key
        try:
            key.verify(signature, payload)
            return True
        except Exception:
            return False

    def to_identity_file(self) -> dict[str, Any]:
        private_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {
            "did": self.did,
            "display_name": self.display_name,
            "private_key_hex": private_bytes.hex(),
            "public_key_hex": public_bytes.hex(),
        }

    @classmethod
    def from_identity_file(cls, data: dict[str, Any]) -> NodeIdentity:
        private_key = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(data["private_key_hex"])
        )
        did = data.get("did") or public_key_to_did(private_key.public_key())
        return cls(
            did=did,
            display_name=str(data.get("display_name", "OHM Node")),
            private_key=private_key,
        )


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Deterministic JSON encoding for signing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    """Sign a canonical JSON payload, returning a hex signature.

    Generic over persons/spaces/nodes — reused for capability grants and identity
    links, not just node-level signing.
    """
    return private_key.sign(canonical_json_bytes(payload)).hex()


def verify_payload(did: str, payload: dict[str, Any], signature_hex: str) -> bool:
    """Verify a hex signature over a canonical payload against ``did``'s pubkey.

    Fully offline: resolves the Ed25519 public key from the ``did:key`` and checks
    the signature. Returns False on any error (bad DID, bad hex, mismatch).
    """
    try:
        did_to_public_key(did).verify(
            bytes.fromhex(signature_hex), canonical_json_bytes(payload)
        )
        return True
    except Exception:
        return False


# Private key material is written by two callers — the node's own identity and
# the person/space key store — so the mode belongs to a shared helper rather
# than to each write site. Plaintext-at-rest is a documented peacetime decision
# (#410 does not change it); the permissions were never a decision at all, just
# the default from a plain text write, which left every user's signing key
# readable by any local process.
SECRET_FILE_MODE = 0o600
SECRET_DIR_MODE = 0o700

_repaired_dirs: set[str] = set()


def secret_dir(path: Path) -> Path:
    """Ensure ``path`` exists and holds secrets at 0700, repairing it once."""
    path.mkdir(parents=True, exist_ok=True, mode=SECRET_DIR_MODE)
    key = str(path.resolve())
    if key in _repaired_dirs:
        return path
    _repaired_dirs.add(key)
    # mkdir's mode is masked by umask, and ignored outright when the directory
    # already exists — so an explicit chmod is what actually settles it, and is
    # also what repairs directories created before this change.
    if stat.S_IMODE(path.stat().st_mode) != SECRET_DIR_MODE:
        path.chmod(SECRET_DIR_MODE)
    repaired = 0
    for child in path.glob("*.json"):
        if stat.S_IMODE(child.stat().st_mode) != SECRET_FILE_MODE:
            child.chmod(SECRET_FILE_MODE)
            repaired += 1
    if repaired:
        logger.warning(
            f"Tightened permissions on {repaired} key file(s) in {path} that "
            "were written world-readable before this version"
        )
    return path


def write_secret_file(path: Path, text: str) -> None:
    """Write private key material, never observable wider than 0600.

    Opened with an explicit mode rather than written and then chmod-ed: a
    create-then-chmod leaves a window in which the key is readable, which is
    the whole bug this closes. The trailing chmod covers the case where the
    file already existed at a wider mode, since ``os.open`` applies its mode
    only on creation.
    """
    secret_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECRET_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    if stat.S_IMODE(path.stat().st_mode) != SECRET_FILE_MODE:
        path.chmod(SECRET_FILE_MODE)


def generate_identity(display_name: str) -> NodeIdentity:
    """Create a new node identity."""
    private_key = Ed25519PrivateKey.generate()
    did = public_key_to_did(private_key.public_key())
    return NodeIdentity(did=did, display_name=display_name, private_key=private_key)


def load_or_create_identity(data_dir: Path, display_name: str) -> NodeIdentity:
    """Load identity from data_dir/identity.json or create and persist it."""
    secret_dir(data_dir)
    identity_path = data_dir / "identity.json"
    if identity_path.is_file():
        raw = json.loads(identity_path.read_text(encoding="utf-8"))
        identity = NodeIdentity.from_identity_file(raw)
        if display_name and identity.display_name != display_name:
            identity = NodeIdentity(
                did=identity.did,
                display_name=display_name,
                private_key=identity.private_key,
            )
            write_secret_file(
                identity_path, json.dumps(identity.to_identity_file(), indent=2)
            )
        return identity
    identity = generate_identity(display_name or "OHM Node")
    write_secret_file(identity_path, json.dumps(identity.to_identity_file(), indent=2))
    return identity
