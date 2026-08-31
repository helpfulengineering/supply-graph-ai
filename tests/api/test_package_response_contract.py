"""The package routes must return a dict, and keep the shape they return (#373).

Two things at once, because the first had to be fixed before the second was
possible.

**The bug.** Six routes here returned the ``SuccessResponse`` object from
``create_success_response`` while declaring ``response_model=Dict[str, Any]``.
FastAPI validates the returned value against that model, a model instance is
not a dict, so every one of them answered 500 — after computing the whole
payload. It is the same defect as #439 in ``POST /api/match``, and two routes
in this very file (``/build/{manifest_id}`` and ``/remote``) already called
``.model_dump(mode="json")`` for exactly this reason, with a test named for it
(``test_package_build_response.py``). The fix was never applied to the rest.

Three of the six are called by the UI: the package detail page, pin, and
verify-pin.

**The shapes.** Goldens are captured here so the response models added in the
same change can be shown to filter nothing. Capturing them was impossible
while the routes 500'd, which is why the fix and the models travel together.

The service is mocked, as everywhere else in this file's neighbours: building a
real package downloads files. What is under test is the route's own
serialisation, which is what a ``response_model`` acts on.

    BLESS_PACKAGE=1 .venv/bin/python -m pytest \
        tests/api/test_package_response_contract.py
"""

from __future__ import annotations

import hashlib
import json
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

from src.core.models.package import (
    BuildOptions,
    FileInfo,
    PackageMetadata,
)  # noqa: E402
from tests.contract_shape import assert_shape  # noqa: E402

BLESS = "BLESS_PACKAGE"
ENVELOPE_KEYS = {"status", "message", "timestamp", "request_id", "data", "metadata"}


def _metadata(package_path: Path) -> PackageMetadata:
    readme = package_path / "README.md"
    readme.write_text("package contract\n", encoding="utf-8")
    file_info = FileInfo(
        original_url="file://README.md",
        local_path="README.md",
        content_type="text/plain",
        size_bytes=readme.stat().st_size,
        checksum_sha256=hashlib.sha256(readme.read_bytes()).hexdigest(),
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


@pytest.fixture
def packaged(tmp_path):
    """A built-looking package on disk, plus a client whose service returns it.

    The on-disk layout is real because pin and signature verification read it:
    ``create_pin_record`` needs ``okh-manifest.json`` and
    ``metadata/file-manifest.json``, and signing writes a record next to them.
    Without those, verify-pin and verify-signature answer 404 and never reach
    the success path where the bug lived — which is how the 500 stayed hidden
    in a suite that already had package tests.
    """
    from src.core.api.routes.package import get_package_service, get_remote_storage
    from src.core.federation.identity import generate_identity
    from src.core.main import api_v1
    from src.core.packaging.pin import create_pin_record
    from src.core.packaging.signing import sign_package
    from src.core.services.package_service import PackageService

    package_path = tmp_path / "packages" / "test-org" / "test-project" / "1.0.0"
    package_path.mkdir(parents=True)
    metadata = _metadata(package_path)

    (package_path / "okh-manifest.json").write_text(
        json.dumps({"title": "contract"}), encoding="utf-8"
    )
    (package_path / "metadata").mkdir()
    (package_path / "metadata" / "file-manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "local_path": "README.md",
                        "checksum_sha256": metadata.file_inventory[0].checksum_sha256,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    create_pin_record(package_path, pinned_by="contract", note=None)
    sign_package(package_path, generate_identity("contract"))

    # A populated remote listing. An empty one would freeze `packages: []`,
    # which says nothing about the item shape a client actually reads — the
    # vacuous golden this whole procedure exists to avoid.
    remote = MagicMock()
    remote.list_remote_packages = AsyncMock(
        return_value=[
            {
                "package_name": "test-org/test-project",
                "version": "1.0.0",
                "org": "test-org",
                "project": "test-project",
                "last_modified": datetime.now(UTC).isoformat(),
                "size": 2048,
            }
        ]
    )

    service = MagicMock()
    service.get_package_metadata = AsyncMock(return_value=metadata)
    # Delegate to the real implementation rather than inventing a return. A
    # hand-written stub here froze `{valid, errors, checked_files}` into the
    # golden — a shape the service has never produced — and the model derived
    # from it would have filtered every field the route actually returns.
    # `_verify_package_integrity` reads only `metadata`, never `self`.
    service.verify_package = AsyncMock(
        return_value=PackageService._verify_package_integrity(None, metadata)
    )
    service.delete_package = AsyncMock(return_value=True)
    service.build_package_from_storage = AsyncMock(return_value=metadata)

    app = FastAPI()
    app.mount("/v1", api_v1)
    api_v1.dependency_overrides[get_package_service] = lambda: service
    api_v1.dependency_overrides[get_remote_storage] = lambda: remote
    try:
        yield app, metadata
    finally:
        api_v1.dependency_overrides.clear()


async def _get(app, path: str, method: str = "GET"):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        return await client.request(method, path)


BASE = "/v1/api/package/test-org/test-project/1.0.0"

# (label, path, method, golden) — the six that returned 500.
ROUTES = [
    ("metadata", BASE, "GET", "package_metadata"),
    ("verify", f"{BASE}/verify", "GET", "package_verify"),
    ("pin", f"{BASE}/pin", "POST", "package_pin"),
    ("verify-pin", f"{BASE}/verify-pin", "GET", "package_verify_pin"),
    ("verify-signature", f"{BASE}/verify-signature", "GET", "package_verify_signature"),
    ("delete", BASE, "DELETE", "package_delete"),
]


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("label,path,method,golden", ROUTES)
async def test_route_returns_an_envelope_not_a_model(
    packaged, label, path, method, golden
):
    """The regression: each of these answered 500 for every caller."""
    app, _ = packaged
    response = await _get(app, path, method)

    assert response.status_code == 200, f"{label}: {response.text[:400]}"
    body = response.json()
    assert ENVELOPE_KEYS <= set(body), (
        f"{label} lost the envelope; returning the model object is what caused "
        "the 500 this test exists for"
    )
    assert body["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("label,path,method,golden", ROUTES)
async def test_route_shape_is_frozen(packaged, label, path, method, golden):
    """Freeze the payload so the response models can be shown to filter nothing."""
    app, _ = packaged
    response = await _get(app, path, method)
    assert response.status_code == 200, f"{label}: {response.text[:400]}"
    assert_shape(response.json(), golden, BLESS)


# One route per test, deliberately: `assert_shape` skips the test when
# re-blessing, so a second call in the same test would never run and its golden
# would silently never be captured.


@pytest.mark.asyncio
@pytest.mark.contract
async def test_build_shape_is_frozen(packaged):
    """Already returned a dict, but still needs a model — and so a golden."""
    app, metadata = packaged
    build = await _get(app, f"/v1/api/package/build/{metadata.okh_manifest_id}", "POST")
    assert build.status_code == 201, build.text
    assert_shape(build.json(), "package_build", BLESS)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_remote_shape_is_frozen(packaged):
    """The other route that already returned a dict."""
    app, _ = packaged
    response = await _get(app, "/v1/api/package/remote")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["packages"], "empty listing freezes no item shape"
    assert_shape(response.json(), "package_remote", BLESS)
