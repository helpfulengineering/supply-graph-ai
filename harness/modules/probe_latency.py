"""Probe: endpoint latency against configurable SLOs."""

from __future__ import annotations

from typing import Any

from harness.probes.base import ProbeModule
from harness.probes.http import api_request, extract_detail
from harness.probes.okh import first_okh_id_from_list_body
from harness.protocol import Finding, FindingKind, Inventory, Observations, Severity

DEFAULT_CHECKS: tuple[dict[str, Any], ...] = (
    {
        "name": "okh_list",
        "method": "GET",
        "path": "/okh?page=1&page_size=5",
        "warn_ms": 3000,
        "error_ms": 10000,
    },
    {
        "name": "okw_search",
        "method": "GET",
        "path": "/okw/search?query=&page=1&page_size=5",
        "warn_ms": 3000,
        "error_ms": 10000,
    },
    {
        "name": "okw_spaces",
        "method": "GET",
        "path": "/okw/spaces?include_mom=false",
        "warn_ms": 5000,
        "error_ms": 15000,
    },
)


class ProbeLatencyLoop(ProbeModule):
    name = "probe_latency"

    def discover(self) -> Inventory:
        checks = list(self.module_config.options.get("checks") or DEFAULT_CHECKS)
        return Inventory(
            items={"checks": checks, "api_base_url": self.config.api_base_url},
            notes=["Compares live request duration_ms to per-check warn/error SLOs"],
        )

    def observe(self) -> Observations:
        checks = list(self.module_config.options.get("checks") or DEFAULT_CHECKS)
        results: list[dict[str, Any]] = []
        okh_id: str | None = self.module_config.options.get("okh_id")

        for check in checks:
            path = str(check["path"])
            method = str(check.get("method", "GET"))
            json_body = check.get("json_body")

            if "{okh_id}" in path:
                if not okh_id:
                    list_res = api_request(
                        base_url=self.config.api_base_url,
                        api_path_prefix=self._api_path_prefix(),
                        path="/okh?page=1&page_size=1",
                        timeout=30,
                    )
                    okh_id = first_okh_id_from_list_body(list_res.body)
                path = path.replace("{okh_id}", okh_id or "missing")

            timeout = float(check.get("timeout_seconds", 120))
            if method.upper() == "POST" and json_body and okh_id:
                body = dict(json_body)
                if "okh_id" in body and body["okh_id"] == "{okh_id}":
                    body["okh_id"] = okh_id
                res = api_request(
                    base_url=self.config.api_base_url,
                    api_path_prefix=self._api_path_prefix(),
                    path=path.split("?", 1)[0],
                    method="POST",
                    json_body=body,
                    timeout=timeout,
                )
            else:
                res = api_request(
                    base_url=self.config.api_base_url,
                    api_path_prefix=self._api_path_prefix(),
                    path=path,
                    method=method,
                    timeout=timeout,
                )

            results.append(
                {
                    "name": check.get("name", path),
                    "method": method,
                    "path": path,
                    "status": res.status,
                    "duration_ms": round(res.duration_ms, 1),
                    "warn_ms": int(check.get("warn_ms", 3000)),
                    "error_ms": int(check.get("error_ms", 10000)),
                    "request_id": res.headers.get("x-request-id"),
                    "detail": extract_detail(res.body) if res.status >= 400 else "",
                }
            )

        return Observations(
            data={"results": results, "okh_id_used": okh_id},
            notes=[
                f"{r['name']}: {r['duration_ms']}ms (status {r['status']})"
                for r in results
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        for r in observations.data.get("results") or []:
            ms = float(r["duration_ms"])
            warn_ms = int(r["warn_ms"])
            error_ms = int(r["error_ms"])
            name = str(r["name"])
            if ms >= error_ms:
                findings.append(
                    Finding(
                        module=self.name,
                        kind=FindingKind.PERF,
                        severity=Severity.ERROR,
                        title=f"{name} exceeded error SLO ({ms:.0f}ms >= {error_ms}ms)",
                        evidence={
                            **r,
                            "recommendation": (
                                "Profile hot path (storage I/O, NLP, MoM fetch, cold "
                                "start). Add caching (see probe_cache), reduce candidate "
                                "scope, tune ACA CPU/memory and min replicas."
                            ),
                        },
                        suggested_state="ready-for-human",
                    )
                )
            elif ms >= warn_ms:
                findings.append(
                    Finding(
                        module=self.name,
                        kind=FindingKind.PERF,
                        severity=Severity.WARN,
                        title=f"{name} exceeded warn SLO ({ms:.0f}ms >= {warn_ms}ms)",
                        evidence={**r},
                        suggested_state="needs-triage",
                    )
                )
        return findings
