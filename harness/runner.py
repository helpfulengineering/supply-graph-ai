"""CLI runner: load and tick triage loop modules independently.

Usage:
    uv run python -m harness.runner
    uv run python -m harness.runner --modules parity,client_drift
    uv run python -m harness.runner --probes
    uv run python -m harness.runner --write-proposals
    uv run python -m harness.runner --list
    uv run python -m harness.runner --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from harness.config import HarnessConfig, load_config, repo_root
from harness.modules import instantiate, known_loops, known_modules, known_probes
from harness.probes.proposal import write_probe_proposals
from harness.protocol import Finding, LoopReport, LoopStatus, Severity


@dataclass
class HarnessRunResult:
    reports: list[LoopReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.reports)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "modules": [r.to_dict() for r in self.reports],
            "error_findings": sum(
                1
                for r in self.reports
                for f in r.findings
                if f.severity == Severity.ERROR
            ),
            "stub_count": sum(1 for r in self.reports if r.status == LoopStatus.STUB),
            "online_count": sum(
                1 for r in self.reports if r.status == LoopStatus.ONLINE
            ),
        }


def run_modules(
    names: Optional[Sequence[str]] = None,
    config: Optional[HarnessConfig] = None,
) -> HarnessRunResult:
    """Instantiate and tick the selected modules (default: all known)."""
    cfg = config or load_config()
    selected = list(names) if names else known_modules()
    unknown = [n for n in selected if n not in known_modules()]
    if unknown:
        raise SystemExit(f"Unknown module(s): {unknown}. Known: {known_modules()}")

    reports: list[LoopReport] = []
    for name in selected:
        module = instantiate(name, cfg)
        reports.append(module.run())
    return HarnessRunResult(reports=reports)


def _print_human(result: HarnessRunResult) -> None:
    for report in result.reports:
        mark = "✓" if report.ok else "✗"
        status = report.status.value
        print(f"{mark} [{status}] {report.summary}")
        if report.error:
            print(f"    error: {report.error}")
        for finding in report.findings:
            print(
                f"    - ({finding.severity.value}/{finding.kind.value}) {finding.title}"
            )
            ops = finding.evidence.get("operations")
            if isinstance(ops, list) and ops:
                preview = ", ".join(ops[:8])
                more = f" (+{len(ops) - 8} more)" if len(ops) > 8 else ""
                print(f"      ops: {preview}{more}")
        if report.inventory and report.inventory.notes:
            for note in report.inventory.notes:
                print(f"    · {note}")
    print()
    print(
        f"harness: {'OK' if result.ok else 'FAILED'} "
        f"({result.to_dict()['stub_count']} stub, "
        f"{result.to_dict()['online_count']} online)"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run OHM triage harness loops (parity, RED, smoke, client drift) "
            "and optional production probes."
        ),
    )
    parser.add_argument(
        "--modules",
        "-m",
        help="Comma-separated module names (default: all enabled in config).",
    )
    parser.add_argument(
        "--probes",
        action="store_true",
        help="Run only production probe modules (probe_*).",
    )
    parser.add_argument(
        "--loops",
        action="store_true",
        help="Run only verification loops (exclude probe_*).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to harness.config.json (default: repo-root).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List known modules and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report.",
    )
    parser.add_argument(
        "--write-proposals",
        action="store_true",
        help=(
            "Write draft fix proposals under docs/proposals/ for probe ERROR "
            "findings (human review before implementation)."
        ),
    )
    args = parser.parse_args(argv)

    if args.list:
        for name in known_modules():
            kind = "probe" if name.startswith("probe_") else "loop"
            print(f"{name}\t{kind}")
        return 0

    config = load_config(args.config) if args.config else load_config()

    if args.modules:
        names = [n.strip() for n in args.modules.split(",") if n.strip()]
    elif args.probes:
        names = known_probes()
    elif args.loops:
        names = known_loops()
    else:
        names = [n for n in known_modules() if config.module(n).enabled]

    result = run_modules(names=names, config=config)

    if args.write_proposals:
        findings: list[Finding] = [f for r in result.reports for f in r.findings]
        written = write_probe_proposals(
            findings,
            repo_root() / "docs" / "proposals",
        )
        if not args.json:
            if written:
                print("Proposals written:")
                for path in written:
                    print(f"  {path.relative_to(repo_root())}")
            else:
                print("No probe ERROR findings — no proposals written.")

    if args.json:
        payload = result.to_dict()
        if args.write_proposals:
            payload["proposals_dir"] = str(repo_root() / "docs" / "proposals")
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_human(result)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
