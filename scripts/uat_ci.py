#!/usr/bin/env python3
"""Decisions for the weekly UAT workflow (.github/workflows/uat-e2e.yml).

Two things a workflow cannot say for itself:

  gate   A cron cannot skip itself. Decide whether anything worth re-testing has
         landed since the last run that actually executed.
  prune  `retention-days` counts days, not runs. Keep the evidence of the last N
         runs and delete the rest.

The judgements are pure functions, tested in tests/unit/test_uat_ci.py. The `gh`
calls around them are thin. Standard library only, so the workflow runs it with
the runner's own python3 and no environment sync.

Both fail toward the safe side. A gate that cannot find an answer runs the suite,
because a wasted run is cheap and a silently skipped one is the failure the job
exists to prevent. A prune that cannot read the listing deletes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

WORKFLOW = "uat-e2e.yml"
EVIDENCE_PREFIX = "uat-"
DEFAULT_KEEP = 3

# Anything under these, or any Markdown file, is not a change to the code that
# the suite exercises. The membership guides live in docs-site/, so a guide-only
# edit does not trigger a run; part 11 of the runbook is read by a person.
DOC_PREFIXES = ("docs/", "docs-site/", "notes/")


# --- gate --------------------------------------------------------------------


def last_executed_run(runs: Iterable[dict]) -> Optional[dict]:
    """The newest run that ran to a verdict.

    `gh run list` is newest first. A skipped, cancelled, or still-running run says
    nothing about the code, so it is passed over. A manual run counts: a dispatch
    yesterday means a cron today has nothing new to find.
    """
    for candidate in runs:
        if candidate.get("conclusion") in ("success", "failure"):
            return candidate
    return None


def is_code_change(paths: Iterable[str]) -> bool:
    """True when at least one changed path is not documentation."""
    for path in paths:
        if path.endswith(".md") or path.startswith(DOC_PREFIXES):
            continue
        return True
    return False


def gate_decision(
    event: str,
    last_run_sha: Optional[str],
    head_sha: str,
    changed_paths: Optional[list[str]],
) -> tuple[bool, str]:
    """Whether to run the suite, and the sentence that says why.

    `changed_paths` is None when the diff could not be read.
    """
    if event == "workflow_dispatch":
        return True, "manual dispatch always runs"
    if last_run_sha is None:
        return True, "no earlier run to compare with"
    if changed_paths is None:
        return True, "could not read the diff since the last run, so running"
    if last_run_sha == head_sha:
        return False, "no commits since the last run"
    if not changed_paths:
        return False, "no files changed since the last run"
    if not is_code_change(changed_paths):
        return False, "only documentation changed since the last run"
    return True, "code changed since the last run"


# --- prune -------------------------------------------------------------------


def _run_id(item: dict) -> int:
    return int(item["workflow_run"]["id"])


def plan_prune(
    artifacts: Iterable[dict], current_run_id: int, keep: int = DEFAULT_KEEP
) -> tuple[list[dict], list[dict]]:
    """Split our evidence into (kept, to_delete).

    Only artifacts whose name starts with `uat-` are considered, and expired ones
    are ignored. Both jobs of one run share a run id, so a run counts once. The
    current run is named explicitly rather than trusted to appear in the listing,
    which can lag the upload: it takes one of the `keep` slots whether or not it
    is listed, and the rest go to the newest other runs.
    """
    ours = [
        a
        for a in artifacts
        if str(a.get("name", "")).startswith(EVIDENCE_PREFIX)
        and not a.get("expired", False)
    ]
    newest_by_run: dict[int, str] = {}
    for item in ours:
        run_id = _run_id(item)
        stamp = str(item.get("created_at", ""))
        if stamp > newest_by_run.get(run_id, ""):
            newest_by_run[run_id] = stamp

    others = sorted(
        (rid for rid in newest_by_run if rid != current_run_id),
        key=lambda rid: newest_by_run[rid],
        reverse=True,
    )
    keep_ids = {current_run_id, *others[: max(keep - 1, 0)]}

    kept = [a for a in ours if _run_id(a) in keep_ids]
    doomed = [a for a in ours if _run_id(a) not in keep_ids]
    return kept, doomed


def prune(
    list_artifacts: Callable[[], list[dict]],
    delete_artifact: Callable[[int], None],
    current_run_id: int,
    keep: int,
    dry_run: bool,
    log: Callable[[str], None],
) -> int:
    """Delete evidence older than the last `keep` runs. Returns an exit status.

    One failed delete does not stop the others. An unreadable listing deletes
    nothing.
    """
    try:
        artifacts = list_artifacts()
    except Exception as exc:  # noqa: BLE001 - any failure means "touch nothing"
        log(f"could not list artifacts, deleting nothing: {exc}")
        return 1

    kept, doomed = plan_prune(artifacts, current_run_id, keep)
    for item in kept:
        log(
            f"keep   run {_run_id(item)}  {item['name']}  "
            f"{item.get('size_in_bytes', 0)} bytes"
        )
    failures = 0
    for item in doomed:
        line = (
            f"run {_run_id(item)}  {item['name']}  "
            f"{item.get('size_in_bytes', 0)} bytes"
        )
        if dry_run:
            log(f"would delete  {line}")
            continue
        try:
            delete_artifact(int(item["id"]))
            log(f"deleted  {line}")
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            failures += 1
            log(f"FAILED to delete  {line}: {exc}")
    if dry_run:
        log(f"dry run: {len(doomed)} artifact(s) would be deleted, none were")
    return 1 if failures else 0


# --- gh wrappers -------------------------------------------------------------


def _gh(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return result.stdout


def _git_changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _write(path_env: str, text: str) -> None:
    path = os.environ.get(path_env)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def _emit_gate(go: bool, reason: str) -> None:
    print(f"gate: run={'true' if go else 'false'}  ({reason})")
    _write("GITHUB_OUTPUT", f"run={'true' if go else 'false'}\nreason={reason}\n")
    _write(
        "GITHUB_STEP_SUMMARY",
        f"### UAT gate\n\n{'Running' if go else 'Skipping'}: {reason}.\n",
    )


def cmd_gate(_args: argparse.Namespace) -> int:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    head = os.environ.get("GITHUB_SHA", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if event == "workflow_dispatch":
        _emit_gate(*gate_decision(event, None, head, None))
        return 0
    try:
        runs = json.loads(
            _gh(
                [
                    "run",
                    "list",
                    "--workflow",
                    WORKFLOW,
                    "--repo",
                    repo,
                    "--json",
                    "headSha,conclusion",
                    "--limit",
                    "20",
                ]
            )
        )
    except Exception as exc:  # noqa: BLE001 - fail open
        _emit_gate(True, f"could not read run history ({exc}), so running")
        return 0
    last = last_executed_run(runs)
    last_sha = last["headSha"] if last else None
    changed: Optional[list[str]] = None
    if last_sha is not None:
        if last_sha == head:
            changed = []
        else:
            try:
                changed = _git_changed_paths(last_sha, head)
            except Exception:  # noqa: BLE001 - fail open
                changed = None
    _emit_gate(*gate_decision(event, last_sha, head, changed))
    return 0


def pass_lines_from_report(report: dict) -> list[tuple[str, str]]:
    """Extract (title, status) rows from a Playwright JSON report.

    A `test.step` whose title is a Pass sentence becomes one row. Specs that
    wrap every Pass line in a step (the membership UAT) produce a table a
    person can read without opening the HTML report. Specs without steps still
    contribute their test title.
    """
    rows: list[tuple[str, str]] = []

    def walk_specs(suites: list) -> None:
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    results = test.get("results") or []
                    status = (
                        results[-1].get("status", "unknown") if results else "unknown"
                    )
                    steps = []
                    for result in results:
                        steps.extend(result.get("steps") or [])
                    if steps:
                        for step in steps:
                            rows.append((str(step.get("title", "")), status))
                    else:
                        rows.append((str(spec.get("title", "")), status))
            walk_specs(suite.get("suites") or [])

    walk_specs(report.get("suites") or [])
    return rows


def render_summary(rows: list[tuple[str, str]]) -> str:
    """Markdown table of Pass lines for $GITHUB_STEP_SUMMARY."""
    if not rows:
        return "### UAT results\n\nNo steps were recorded.\n"
    lines = [
        "### UAT results",
        "",
        "| Status | Step |",
        "| --- | --- |",
    ]
    for title, status in rows:
        safe = title.replace("|", "\\|")
        lines.append(f"| {status} | {safe} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def cmd_summary(args: argparse.Namespace) -> int:
    path = Path(args.report)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"could not read report: {exc}", file=sys.stderr)
        return 1
    text = render_summary(pass_lines_from_report(report))
    print(text, end="")
    _write("GITHUB_STEP_SUMMARY", text)
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    def list_artifacts() -> list[dict]:
        out = _gh(
            [
                "api",
                "--paginate",
                f"repos/{repo}/actions/artifacts?per_page=100",
                "--jq",
                ".artifacts[]",
            ]
        )
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def delete_artifact(art_id: int) -> None:
        _gh(["api", "-X", "DELETE", f"repos/{repo}/actions/artifacts/{art_id}"])

    lines: list[str] = []

    def log(line: str) -> None:
        lines.append(line)
        print(line)

    status = prune(
        list_artifacts,
        delete_artifact,
        current_run_id=args.current_run,
        keep=args.keep,
        dry_run=args.dry_run,
        log=log,
    )
    mode = "dry run" if args.dry_run else "live"
    _write(
        "GITHUB_STEP_SUMMARY",
        f"### UAT evidence retention ({mode})\n\n```\n" + "\n".join(lines) + "\n```\n",
    )
    return status


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("gate", help="decide whether the suite should run").set_defaults(
        func=cmd_gate
    )

    s = sub.add_parser(
        "summary", help="write a Pass-line table from a Playwright JSON report"
    )
    s.add_argument("report", help="path to the Playwright JSON report")
    s.set_defaults(func=cmd_summary)

    p = sub.add_parser("prune", help="delete evidence older than the last N runs")
    p.add_argument("--current-run", type=int, required=True, help="this run's id")
    p.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be deleted and delete nothing",
    )
    p.set_defaults(func=cmd_prune)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
