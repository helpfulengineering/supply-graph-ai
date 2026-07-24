"""Probe remote download URLs for a real filename (Content-Disposition / redirect)."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Optional
from urllib.parse import unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

# Browser-like UA: some CDNs (Thingiverse/Cloudflare) block default httpx HEAD.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

_CD_FILENAME = re.compile(
    r"""filename\*\s*=\s*(?:UTF-8''|utf-8'')([^;]+)|filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;\s]+)""",
    re.IGNORECASE,
)


def filename_from_content_disposition(header: str) -> Optional[str]:
    if not header:
        return None
    match = _CD_FILENAME.search(header)
    if not match:
        return None
    raw = next((g for g in match.groups() if g), None)
    if not raw:
        return None
    name = unquote(raw.strip().strip("'"))
    return name or None


def filename_from_url_path(url: str) -> Optional[str]:
    path = urlparse(url).path or ""
    name = unquote(path.rstrip("/").split("/")[-1] if path else "")
    if not name or "." not in name:
        return None
    # Ignore opaque download tokens like "download:7851122"
    if ":" in name.split(".")[0]:
        return None
    return name


def clear_remote_filename_cache() -> None:
    probe_remote_filename.cache_clear()


def _filename_from_response(response: httpx.Response) -> Optional[str]:
    from_cd = filename_from_content_disposition(
        response.headers.get("content-disposition", "")
    )
    if from_cd:
        return from_cd
    location = response.headers.get("location")
    if location:
        from_loc = filename_from_url_path(location)
        if from_loc:
            return from_loc
    return filename_from_url_path(str(response.url))


@lru_cache(maxsize=256)
def probe_remote_filename(url: str, timeout: float = 4.0) -> Optional[str]:
    """
    Return a filename hint for classification without downloading bodies.

    Prefer a single non-following GET so redirect ``Location`` headers (e.g.
    Thingiverse → CDN ``.stl``) yield the name. Fail-soft on network errors.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    headers = {**_BROWSER_HEADERS, "Referer": url}
    try:
        with httpx.Client(
            follow_redirects=False, timeout=timeout, headers=headers
        ) as client:
            # GET not HEAD: several hosts 403 HEAD but 302 GET with Location.
            response = client.get(url)
            name = _filename_from_response(response)
            if name:
                return name

        # Rare: no redirect filename — follow once and read CD / final URL.
        with httpx.Client(
            follow_redirects=True, timeout=timeout, headers=headers
        ) as client:
            response = client.get(url)
            return _filename_from_response(response)
    except Exception as exc:  # noqa: BLE001 — enrich path must never fail hard
        logger.debug("remote filename probe failed for %s: %s", url, exc)
        return None
