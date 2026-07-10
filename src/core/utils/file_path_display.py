"""Normalize OKH file paths for display, sorting, and directory grouping."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

ROOT_DIRECTORY_LABEL = "(root)"

# github.com/org/repo/raw/branch/path or blob/branch/path
_GITHUB_HOSTED = re.compile(
    r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+/(?:raw|blob)/[^/]+/(?P<path>.+)$",
    re.IGNORECASE,
)
# raw.githubusercontent.com/org/repo/branch/path
_GITHUB_RAW = re.compile(
    r"^https?://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(?P<path>.+)$",
    re.IGNORECASE,
)
# gitlab.com/org/repo/-/raw/branch/path or blob/branch/path
_GITLAB_HOSTED = re.compile(
    r"^https?://[^/]+/[^/]+/[^/]+/-/raw/[^/]+/(?P<path>.+)$",
    re.IGNORECASE,
)
_GITLAB_BLOB = re.compile(
    r"^https?://[^/]+/[^/]+/[^/]+/-/blob/[^/]+/(?P<path>.+)$",
    re.IGNORECASE,
)


def _reject_traversal(path: str) -> str:
    parts = PurePosixPath(path).parts
    if ".." in parts:
        raise ValueError("invalid file path")
    return path


def normalize_display_path(path: str) -> str:
    """Return a repo-relative posix path suitable for display and sorting."""
    raw = (path or "").strip().replace("\\", "/")
    if not raw:
        return ""

    for pattern in (_GITHUB_HOSTED, _GITHUB_RAW, _GITLAB_HOSTED, _GITLAB_BLOB):
        match = pattern.match(raw)
        if match:
            rel = match.group("path").lstrip("/")
            return _reject_traversal(rel)

    if raw.startswith(("http://", "https://")):
        # Unknown URL host — use path after last meaningful segment
        without_query = raw.split("?", 1)[0]
        return _reject_traversal(without_query.rstrip("/").split("/")[-1])

    return _reject_traversal(raw.lstrip("/"))


def file_basename(display_path: str) -> str:
    """Last path segment of a display path."""
    if not display_path:
        return ""
    return PurePosixPath(display_path).name


def file_directory(display_path: str) -> str:
    """Parent directory of a display path, or ROOT_DIRECTORY_LABEL."""
    if not display_path:
        return ROOT_DIRECTORY_LABEL
    parent = str(PurePosixPath(display_path).parent)
    if parent in (".", ""):
        return ROOT_DIRECTORY_LABEL
    return parent


def enrich_path_fields(path: str) -> dict[str, str]:
    """Build display_path and directory from a manifest file path."""
    display_path = normalize_display_path(path)
    return {
        "display_path": display_path,
        "directory": file_directory(display_path),
        "basename": file_basename(display_path),
    }
