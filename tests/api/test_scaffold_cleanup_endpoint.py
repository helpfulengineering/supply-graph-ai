import asyncio
from pathlib import Path
import os
import sys

import pytest
import httpx

# Ensure repository root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.services.scaffold_service import ScaffoldService, ScaffoldOptions


if __name__ == "__main__":
    import pytest
    import sys as _sys
    _sys.exit(pytest.main([__file__]))


def _get_app():
    # Lazy import to avoid heavy app import in test collection
    from src.core.main import app as fastapi_app
    return fastapi_app


async def _create_scaffold(tmp_path: Path) -> Path:
    svc = ScaffoldService()
    opts = ScaffoldOptions(
        project_name="Cleanup API Test Project",
        output_format="filesystem",
        output_path=str(tmp_path),
    )
    await svc.generate_scaffold(opts)
    project_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    return project_dir


@pytest.mark.asyncio
async def test_cleanup_endpoint_dry_run_and_apply(tmp_path):
    project_dir = await _create_scaffold(tmp_path)

    transport = httpx.ASGITransport(app=_get_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Dry run
        resp = await client.post(
            "/v1/api/okh/scaffold/cleanup",
            json={
                "project_path": str(project_dir),
                "dry_run": True,
                "remove_unmodified_stubs": True,
                "remove_empty_directories": True,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"
        assert isinstance(data.get("removed_files", []), list)
        assert isinstance(data.get("removed_directories", []), list)
        # README.md should be slated for removal in dry-run
        assert any(Path(p).name == "README.md" for p in data.get("removed_files", []))

        # Apply
        resp2 = await client.post(
            "/v1/api/okh/scaffold/cleanup",
            json={
                "project_path": str(project_dir),
                "dry_run": False,
                "remove_unmodified_stubs": True,
                "remove_empty_directories": True,
            },
        )
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json()
        assert data2["status"] == "success"
        assert any(Path(p).name == "README.md" for p in data2.get("removed_files", []))
        # README.md actually removed
        assert not (project_dir / "README.md").exists()


@pytest.mark.asyncio
async def test_cleanup_endpoint_invalid_path_returns_500(tmp_path):
    transport = httpx.ASGITransport(app=_get_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/v1/api/okh/scaffold/cleanup",
            json={
                "project_path": str(tmp_path / "does-not-exist"),
                "dry_run": True,
            },
        )
        # Service returns success with warnings when path missing; verify robustness
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"
        assert any("not found" in w.lower() for w in data.get("warnings", []))


