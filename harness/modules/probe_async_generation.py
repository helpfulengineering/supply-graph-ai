"""Probe: async generate-from-url jobs actually complete.

This is the health signal for the Celery worker. A liveness probe would be
weaker: ACA probes are HTTP/TCP only, a worker serves no HTTP, and a worker
whose pool is wedged still answers ``celery inspect ping`` from its main
process while consuming nothing.

The failure this exists to catch is the quiet one. ``enforce_job_capacity``
swallows broker-inspect failures and returns zero counts, so when no worker is
consuming, submissions are *accepted* and then sit in PENDING forever — no
error, no timeout, a progress bar at 0%. Only an end-to-end submit-and-poll
sees it.

Runs heuristic-only (``no_llm``) by default: it exercises the same submit →
broker → worker → result path, but stays fast, deterministic, and free of LLM
spend for something that may run on every release. Set ``no_llm: false`` in the
module options to exercise the LLM-enabled path users get from the UI.
"""

from __future__ import annotations

import time
from typing import Any

from harness.probes.base import ProbeModule
from harness.probes.http import api_request, extract_detail
from harness.protocol import Finding, FindingKind, Inventory, Observations, Severity

JOBS_PATH = "/okh/generate-from-url/jobs"

# Small, stable, public. The probe is testing the pipeline, not the extractor.
DEFAULT_REPO_URL = "https://github.com/octocat/Hello-World"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_POLL_SECONDS = 5

TERMINAL_STATES = {"SUCCESS", "FAILURE", "REVOKED"}


