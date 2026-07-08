"""Probe: intermittent POST /api/match 503 and empty error envelopes."""

from __future__ import annotations

from typing import Any

from harness.probes.base import ProbeModule
from harness.probes.http import api_request, extract_detail
from harness.probes.okh import first_okh_id_from_list_body
from harness.protocol import Finding, FindingKind, Inventory, Observations, Severity


def run_match_attempts(
    *,
    base_url: str,
    api_path_prefix: str,
    okh_id: str,
    attempts: int,
    timeout: float,
) -> list[dict[str, Any]]:
    """POST /match ``attempts`` times; return per-attempt diagnostics."""
    body = {
        "okh_id": okh_id,
        "max_results": 3,
        "include_human_summary": False,
        "save_solution": False,
    }
    samples: list[dict[str, Any]] = []
    for i in range(attempts):
        res = api_request(
            base_url=base_url,
            api_path_prefix=api_path_prefix,
            path="/match",
            method="POST",
            json_body=body,
            timeout=timeout,
        )
        detail = extract_detail(res.body)
        samples.append(
            {
                "attempt": i + 1,
                "status": res.status,
                "duration_ms": round(res.duration_ms, 1),
                "request_id": res.headers.get("x-request-id"),
                "processing_time": res.headers.get("x-processing-time"),
                "detail": detail,
                "error": res.error,
            }
        )
    return samples


class ProbeMatchLoop(ProbeModule):
    name = "probe_match"

    def discover(self) -> Inventory:
        opts = self.module_config.options
        return Inventory(
            items={
                "endpoint": "POST /api/match",
                "attempts": int(opts.get("attempts", 5)),
                "max_503_rate": float(opts.get("max_503_rate", 0.0)),
                "okh_id": opts.get("okh_id"),
                "api_base_url": self.config.api_base_url,
            },
            notes=[
                "Detects 503 on match (often MatchingService init timeout)",
                "Captures request-id and API detail for Azure log correlation",
            ],
        )

    def observe(self) -> Observations:
        opts = self.module_config.options
        attempts = int(opts.get("attempts", 5))
        timeout = float(opts.get("timeout_seconds", 120))
        okh_id = opts.get("okh_id")

        if not okh_id:
            list_res = api_request(
                base_url=self.config.api_base_url,
                api_path_prefix=self._api_path_prefix(),
                path="/okh?page=1&page_size=1",
                timeout=30,
            )
            okh_id = first_okh_id_from_list_body(list_res.body)
            if not okh_id:
                return Observations(
                    data={"error": "no_okh_id", "list_status": list_res.status},
                    notes=["Could not resolve okh_id from GET /okh"],
                )

        samples = run_match_attempts(
            base_url=self.config.api_base_url,
            api_path_prefix=self._api_path_prefix(),
            okh_id=str(okh_id),
            attempts=attempts,
            timeout=timeout,
        )
        status_counts: dict[int, int] = {}
        for s in samples:
            st = int(s["status"])
            status_counts[st] = status_counts.get(st, 0) + 1

        return Observations(
            data={
                "okh_id": okh_id,
                "attempts": attempts,
                "samples": samples,
                "status_counts": status_counts,
                "503_count": status_counts.get(503, 0),
                "empty_detail_count": sum(
                    1 for s in samples if s["status"] >= 400 and not s.get("detail")
                ),
            },
            notes=[
                f"okh_id={okh_id} status_counts={status_counts}",
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        data = observations.data
        if data.get("error") == "no_okh_id":
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title="Match probe could not resolve an OKH id",
                    evidence={
                        **data,
                        "recommendation": (
                            "Seed storage with OKH data or set "
                            "modules.probe_match.options.okh_id in harness.config.json"
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )
            return findings

        opts = self.module_config.options
        max_503_rate = float(opts.get("max_503_rate", 0.0))
        attempts = int(data.get("attempts") or 1)
        count_503 = int(data.get("503_count") or 0)
        rate_503 = count_503 / attempts if attempts else 0.0
        empty_detail = int(data.get("empty_detail_count") or 0)
        samples = list(data.get("samples") or [])

        if rate_503 > max_503_rate:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title=(
                        f"Match returned 503 on {count_503}/{attempts} attempts "
                        f"({rate_503:.0%})"
                    ),
                    evidence={
                        "503_rate": rate_503,
                        "samples": samples,
                        "status_counts": data.get("status_counts"),
                        "recommendation": (
                            "Investigate MatchingService cold init on ACA (20s timeout in "
                            "get_matching_service). Consider eager startup init, longer "
                            "timeout, readiness probe that waits for service singleton, "
                            "and surface API `detail` + request_id in the frontend."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )

        if empty_detail > 0:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.WARN,
                    title=f"{empty_detail} match error(s) lacked API detail body",
                    evidence={
                        "samples": [s for s in samples if s["status"] >= 400],
                        "recommendation": (
                            "Improve frontend error display to show response JSON "
                            "detail and X-Request-Id for support triage."
                        ),
                    },
                    suggested_state="needs-triage",
                )
            )
        return findings
