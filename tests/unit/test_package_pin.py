"""Unit tests for OKH package pin record creation and verification (issue #174)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_MANIFEST = {
    "title": "Test Robot",
    "version": "1.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "Moves things",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_fake_package(tmp_path: Path, manifest: dict = _MANIFEST) -> Path:
    """Create the minimal package directory structure create_pin_record expects."""
    pkg = tmp_path / "org" / "project" / "1.0"
    (pkg / "metadata").mkdir(parents=True)

    # okh-manifest.json
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    (pkg / "okh-manifest.json").write_bytes(manifest_bytes)

    # A fake content file
    content = b"design data"
    design_dir = pkg / "design-files"
    design_dir.mkdir()
    (design_dir / "schematic.pdf").write_bytes(content)

    # file-manifest.json matching that file
    file_manifest = {
        "total_files": 1,
        "total_size_bytes": len(content),
        "files": [
            {
                "local_path": "design-files/schematic.pdf",
                "checksum_sha256": _sha256(content),
                "original_url": "https://example.com/schematic.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(content),
                "downloaded_at": "2024-01-01T00:00:00",
                "file_type": "design-files",
            }
        ],
    }
    (pkg / "metadata" / "file-manifest.json").write_text(json.dumps(file_manifest))

    return pkg


# ---------------------------------------------------------------------------
# create_pin_record
# ---------------------------------------------------------------------------


def test_create_pin_record_writes_file(tmp_path):
    from src.core.packaging.pin import create_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")
    assert (pkg / "metadata" / "pin-record.json").exists()


def test_create_pin_record_fields_present(tmp_path):
    from src.core.packaging.pin import create_pin_record

    pkg = _build_fake_package(tmp_path)
    record = create_pin_record(pkg, pinned_by="alice", note="Validated 2024-01-01")

    assert record["pinned_by"] == "alice"
    assert record["note"] == "Validated 2024-01-01"
    assert record["pinned_at"]
    assert record["manifest_content_hash"].startswith("sha256:")
    assert "design-files/schematic.pdf" in record["file_hashes"]


def test_create_pin_record_manifest_hash_stable(tmp_path):
    from src.core.federation.catalog import manifest_content_hash
    from src.core.packaging.pin import create_pin_record

    pkg = _build_fake_package(tmp_path)
    record = create_pin_record(pkg, pinned_by="alice")

    expected = manifest_content_hash(_MANIFEST)
    assert record["manifest_content_hash"] == expected


def test_create_pin_record_file_hash_matches_content(tmp_path):
    from src.core.packaging.pin import create_pin_record

    pkg = _build_fake_package(tmp_path)
    record = create_pin_record(pkg, pinned_by="alice")

    expected_hash = _sha256(b"design data")
    assert record["file_hashes"]["design-files/schematic.pdf"] == expected_hash


def test_create_pin_record_note_none_by_default(tmp_path):
    from src.core.packaging.pin import create_pin_record

    pkg = _build_fake_package(tmp_path)
    record = create_pin_record(pkg, pinned_by="alice")
    assert record["note"] is None


# ---------------------------------------------------------------------------
# verify_pin_record — clean package
# ---------------------------------------------------------------------------


def test_verify_pin_record_clean_package(tmp_path):
    from src.core.packaging.pin import create_pin_record, verify_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")
    ok, changed = verify_pin_record(pkg)
    assert ok is True
    assert changed == []


# ---------------------------------------------------------------------------
# verify_pin_record — tampered file
# ---------------------------------------------------------------------------


def test_verify_pin_record_detects_changed_file(tmp_path):
    from src.core.packaging.pin import create_pin_record, verify_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")

    # Tamper with the content file after pinning
    (pkg / "design-files" / "schematic.pdf").write_bytes(b"tampered!")

    ok, changed = verify_pin_record(pkg)
    assert ok is False
    assert "design-files/schematic.pdf" in changed


def test_verify_pin_record_detects_missing_file(tmp_path):
    from src.core.packaging.pin import create_pin_record, verify_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")

    (pkg / "design-files" / "schematic.pdf").unlink()

    ok, changed = verify_pin_record(pkg)
    assert ok is False
    assert "design-files/schematic.pdf" in changed


def test_verify_pin_record_detects_changed_manifest(tmp_path):
    from src.core.packaging.pin import create_pin_record, verify_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")

    # Tamper with the manifest
    tampered = {**_MANIFEST, "title": "TAMPERED"}
    (pkg / "okh-manifest.json").write_text(json.dumps(tampered))

    ok, changed = verify_pin_record(pkg)
    assert ok is False
    assert "okh-manifest.json" in changed


# ---------------------------------------------------------------------------
# verify_pin_record — missing pin record
# ---------------------------------------------------------------------------


def test_verify_pin_record_raises_when_no_pin(tmp_path):
    from src.core.packaging.pin import verify_pin_record
    import pytest

    pkg = _build_fake_package(tmp_path)
    with pytest.raises(FileNotFoundError):
        verify_pin_record(pkg)


# ---------------------------------------------------------------------------
# load_pin_record
# ---------------------------------------------------------------------------


def test_load_pin_record_returns_none_when_absent(tmp_path):
    from src.core.packaging.pin import load_pin_record

    pkg = _build_fake_package(tmp_path)
    assert load_pin_record(pkg) is None


def test_load_pin_record_returns_dict_when_present(tmp_path):
    from src.core.packaging.pin import create_pin_record, load_pin_record

    pkg = _build_fake_package(tmp_path)
    create_pin_record(pkg, pinned_by="alice")
    record = load_pin_record(pkg)
    assert record is not None
    assert record["pinned_by"] == "alice"