class ProbeAsyncGenerationLoop(ProbeModule):
    name = "probe_async_generation"

    def _options(self) -> dict[str, Any]:
        return self.module_config.options or {}

    def discover(self) -> Inventory:
        opts = self._options()
        return Inventory(
            items={
                "repo_url": opts.get("repo_url", DEFAULT_REPO_URL),
                "timeout_seconds": opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
                "no_llm": opts.get("no_llm", True),
                "expect_llm": opts.get("expect_llm", False),
                "api_base_url": self.config.api_base_url,
            },
            notes=[
                "Submits a real generate-from-url job and polls to a terminal state",
                "Detects jobs accepted but never consumed (no worker on the broker)",
            ],
        )

    def observe(self) -> Observations:
        opts = self._options()
        repo_url = opts.get("repo_url", DEFAULT_REPO_URL)
        timeout_seconds = float(opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        poll_seconds = float(opts.get("poll_seconds", DEFAULT_POLL_SECONDS))
        no_llm = bool(opts.get("no_llm", True))

        submit = api_request(
            base_url=self.config.api_base_url,
            api_path_prefix=self._api_path_prefix(),
            path=JOBS_PATH,
            method="POST",
            json_body={
                "urls": [repo_url],
                "verbose": False,
                "skip_review": True,
                "clone": True,
                "no_llm": no_llm,
            },
            timeout=60,
        )

        data: dict[str, Any] = {
            "repo_url": repo_url,
            "submit_status": submit.status,
            "no_llm": no_llm,
            "timeout_seconds": timeout_seconds,
        }

        if not submit.ok:
            data["submit_detail"] = extract_detail(submit.body)
            return Observations(
                data=data, notes=[f"submit failed with HTTP {submit.status}"]
            )

        body = submit.body if isinstance(submit.body, dict) else {}
        jobs = body.get("jobs") or []
        job_id = jobs[0].get("job_id") if jobs and isinstance(jobs[0], dict) else None
        data["job_id"] = job_id
        if not job_id:
            data["submit_detail"] = "submit returned no job id"
            return Observations(data=data, notes=["submit returned no job id"])

        states_seen: list[str] = []
        stages_seen: list[str] = []
        state = "PENDING"
        status_body: dict[str, Any] = {}
        started = time.monotonic()

        while time.monotonic() - started < timeout_seconds:
            status = api_request(
                base_url=self.config.api_base_url,
                api_path_prefix=self._api_path_prefix(),
                path=f"{JOBS_PATH}/{job_id}",
                timeout=30,
            )
            if isinstance(status.body, dict):
                status_body = status.body
                state = str(status_body.get("state") or "PENDING")
                if not states_seen or states_seen[-1] != state:
                    states_seen.append(state)
                stage = status_body.get("stage")
                if stage and (not stages_seen or stages_seen[-1] != stage):
                    stages_seen.append(str(stage))
            if state in TERMINAL_STATES:
                break
            time.sleep(poll_seconds)

        elapsed = time.monotonic() - started
        quality = status_body.get("quality_report") or {}
        data.update(
            {
                "state": state,
                "states_seen": states_seen,
                "stages_seen": stages_seen,
                "elapsed_seconds": round(elapsed, 1),
                "timed_out": state not in TERMINAL_STATES,
                "has_manifest": bool(status_body.get("manifest")),
                "job_error": status_body.get("error"),
                "llm_used": quality.get("llm_used"),
                "llm_status": quality.get("llm_status"),
            }
        )

        # Do not leave an unfinished job running after a timeout.
        if state not in TERMINAL_STATES:
            api_request(
                base_url=self.config.api_base_url,
                api_path_prefix=self._api_path_prefix(),
                path=f"{JOBS_PATH}/{job_id}/revoke",
                method="POST",
                timeout=30,
            )
            data["revoked_after_timeout"] = True

        return Observations(
            data=data,
            notes=[f"state={state} after {elapsed:.1f}s stages={stages_seen}"],
        )

    def judge(self, observations: Observations) -> list[Finding]:
        data = observations.data
        findings: list[Finding] = []
        submit_status = int(data.get("submit_status") or 0)

        if submit_status == 503:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.ERROR,
                    title="Async generation is not enabled on this node",
                    evidence={
                        "detail": data.get("submit_detail"),
                        "recommendation": (
                            "Set JOBS_ENABLED=true and JOB_BROKER_URL on the API, "
                            "and deploy the Celery worker."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )
            return findings

        if submit_status == 429:
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.GAP,
                    severity=Severity.WARN,
                    title="Generation job submission was rate limited",
                    evidence={
                        "detail": data.get("submit_detail"),
                        "recommendation": (
                            "Transient if the per-IP limit or the concurrency cap "
                            "was hit; re-run. Persistent means the caps are too "
                            "tight or jobs are not draining."
                        ),
                    },
                    suggested_state="needs-triage",
                )
            )
            return findings

        if submit_status < 200 or submit_status >= 300 or not data.get("job_id"):
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title=f"Generation job submission failed (HTTP {submit_status})",
                    evidence={"detail": data.get("submit_detail")},
                    suggested_state="needs-triage",
                )
            )
            return findings

        if data.get("timed_out"):
            never_started = set(data.get("states_seen") or []) <= {"PENDING"}
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title=(
                        "Generation job was accepted but never consumed"
                        if never_started
                        else "Generation job did not finish within the time budget"
                    ),
                    evidence={
                        "job_id": data.get("job_id"),
                        "states_seen": data.get("states_seen"),
                        "elapsed_seconds": data.get("elapsed_seconds"),
                        "recommendation": (
                            "No worker is consuming the broker queue. Check the "
                            "worker container app is running and that its "
                            "JOB_BROKER_URL matches the API's."
                            if never_started
                            else "Check worker logs; the repository may be large "
                            "or the worker starved."
                        ),
                    },
                    suggested_state="ready-for-human",
                )
            )
            return findings

        state = data.get("state")
        if state == "FAILURE":
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title="Generation job failed",
                    evidence={
                        "job_id": data.get("job_id"),
                        "error": data.get("job_error"),
                        "stages_seen": data.get("stages_seen"),
                    },
                    suggested_state="needs-triage",
                )
            )
        elif state == "REVOKED":
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title="Generation job was revoked unexpectedly",
                    evidence={"job_id": data.get("job_id")},
                    suggested_state="needs-triage",
                )
            )
        elif (
            state == "SUCCESS"
            and self._options().get("expect_llm")
            and not data.get("llm_used")
        ):
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title="Generation succeeded but ran without an LLM",
                    evidence={
                        "llm_status": data.get("llm_status"),
                        "recommendation": (
                            "This node is expected to have an LLM provider "
                            "configured. 'not_configured' means the credential is "
                            "missing; 'disabled' means LLM_ENABLED is false; "
                            "'failed' means the provider could not be reached."
                        ),
                    },
                    suggested_state="needs-triage",
                )
            )
        elif state == "SUCCESS" and not data.get("has_manifest"):
            findings.append(
                Finding(
                    module=self.name,
                    kind=FindingKind.BUG,
                    severity=Severity.ERROR,
                    title="Generation job succeeded but returned no manifest",
                    evidence={"job_id": data.get("job_id")},
                    suggested_state="needs-triage",
                )
            )

        return findings
