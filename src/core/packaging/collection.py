"""Bulk export/import/diff for OKH collection sync (manual federation)."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..federation.catalog import manifest_content_hash
from ..models.okh import OKHManifest
from ..models.provenance import RecordProvenance

_INDEX_FILE = "collection-index.json"


def _manifest_filename(content_hash: str) -> str:
    short = content_hash.removeprefix("sha256:")[:12]
    return f"manifests/sha256_{short}.okh.json"


def _provenance_filename(content_hash: str) -> str:
    short = content_hash.removeprefix("sha256:")[:12]
    return f"provenance/sha256_{short}.json"


@dataclass
class ImportReport:
    new: List[dict] = field(default_factory=list)
    duplicate: List[dict] = field(default_factory=list)
    conflict: List[dict] = field(default_factory=list)
    imported: List[dict] = field(default_factory=list)
    # Provenance for the new records, keyed by content hash. Absent for an
    # archive written before provenance was carried.
    provenance: Dict[str, RecordProvenance] = field(default_factory=dict)


def export_collection(
    manifests: List[OKHManifest],
    provenance_by_id: Optional[Dict[str, RecordProvenance]] = None,
) -> bytes:
    """Return a zip of the manifests, their provenance, and a collection-index.json.

    Provenance rides beside the manifest, keyed by the same content hash, so it
    never enters that hash. Visibility is not written: the receiver restamps it.
    """
    exported_at = datetime.now(timezone.utc).isoformat()
    carried = provenance_by_id or {}
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
            provenance = carried.get(str(manifest.id))
            if provenance is not None:
                zf.writestr(
                    _provenance_filename(content_hash),
                    json.dumps(
                        provenance.model_dump(mode="json"), indent=2, sort_keys=True
                    ),
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
            provenance_name = _provenance_filename(content_hash)
            provenance = (
                RecordProvenance.model_validate(json.loads(zf.read(provenance_name)))
                if provenance_name in zf.namelist()
                else None
            )

            if actual_hash in local_hashes:
                report.duplicate.append(s)
            elif (manifest.title, manifest.version) in local_by_tv:
                report.conflict.append(s)
            else:
                report.new.append(s)
                incoming[actual_hash] = manifest
                if provenance is not None:
                    report.provenance[actual_hash] = provenance

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
