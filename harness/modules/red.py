"""RED loop — Rate / Errors / Duration over API endpoints."""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.modules.red_metrics import judge_endpoints, load_metrics
from harness.protocol import (
    Finding,
    FindingKind,
    Inventory,
    LoopStatus,
    Observations,
    Severity,
)


class RedLoop(BaseLoopModule):
    name = "red"
    status = LoopStatus.ONLINE

    def _thresholds(self) -> dict[str, float | int]:
        opts = self.module_config.options
        return {
            "error_rate_warn": float(opts.get("error_rate_warn", 0.05)),
            "p95_ms_warn": float(opts.get("p95_ms_warn", 2000)),
            "min_requests": int(opts.get("min_requests", 1)),
        }

    def _metrics_source(self) -> str:
        return str(self.module_config.options.get("source", "in-process"))

    def discover(self) -> Inventory:
        thresholds = self._thresholds()
        return Inventory(
            items={
                "source": self._metrics_source(),
                "metrics_path": self.module_config.options.get(
                    "metrics_path", "/v1/api/utility/metrics"
                ),
                "thresholds": thresholds,
                "api_base_url": self.config.api_base_url,
            },
            notes=[
                "RED: Rate / Errors / Duration per endpoint",
                "Default source is in-process MetricsTracker (no server required)",
                "Set modules.red.options.source=http for live cloud scrape",
            ],
        )

    def observe(self) -> Observations:
        opts = self.module_config.options
        metrics_path = str(opts.get("metrics_path", "/v1/api/utility/metrics"))
        payload = load_metrics(
            source=self._metrics_source(),
            base_url=self.config.api_base_url,
            metrics_path=metrics_path,
        )
        endpoints = dict(payload.get("endpoints") or {})
        summary = dict(payload.get("summary") or {})
        thresholds = self._thresholds()
        breaches = judge_endpoints(
            endpoints,
            error_rate_warn=float(thresholds["error_rate_warn"]),
            p95_ms_warn=float(thresholds["p95_ms_warn"]),
            min_requests=int(thresholds["min_requests"]),
        )
        return Observations(
            data={
                "summary": summary,
                "endpoint_count": len(endpoints),
                "breaches": breaches,
                "thresholds": thresholds,
            },
            notes=[
                f"source={self._metrics_source()} endpoints={len(endpoints)} "
                f"breaches={len(breaches)}",
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        breaches = list(observations.data.get("breaches") or [])
        thresholds = observations.data.get("thresholds") or {}

        for breach in breaches:
            endpoint = str(breach.get("endpoint", "unknown"))
            issues = list(breach.get("issues") or [])
            err = float(breach.get("error_rate") or 0.0)
            p95 = float(breach.get("p95_ms") or 0.0)
            if "error_rate" in issues:
                findings.append(
                    Finding(
                        module=self.name,
                        kind=FindingKind.BUG,
                        severity=Severity.WARN,
                        title=f"Elevated error rate on {endpoint}",
                        evidence={
                            "endpoint": endpoint,
                            "error_rate": err,
                            "threshold": thresholds.get("error_rate_warn"),
                            "total_requests": breach.get("total_requests"),
                        },
                        suggested_state="needs-triage",
                    )
                )
            if "latency" in issues:
                findings.append(
                    Finding(
                        module=self.name,
                        kind=FindingKind.PERF,
                        severity=Severity.WARN,
                        title=f"Elevated latency on {endpoint}",
                        evidence={
                            "endpoint": endpoint,
                            "p95_ms": p95,
                            "threshold_ms": thresholds.get("p95_ms_warn"),
                            "total_requests": breach.get("total_requests"),
                        },
                        suggested_state="needs-triage",
                    )
                )
        return findings
