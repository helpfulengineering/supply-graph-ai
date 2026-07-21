"""Build-from-storage must return a JSON-serializable dict (not a SuccessResponse model)."""

from __future__ import annotations

import os
import sys
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


def _sample_metadata(package_path: Path) -> PackageMetadata:
    readme = package_path / "README.md"
    readme.write_text("build response contract\n", encoding="utf-8")
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
        version="1.0.0",
        okh_manifest_id=uuid4(),
        build_timestamp=datetime.now(UTC),
        ohm_version="test",
        total_files=1,
        total_size_bytes=file_info.size_bytes,
        file_inventory=[file_info],
        build_options=BuildOptions(),
        package_path=str(package_path),
    )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_build_from_storage_returns_dict_success(tmp_path: Path):
    from src.core.api.routes.package import get_package_service

    pkg_dir = tmp_path / "packages" / "test-org" / "test-project" / "1.0.0"
    pkg_dir.mkdir(parents=True)
    metadata = _sample_metadata(pkg_dir)

    svc = MagicMock()
    svc.build_package_from_storage = AsyncMock(return_value=metadata)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_package_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.post(
                f"/v1/api/package/build/{metadata.okh_manifest_id}", json={}
            )

        assert res.status_code == 201, res.text
        body = res.json()
        assert body["status"] == "success"
        assert body["data"]["metadata"]["package_name"] == "test-org/test-project"
        assert body["data"]["metadata"]["version"] == "1.0.0"
    finally:
        api_v1.dependency_overrides.clear()
