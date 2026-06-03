"""Per-peer rate limiting for federation sync endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import settings

from ..services.rate_limit_service import get_rate_limit_service


@dataclass
class FederationRateLimitInfo:
    allowed: bool
    limit: int
    remaining: int
    reset_time: int


class FederationPeerRateLimiter:
    """Token-bucket style limits keyed by peer DID or client identifier."""

    def __init__(self, requests_per_minute: int | None = None) -> None:
        self.requests_per_minute = (
            requests_per_minute or settings.OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN
        )
        self._service = get_rate_limit_service()

    def check(self, peer_identifier: str) -> FederationRateLimitInfo:
        key = f"federation:peer:{peer_identifier}"
        allowed, info = self._service.check_rate_limit(
            identifier=key,
            requests_per_minute=self.requests_per_minute,
        )
        return FederationRateLimitInfo(
            allowed=allowed,
            limit=info["limit"],
            remaining=info["remaining"],
            reset_time=info["reset_time"],
        )


_limiter: FederationPeerRateLimiter | None = None


def get_federation_rate_limiter() -> FederationPeerRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = FederationPeerRateLimiter()
    return _limiter
