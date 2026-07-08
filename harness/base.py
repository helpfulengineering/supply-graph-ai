"""Base helpers for loop modules."""

from __future__ import annotations

from typing import Optional

from harness.config import HarnessConfig, ModuleConfig
from harness.protocol import (
    Finding,
    Inventory,
    LoopReport,
    LoopStatus,
    Observations,
)


class BaseLoopModule:
    """Default run() wiring; subclasses override discover/observe/judge."""

    name: str = "base"
    status: LoopStatus = LoopStatus.STUB

    def __init__(
        self,
        config: HarnessConfig,
        module_config: Optional[ModuleConfig] = None,
    ) -> None:
        self.config = config
        self.module_config = module_config or config.module(self.name)

    def discover(self) -> Inventory:
        return Inventory(notes=[f"{self.name}: discover not yet implemented"])

    def observe(self) -> Observations:
        return Observations(notes=[f"{self.name}: observe not yet implemented"])

    def judge(self, observations: Observations) -> list[Finding]:
        del observations
        return []

    def run(self) -> LoopReport:
        if not self.module_config.enabled:
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                summary=f"{self.name} disabled in config",
            )

        try:
            inventory = self.discover()
            observations = self.observe()
            findings = self.judge(observations)
        except Exception as exc:  # noqa: BLE001 — surface as FAILED report
            return LoopReport(
                module=self.name,
                status=LoopStatus.FAILED,
                summary=f"{self.name} failed",
                error=f"{type(exc).__name__}: {exc}",
            )

        summary = self._summary(findings)
        return LoopReport(
            module=self.name,
            status=self.status,
            findings=findings,
            inventory=inventory,
            observations=observations,
            summary=summary,
        )

    def _summary(self, findings: list[Finding]) -> str:
        if self.status == LoopStatus.STUB:
            return f"{self.name}: stub (not yet online)"
        if not findings:
            return f"{self.name}: clean"
        return f"{self.name}: {len(findings)} finding(s)"
