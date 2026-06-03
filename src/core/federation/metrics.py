"""In-memory federation sync metrics (single-instance MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock


@dataclass
class FederationSyncMetrics:
    total_records_pulled: int = 0
    total_records_skipped: int = 0
    total_sync_runs: int = 0
    total_digest_requests_inbound: int = 0
    total_digest_requests_outbound: int = 0
    total_rate_limit_rejections: int = 0
    last_sync_at: datetime | None = None
    last_background_sync_at: datetime | None = None
    per_peer_pulled: dict[str, int] = field(default_factory=dict)


class FederationMetricsCollector:
    """Thread-safe counters for federation operations."""

    def __init__(self) -> None:
        self._metrics = FederationSyncMetrics()
        self._lock = Lock()

    @property
    def snapshot(self) -> FederationSyncMetrics:
        with self._lock:
            return FederationSyncMetrics(
                total_records_pulled=self._metrics.total_records_pulled,
                total_records_skipped=self._metrics.total_records_skipped,
                total_sync_runs=self._metrics.total_sync_runs,
                total_digest_requests_inbound=self._metrics.total_digest_requests_inbound,
                total_digest_requests_outbound=self._metrics.total_digest_requests_outbound,
                total_rate_limit_rejections=self._metrics.total_rate_limit_rejections,
                last_sync_at=self._metrics.last_sync_at,
                last_background_sync_at=self._metrics.last_background_sync_at,
                per_peer_pulled=dict(self._metrics.per_peer_pulled),
            )

    def record_sync_run(
        self,
        *,
        peer_did: str,
        pulled: int,
        skipped: int,
        background: bool = False,
        when: datetime,
    ) -> None:
        with self._lock:
            self._metrics.total_sync_runs += 1
            self._metrics.total_records_pulled += pulled
            self._metrics.total_records_skipped += skipped
            self._metrics.last_sync_at = when
            if background:
                self._metrics.last_background_sync_at = when
            if pulled:
                self._metrics.per_peer_pulled[peer_did] = (
                    self._metrics.per_peer_pulled.get(peer_did, 0) + pulled
                )

    def record_inbound_digest(self) -> None:
        with self._lock:
            self._metrics.total_digest_requests_inbound += 1

    def record_outbound_digest(self) -> None:
        with self._lock:
            self._metrics.total_digest_requests_outbound += 1

    def record_rate_limit_rejection(self) -> None:
        with self._lock:
            self._metrics.total_rate_limit_rejections += 1
