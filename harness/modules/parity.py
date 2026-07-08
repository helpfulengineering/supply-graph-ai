"""Parity loop — feature inventory across service / API / CLI / frontend."""

from __future__ import annotations

from harness.base import BaseLoopModule
from harness.config import repo_root
from harness.protocol import (
    Finding,
    FindingKind,
    Inventory,
    LoopStatus,
    Observations,
    Severity,
)
from tests.parity.inventory import (
    actual_api_tags,
    actual_cli_groups,
    actual_fe_api_prefixes,
    actual_fe_routes,
    actual_services,
    layer_diff,
)
from tests.parity.manifest import (
    AREAS,
    expected_api_tags,
    expected_cli_groups,
    expected_fe_api_prefixes,
    expected_fe_routes,
    expected_services,
)


def _layer_finding(
    *,
    module: str,
    layer: str,
    undeclared: list[str],
    missing: list[str],
) -> list[Finding]:
    findings: list[Finding] = []
    if undeclared:
        findings.append(
            Finding(
                module=module,
                kind=FindingKind.GAP,
                severity=Severity.ERROR,
                title=f"{layer}: undeclared in manifest ({len(undeclared)})",
                evidence={"undeclared": undeclared, "fix": "tests/parity/manifest.py"},
                suggested_state="ready-for-agent",
            )
        )
    if missing:
        findings.append(
            Finding(
                module=module,
                kind=FindingKind.GAP,
                severity=Severity.ERROR,
                title=f"{layer}: declared but missing in code ({len(missing)})",
                evidence={"missing": missing, "fix": "wire layer or update manifest"},
                suggested_state="ready-for-agent",
            )
        )
    return findings


class ParityLoop(BaseLoopModule):
    name = "parity"
    status = LoopStatus.ONLINE

    def discover(self) -> Inventory:
        areas = {
            a.name: {
                "service": a.service,
                "api_tag": a.api_tag,
                "cli_group": a.cli_group,
                "fe_routes": list(a.fe_routes or ()),
                "fe_api_prefixes": list(a.fe_api_prefixes or ()),
                "status": a.status,
            }
            for a in AREAS
        }
        return Inventory(
            items={
                "areas": areas,
                "count": len(areas),
                "expected_fe_routes": sorted(expected_fe_routes()),
                "expected_fe_api_prefixes": sorted(expected_fe_api_prefixes()),
            },
            notes=[
                "Contract: tests/parity/manifest.py",
                "Backend + frontend inventories enumerated each tick",
            ],
        )

    def observe(self) -> Observations:
        root = repo_root()
        app_tsx = root / self.config.frontend_dir / "src" / "App.tsx"
        fe_src = root / self.config.frontend_dir / "src"

        service_diff = layer_diff(expected_services(), actual_services())
        api_diff = layer_diff(expected_api_tags(), actual_api_tags())
        cli_diff = layer_diff(expected_cli_groups(), actual_cli_groups())
        fe_route_diff = layer_diff(expected_fe_routes(), actual_fe_routes(app_tsx))
        fe_api_diff = layer_diff(
            expected_fe_api_prefixes(), actual_fe_api_prefixes(fe_src)
        )

        return Observations(
            data={
                "service": service_diff,
                "api_tag": api_diff,
                "cli_group": cli_diff,
                "fe_route": fe_route_diff,
                "fe_api_prefix": fe_api_diff,
            },
            notes=[
                "service "
                f"u={len(service_diff['undeclared'])} m={len(service_diff['missing'])}",
                "api_tag "
                f"u={len(api_diff['undeclared'])} m={len(api_diff['missing'])}",
                "cli_group "
                f"u={len(cli_diff['undeclared'])} m={len(cli_diff['missing'])}",
                "fe_route "
                f"u={len(fe_route_diff['undeclared'])} m={len(fe_route_diff['missing'])}",
                "fe_api "
                f"u={len(fe_api_diff['undeclared'])} m={len(fe_api_diff['missing'])}",
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        data = observations.data
        for layer_key, label in (
            ("service", "Service"),
            ("api_tag", "API tag"),
            ("cli_group", "CLI group"),
            ("fe_route", "Frontend route"),
            ("fe_api_prefix", "Frontend API prefix"),
        ):
            layer = data.get(layer_key) or {}
            findings.extend(
                _layer_finding(
                    module=self.name,
                    layer=label,
                    undeclared=list(layer.get("undeclared") or []),
                    missing=list(layer.get("missing") or []),
                )
            )
        return findings
