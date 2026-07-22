"""Resolve local package artifacts for federation catalog pointers."""

from __future__ import annotations

import io
import json
import shutil
import tarfile
import zipfile
from pathlib import Path
from uuid import UUID

from ..packaging.pin import bundle_hash, load_pin_record
from ..utils.logging import get_logger
from .catalog import manifest_content_hash
from .models import PackagePointer

logger = get_logger(__name__)


def _package_search_roots() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[3]
    return [
        repo_root / "packages",
        repo_root / "test-data" / "microlab" / "package",
    ]


def _normalize_hash(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _find_archive(package_dir: Path) -> Path | None:
    for name in (f"{package_dir.name}.zip", "package.zip", "bundle.zip"):
        candidate = package_dir / name
        if candidate.is_file():
            return candidate
    parent_zip = package_dir.parent / f"{package_dir.name}.zip"
    return parent_zip if parent_zip.is_file() else None


def _pin_for_dir(package_dir: Path) -> dict | None:
    pin = load_pin_record(package_dir)
    if pin is not None:
        return pin
    file_manifest = package_dir / "metadata" / "file-manifest.json"
    okh_path = package_dir / "okh-manifest.json"
    if not file_manifest.exists() or not okh_path.exists():
        return None
    try:
        manifest_dict = json.loads(okh_path.read_text(encoding="utf-8"))
        file_data = json.loads(file_manifest.read_text(encoding="utf-8"))
        file_hashes = {
            fi["local_path"]: fi["checksum_sha256"]
            for fi in file_data.get("files", [])
            if fi.get("local_path") and fi.get("checksum_sha256")
        }
        return {
            "manifest_content_hash": manifest_content_hash(manifest_dict),
            "file_hashes": file_hashes,
        }
    except (OSError, json.JSONDecodeError, KeyError) as e:
        logger.debug(f"Could not derive pin for {package_dir}: {e}")
        return None


def _pointer_from_dir(package_dir: Path) -> PackagePointer | None:
    pin = _pin_for_dir(package_dir)
    if pin is None:
        return None
    bhash = bundle_hash(pin)
    archive = _find_archive(package_dir)
    if archive is not None:
        return PackagePointer(
            bundle_hash=bhash,
            byte_size=archive.stat().st_size,
            filename=archive.name,
        )
    total = sum(f.stat().st_size for f in package_dir.rglob("*") if f.is_file())
    return PackagePointer(
        bundle_hash=bhash,
        byte_size=total,
        filename=f"{package_dir.name}.tar.gz",
    )


def find_package_dir_for_manifest(manifest_id: UUID) -> Path | None:
    """Return the package directory whose okh-manifest.json matches ``manifest_id``."""
    target = str(manifest_id)
    for root in _package_search_roots():
        if not root.is_dir():
            continue
        for manifest_path in root.rglob("okh-manifest.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(data.get("id")) == target:
                return manifest_path.parent
    return None


def resolve_package_pointer(manifest_id: UUID) -> PackagePointer | None:
    """Build a catalog package pointer if a local package exists for the design."""
    package_dir = find_package_dir_for_manifest(manifest_id)
    if package_dir is None:
        return None
    return _pointer_from_dir(package_dir)


def find_package_dir_by_bundle_hash(bundle_hash_value: str) -> Path | None:
    """Locate a local package directory whose pin-derived bundle hash matches."""
    normalized = _normalize_hash(bundle_hash_value)
    for root in _package_search_roots():
        if not root.is_dir():
            continue
        for manifest_path in root.rglob("okh-manifest.json"):
            package_dir = manifest_path.parent
            pointer = _pointer_from_dir(package_dir)
            if pointer is not None and pointer.bundle_hash == normalized:
                return package_dir
    return None


def package_dir_to_archive_bytes(package_dir: Path) -> tuple[bytes, str]:
    """Return (bytes, filename) for serving — prefer existing zip, else tar.gz."""
    archive = _find_archive(package_dir)
    if archive is not None:
        return archive.read_bytes(), archive.name

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(package_dir, arcname=package_dir.name)
    return buf.getvalue(), f"{package_dir.name}.tar.gz"


def _try_extract(archive_path: Path, dest: Path) -> bool:
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(dest)
            return True
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as tf:
                tf.extractall(dest)
            return True
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as e:
        logger.debug(f"extract failed: {e}")
    return False


def write_fetched_package(
    data: bytes,
    *,
    expected_hash: str,
    dest_root: Path | None = None,
) -> Path:
    """Verify pin bundle_hash and materialize under packages/_federated/."""
    expected = _normalize_hash(expected_hash)
    if dest_root is None:
        dest_root = _package_search_roots()[0] / "_federated"
    work = dest_root / expected.replace(":", "_")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    archive_path = work / "fetched-package.bin"
    archive_path.write_bytes(data)
    contents = work / "contents"
    contents.mkdir()

    if not _try_extract(archive_path, contents):
        shutil.rmtree(work, ignore_errors=True)
        raise ValueError(f"bundle_hash mismatch for {expected}")

    manifests = list(contents.rglob("okh-manifest.json"))
    package_dir = manifests[0].parent if manifests else None
    pointer = _pointer_from_dir(package_dir) if package_dir else None
    if pointer is None or pointer.bundle_hash != expected:
        shutil.rmtree(work, ignore_errors=True)
        raise ValueError(f"bundle_hash mismatch for {expected}")
    return package_dir
