"""
Rate limiting service for API endpoints.

Provides sliding window rate limiting with per-IP and per-user support.
"""

import time
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitService:
    """
    Rate limiting service using sliding window algorithm.

    Thread-safe rate limiting suitable for single-instance deployments.
    For multi-instance deployments, use Redis-based rate limiting (Phase 2).
    """

    def __init__(self, cleanup_interval_seconds: int = 60):
        """
        Initialize rate limit service.

        Args:
            cleanup_interval_seconds: How often to clean old request timestamps
        """
        self.cleanup_interval = cleanup_interval_seconds
        # Store request timestamps per identifier (IP or user ID)
        self._request_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = time.time()

    def check_rate_limit(
        self,
        identifier: str,
        requests_per_minute: int,
        current_time: Optional[float] = None,
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (IP address or user ID)
            requests_per_minute: Maximum requests per minute
            current_time: Current timestamp (for testing)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains: limit, remaining, reset_time
        """
        if current_time is None:
            current_time = time.time()

        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed(current_time)

            # Get request timestamps for this identifier
            timestamps = self._request_timestamps[identifier]

            # Remove timestamps older than 1 minute
            cutoff_time = current_time - 60.0
            timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]

            # Check if limit exceeded
            request_count = len(timestamps)
            is_allowed = request_count < requests_per_minute

            # Calculate reset time (1 minute from oldest request, or now if no requests)
            if timestamps:
                oldest_request = min(timestamps)
                reset_time = int(oldest_request + 60.0)
            else:
                reset_time = int(current_time + 60.0)

            # If allowed, add current request timestamp
            if is_allowed:
                timestamps.append(current_time)

            rate_limit_info = {
                "limit": requests_per_minute,
                "remaining": max(
                    0, requests_per_minute - request_count - (1 if is_allowed else 0)
                ),
                "reset_time": reset_time,
            }

            return is_allowed, rate_limit_info

    def _cleanup_if_needed(self, current_time: float) -> None:
        """Clean up old request timestamps if cleanup interval has passed"""
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        # Remove timestamps older than 1 minute for all identifiers
        cutoff_time = current_time - 60.0
        identifiers_to_remove = []

        for identifier, timestamps in self._request_timestamps.items():
            # Remove old timestamps
            self._request_timestamps[identifier] = [
                ts for ts in timestamps if ts > cutoff_time
            ]

            # Remove identifier if no timestamps left
            if not self._request_timestamps[identifier]:
                identifiers_to_remove.append(identifier)

        for identifier in identifiers_to_remove:
            del self._request_timestamps[identifier]

        self._last_cleanup = current_time

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 60.0

            active_identifiers = {}
            for identifier, timestamps in self._request_timestamps.items():
                recent_timestamps = [ts for ts in timestamps if ts > cutoff_time]
                if recent_timestamps:
                    active_identifiers[identifier] = len(recent_timestamps)

            return {
                "active_identifiers": len(active_identifiers),
                "total_identifiers": len(self._request_timestamps),
                "identifier_counts": active_identifiers,
            }


# Global rate limit service instance
_rate_limit_service: Optional[RateLimitService] = None


def get_rate_limit_service() -> RateLimitService:
    """Get global rate limit service instance"""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service
