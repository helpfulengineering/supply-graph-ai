"""
Live API integration test for package download (requires running OHM API).

Run against a server with the org/project/version route fix, e.g. after
``docker compose build ohm-api && docker compose up -d ohm-api``:

    OHM_API_BASE=http://localhost:8001 pytest tests/api/test_package_download_integration.py -m integration
"""

from __future__ import annotations

import os
import tarfile
import tempfile

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.allow_network
@pytest.mark.asyncio
async def test_live_package_download_from_remote_storage():
    base = os.environ.get("OHM_API_BASE", "http://localhost:8001").rstrip("/")
    package_name = "beagleboard/beaglebone-black"
    version = "Rev C"
    org, project = package_name.split("/")
    url = f"{base}/v1/api/package/{org}/{project}/{version}/download"

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(url)

    assert resp.status_code == 200, resp.text[:500]
    assert "gzip" in (resp.headers.get("content-type") or "")
    assert len(resp.content) > 1000

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(resp.content)
        tar_path = tmp.name

    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
    assert len(names) > 0
