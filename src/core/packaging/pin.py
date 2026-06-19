"""Pin record creation and verification for OKH packages."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..federation.catalog import manifest_content_hash
from ..models.package import calculate_file_checksum


def _pin_record_path(package_path: Path) -> Path:
    return package_path / "metadata" / "pin-record.json"


def create_pin_record(
    package_path: Path,
    pinned_by: str,
    note: Optional[str] = None,
) -> dict:
    """Create a pin record for the package and write it to metadata/pin-record.json.

    Reads the existing file-manifest.json for file hashes — no files are rehashed.
    """
    manifest_path = package_path / "okh-manifest.json"
    with open(manifest_path, "r") as f:
        manifest_dict = json.load(f)

    file_manifest_path = package_path / "metadata" / "file-manifest.json"
    with open(file_manifest_path, "r") as f:
        file_manifest = json.load(f)

    file_hashes: Dict[str, str] = {
        fi["local_path"]: fi["checksum_sha256"]
        for fi in file_manifest.get("files", [])
        if fi.get("local_path") and fi.get("checksum_sha256")
    }

    pin_record = {
        "pinned_at": datetime.now(timezone.utc).isoformat(),
        "pinned_by": pinned_by,
        "manifest_content_hash": manifest_content_hash(manifest_dict),
        "file_hashes": file_hashes,
        "note": note,
    }

    with open(_pin_record_path(package_path), "w") as f:
        json.dump(pin_record, f, indent=2)

    return pin_record


def verify_pin_record(package_path: Path) -> Tuple[bool, List[str]]:
    """Verify a package against its pin record.

    Returns (ok, changed_paths) where changed_paths lists every file that has
    changed or gone missing since pinning.
    """
    pin_path = _pin_record_path(package_path)
    if not pin_path.exists():
        raise FileNotFoundError(f"No pin record found at {pin_path}")

    with open(pin_path, "r") as f:
        pin_record = json.load(f)

    changed: List[str] = []

    manifest_path = package_path / "okh-manifest.json"
    with open(manifest_path, "r") as f:
        manifest_dict = json.load(f)

    if manifest_content_hash(manifest_dict) != pin_record["manifest_content_hash"]:
        changed.append("okh-manifest.json")

    for rel_path, pinned_hash in pin_record.get("file_hashes", {}).items():
        abs_path = package_path / rel_path
        if not abs_path.exists():
            changed.append(rel_path)
            continue
        if calculate_file_checksum(abs_path) != pinned_hash:
            changed.append(rel_path)

    return len(changed) == 0, changed


def load_pin_record(package_path: Path) -> Optional[dict]:
    """Return the pin record dict if one exists, else None."""
    pin_path = _pin_record_path(package_path)
    if not pin_path.exists():
        return None
    with open(pin_path, "r") as f:
        return json.load(f)
