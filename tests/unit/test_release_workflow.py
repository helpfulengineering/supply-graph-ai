"""Invariants of the release pipeline that are expensive to get wrong.

These are ordering and gating properties, not syntax checks. They exist because
the failure modes they guard against are silent: a worker rolled after the API,
or on a different image, produces jobs that SUCCEED and return subtly wrong
manifests — far worse than an outage, because nothing alerts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release.yml"

DIGEST_EXPR = "needs.publish.outputs.digest"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _steps(workflow: dict, job: str) -> list[dict]:
    return workflow["jobs"][job]["steps"]


def _run_text(workflow: dict, job: str) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(workflow, job))


def test_worker_deploys_before_the_api(workflow):
    """Consumer before producer: the API must never enqueue work for stale code."""
    assert "deploy-worker" in workflow["jobs"]
    assert "deploy-worker" in workflow["jobs"]["deploy-azure"]["needs"]


def test_worker_and_api_deploy_the_same_digest(workflow):
    """Pinned to one digest, so the two cannot run different code."""
    for job in ("deploy-worker", "deploy-azure"):
        assert DIGEST_EXPR in _run_text(workflow, job), job


def test_worker_deploy_is_gated_like_the_api_deploy(workflow):
    """One production approval covers the release; no unguarded side door."""
    worker = workflow["jobs"]["deploy-worker"]
    api = workflow["jobs"]["deploy-azure"]

    assert worker["environment"] == api["environment"] == "production"
    assert worker["if"] == api["if"]
    assert worker["permissions"] == api["permissions"]


def test_worker_deploy_verifies_the_rolled_image(workflow):
    """The worker has no HTTP endpoint, so identity is checked via the revision."""
    run_text = _run_text(workflow, "deploy-worker")

    assert "containerapp revision list" in run_text
    assert "properties.active" in run_text
    assert "EXPECTED_IMAGE" in run_text


def test_async_generation_probe_is_the_final_gate(workflow):
    """The only check that proves the whole path, not just that pods rolled."""
    steps = _steps(workflow, "deploy-azure")
    last = steps[-1]

    assert "probe_async_generation" in str(last.get("run", ""))


def test_release_deploys_worker_api_and_frontend(workflow):
    """A release with no functional change must still roll every component."""
    jobs = workflow["jobs"]
    for job in ("deploy-worker", "deploy-azure", "deploy-frontend-azure"):
        assert job in jobs, job
        assert jobs[job]["environment"] == "production"
