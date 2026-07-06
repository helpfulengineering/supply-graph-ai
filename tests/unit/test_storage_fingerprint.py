"""Tests for StorageService.get_config_fingerprint (config drift guard / #241).

The fingerprint feeds the public /health endpoint and the deploy gate, so it
must report the resolved target + per-prefix counts and never raise.
"""

import pytest

from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig


class _FakeManager:
    def __init__(self, provider, bucket, account, blobs, raises=False):
        self.config = StorageConfig(
            provider=provider,
            bucket_name=bucket,
            credentials={"account_name": account} if account else {},
        )
        self._blobs = blobs
        self._raises = raises

    async def list_objects(self, prefix=None):
        if self._raises:
            raise RuntimeError("storage unavailable")
        for key in self._blobs:
            if prefix is None or key.startswith(prefix):
                yield {"key": key}


def _service(manager, configured=True):
    svc = StorageService.__new__(StorageService)
    svc.manager = manager
    svc._configured = configured
    return svc


@pytest.mark.asyncio
async def test_fingerprint_reports_target_and_counts():
    manager = _FakeManager(
        "azure_blob",
        "production",
        "projdatablobstorage",
        ["okh/a.json", "okh/b.json", "okw/x.json", "supply-trees/z.json"],
    )
    fp = await _service(manager).get_config_fingerprint()
    assert fp["provider"] == "azure_blob"
    assert fp["account"] == "projdatablobstorage"
    assert fp["container"] == "production"
    assert fp["okh_count"] == 2  # supply-trees/ excluded
    assert fp["okw_count"] == 1
    assert "error" not in fp


@pytest.mark.asyncio
async def test_fingerprint_never_raises_on_storage_error():
    fp = await _service(
        _FakeManager("azure_blob", "c", "a", [], raises=True)
    ).get_config_fingerprint()
    assert fp["okh_count"] is None and fp["okw_count"] is None
    assert "error" in fp


@pytest.mark.asyncio
async def test_fingerprint_when_unconfigured():
    fp = await _service(None, configured=False).get_config_fingerprint()
    assert fp["provider"] is None
    assert fp["error"] == "storage not configured"
