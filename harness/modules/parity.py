"""Parity loop — feature inventory across service / API / CLI / (soon) frontend.

Currently a stub that surfaces the existing ``tests/parity`` contract area so
the harness can load it. Next increment: FE route inventory vs API tags.
"""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.protocol import Inventory, LoopStatus, Observations


class ParityLoop(BaseLoopModule):
    name = "parity"
    status = LoopStatus.STUB

    def discover(self) -> Inventory:
        try:
            from tests.parity.manifest import AREAS

            areas = {
                a.name: {
                    "service": a.service,
                    "api_tag": a.api_tag,
                    "cli_group": a.cli_group,
                    "status": a.status,
                }
                for a in AREAS
            }
            return Inventory(
                items={"areas": areas, "count": len(areas)},
                notes=[
                    "Backend service↔API↔CLI inventory loaded from tests/parity/manifest.py",
                    "Frontend route inventory not yet wired",
                ],
            )
        except Exception as exc:  # noqa: BLE001
            return Inventory(
                notes=[f"Could not load parity manifest: {type(exc).__name__}: {exc}"]
            )

    def observe(self) -> Observations:
        return Observations(
            data={"phase": "stub"},
            notes=[
                "Parity observe is a stub. Next: run live enumeration "
                "(actual_services / actual_api_tags / actual_cli_groups / FE routes) "
                "and diff against the manifest."
            ],
        )
