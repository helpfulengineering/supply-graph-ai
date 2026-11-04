"""Unit tests for OKH bulk import/export/diff (issue #176)."""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_REQUIRED = {
    "title": "",
    "version": "1.0",
    "license": "MIT",
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "does a thing",
}


def _manifest(title: str, version: str = "1.0"):
    from src.core.models.okh import OKHManifest

    d = {**_REQUIRED, "title": title, "version": version}
    return OKHManifest.from_dict(d)


# ---------------------------------------------------------------------------
# export_collection
# ---------------------------------------------------------------------------


def test_export_returns_bytes():
    from src.core.packaging.collection import export_collection

    data = export_collection([_manifest("Widget")])
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_export_is_valid_zip():
    from src.core.packaging.collection import export_collection

    data = export_collection([_manifest("Widget")])
    assert zipfile.is_zipfile(io.BytesIO(data))


def test_export_contains_index():
    from src.core.packaging.collection import export_collection, _INDEX_FILE

    data = export_collection([_manifest("Widget")])
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        assert _INDEX_FILE in zf.namelist()


def test_export_index_entry_fields():
    from src.core.packaging.collection import export_collection, _INDEX_FILE

    m = _manifest("Widget")
    data = export_collection([m])
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        index = json.loads(zf.read(_INDEX_FILE))
    assert len(index) == 1
    entry = index[0]
    assert entry["title"] == "Widget"
    assert entry["version"] == "1.0"
    assert entry["content_hash"].startswith("sha256:")
    assert "exported_at" in entry


def test_export_manifest_file_present():
    from src.core.packaging.collection import (
        export_collection,
        _INDEX_FILE,
        _manifest_filename,
    )
    from src.core.federation.catalog import manifest_content_hash

    m = _manifest("Sprocket")
    data = export_collection([m])
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        index = json.loads(zf.read(_INDEX_FILE))
        h = index[0]["content_hash"]
        assert _manifest_filename(h) in zf.namelist()


def test_export_empty_collection():
    from src.core.packaging.collection import export_collection, _INDEX_FILE

    data = export_collection([])
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        index = json.loads(zf.read(_INDEX_FILE))
    assert index == []


# ---------------------------------------------------------------------------
# analyse_import
# ---------------------------------------------------------------------------


def _make_archive(manifests):
    from src.core.packaging.collection import export_collection

    return export_collection(manifests)


def test_analyse_import_new():
    from src.core.packaging.collection import analyse_import

    archive = _make_archive([_manifest("Widget")])
    report, incoming = analyse_import(archive, [])
    assert len(report.new) == 1
    assert len(report.duplicate) == 0
    assert len(report.conflict) == 0
    assert len(incoming) == 1


def test_analyse_import_duplicate():
    from src.core.packaging.collection import analyse_import

    m = _manifest("Widget")
    archive = _make_archive([m])
    report, incoming = analyse_import(archive, [m])
    assert len(report.duplicate) == 1
    assert len(report.new) == 0
    assert len(incoming) == 0


def test_analyse_import_conflict():
    from src.core.packaging.collection import analyse_import
    from src.core.models.okh import OKHManifest

    # same title/version but different function → different content hash
    local = _manifest("Widget", "1.0")
    archive_m = OKHManifest.from_dict(
        {**_REQUIRED, "title": "Widget", "version": "1.0", "function": "different"}
    )
    archive = _make_archive([archive_m])
    report, incoming = analyse_import(archive, [local])
    assert len(report.conflict) == 1
    assert len(report.new) == 0
    assert len(incoming) == 0


def test_analyse_import_mixed():
    from src.core.packaging.collection import analyse_import
    from src.core.models.okh import OKHManifest

    m_dup = _manifest("Alpha")
    m_new = _manifest("Beta")
    m_conflict_local = _manifest("Gamma")
    m_conflict_archive = OKHManifest.from_dict(
        {**_REQUIRED, "title": "Gamma", "version": "1.0", "function": "different"}
    )

    archive = _make_archive([m_dup, m_new, m_conflict_archive])
    report, incoming = analyse_import(archive, [m_dup, m_conflict_local])

    assert len(report.new) == 1
    assert len(report.duplicate) == 1
    assert len(report.conflict) == 1
    assert len(incoming) == 1


# ---------------------------------------------------------------------------
# diff_collection
# ---------------------------------------------------------------------------


