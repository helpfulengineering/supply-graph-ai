"""Synthetic smoke loop — scheduled / CLI-driven UI journey walks.

Wraps the existing Playwright real-api lane. Stub until observe() invokes
journeys and judge() maps failures to Findings.
"""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.protocol import Inventory, LoopStatus, Observations


class SyntheticSmokeLoop(BaseLoopModule):
    name = "synthetic_smoke"
    status = LoopStatus.STUB

    def discover(self) -> Inventory:
        opts = self.module_config.options
        return Inventory(
            items={
                "frontend_url": self.config.frontend_url,
                "frontend_dir": self.config.frontend_dir,
                "lane": opts.get("lane", "real-api"),
                "journey_specs": list(opts.get("journey_specs") or []),
            },
            notes=[
                "Builds on frontend/e2e + frontend/harness.config.json routes",
                "UI build gate (frontend-ready) stays separate; this loop is continuous smoke",
            ],
        )

    def observe(self) -> Observations:
        return Observations(
            data={"phase": "stub"},
            notes=[
                "Synthetic smoke observe is a stub. Next: run Playwright real-api "
                "journeys and capture pass/fail + latency per journey."
            ],
        )
