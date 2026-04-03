"""
Self-hosted GitLab instance detection and API base URL helpers.

Hosts are trusted as GitLab only when listed in GITLAB_SELF_HOSTED_HOSTS (comma-separated)
or when using gitlab.com (handled separately in URLRouter regexes).
"""

from __future__ import annotations

import os
from typing import Tuple
from urllib.parse import urlparse


def normalize_http_url(url: str) -> str:
    """Match URLRouter-style normalization without importing URLRouter (avoid cycles)."""
    if not url:
        return ""
    u = url.strip()
    if u.endswith(".git"):
        u = u[:-4]
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    elif u.startswith("http://"):
        u = "https://" + u[7:]
    return u


def parse_self_hosted_gitlab_hosts() -> frozenset[str]:
    """Read allowlist from env each time so tests can monkeypatch GITLAB_SELF_HOSTED_HOSTS."""
    raw = os.environ.get("GITLAB_SELF_HOSTED_HOSTS", "")
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def gitlab_path_has_namespace_and_project(path: str) -> bool:
    segments = [s for s in path.strip("/").split("/") if s]
    return len(segments) >= 2


def is_allowlisted_self_hosted_gitlab_url(normalized_url: str) -> bool:
    """True if hostname is in GITLAB_SELF_HOSTED_HOSTS and path looks like a project."""
    parsed = urlparse(normalized_url)
    host = (parsed.hostname or "").lower()
    if not host or host == "gitlab.com":
        return False
    if host not in parse_self_hosted_gitlab_hosts():
        return False
    return gitlab_path_has_namespace_and_project(parsed.path)


def is_gitlab_http_clone_url(normalized_url: str) -> bool:
    """True for gitlab.com or allowlisted host with a valid project path (clone/API eligibility)."""
    parsed = urlparse(normalized_url)
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if not gitlab_path_has_namespace_and_project(parsed.path):
        return False
    if host == "gitlab.com":
        return True
    return host in parse_self_hosted_gitlab_hosts()


def extract_gitlab_owner_repo_from_path(path: str) -> Tuple[str, str]:
    """
    Map URL path to GitLab API (owner, repo) pair used with urllib.parse.quote(f'{owner}/{repo}').

    - /group/project -> group, project
    - /a/b/c -> a/b, c (nested namespace)
    """
    clean = path.strip("/")
    if clean.endswith(".git"):
        clean = clean[: -len(".git")]
    segments = [s for s in clean.split("/") if s]
    if len(segments) < 2:
        raise ValueError("GitLab project path must have at least namespace and project")
    if len(segments) == 2:
        return segments[0], segments[1]
    return "/".join(segments[:-1]), segments[-1]


def gitlab_api_v4_base_url(url: str) -> str:
    """https://{host}/api/v4 for the given repository web URL."""
    parsed = urlparse(normalize_http_url(url))
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Cannot derive GitLab API base from URL: {url!r}")
    return f"{parsed.scheme}://{parsed.netloc}/api/v4"
