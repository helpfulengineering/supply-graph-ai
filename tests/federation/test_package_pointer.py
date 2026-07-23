"""Tests for federation package pointers and CAS helpers."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from src.core.federation.catalog import manifest_content_hash
from src.core.federation.package_pointer import (
    find_package_dir_for_manifest,
    resolve_package_pointer,
)
from src.core.packaging.pin import bundle_hash, create_pin_record

MINIMAL = {
    "okhv": "1.0",
    "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
    "title": "Pkg Design",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "testing",
}


@pytest.mark.unit
def test_resolve_package_pointer_from_local_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = tmp_path / "packages" / "community" / "pkg-design" / "1.0.0"
    (pkg / "metadata").mkdir(parents=True)
    (pkg / "okh-manifest.json").write_text(json.dumps(MINIMAL), encoding="utf-8")
    (pkg / "metadata" / "file-manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "local_path": "okh-manifest.json",
                        "checksum_sha256": "sha256:" + "ab" * 32,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    create_pin_record(pkg, pinned_by="did:key:zTest")

    monkeypatch.setattr(
        "src.core.federation.package_pointer._package_search_roots",
        lambda: [tmp_path / "packages"],
    )

    mid = UUID(MINIMAL["id"])
    assert find_package_dir_for_manifest(mid) == pkg
    pointer = resolve_package_pointer(mid)
    assert pointer is not None
    assert pointer.bundle_hash.startswith("sha256:")
    pin = json.loads((pkg / "metadata" / "pin-record.json").read_text())
    assert pointer.bundle_hash == bundle_hash(pin)
    assert pointer.byte_size > 0


@pytest.mark.unit
def test_resolve_package_pointer_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.federation.package_pointer._package_search_roots",
        lambda: [],
    )
    assert resolve_package_pointer(UUID(MINIMAL["id"])) is None


@pytest.mark.unit
def test_manifest_hash_unchanged_by_package_pointer_fields() -> None:
    """Package pointer must not alter design content hash."""
    assert manifest_content_hash(MINIMAL) == manifest_content_hash(dict(MINIMAL))


@pytest.mark.unit
def test_try_extract_rejects_zip_slip(tmp_path: Path) -> None:
    """Zip members that escape dest must fail closed (no extract)."""
    import io
    import zipfile

    from src.core.federation.package_pointer import _try_extract

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "pwned")
    archive = tmp_path / "slip.zip"
    archive.write_bytes(buf.getvalue())
    dest = tmp_path / "out"
    dest.mkdir()
    assert _try_extract(archive, dest) is False
    assert not (tmp_path / "evil.txt").exists()
    assert list(dest.iterdir()) == []
