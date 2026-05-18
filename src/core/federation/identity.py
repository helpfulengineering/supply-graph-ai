"""Node identity: Ed25519 keypair and did:key encoding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

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


def generate_identity(display_name: str) -> NodeIdentity:
    """Create a new node identity."""
    private_key = Ed25519PrivateKey.generate()
    did = public_key_to_did(private_key.public_key())
    return NodeIdentity(did=did, display_name=display_name, private_key=private_key)


def load_or_create_identity(data_dir: Path, display_name: str) -> NodeIdentity:
    """Load identity from data_dir/identity.json or create and persist it."""
    data_dir.mkdir(parents=True, exist_ok=True)
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
            identity_path.write_text(
                json.dumps(identity.to_identity_file(), indent=2),
                encoding="utf-8",
            )
        return identity
    identity = generate_identity(display_name or "OHM Node")
    identity_path.write_text(
        json.dumps(identity.to_identity_file(), indent=2),
        encoding="utf-8",
    )
    return identity
