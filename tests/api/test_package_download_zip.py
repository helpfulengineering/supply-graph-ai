"""Contract tests for POST /api/package/download-zip."""

from __future__ import annotations

import io
import os
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.package import BuildOptions, FileInfo, PackageMetadata


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    isolated_app = FastAPI()
    isolated_app.mount("/v1", api_v1)
    return isolated_app, api_v1


def _sample_metadata(package_path: Path, name: str, version: str) -> PackageMetadata:
    readme = package_path / "README.md"
    readme.write_text(f"{name}@{version}\n", encoding="utf-8")
    file_info = FileInfo(
        original_url="file://README.md",
        local_path="README.md",
        content_type="text/plain",
        size_bytes=readme.stat().st_size,
        checksum_sha256="abc",
        downloaded_at=datetime.now(UTC),
        file_type="design-files",
    )
    return PackageMetadata(
        package_name=name,
        version=version,
        okh_manifest_id=uuid4(),
        build_timestamp=datetime.now(UTC),
        ohm_version="test",
        total_files=1,
        total_size_bytes=file_info.size_bytes,
        file_inventory=[file_info],
        build_options=BuildOptions(),
        package_path=str(package_path),
    )


@pytest.fixture
def mock_two_packages(tmp_path: Path):
    a = tmp_path / "packages" / "org-a" / "proj-a" / "1.0.0"
    b = tmp_path / "packages" / "org-b" / "proj-b" / "2.0.0"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    meta_a = _sample_metadata(a, "org-a/proj-a", "1.0.0")
    meta_b = _sample_metadata(b, "org-b/proj-b", "2.0.0")

    async def get_meta(name: str, version: str):
        if name == "org-a/proj-a" and version == "1.0.0":
            return meta_a
        if name == "org-b/proj-b" and version == "2.0.0":
            return meta_b
        return None

    svc = MagicMock()
    svc.get_package_metadata = AsyncMock(side_effect=get_meta)
    return svc


@pytest.mark.asyncio
@pytest.mark.contract
async def test_download_zip_returns_zip_of_tarballs(mock_two_packages):
    from src.core.api.routes.package import get_package_service

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: mock_two_packages

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/package/download-zip",
                json={
                    "items": [
                        {"org": "org-a", "project": "proj-a", "version": "1.0.0"},
                        {"org": "org-b", "project": "proj-b", "version": "2.0.0"},
                    ]
                },
            )

        assert resp.status_code == 200, resp.text
        assert "zip" in (resp.headers.get("content-type") or "")
        assert "ohm-packages.zip" in (resp.headers.get("content-disposition") or "")

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = sorted(zf.namelist())
            assert names == [
                "org-a-proj-a-1.0.0.tar.gz",
                "org-b-proj-b-2.0.0.tar.gz",
            ]
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_download_zip_falls_back_to_a_trusted_remote_pull(
    mock_two_packages, monkeypatch
):
    """When a package isn't built locally, download-zip falls back to
    PackageRemoteStorage.pull_package with a server-generated tempdir
    (_materialize_package_tarball) — not a caller-supplied path, so it must
    stay unsandboxed even with no PACKAGE_PULL_OUTPUT_ROOT configured (#521
    only sandboxes the API/CLI's own caller-supplied output_dir)."""
    import src.core.api.routes.package as package_routes
    from src.core.api.routes.package import get_package_service

    monkeypatch.delenv("PACKAGE_PULL_OUTPUT_ROOT", raising=False)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: mock_two_packages

    remote_storage = MagicMock()

    async def fake_pull(package_name, version, local_output_dir, **kwargs):
        assert kwargs.get("trusted_output_dir") is True
        package_path = Path(local_output_dir) / "org-c" / "proj-c" / "1.0.0"
        package_path.mkdir(parents=True)
        return _sample_metadata(package_path, "org-c/proj-c", "1.0.0")

    remote_storage.pull_package = AsyncMock(side_effect=fake_pull)
    # _materialize_package_tarball calls get_remote_storage() directly, not
    # through FastAPI's Depends resolution, so dependency_overrides can't
    # reach it — patch the module-level function itself instead.
    monkeypatch.setattr(
        package_routes, "get_remote_storage", AsyncMock(return_value=remote_storage)
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/package/download-zip",
                json={
                    "items": [
                        {"org": "org-c", "project": "proj-c", "version": "1.0.0"},
                    ]
                },
            )

        assert resp.status_code == 200, resp.text
        remote_storage.pull_package.assert_awaited_once()
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_download_zip_404_when_missing(mock_two_packages):
    from src.core.api.routes.package import get_package_service

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: mock_two_packages

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/package/download-zip",
                json={
                    "items": [
                        {"org": "missing", "project": "pkg", "version": "9.9.9"},
                    ]
                },
            )
        assert resp.status_code == 404
    finally:
        api_v1.dependency_overrides.clear()
