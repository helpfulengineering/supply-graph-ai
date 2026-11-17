"""The decisions behind the weekly UAT workflow: when to run, and what to delete.

`scripts/uat_ci.py` holds two judgements that GitHub Actions cannot express by
itself. A cron cannot skip itself, so `gate` decides whether anything worth
re-testing has landed. `retention-days` counts days, not runs, so `prune` decides
which runs keep their evidence. Both are pure functions here so they can be pinned
without a runner; the `gh` calls around them are thin.

The shapes are the ones `gh` returns: runs from `gh run list --json`, artifacts
from the REST artifacts listing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "uat_ci.py"


def _load():
    spec = importlib.util.spec_from_file_location("uat_ci", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


uat = _load()


def run(sha: str, conclusion: str) -> dict:
    return {"headSha": sha, "conclusion": conclusion}


def artifact(
    art_id: int, run_id: int, created: str, name: str = "uat-membership-evidence"
) -> dict:
    return {
        "id": art_id,
        "name": name,
        "size_in_bytes": 1000,
        "created_at": created,
        "expired": False,
        "workflow_run": {"id": run_id},
    }


# --- last_executed_run -------------------------------------------------------


def test_last_executed_run_skips_runs_that_did_not_execute():
    runs = [run("c", "skipped"), run("b", ""), run("a", "success")]
    assert uat.last_executed_run(runs)["headSha"] == "a"


def test_last_executed_run_counts_a_failure():
    assert (
        uat.last_executed_run([run("b", "failure"), run("a", "success")])["headSha"]
        == "b"
    )


def test_last_executed_run_ignores_cancelled():
    # A cancelled run stopped before it could say anything about the code.
    runs = [run("b", "cancelled"), run("a", "success")]
    assert uat.last_executed_run(runs)["headSha"] == "a"


def test_last_executed_run_is_none_without_history():
    assert uat.last_executed_run([]) is None
    assert uat.last_executed_run([run("a", "skipped")]) is None


# --- is_code_change ----------------------------------------------------------


@pytest.mark.parametrize(
    "paths",
    [
        ["README.md"],
        ["docs/architecture/identity-model.md"],
        ["docs-site/docs/guides/join-a-node.md"],
        ["notes/uat-ci-proposal.md"],
        ["docs/img/diagram.png", "CHANGELOG.md"],
    ],
)
def test_documentation_only_is_not_a_code_change(paths):
    assert uat.is_code_change(paths) is False


@pytest.mark.parametrize(
    "paths",
    [
        ["src/core/auth/registration.py"],
        ["frontend/src/features/auth/RegisterView.tsx"],
        [".github/workflows/uat-e2e.yml"],
        ["docker-compose.yml"],
        ["README.md", "src/cli/identity.py"],
    ],
)
def test_any_source_file_is_a_code_change(paths):
    assert uat.is_code_change(paths) is True


def test_no_changed_files_is_not_a_code_change():
    assert uat.is_code_change([]) is False


# --- gate_decision -----------------------------------------------------------


def test_manual_dispatch_always_runs():
    go, reason = uat.gate_decision("workflow_dispatch", "same", "same", ["README.md"])
    assert go is True
    assert "manual" in reason


def test_no_earlier_run_runs():
    go, reason = uat.gate_decision("schedule", None, "head", ["README.md"])
    assert go is True
    assert "no earlier run" in reason


def test_an_unreadable_diff_fails_open():
    go, reason = uat.gate_decision("schedule", "old", "head", None)
    assert go is True
    assert "could not" in reason


def test_same_sha_skips():
    go, reason = uat.gate_decision("schedule", "abc", "abc", [])
    assert go is False
    assert "since the last run" in reason


def test_docs_only_since_last_run_skips():
    go, reason = uat.gate_decision(
        "schedule", "old", "new", ["docs-site/docs/guides/x.md", "notes/y.md"]
    )
    assert go is False
    assert "documentation" in reason


def test_code_since_last_run_runs():
    go, _ = uat.gate_decision(
        "schedule", "old", "new", ["docs/x.md", "src/core/auth/invites.py"]
    )
    assert go is True


def test_a_new_sha_with_no_changed_files_skips():
    go, _ = uat.gate_decision("schedule", "old", "new", [])
    assert go is False


# --- plan_prune --------------------------------------------------------------


def _four_runs():
    return [
        artifact(1, 101, "2026-11-02T07:30:00Z"),
        artifact(2, 102, "2026-11-09T07:30:00Z"),
        artifact(3, 103, "2026-11-16T07:30:00Z"),
        artifact(4, 104, "2026-11-23T07:30:00Z"),
    ]


def test_keeps_the_current_run_and_the_two_newest_others():
    kept, doomed = uat.plan_prune(_four_runs(), current_run_id=104, keep=3)
    assert {a["workflow_run"]["id"] for a in kept} == {104, 103, 102}
    assert [a["id"] for a in doomed] == [1]


def test_fewer_than_three_runs_deletes_nothing():
    arts = _four_runs()[2:]
    kept, doomed = uat.plan_prune(arts, current_run_id=104, keep=3)
    assert doomed == []
    assert len(kept) == 2


def test_the_current_run_is_kept_even_when_the_listing_lags_its_upload():
    # The listing has not caught up: three older runs, the current one absent.
    arts = _four_runs()[:3]
    kept, doomed = uat.plan_prune(arts, current_run_id=999, keep=3)
    # Current (unlisted) takes one slot, so only the two newest others stay.
    assert {a["workflow_run"]["id"] for a in kept} == {103, 102}
    assert [a["id"] for a in doomed] == [1]


def test_the_current_run_is_never_deleted_even_if_it_looks_oldest():
    arts = _four_runs()
    kept, doomed = uat.plan_prune(arts, current_run_id=101, keep=3)
    assert 101 in {a["workflow_run"]["id"] for a in kept}
    assert 101 not in {a["workflow_run"]["id"] for a in doomed}


def test_both_jobs_of_one_run_count_once():
    arts = [
        artifact(1, 101, "2026-11-02T07:30:00Z", "uat-membership-evidence"),
        artifact(2, 101, "2026-11-02T07:45:00Z", "uat-federation-evidence"),
        artifact(3, 102, "2026-11-09T07:30:00Z", "uat-membership-evidence"),
        artifact(4, 102, "2026-11-09T07:45:00Z", "uat-federation-evidence"),
        artifact(5, 103, "2026-11-16T07:30:00Z", "uat-membership-evidence"),
        artifact(6, 103, "2026-11-16T07:45:00Z", "uat-federation-evidence"),
    ]
    kept, doomed = uat.plan_prune(arts, current_run_id=103, keep=3)
    assert doomed == []
    assert len(kept) == 6


def test_deletes_every_artifact_of_an_old_run():
    arts = _four_runs() + [
        artifact(5, 101, "2026-11-02T07:45:00Z", "uat-federation-evidence")
    ]
    _kept, doomed = uat.plan_prune(arts, current_run_id=104, keep=3)
    assert sorted(a["id"] for a in doomed) == [1, 5]


def test_artifacts_that_are_not_ours_are_never_touched():
    arts = _four_runs() + [
        artifact(90, 50, "2026-01-01T00:00:00Z", "playwright-report"),
        artifact(91, 51, "2026-01-01T00:00:00Z", "coverage"),
    ]
    kept, doomed = uat.plan_prune(arts, current_run_id=104, keep=3)
    touched = {a["id"] for a in kept} | {a["id"] for a in doomed}
    assert 90 not in touched and 91 not in touched


def test_expired_artifacts_are_not_planned():
    arts = _four_runs()
    arts[0] = {**arts[0], "expired": True}
    _kept, doomed = uat.plan_prune(arts, current_run_id=104, keep=3)
    assert doomed == []


# --- prune (the part that deletes) ------------------------------------------


def test_a_dry_run_deletes_nothing_and_says_what_it_would():
    deleted: list[int] = []
    lines: list[str] = []
    uat.prune(
        list_artifacts=_four_runs,
        delete_artifact=deleted.append,
        current_run_id=104,
        keep=3,
        dry_run=True,
        log=lines.append,
    )
    assert deleted == []
    assert any("would delete" in line.lower() for line in lines)


def test_a_live_run_deletes_exactly_what_was_planned():
    deleted: list[int] = []
    uat.prune(
        list_artifacts=_four_runs,
        delete_artifact=deleted.append,
        current_run_id=104,
        keep=3,
        dry_run=False,
        log=lambda _line: None,
    )
    assert deleted == [1]


def test_a_failed_delete_does_not_stop_the_rest():
    deleted: list[int] = []

    def flaky(art_id: int) -> None:
        if art_id == 1:
            raise RuntimeError("boom")
        deleted.append(art_id)

    arts = _four_runs() + [
        artifact(7, 100, "2026-10-26T07:30:00Z"),
    ]
    status = uat.prune(
        list_artifacts=lambda: arts,
        delete_artifact=flaky,
        current_run_id=104,
        keep=3,
        dry_run=False,
        log=lambda _line: None,
    )
    assert 7 in deleted
    assert status != 0


def test_an_unreadable_listing_deletes_nothing():
    def boom():
        raise RuntimeError("no network")

    deleted: list[int] = []
    status = uat.prune(
        list_artifacts=boom,
        delete_artifact=deleted.append,
        current_run_id=104,
        keep=3,
        dry_run=False,
        log=lambda _line: None,
    )
    assert deleted == []
    assert status != 0


# --- summary -----------------------------------------------------------------


def test_pass_lines_prefer_steps_over_the_test_title():
    report = {
        "suites": [
            {
                "specs": [
                    {
                        "title": "outer",
                        "tests": [
                            {
                                "results": [
                                    {
                                        "status": "passed",
                                        "steps": [
                                            {
                                                "title": "the form is there",
                                            }
                                        ],
                                    }
                                ]
                            }
                        ],
                    }
                ],
                "suites": [],
            }
        ]
    }
    rows = uat.pass_lines_from_report(report)
    assert rows == [("the form is there", "passed")]


def test_a_spec_without_steps_uses_its_title():
    report = {
        "suites": [
            {
                "specs": [
                    {
                        "title": "mint the operator",
                        "tests": [{"results": [{"status": "failed", "steps": []}]}],
                    }
                ],
                "suites": [],
            }
        ]
    }
    assert uat.pass_lines_from_report(report) == [("mint the operator", "failed")]


def test_render_summary_is_a_markdown_table():
    text = uat.render_summary([("the form is there", "passed")])
    assert "| Status | Step |" in text
    assert "| passed | the form is there |" in text
