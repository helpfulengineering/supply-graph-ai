"""
Contract tests for package download routes.

Package names use ``org/project`` (a slash). Routes must use ``{package_name:path}``
so FastAPI does not treat the project segment as the version.
"""

from __future__ import annotations

import os
import sys
import tarfile
import tempfile
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


def _get_package_service_dep():
    from src.core.api.routes.package import get_package_service

    return get_package_service


def _sample_metadata(package_path: Path) -> PackageMetadata:
    readme = package_path / "README.md"
    readme.write_text("package download contract test\n", encoding="utf-8")
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
        package_name="test-org/test-project",
        version="1.2.3",
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
def mock_package_service(tmp_path: Path):
    pkg_dir = tmp_path / "packages" / "test-org" / "test-project" / "1.2.3"
    pkg_dir.mkdir(parents=True)
    metadata = _sample_metadata(pkg_dir)

    svc = MagicMock()
    svc.get_package_metadata = AsyncMock(return_value=metadata)
    return svc


@pytest.mark.asyncio
@pytest.mark.contract
async def test_download_slash_package_name_returns_tarball(mock_package_service):
    """GET .../org/project/version/download must resolve org/project, not org only."""
    get_package_service = _get_package_service_dep()
    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: mock_package_service

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            url = "/v1/api/package/test-org/test-project/1.2.3/download"
            resp = await client.get(url)

        assert resp.status_code == 200, resp.text
        assert "gzip" in (resp.headers.get("content-type") or "")
        assert ".tar.gz" in (resp.headers.get("content-disposition") or "")

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp.write(resp.content)
            tar_path = tmp.name

        with tarfile.open(tar_path, "r:gz") as tar:
            names = tar.getnames()
        assert any("README.md" in n for n in names), names
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_download_resolves_org_project_path(mock_package_service):
    """``/{org}/{project}/{version}/download`` must pass ``org/project`` to the service."""
    get_package_service = _get_package_service_dep()
    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: mock_package_service

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            await client.get("/v1/api/package/test-org/test-project/1.2.3/download")
        mock_package_service.get_package_metadata.assert_awaited_with(
            "test-org/test-project", "1.2.3"
        )
    finally:
        api_v1.dependency_overrides.clear()
