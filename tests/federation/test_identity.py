"""Unit tests for federation node identity and did:key encoding."""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.core.federation.identity import (
    canonical_json_bytes,
    did_to_public_key,
    generate_identity,
    load_or_create_identity,
    public_key_to_did,
)


@pytest.mark.unit
def test_canonical_json_bytes_is_stable() -> None:
    a = canonical_json_bytes({"b": 2, "a": 1})
    b = canonical_json_bytes({"a": 1, "b": 2})
    assert a == b
    assert a == b'{"a":1,"b":2}'


@pytest.mark.unit
def test_did_round_trip() -> None:
    private_key = Ed25519PrivateKey.generate()
    did = public_key_to_did(private_key.public_key())
    assert did.startswith("did:key:z")
    from cryptography.hazmat.primitives import serialization

    restored = did_to_public_key(did)
    assert restored.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ) == private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


@pytest.mark.unit
def test_sign_and_verify_json() -> None:
    identity = generate_identity("Test Node")
    payload = {"manifest_id": "340b030e-e3c6-4869-b947-4a24c52daaf1", "v": 1}
    signature = identity.sign_json(payload)
    assert identity.verify_bytes(canonical_json_bytes(payload), signature)
    assert not identity.verify_bytes(b"tampered", signature)


@pytest.mark.unit
def test_load_or_create_identity_is_idempotent(tmp_path) -> None:
    first = load_or_create_identity(tmp_path, "Peer A")
    second = load_or_create_identity(tmp_path, "Peer A")
    assert first.did == second.did
    assert (tmp_path / "identity.json").is_file()
    on_disk = json.loads((tmp_path / "identity.json").read_text(encoding="utf-8"))
    assert on_disk["did"] == first.did


@pytest.mark.unit
def test_load_or_create_updates_display_name(tmp_path) -> None:
    first = load_or_create_identity(tmp_path, "Old Name")
    second = load_or_create_identity(tmp_path, "New Name")
    assert second.display_name == "New Name"
    assert first.did == second.did
