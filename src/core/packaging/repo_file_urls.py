"""
Resolve repository-relative file paths to fetchable raw URLs (GitHub, GitLab).

Used by :class:`PackageBuilder` when manifest ``repo`` points at a host that
serves raw files over HTTP, so relative ``DocumentRef.path`` values work.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urlparse

from .github_raw_urls import (
    github_raw_file_url,
    parse_github_owner_repo,
    quote_github_raw_relative_path,
)

logger = logging.getLogger(__name__)


def _urlopen_https(req: urllib.request.Request, *, timeout: float):
    """Open only HTTPS URLs (packaging metadata lookups)."""
    url = req.full_url
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError(f"Refusing non-HTTPS URL: {url}")
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310


def _is_github_repo(repo_url: str) -> bool:
    return bool(repo_url and "github.com" in repo_url.lower())


def _is_gitlab_repo(repo_url: str) -> bool:
    if not repo_url:
        return False
    try:
        host = urlparse(repo_url.strip()).netloc.lower()
    except Exception:
        return False
    return "gitlab." in host or host == "gitlab.com"


def _resolve_github_raw_url(repo_url: str, repo_relative_path: str) -> str:
    """Default-branch GitHub raw URL with legacy ``/master/`` fallback."""
    try:
        return github_raw_file_url(repo_url, repo_relative_path)
    except (ValueError, OSError) as e:
        logger.debug(
            "GitHub raw URL fallback to master (%s): %s",
            repo_relative_path,
            e,
        )
    ru = repo_url.strip().rstrip("/")
    quoted = quote_github_raw_relative_path(repo_relative_path)
    if "/github.com/" in ru:
        repo_part = ru.split("/github.com/")[-1]
        if repo_part.lower().endswith(".git"):
            repo_part = repo_part[:-4]
        return f"https://raw.githubusercontent.com/{repo_part}/master/{quoted}"
    return f"{ru}/raw/master/{quoted}"


def parse_gitlab_origin_and_project(repo_url: str) -> Optional[Tuple[str, str]]:
    """
    Return ``(origin, project_path)`` for a GitLab project URL.

    ``origin`` is ``scheme://netloc`` (no trailing slash).
    ``project_path`` is ``group/subgroup/project`` without leading slash.
    """
    u = repo_url.strip().rstrip("/")
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return None
    if not _is_gitlab_repo(u):
        return None
    path = p.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if "/-/" in path:
        path = path.split("/-/")[0]
    path = path.lstrip("/")
    if not path:
        return None
    origin = f"{p.scheme}://{p.netloc}"
    return origin, path


@lru_cache(maxsize=256)
def get_gitlab_default_branch(origin: str, project_path: str) -> str:
    """
    Return default branch via GitLab API v4, or ``main`` / ``master`` fallback.
    """
    enc = urllib.parse.quote(project_path, safe="")
    url = f"{origin.rstrip('/')}/api/v4/projects/{enc}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "supply-graph-ai-packaging/1.0",
        },
    )
    try:
        with _urlopen_https(req, timeout=15) as resp:
            data = json.load(resp)
        branch = data.get("default_branch")
        if isinstance(branch, str) and branch.strip():
            return branch.strip()
    except urllib.error.HTTPError as e:
        logger.debug(
            "GitLab default_branch lookup failed for %s/%s: HTTP %s",
            origin,
            project_path,
            e.code,
        )
    except Exception as e:
        logger.debug(
            "GitLab default_branch lookup failed for %s/%s: %s",
            origin,
            project_path,
            e,
        )
    return "main"


def gitlab_raw_file_url(repo_url: str, repo_relative_path: str) -> str:
    """Map a repository-relative path to a GitLab ``/-/raw/{branch}/...`` URL."""
    parsed = parse_gitlab_origin_and_project(repo_url)
    if not parsed:
        raise ValueError(f"Not a recognized GitLab repo URL: {repo_url!r}")

    origin, project_path = parsed
    branch = get_gitlab_default_branch(origin, project_path)
    rel = repo_relative_path.lstrip("/")
    parts = [p for p in rel.split("/") if p != ""]
    quoted_rel = "/".join(urllib.parse.quote(p, safe="") for p in parts)

    base = f"{origin.rstrip('/')}/{project_path}/-/raw/{branch}"
    return f"{base}/{quoted_rel}" if quoted_rel else base


def resolve_repo_relative_file_url(
    repo_url: Optional[str], repo_relative_path: str
) -> str:
    """
    If ``repo_relative_path`` is not already absolute HTTP(S) and ``repo_url``
    is a known forge, return a raw file URL; otherwise return ``repo_relative_path``.
    """
    if not repo_relative_path:
        return repo_relative_path
    if repo_relative_path.startswith(("http://", "https://")):
        return repo_relative_path
    if not repo_url:
        return repo_relative_path
    if _is_github_repo(repo_url):
        try:
            return _resolve_github_raw_url(repo_url, repo_relative_path)
        except Exception as e:
            logger.warning("Could not build GitHub raw URL: %s", e)
            return repo_relative_path
    if _is_gitlab_repo(repo_url):
        try:
            return gitlab_raw_file_url(repo_url, repo_relative_path)
        except Exception as e:
            logger.warning("Could not build GitLab raw URL: %s", e)
            return repo_relative_path
    return repo_relative_path


__all__ = [
    "resolve_repo_relative_file_url",
    "gitlab_raw_file_url",
    "parse_gitlab_origin_and_project",
]
