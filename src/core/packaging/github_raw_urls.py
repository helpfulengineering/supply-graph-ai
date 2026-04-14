"""
Build raw.githubusercontent.com URLs for files stored in GitHub repos.

Historically we assumed branch ``master``. Many repositories use ``main`` (or
other defaults). We resolve the default branch via the unauthenticated GitHub
API (cached per owner/repo) so relative paths in manifests map to real blobs.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def parse_github_owner_repo(repo_url: str) -> Optional[Tuple[str, str]]:
    """
    Parse ``owner`` and ``repo`` from a GitHub browser or git HTTPS URL.

    Accepts:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - http://github.com/owner/repo/tree/main/sub (uses owner/repo only)
    """
    if not repo_url or "github.com" not in repo_url:
        return None
    u = repo_url.strip().rstrip("/")
    u = re.sub(r"\.git$", "", u, flags=re.IGNORECASE)
    if "/github.com/" not in u:
        return None
    tail = u.split("/github.com/", 1)[-1]
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    # Strip query/fragment leftovers
    repo = repo.split("?")[0].split("#")[0]
    if not owner or not repo:
        return None
    return owner, repo


@lru_cache(maxsize=256)
def get_github_default_branch(owner: str, repo: str) -> str:
    """
    Return the repo's default branch (``main``, ``master``, etc.).

    Falls back to ``master`` if the API is unreachable or the repo is missing.
    Unauthenticated limit: 60 requests/hour per IP — cache keeps this low.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "supply-graph-ai-packaging/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)
        branch = data.get("default_branch")
        if isinstance(branch, str) and branch:
            return branch
    except urllib.error.HTTPError as e:
        logger.debug(
            "GitHub API default_branch lookup failed for %s/%s: HTTP %s",
            owner,
            repo,
            e.code,
        )
    except Exception as e:
        logger.debug(
            "GitHub API default_branch lookup failed for %s/%s: %s",
            owner,
            repo,
            e,
        )
    return "master"


def github_raw_file_url(repo_url: str, repo_relative_path: str) -> str:
    """
    Map a repository-relative file path to a raw GitHub URL.

    ``repo_relative_path`` must be relative to the repo root (e.g.
    ``docs/readme.md``), not a URL.
    """
    parsed = parse_github_owner_repo(repo_url)
    if not parsed:
        raise ValueError(f"Not a recognized GitHub repo URL: {repo_url!r}")

    owner, repo = parsed
    branch = get_github_default_branch(owner, repo)
    rel = repo_relative_path.lstrip("/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel}"
