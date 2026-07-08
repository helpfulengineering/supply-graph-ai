"""Synthetic smoke loop — Playwright real-api UI journey walks."""

from __future__ import annotations

from pathlib import Path

from harness.base import BaseLoopModule
from harness.config import repo_root
from harness.modules.smoke_runner import (
    DEFAULT_JOURNEY_SPECS,
    check_api_health,
    check_playwright_chromium_ready,
    run_playwright_smoke,
)
from harness.protocol import (
    Finding,
    FindingKind,
    Inventory,
    LoopReport,
    LoopStatus,
    Observations,
    Severity,
)


class SyntheticSmokeLoop(BaseLoopModule):
    name = "synthetic_smoke"
    status = LoopStatus.ONLINE

    def _lane(self) -> str:
        return str(self.module_config.options.get("lane", "real-api"))

    def _journey_specs(self) -> list[str]:
        raw = self.module_config.options.get("journey_specs")
        if raw:
            return list(raw)
        return list(DEFAULT_JOURNEY_SPECS)

    def _skip_if_unreachable(self) -> bool:
        return bool(self.module_config.options.get("skip_if_unreachable", True))

    def _skip_if_playwright_unavailable(self) -> bool:
        return bool(
            self.module_config.options.get("skip_if_playwright_unavailable", True)
        )

    def _timeout_seconds(self) -> float:
        return float(self.module_config.options.get("timeout_seconds", 300))

    def _frontend_path(self) -> Path:
        return repo_root() / self.config.frontend_dir

    def discover(self) -> Inventory:
        return Inventory(
            items={
                "frontend_url": self.config.frontend_url,
                "frontend_dir": self.config.frontend_dir,
                "api_health_url": self.config.api_health_url,
                "lane": self._lane(),
                "journey_specs": self._journey_specs(),
                "skip_if_unreachable": self._skip_if_unreachable(),
                "skip_if_playwright_unavailable": self._skip_if_playwright_unavailable(),
            },
            notes=[
                "Playwright real-api lane — UI journeys against live backend wiring",
                "Distinct from make frontend-ready (mocked gate)",
                "Requires: API up + `make frontend-setup` (Chromium)",
            ],
        )

    def _api_reachable(self) -> bool:
        return check_api_health(self.config.api_health_url)

    def run(self) -> LoopReport:
        if not self.module_config.enabled:
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                summary=f"{self.name} disabled in config",
            )

        inventory = self.discover()
        if self._skip_if_unreachable() and not self._api_reachable():
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                inventory=inventory,
                summary=(
                    f"{self.name}: skipped (API unreachable at "
                    f"{self.config.api_health_url})"
                ),
                observations=Observations(
                    data={"skipped": True, "reason": "api_unreachable"},
                    notes=["Start the OHM API or set skip_if_unreachable=false"],
                ),
            )

        if (
            self._skip_if_playwright_unavailable()
            and not check_playwright_chromium_ready(str(self._frontend_path()))
        ):
            return LoopReport(
                module=self.name,
                status=LoopStatus.SKIPPED,
                inventory=inventory,
                summary=f"{self.name}: skipped (Playwright Chromium not installed)",
                observations=Observations(
                    data={"skipped": True, "reason": "playwright_unavailable"},
                    notes=["Run `make frontend-setup` to install Chromium"],
                ),
            )

        try:
            observations = self.observe()
            findings = self.judge(observations)
        except Exception as exc:  # noqa: BLE001
            return LoopReport(
                module=self.name,
                status=LoopStatus.FAILED,
                inventory=inventory,
                summary=f"{self.name} failed",
                error=f"{type(exc).__name__}: {exc}",
            )

        return LoopReport(
            module=self.name,
            status=self.status,
            findings=findings,
            inventory=inventory,
            observations=observations,
            summary=self._summary(findings),
        )

    def observe(self) -> Observations:
        frontend_path = self._frontend_path()
        smoke = run_playwright_smoke(
            frontend_dir=str(frontend_path),
            lane=self._lane(),
            journey_specs=self._journey_specs(),
            timeout_seconds=self._timeout_seconds(),
        )
        return Observations(
            data={
                "exit_code": smoke.exit_code,
                "passed": smoke.passed,
                "failed": smoke.failed,
                "skipped": smoke.skipped,
                "duration_ms": smoke.duration_ms,
                "parse_error": smoke.parse_error,
                "failures": [
                    {
                        "spec": f.spec,
                        "title": f.title,
                        "status": f.status,
                        "error": f.error,
                    }
                    for f in smoke.failures
                ],
            },
            notes=[
                f"lane={self._lane()} passed={smoke.passed} "
                f"failed={smoke.failed} skipped={smoke.skipped} "
                f"duration_ms={smoke.duration_ms:.0f}",
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        data = observations.data

        if data.get("parse_error"):
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title="Synthetic smoke could not parse Playwright report",
                    evidence={"parse_error": data["parse_error"]},
                    suggested_state="needs-triage",
                )
            )
            return findings

        for failure in data.get("failures") or []:
            spec = str(failure.get("spec", "unknown"))
            title = str(failure.get("title", "unknown"))
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title=f"Journey failed: {title}",
                    evidence={
                        "spec": spec,
                        "title": title,
                        "status": failure.get("status"),
                        "error": failure.get("error"),
                    },
                    suggested_state="ready-for-agent",
                )
            )

        failed = int(data.get("failed") or 0)
        if failed > 0 and not findings:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title=f"{failed} synthetic smoke journey(s) failed",
                    evidence={"failed": failed, "exit_code": data.get("exit_code")},
                    suggested_state="needs-triage",
                )
            )
        return findings
