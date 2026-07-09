"""Probe: OKH manifest file refs are reachable (view/download)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from harness.probes.base import ProbeModule
from harness.probes.http import api_request
from harness.probes.okh import first_okh_id_from_list_body
from harness.protocol import Finding, FindingKind, Inventory, Observations, Severity

FILE_FIELDS = ("design_files", "manufacturing_files", "making_instructions")


def _collect_file_refs(manifest: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for field in FILE_FIELDS:
        for item in manifest.get(field) or []:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            url = str(item.get("url") or item.get("download_url") or "").strip()
            check_url = url or path
            if check_url:
                refs.append(
                    {
                        "field": field,
                        "title": str(item.get("title") or ""),
                        "path": check_url,
                        "type": str(item.get("type") or ""),
                    }
                )
    return refs


def _check_file_url(path: str, *, timeout: float = 15.0) -> dict[str, Any]:
    """HEAD/GET external or relative file URL."""
    import urllib.error
    import urllib.request

    parsed = urlparse(path)
    if not parsed.scheme:
        return {
            "path": path,
            "reachable": False,
            "status": 0,
            "reason": "relative_path_no_api_proxy",
            "kind": "gap",
        }

    req = urllib.request.Request(path, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "path": path,
                "reachable": 200 <= resp.status < 400,
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type", ""),
                "kind": "external",
            }
    except urllib.error.HTTPError as exc:
        return {
            "path": path,
            "reachable": False,
            "status": exc.code,
            "reason": str(exc),
            "kind": "external",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "path": path,
            "reachable": False,
            "status": 0,
            "reason": str(exc),
            "kind": "external",
        }


class ProbeOkhFilesLoop(ProbeModule):
    name = "probe_okh_files"

    def discover(self) -> Inventory:
        opts = self.module_config.options
        return Inventory(
            items={
                "okh_id": opts.get("okh_id"),
                "file_fields": list(FILE_FIELDS),
                "api_base_url": self.config.api_base_url,
            },
            notes=[
                "Checks manifest file refs from GET /okh/{id}",
                "Flags relative paths (no OHM download proxy) and broken external URLs",
            ],
        )

    def observe(self) -> Observations:
        opts = self.module_config.options
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
            return Observations(data={"error": "no_okh_id"})

        detail = api_request(
            base_url=self.config.api_base_url,
            api_path_prefix=self._api_path_prefix(),
            path=f"/okh/{okh_id}",
            timeout=60,
        )
        manifest: dict[str, Any] = {}
        if isinstance(detail.body, dict):
            inner = detail.body.get("data")
            manifest = inner if isinstance(inner, dict) else detail.body

        refs = _collect_file_refs(manifest)
        checks = [_check_file_url(r["path"]) for r in refs]
        for ref, chk in zip(refs, checks):
            chk["title"] = ref["title"]
            chk["field"] = ref["field"]

        return Observations(
            data={
                "okh_id": okh_id,
                "file_count": len(refs),
                "checks": checks,
                "detail_status": detail.status,
            },
            notes=[f"okh_id={okh_id} files={len(refs)}"],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        if observations.data.get("error") == "no_okh_id":
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title="OKH file probe could not resolve an OKH id",
                    evidence={
                        "recommendation": "Seed OKH data or set probe_okh_files.options.okh_id"
                    },
                    suggested_state="ready-for-human",
                )
            )
            return findings

        checks = list(observations.data.get("checks") or [])
        relative = [
            c for c in checks if c.get("reason") == "relative_path_no_api_proxy"
        ]
        broken = [
            c for c in checks if c.get("kind") == "external" and not c.get("reachable")
        ]

        if relative:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title=(
                        f"{len(relative)} OKH file ref(s) are not API-proxied "
                        "(relative/raw paths)"
                    ),
                    evidence={
                        "samples": relative[:20],
                        "recommendation": (
                            "Add OHM storage/file API (signed URLs or /api/okh/{id}/files/...) "
                            "and update OkhFileGroup to use download + in-browser viewer "
                            "by MIME type (pdf, png, stl, md)."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )

        if broken:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.WARN,
                    title=f"{len(broken)} external OKH file URL(s) unreachable",
                    evidence={
                        "samples": broken[:20],
                        "recommendation": (
                            "Verify storage sync, replace stale GitHub raw URLs, "
                            "or proxy through OHM blob storage."
                        ),
                    },
                    suggested_state="needs-triage",
                )
            )

        if not checks:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.WARN,
                    title="OKH detail has no design/manufacturing/instruction files",
                    evidence={"okh_id": observations.data.get("okh_id")},
                    suggested_state="needs-triage",
                )
            )
        return findings
