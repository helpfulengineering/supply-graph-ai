"""Unit tests for federation per-peer rate limiting."""

from __future__ import annotations

import pytest

from src.core.federation.rate_limit import FederationPeerRateLimiter


@pytest.mark.unit
def test_rate_limiter_allows_under_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.core.federation.rate_limit.settings.OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN",
        5,
    )
    limiter = FederationPeerRateLimiter(requests_per_minute=5)
    for _ in range(5):
        info = limiter.check("did:key:z6Mktest")
        assert info.allowed is True


@pytest.mark.unit
def test_rate_limiter_blocks_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.core.federation.rate_limit.settings.OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN",
        2,
    )
    limiter = FederationPeerRateLimiter(requests_per_minute=2)
    assert limiter.check("did:key:z6Mkpeer").allowed is True
    assert limiter.check("did:key:z6Mkpeer").allowed is True
    blocked = limiter.check("did:key:z6Mkpeer")
    assert blocked.allowed is False
    assert limiter.check("did:key:z6Mkother").allowed is True