def test_diff_identical():
    from src.core.packaging.collection import diff_collection

    m = _manifest("Widget")
    archive = _make_archive([m])
    result = diff_collection(archive, [m])
    assert result["only_in_archive"] == []
    assert result["only_local"] == []


def test_diff_only_in_archive():
    from src.core.packaging.collection import diff_collection

    m = _manifest("Widget")
    archive = _make_archive([m])
    result = diff_collection(archive, [])
    assert len(result["only_in_archive"]) == 1
    assert result["only_local"] == []


def test_diff_only_local():
    from src.core.packaging.collection import diff_collection

    m = _manifest("Widget")
    archive = _make_archive([])
    result = diff_collection(archive, [m])
    assert result["only_in_archive"] == []
    assert len(result["only_local"]) == 1


def test_diff_symmetric():
    from src.core.packaging.collection import diff_collection

    m_a = _manifest("Alpha")
    m_b = _manifest("Beta")
    archive = _make_archive([m_a])
    result = diff_collection(archive, [m_b])
    assert len(result["only_in_archive"]) == 1
    assert len(result["only_local"]) == 1
    assert result["only_in_archive"][0]["title"] == "Alpha"
    assert result["only_local"][0]["title"] == "Beta"


def test_a_carried_chain_keeps_the_verdict_it_had():
    from src.core.federation.catalog import manifest_content_hash
    from src.core.models.provenance import organisation_verified
    from src.core.packaging.collection import analyse_import, export_collection
    from tests.federation.test_organisation_chain import _chain

    manifest = _manifest("Widget")
    held = _chain()
    broken = _chain(tamper_claim=True)
    archive = export_collection(
        [manifest],
        {str(manifest.id): held},
    )
    report, _incoming = analyse_import(archive, [])
    restored = report.provenance[report.new[0]["content_hash"]]
    assert report.new[0]["content_hash"] == manifest_content_hash(manifest.to_dict())
    assert organisation_verified(restored)

    other = _manifest("Other")
    archive = export_collection([other], {str(other.id): broken})
    report, _incoming = analyse_import(archive, [])
    restored = report.provenance[report.new[0]["content_hash"]]
    assert not organisation_verified(restored)


def test_an_archive_without_provenance_still_imports():
    from src.core.federation.catalog import manifest_content_hash
    from src.core.packaging.collection import (
        _INDEX_FILE,
        _manifest_filename,
        analyse_import,
    )

    manifest = _manifest("Widget")
    body = manifest.to_dict()
    content_hash = manifest_content_hash(body)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(_manifest_filename(content_hash), json.dumps(body))
        zf.writestr(
            _INDEX_FILE,
            json.dumps(
                [
                    {
                        "content_hash": content_hash,
                        "title": manifest.title,
                        "version": manifest.version,
                        "exported_at": "2020-01-01T00:00:00+00:00",
                    }
                ]
            ),
        )
    report, incoming = analyse_import(buf.getvalue(), [])
    assert len(incoming) == 1
    assert report.provenance == {}


def test_the_archive_does_not_carry_visibility():
    from src.core.packaging.collection import export_collection

    data = export_collection([_manifest("Widget")])
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert not any("visibility" in name for name in zf.namelist())


def test_export_then_import_keeps_the_author_and_organisation():
    from src.core.federation.identity import generate_identity
    from src.core.models.provenance import (
        Credit,
        RecordProvenance,
        sign_provenance,
        verify_provenance,
    )
    from src.core.packaging.collection import analyse_import, export_collection

    author = generate_identity("Ada")
    manifest = _manifest("Widget")
    provenance = RecordProvenance(
        authored_by=[Credit(subject_did=author.did, role="author")],
        published_by=author.did,
        on_behalf_of="did:key:zFab",
    )
    sign_provenance(provenance, author.private_key, author.did)
    archive = export_collection([manifest], {str(manifest.id): provenance})

    report, incoming = analyse_import(archive, [])
    assert len(incoming) == 1
    restored = report.provenance[report.new[0]["content_hash"]]
    assert restored.published_by == author.did
    assert restored.on_behalf_of == "did:key:zFab"
    assert verify_provenance(restored)


def test_diff_entry_has_required_keys():
    from src.core.packaging.collection import diff_collection

    m = _manifest("Widget")
    archive = _make_archive([m])
    result = diff_collection(archive, [])
    entry = result["only_in_archive"][0]
    assert "content_hash" in entry
    assert "title" in entry
    assert "version" in entry
