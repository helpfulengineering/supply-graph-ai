"""Client drift loop — live OpenAPI vs committed frontend schema.

Compares operation inventories (METHOD + path) extracted from:

* the versioned FastAPI OpenAPI schema (in-process, no server required), and
* the committed ``openapi-typescript`` output ``schema.d.ts``.

Drift becomes ``gap`` findings. Module is online when both inventories load.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

# Implemented method (not `get?: never`):
_METHOD_IMPL_RE = re.compile(
    r"^\s+(get|post|put|patch|delete|head|options):\s*(?:operations\[|\{)",
    re.MULTILINE,
)


def operations_from_openapi(spec: dict[str, Any]) -> set[str]:
    """Return ``METHOD /path`` strings from an OpenAPI 3 paths object."""
    ops: set[str] = set()
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, body in methods.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            if body is None:
                continue
            ops.add(f"{method.upper()} {path}")
    return ops


def operations_from_schema_dts(text: str) -> set[str]:
    """Parse openapi-typescript ``paths`` interface into ``METHOD /path`` set.

    Only methods that are *implemented* (bound to ``operations[...]`` or an
    object type) count. ``method?: never`` stubs are ignored.
    """
    # Restrict to the paths interface body to avoid matching elsewhere.
    start = text.find("export interface paths")
    if start < 0:
        return set()
    # Naive brace match for the interface.
    brace_start = text.find("{", start)
    if brace_start < 0:
        return set()
    depth = 0
    end = brace_start
    for i, ch in enumerate(text[brace_start:], start=brace_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = text[brace_start : end + 1]

    ops: set[str] = set()
    # Split on path keys; for each path block, find implemented methods.
    parts = re.split(r'\n\s+"/([^"]+)":\s*\{', body)
    # parts[0] is preamble; then (path, block, path, block, ...)
    it = iter(parts[1:])
    for path, block in zip(it, it):
        # Truncate block at its balancing close for this path object.
        # The split already left the interior starting after `{`; find methods
        # before the next path-level content becomes unreliable. Scan until we
        # would leave the path object by tracking braces from an implicit depth 1.
        depth = 1
        cut = 0
        for i, ch in enumerate(block):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cut = i
                    break
        path_body = block[:cut] if cut else block
        for m in _METHOD_IMPL_RE.finditer(path_body):
            ops.add(f"{m.group(1).upper()} /{path}")
    return ops


def diff_operations(
    *,
    live: set[str],
    committed: set[str],
) -> dict[str, list[str]]:
    """Compare live OpenAPI ops to committed client schema ops."""
    return {
        "missing_from_client": sorted(live - committed),
        "extra_in_client": sorted(committed - live),
        "shared": sorted(live & committed),
    }


def load_live_openapi() -> dict[str, Any]:
    """Build OpenAPI from the in-process FastAPI app (no HTTP server needed)."""
    from src.core.main import api_v1

    return api_v1.openapi()


class ClientDriftLoop(BaseLoopModule):
    name = "client_drift"
    status = LoopStatus.ONLINE

    def discover(self) -> Inventory:
        schema_rel = self.config.committed_schema
        schema_path = repo_root() / schema_rel
        return Inventory(
            items={
                "openapi_source": "in-process:src.core.main.api_v1",
                "openapi_url": self.config.openapi_url,
                "committed_schema": schema_rel,
                "committed_schema_exists": schema_path.is_file(),
                "committed_schema_bytes": (
                    schema_path.stat().st_size if schema_path.is_file() else 0
                ),
            },
            notes=[
                "Live ops from api_v1.openapi(); committed ops from schema.d.ts",
                "Regenerate client with: cd frontend && npm run gen:api",
            ],
        )

    def observe(self) -> Observations:
        schema_path = repo_root() / self.config.committed_schema
        if not schema_path.is_file():
            return Observations(
                data={"error": "committed_schema_missing"},
                notes=[f"Committed schema not found: {schema_path}"],
            )

        live_spec = load_live_openapi()
        live_ops = operations_from_openapi(live_spec)
        committed_ops = operations_from_schema_dts(
            schema_path.read_text(encoding="utf-8")
        )
        diff = diff_operations(live=live_ops, committed=committed_ops)
        return Observations(
            data={
                "live_count": len(live_ops),
                "committed_count": len(committed_ops),
                "shared_count": len(diff["shared"]),
                "missing_from_client": diff["missing_from_client"],
                "extra_in_client": diff["extra_in_client"],
            },
            notes=[
                f"live={len(live_ops)} committed={len(committed_ops)} "
                f"shared={len(diff['shared'])} "
                f"missing={len(diff['missing_from_client'])} "
                f"extra={len(diff['extra_in_client'])}"
            ],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        findings: list[Finding] = []
        data = observations.data
        if data.get("error") == "committed_schema_missing":
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title="Committed frontend schema.d.ts is missing",
                    evidence={"path": self.config.committed_schema},
                    suggested_state="ready-for-agent",
                )
            )
            return findings

        missing = list(data.get("missing_from_client") or [])
        extra = list(data.get("extra_in_client") or [])

        if missing:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title=(
                        f"{len(missing)} API operation(s) missing from "
                        "committed frontend schema"
                    ),
                    evidence={
                        "operations": missing[:50],
                        "total": len(missing),
                        "fix": "cd frontend && npm run gen:api (API must be reachable)",
                    },
                    suggested_state="ready-for-agent",
                )
            )
        if extra:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.WARN,
                    title=(
                        f"{len(extra)} operation(s) in committed schema "
                        "absent from live OpenAPI"
                    ),
                    evidence={
                        "operations": extra[:50],
                        "total": len(extra),
                        "hint": "Schema is ahead of (or stale vs) live API routes",
                    },
                    suggested_state="needs-triage",
                )
            )
        return findings
