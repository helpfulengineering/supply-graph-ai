import asyncio
import json
from pathlib import Path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from click.testing import CliRunner

from src.cli.okh import okh_group

from src.core.services.scaffold_service import ScaffoldService, ScaffoldOptions


async def _create_scaffold(tmp_path: Path) -> Path:
    svc = ScaffoldService()
    opts = ScaffoldOptions(
        project_name="Cleanup CLI Test Project",
        output_format="filesystem",
        output_path=str(tmp_path),
    )
    await svc.generate_scaffold(opts)
    project_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    return project_dir


def test_scaffold_cleanup_cli_dry_run_and_apply(tmp_path, monkeypatch):
    project_dir = asyncio.get_event_loop().run_until_complete(_create_scaffold(tmp_path))

    # Patch API client used by CLI to avoid real HTTP; emulate server response
    class DummyApiClient:
        def __init__(self):
            pass

        async def request(self, method: str, endpoint: str, json_data: dict):
            # Simulate a dry-run with README.md slated for removal
            dry_run = json_data.get("dry_run", True)
            removed_files = [str(Path(json_data["project_path"]) / "README.md")]
            if not dry_run:
                # Remove the file to emulate server side effect
                readme = Path(json_data["project_path"]) / "README.md"
                if readme.exists():
                    readme.unlink()
            return {
                "status": "success",
                "removed_files": removed_files,
                "removed_directories": [],
                "bytes_saved": 10 if not dry_run else 0,
                "warnings": [],
            }

    # Build CLI context fixture shim
    class DummyCLIContext:
        def __init__(self):
            self.output_format = 'text'
            self.verbose = False
            self.api_client = DummyApiClient()

        def start_command_tracking(self, *_args, **_kwargs):
            pass

        def end_command_tracking(self):
            pass

        def log(self, *_args, **_kwargs):
            pass

    # Inject Dummy CLI context
    def get_dummy_context():
        return DummyCLIContext()

    runner = CliRunner()

    # Provide context object via CliRunner.invoke
    result = runner.invoke(
        okh_group,
        [
            'scaffold-cleanup',
            str(project_dir),
        ],
        obj=get_dummy_context(),
    )
    assert result.exit_code == 0, result.output
    assert "Files to remove" in result.output or "Files removed" in result.output

    # Apply
    result2 = runner.invoke(
        okh_group,
        [
            'scaffold-cleanup',
            str(project_dir),
            '--apply',
        ],
        obj=get_dummy_context(),
    )
    assert result2.exit_code == 0, result2.output
    assert not (project_dir / 'README.md').exists()



if __name__ == "__main__":
    import pytest
    import sys as _sys
    _sys.exit(pytest.main([__file__]))
