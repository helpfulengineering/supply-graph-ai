"""RED loop — Rate / Errors / Duration over API endpoints.

Wraps the existing ``MetricsTracker`` / utility metrics surface. Stub until
observe() fetches live metrics and judge() applies configured thresholds.
"""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.protocol import Inventory, LoopStatus, Observations


class RedLoop(BaseLoopModule):
    name = "red"
    status = LoopStatus.STUB

    def discover(self) -> Inventory:
        opts = self.module_config.options
        return Inventory(
            items={
                "metrics_path": opts.get("metrics_path", "/v1/api/utility/metrics"),
                "thresholds": {
                    "error_rate_warn": opts.get("error_rate_warn", 0.05),
                    "p95_ms_warn": opts.get("p95_ms_warn", 2000),
                },
                "api_base_url": self.config.api_base_url,
            },
            notes=[
                "RED signals already collected by RequestTrackingMiddleware + MetricsTracker",
                "This loop will scrape and judge them once online",
            ],
        )

    def observe(self) -> Observations:
        return Observations(
            data={"phase": "stub"},
            notes=[
                "RED observe is a stub. Next: GET metrics from the running API "
                "and normalize per-endpoint rate / error class / duration."
            ],
        )
