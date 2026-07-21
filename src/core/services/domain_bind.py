"""Fetch and validate ``.well-known/ohm-did.json`` for domain bindings."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx

from ..models.binding import well_known_url

# (url) -> response body dict. Injected in tests to avoid live HTTP.
WellKnownFetcher = Callable[[str], Awaitable[Dict[str, Any]]]


async def default_fetch_well_known(url: str) -> Dict[str, Any]:
    """HTTPS GET of a well-known document (online path)."""
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def validate_well_known_document(
    doc: Dict[str, Any],
    *,
    expected_did: str,
    expected_challenge: str,
) -> Optional[str]:
    """Return None if valid, else a short error reason."""
    if not isinstance(doc, dict):
        return "well-known document is not a JSON object"
    if doc.get("did") != expected_did:
        return "did mismatch"
    if doc.get("challenge") != expected_challenge:
        return "challenge mismatch"
    return None


async def fetch_and_validate_domain(
    domain: str,
    *,
    expected_did: str,
    expected_challenge: str,
    fetcher: Optional[WellKnownFetcher] = None,
) -> None:
    """Fetch ``.well-known/ohm-did.json`` and validate DID + challenge.

    Raises ``ValueError`` with a reason on failure.
    """
    url = well_known_url(domain)
    fetch = fetcher or default_fetch_well_known
    try:
        doc = await fetch(url)
    except Exception as exc:
        raise ValueError(f"failed to fetch {url}: {exc}") from exc

    if isinstance(doc, (bytes, str)):
        try:
            doc = json.loads(doc)
        except Exception as exc:
            raise ValueError("well-known body is not JSON") from exc

    reason = validate_well_known_document(
        doc, expected_did=expected_did, expected_challenge=expected_challenge
    )
    if reason:
        raise ValueError(reason)
