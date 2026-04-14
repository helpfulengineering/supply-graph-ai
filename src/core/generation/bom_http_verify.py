"""
Optional HTTP checks that GitHub ``raw.githubusercontent.com`` URLs for BOM
candidates return something other than 404.

Used when :attr:`LayerConfig.verify_bom_github_raw` is enabled (e.g. ``generate-from-url``).
Non-404 failures (rate limits, timeouts) keep the path so generation stays conservative.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Tuple, Any

import aiohttp

from src.core.packaging.github_raw_urls import github_raw_file_url

logger = logging.getLogger(__name__)


async def _blob_likely_missing(
    session: aiohttp.ClientSession, url: str, *, timeout: aiohttp.ClientTimeout
) -> bool:
    """
    Return True only when the URL clearly does not exist (HTTP 404).

    On ambiguous errors or non-404 client failures, return False (treat as present).
    """
    try:
        async with session.head(url, allow_redirects=True, timeout=timeout) as resp:
            if resp.status == 404:
                return True
            if resp.status == 405:
                async with session.get(
                    url,
                    allow_redirects=True,
                    timeout=timeout,
                    headers={"Range": "bytes=0-0"},
                ) as g:
                    if g.status == 404:
                        return True
                return False
            return False
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.debug("BOM raw URL probe failed for %s: %s", url, e)
        return False


async def verify_github_raw_bom_paths(
    repo_url: str,
    candidate_paths: List[str],
    *,
    timeout_seconds: float = 12.0,
    max_concurrent: int = 4,
) -> Tuple[frozenset[str], Dict[str, Any]]:
    """
    Probe each repo-relative path on ``raw.githubusercontent.com`` for the repo.

    Returns:
        ``(kept_paths, summary_dict)`` where ``kept_paths`` is a subset of
        ``candidate_paths`` that were not confidently 404.
    """
    if not candidate_paths:
        return frozenset(), {
            "applied": True,
            "candidates_checked": 0,
            "paths_confirmed_missing": [],
            "paths_kept": 0,
        }

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    connector = aiohttp.TCPConnector(limit=max_concurrent, force_close=True)
    sem = asyncio.Semaphore(max_concurrent)
    missing: List[str] = []

    async def check_one(session: aiohttp.ClientSession, rel: str) -> str | None:
        try:
            raw_url = github_raw_file_url(repo_url, rel)
        except Exception as e:
            logger.debug("Could not build raw URL for %r: %s", rel, e)
            return None
        async with sem:
            if await _blob_likely_missing(session, raw_url, timeout=timeout):
                return rel
        return None

    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": "supply-graph-ai-generation/1.0"},
    ) as session:
        tasks = [check_one(session, p) for p in candidate_paths]
        results = await asyncio.gather(*tasks)

    for rel, hit in zip(candidate_paths, results):
        if hit:
            missing.append(hit)

    missing_set = set(missing)
    kept = frozenset(p for p in candidate_paths if p not in missing_set)
    summary: Dict[str, Any] = {
        "applied": True,
        "candidates_checked": len(candidate_paths),
        "paths_confirmed_missing": sorted(missing_set),
        "paths_kept": len(kept),
    }
    if missing_set:
        logger.info(
            "BOM GitHub raw HTTP verification dropped %s path(s): %s",
            len(missing_set),
            sorted(missing_set),
        )
    return kept, summary
