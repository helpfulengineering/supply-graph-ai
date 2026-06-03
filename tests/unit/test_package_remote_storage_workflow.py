"""
Regression: remote package list / locate / pull key layout (packages/ + legacy okh/packages/).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import pytest

from src.core.packaging.remote_storage import PackageRemoteStorage


def _minimal_build_info(org: str, project: str, version: str) -> bytes:
    payload = {
        "package_name": f"{org}/{project}",
        "version": version,
        "okh_manifest_id": None,
        "build_timestamp": datetime(2020, 1, 1).isoformat(),
        "ohm_version": "0.0.0",
        "total_files": 0,
        "total_size_bytes": 0,
        "build_options": {},
    }
    return json.dumps(payload).encode("utf-8")


class _FakeManager:
    """Minimal async blob manager for PackageRemoteStorage tests."""

    def __init__(self, objects: Dict[str, bytes]):
        self.objects = objects

    async def get_object(self, key: str) -> bytes:
        if key not in self.objects:
            raise FileNotFoundError(key)
        return self.objects[key]

    async def list_objects(
        self, prefix: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        p = prefix or ""
        for key in sorted(self.objects):
            if not key.endswith("/build-info.json"):
                continue
            if p and not key.startswith(p):
                continue
            yield {
                "key": key,
                "size": len(self.objects[key]),
                "last_modified": datetime(2020, 1, 1),
            }


class _FakeStorageService:
    def __init__(self, objects: Dict[str, bytes]):
        self.manager = _FakeManager(objects)


@pytest.mark.asyncio
async def test_locate_remote_package_prefers_new_layout_prefix() -> None:
    objects = {
        "packages/acme/widget/1.0.0/build-info.json": _minimal_build_info(
            "acme", "widget", "1.0.0"
        ),
    }
    remote = PackageRemoteStorage(_FakeStorageService(objects))
    base = await remote._locate_remote_package_base("acme", "widget", "1.0.0")
    assert base == "packages/acme/widget/1.0.0"


@pytest.mark.asyncio
async def test_locate_remote_package_falls_back_to_legacy_prefix() -> None:
    objects = {
        "okh/packages/acme/widget/1.0.0/build-info.json": _minimal_build_info(
            "acme", "widget", "1.0.0"
        ),
    }
    remote = PackageRemoteStorage(_FakeStorageService(objects))
    base = await remote._locate_remote_package_base("acme", "widget", "1.0.0")
    assert base == "okh/packages/acme/widget/1.0.0"


@pytest.mark.asyncio
async def test_list_remote_packages_dedupes_new_and_legacy() -> None:
    bi = _minimal_build_info("acme", "widget", "1.0.0")
    objects = {
        "packages/acme/widget/1.0.0/build-info.json": bi,
        "okh/packages/acme/widget/1.0.0/build-info.json": bi,
    }
    remote = PackageRemoteStorage(_FakeStorageService(objects))
    rows: List[Dict[str, Any]] = await remote.list_remote_packages()
    assert len(rows) == 1
    assert rows[0]["package_name"] == "acme/widget"
    assert rows[0]["version"] == "1.0.0"
