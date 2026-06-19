"""Unit tests for cryptographic package signing (issue #175)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_identity():
    from src.core.federation.identity import generate_identity

    return generate_identity("Test Node")


def _build_fake_package(tmp_path: Path) -> Path:
    """Minimal package directory structure sign_package and verify_package_signature need."""
    pkg = tmp_path / "org" / "project" / "1.0"
    (pkg / "metadata").mkdir(parents=True)

    file_manifest = {
        "total_files": 1,
        "total_size_bytes": 42,
        "files": [
            {
                "local_path": "design-files/schematic.pdf",
                "checksum_sha256": "abc123",
                "original_url": "https://example.com/s.pdf",
                "content_type": "application/pdf",
                "size_bytes": 42,
                "downloaded_at": "2024-01-01T00:00:00",
                "file_type": "design-files",
            }
        ],
    }
    (pkg / "metadata" / "file-manifest.json").write_text(json.dumps(file_manifest))
    return pkg


# ---------------------------------------------------------------------------
# sign_package
# ---------------------------------------------------------------------------


def test_sign_package_writes_signature_file(tmp_path):
    from src.core.packaging.signing import sign_package

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    sign_package(pkg, identity)
    assert (pkg / "metadata" / "package-signature.json").exists()


def test_sign_package_record_fields(tmp_path):
    from src.core.packaging.signing import sign_package

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    record = sign_package(pkg, identity)

    assert record["signed_by"] == identity.did
    assert record["algorithm"] == "ed25519"
    assert record["signed_at"]
    assert len(record["signature"]) > 0
    # hex-encoded bytes
    bytes.fromhex(record["signature"])


def test_sign_package_signed_by_matches_did(tmp_path):
    from src.core.packaging.signing import sign_package

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    record = sign_package(pkg, identity)
    assert record["signed_by"].startswith("did:key:")


# ---------------------------------------------------------------------------
# verify_package_signature — valid
# ---------------------------------------------------------------------------


def test_verify_package_signature_valid(tmp_path):
    from src.core.packaging.signing import sign_package, verify_package_signature

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    sign_package(pkg, identity)
    assert verify_package_signature(pkg) is True


# ---------------------------------------------------------------------------
# verify_package_signature — tampered file-manifest
# ---------------------------------------------------------------------------


def test_verify_package_signature_detects_tampered_manifest(tmp_path):
    from src.core.packaging.signing import sign_package, verify_package_signature

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    sign_package(pkg, identity)

    # Tamper with file-manifest.json after signing
    tampered = {"total_files": 99, "files": []}
    (pkg / "metadata" / "file-manifest.json").write_text(json.dumps(tampered))

    assert verify_package_signature(pkg) is False


# ---------------------------------------------------------------------------
# verify_package_signature — missing signature
# ---------------------------------------------------------------------------


def test_verify_package_signature_raises_when_absent(tmp_path):
    from src.core.packaging.signing import verify_package_signature
    import pytest

    pkg = _build_fake_package(tmp_path)
    with pytest.raises(FileNotFoundError):
        verify_package_signature(pkg)


# ---------------------------------------------------------------------------
# load_signature_record
# ---------------------------------------------------------------------------


def test_load_signature_record_returns_none_when_absent(tmp_path):
    from src.core.packaging.signing import load_signature_record

    pkg = _build_fake_package(tmp_path)
    assert load_signature_record(pkg) is None


def test_load_signature_record_returns_dict_when_present(tmp_path):
    from src.core.packaging.signing import load_signature_record, sign_package

    pkg = _build_fake_package(tmp_path)
    identity = _make_identity()
    sign_package(pkg, identity)
    record = load_signature_record(pkg)
    assert record is not None
    assert record["signed_by"] == identity.did


# ---------------------------------------------------------------------------
# Two different identities produce different signatures
# ---------------------------------------------------------------------------


def test_two_identities_produce_different_signatures(tmp_path):
    from src.core.packaging.signing import sign_package

    pkg1 = _build_fake_package(tmp_path / "p1")
    pkg2 = _build_fake_package(tmp_path / "p2")
    id1 = _make_identity()
    id2 = _make_identity()
    rec1 = sign_package(pkg1, id1)
    rec2 = sign_package(pkg2, id2)
    assert rec1["signature"] != rec2["signature"]
    assert rec1["signed_by"] != rec2["signed_by"]
