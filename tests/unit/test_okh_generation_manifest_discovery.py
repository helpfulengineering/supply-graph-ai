"""Unit tests for OKH generation manifest discovery helpers."""

from __future__ import annotations

import json
from pathlib import Path

from tests.data.okh_generation.manifest_discovery import (
    allocate_unique_slug,
    canonical_repo_url,
    find_generated_manifest_path,
    title_slug_for_filename,
)


def test_canonical_repo_url_strips_git_and_slash() -> None:
    assert (
        canonical_repo_url("https://GitHub.com/Org/Repo.git/")
        == "https://github.com/Org/Repo"
    )


def test_title_slug_and_fallback() -> None:
    assert (
        title_slug_for_filename("Open Source Rover!", "repo-001") == "open-source-rover"
    )
    assert title_slug_for_filename("  ", "repo-001") == "repo-001"


def test_allocate_unique_slug() -> None:
    used: set[str] = set()
    assert allocate_unique_slug("rover", used) == "rover"
    assert allocate_unique_slug("rover", used) == "rover-2"
    assert allocate_unique_slug("rover", used) == "rover-3"


def test_find_generated_manifest_path_legacy_and_repo_url(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "repo-001-4L.json"
    legacy.write_text(
        json.dumps(
            {
                "title": "Legacy",
                "repo": "https://github.com/nasa-jpl/open-source-rover",
            }
        ),
        encoding="utf-8",
    )
    found = find_generated_manifest_path(
        tmp_path,
        "4L",
        "https://github.com/nasa-jpl/open-source-rover.git",
        dataset_id="repo-001",
    )
    assert found == legacy

    titled = tmp_path / "jpl-open-source-rover-project-4L.json"
    titled.write_text(
        json.dumps(
            {
                "title": "JPL Open Source Rover Project",
                "repo": "https://github.com/nasa-jpl/open-source-rover",
            }
        ),
        encoding="utf-8",
    )
    # Prefer legacy when both exist
    assert (
        find_generated_manifest_path(
            tmp_path,
            "4L",
            "https://github.com/nasa-jpl/open-source-rover",
            dataset_id="repo-001",
        )
        == legacy
    )

    legacy.unlink()
    found2 = find_generated_manifest_path(
        tmp_path,
        "4L",
        "https://github.com/nasa-jpl/open-source-rover",
        dataset_id="repo-001",
    )
    assert found2 == titled
