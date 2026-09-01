"""A tag must never deploy to production.

Publishing and deploying are different acts. Pushing `vX.Y.Z` builds the
images, publishes them, and creates the GitHub Release; putting that on
production is a deliberate second step, run from the Actions tab with
``deploy: true``.

It was not always so. `deploy-worker`, `deploy-azure` and
`deploy-frontend-azure` each began with ``github.event_name == 'push'``, so a
tag went straight to production — while a *manual* run already had to ask for
`deploy: true`. Tags were the unguarded path, which is the wrong way round: a
tag is a routine act and a deploy is not. The `production` environment has no
required reviewers either, so nothing prompted.

The GitHub-native form of this rule is required reviewers on that environment,
which needs repo admin to configure. This is the part that lives in the repo,
and it fails in one direction only: a deploy job that would run on a push.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

#: A job is a deployment if its name says so or it targets an environment.
#: Both, because either alone is forgeable by a rename.
DEPLOY_ENVIRONMENTS = {"production"}


def _deploy_jobs(workflow: dict) -> dict[str, dict]:
    jobs = workflow.get("jobs") or {}
    return {
        name: job
        for name, job in jobs.items()
        if name.startswith("deploy")
        or str(job.get("environment", "")) in DEPLOY_ENVIRONMENTS
    }


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_no_deploy_job_runs_on_a_tag_push(path: Path) -> None:
    workflow = yaml.safe_load(path.read_text()) or {}
    offenders: list[str] = []

    for name, job in _deploy_jobs(workflow).items():
        condition = " ".join(str(job.get("if", "")).split())
        if not condition:
            # No condition at all means it runs on every trigger, including a
            # tag push — the same failure, spelled differently.
            offenders.append(f"{name}: no `if:` at all, so a tag push runs it")
        elif "event_name == 'push'" in condition:
            offenders.append(f"{name}: `if:` keys on a push event\n        {condition}")

    assert not offenders, (
        f"{path.name}: deploy jobs that a tag push would run:\n    "
        + "\n    ".join(offenders)
        + "\n-> Publishing is not deploying. Gate the job on "
        "`workflow_dispatch` with `deploy == true`, so putting a release on "
        "production stays a deliberate act. See docs/RELEASE.md."
    )
