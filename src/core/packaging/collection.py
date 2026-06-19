"""Bulk export/import/diff for OKH collection sync (manual federation)."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from ..federation.catalog import manifest_content_hash
from ..models.okh import OKHManifest

_INDEX_FILE = "collection-index.json"


def _manifest_filename(content_hash: str) -> str:
    short = content_hash.removeprefix("sha256:")[:12]
    return f"manifests/sha256_{short}.okh.json"


@dataclass
class ImportReport:
    new: List[dict] = field(default_factory=list)
    duplicate: List[dict] = field(default_factory=list)
    conflict: List[dict] = field(default_factory=list)
    imported: List[dict] = field(default_factory=list)


def export_collection(manifests: List[OKHManifest]) -> bytes:
    """Return a zip archive containing all manifests and a collection-index.json."""
    exported_at = datetime.now(timezone.utc).isoformat()
    index = []
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for manifest in manifests:
            manifest_dict = manifest.to_dict()
            content_hash = manifest_content_hash(manifest_dict)
            zf.writestr(
                _manifest_filename(content_hash),
                json.dumps(manifest_dict, indent=2, sort_keys=True),
            )
            index.append(
                {
                    "content_hash": content_hash,
                    "title": manifest.title,
                    "version": manifest.version,
                    "exported_at": exported_at,
                }
            )

        zf.writestr(_INDEX_FILE, json.dumps(index, indent=2))

    return buf.getvalue()


def analyse_import(
    archive_bytes: bytes,
    local_manifests: List[OKHManifest],
) -> Tuple[ImportReport, Dict[str, OKHManifest]]:
    """Classify each archive manifest as new/duplicate/conflict against the local collection.

    Returns (report, new_by_hash). new_by_hash contains manifests the caller should write.
    Does not write anything.
    """
    local_hashes = {manifest_content_hash(m.to_dict()) for m in local_manifests}
    local_by_tv = {
        (m.title, m.version): manifest_content_hash(m.to_dict())
        for m in local_manifests
    }

    report = ImportReport()
    incoming: Dict[str, OKHManifest] = {}

    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as zf:
        index = json.loads(zf.read(_INDEX_FILE))
        for entry in index:
            content_hash = entry["content_hash"]
            manifest_dict = json.loads(zf.read(_manifest_filename(content_hash)))
            manifest = OKHManifest.from_dict(manifest_dict)
            actual_hash = manifest_content_hash(manifest.to_dict())
            s = {
                "content_hash": actual_hash,
                "title": manifest.title,
                "version": manifest.version,
            }

            if actual_hash in local_hashes:
                report.duplicate.append(s)
            elif (manifest.title, manifest.version) in local_by_tv:
                report.conflict.append(s)
            else:
                report.new.append(s)
                incoming[actual_hash] = manifest

    return report, incoming


def diff_collection(
    archive_bytes: bytes,
    local_manifests: List[OKHManifest],
) -> Dict[str, List[dict]]:
    """Return the symmetric diff between archive and local collection.

    Returns {"only_in_archive": [...], "only_local": [...]} with
    {content_hash, title, version} entries.
    """
    local_by_hash: Dict[str, dict] = {}
    for m in local_manifests:
        h = manifest_content_hash(m.to_dict())
        local_by_hash[h] = {"content_hash": h, "title": m.title, "version": m.version}

    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as zf:
        index = json.loads(zf.read(_INDEX_FILE))

    archive_by_hash = {
        e["content_hash"]: {
            "content_hash": e["content_hash"],
            "title": e["title"],
            "version": e["version"],
        }
        for e in index
    }

    return {
        "only_in_archive": [
            v for k, v in archive_by_hash.items() if k not in local_by_hash
        ],
        "only_local": [v for k, v in local_by_hash.items() if k not in archive_by_hash],
    }
