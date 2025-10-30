import asyncio
from pathlib import Path
import os
import sys

# Ensure repository root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.services.scaffold_service import ScaffoldService, ScaffoldOptions
from src.core.services.cleanup_service import CleanupService, CleanupOptions


if __name__ == "__main__":
    import pytest
    import sys as _sys
    _sys.exit(pytest.main([__file__]))


async def _create_scaffold(tmp_path: Path) -> Path:
    svc = ScaffoldService()
    opts = ScaffoldOptions(project_name="Test Project", output_format="filesystem", output_path=str(tmp_path))
    await svc.generate_scaffold(opts)
    project_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    return project_dir


def test_cleanup_removes_unmodified_stubs_and_empty_dirs(tmp_path):
    project_dir = asyncio.get_event_loop().run_until_complete(_create_scaffold(tmp_path))

    # Ensure a stub file exists
    readme = project_dir / "README.md"
    assert readme.exists()
    original_size = readme.stat().st_size

    # Dry run first: nothing should be actually removed
    cleanup = CleanupService()
    res = asyncio.get_event_loop().run_until_complete(
        cleanup.clean(
            CleanupOptions(
                project_path=str(project_dir),
                dry_run=True,
                remove_unmodified_stubs=True,
                remove_empty_directories=True,
            )
        )
    )
    assert readme.exists()
    assert any(str(readme) == p for p in res.removed_files)

    # Real cleanup: README.md should be removed as it is unmodified stub
    res2 = asyncio.get_event_loop().run_until_complete(
        cleanup.clean(
            CleanupOptions(
                project_path=str(project_dir),
                dry_run=False,
                remove_unmodified_stubs=True,
                remove_empty_directories=True,
            )
        )
    )
    assert not readme.exists()
    assert any(str(readme) == p for p in res2.removed_files)
    assert res2.bytes_saved >= original_size


