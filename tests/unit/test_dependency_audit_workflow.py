"""Where the dependency audit runs, and what it can fail (#594).

The audit used to run on every pull request against the whole locked
environment. The lockfile is fixed and the advisory database is not, so a PR
that touched no dependency failed whenever an advisory had been published since
the last bump — and that was the only alerting there was. Five weeks without a
run let 99 advisories pile up in silence.

The rule these pin: a PR's audit answers for the PR's own dependency changes;
drift on ``main`` is found on a schedule and reported to maintainers; a release
cannot ship a known vulnerability.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS = _ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict:
    return yaml.safe_load((_WORKFLOWS / name).read_text(encoding="utf-8"))


def _audit_steps(job: dict) -> list[dict]:
    return [s for s in job["steps"] if "make audit" in str(s.get("run", ""))]


def test_every_workflow_audits_through_one_definition():
    """One recipe, runnable locally, so CI and a laptop cannot disagree."""
    for path in _WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "pip-audit" not in text, f"{path.name} calls pip-audit directly"


def _audit_recipe() -> str:
    recipe = re.search(
        r"^audit:.*?(?=^\S|\Z)", (_ROOT / "Makefile").read_text(), re.S | re.M
    )
    assert recipe, "no `audit` target in the Makefile"
    return recipe.group(0)


def test_the_audit_reads_the_lockfile_not_the_venv():
    """The venv also holds whatever tools CI installed to run the audit."""
    assert "uv export" in _audit_recipe()


def test_the_audit_covers_the_frontend_lockfile():
    """#601: 81 npm advisories accrued because only Python was audited.

    Moderate and low are tolerated: what remains there is dev tooling whose
    only fix is a downgrade or a major upgrade.
    """
    recipe = _audit_recipe()
    assert "npm audit" in recipe and "--package-lock-only" in recipe
    assert "--audit-level=high" in recipe


def test_a_pull_request_audits_only_its_own_dependency_changes():
    ci = _workflow("ci-cd.yml")
    changes = ci["jobs"]["changes"]
    assert "deps" in changes["outputs"]
    filter_script = "\n".join(str(s.get("run", "")) for s in changes["steps"])
    for lockfile in (r"pyproject\.toml", r"uv\.lock", r"frontend/package"):
        assert lockfile in filter_script

    security = ci["jobs"]["security"]
    assert "changes" in security["needs"]
    [step] = _audit_steps(security)
    assert "needs.changes.outputs.deps" in step["if"]


def test_a_release_always_audits():
    [step] = [
        s for j in _workflow("release.yml")["jobs"].values() for s in _audit_steps(j)
    ]
    assert "if" not in step


def test_the_image_scan_on_main_replaces_the_code_scanning_alerts():
    """Its alerts froze in Dec 2025 when the scan was dropped, so they could never close.

    Uploading under the old category supersedes that analysis. Like the audit,
    the scan reports rather than gates: its database moves without the code.
    """
    job = _workflow("docker-build-test.yml")["jobs"]["docker-test"]
    assert job["permissions"]["security-events"] == "write"
    [scan] = [s for s in job["steps"] if "trivy-action" in s.get("uses", "")]
    [upload] = [s for s in job["steps"] if "upload-sarif" in s.get("uses", "")]
    assert re.fullmatch(r"aquasecurity/trivy-action@[0-9a-f]{40}", scan["uses"])
    assert scan["with"]["image-ref"] == "${{ env.IMAGE }}:test"
    assert scan["with"]["exit-code"] == "0"
    assert upload["with"]["category"] == ".github/workflows/ci-cd.yml:security"
    for step in (scan, upload):
        assert "github.event_name != 'pull_request'" in step["if"]


def test_drift_on_main_is_found_on_a_schedule_and_reported():
    scheduled = _workflow("dependency-audit.yml")
    # PyYAML reads the bare `on:` key as boolean True.
    triggers = scheduled.get("on", scheduled.get(True))
    assert "schedule" in triggers
    assert scheduled["permissions"]["issues"] == "write"
    [job] = scheduled["jobs"].values()
    assert _audit_steps(job)
    report = [s for s in job["steps"] if "failure()" in str(s.get("if", ""))]
    assert report and "gh issue" in report[0]["run"]


def test_dependabot_raises_security_fixes_for_both_lockfiles():
    config = yaml.safe_load((_ROOT / ".github" / "dependabot.yml").read_text())
    ecosystems = {(u["package-ecosystem"], u["directory"]) for u in config["updates"]}
    assert {("uv", "/"), ("npm", "/frontend")} <= ecosystems
