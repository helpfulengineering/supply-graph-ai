"""The generate-from-url run log: every stage survives, whatever the poll rate.

Job status reports the stage a run is *on*. Celery's ``update_state``
overwrites its meta, so a client polling that field samples the timeline rather
than receiving it: a stage shorter than the interval between two polls is never
observed at all. The early stages carry small weights against ``llm``'s
dominant one, so on a fast repository several can pass unseen — and a record of
"what was done" cannot be built from a channel that only ever holds the present
moment.

The fix is to publish the cumulative log on every update instead of the latest
event. These tests pin that property from both ends: the worker writes the whole
log, and the reader pages through it.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from src.core.jobs import generation_jobs
from src.core.jobs.tasks import generate_from_url_task

STAGES = [
    ("clone", 0.0),
    ("direct", 0.12),
    ("heuristic", 0.17),
    ("nlp", 0.25),
    ("llm", 0.40),
    ("quality", 0.95),
]


def _run_emitting_stages(published: List[Dict[str, Any]]):
    """Run the real task against a fake generator, capturing every publish."""

    async def fake_generate(*, progress=None, **_kwargs):
        for stage, fraction in STAGES:
            progress(stage, fraction, f"{stage} running")
        return {"manifest": {"title": "Fixture"}}

    def record(*, state, meta):  # noqa: ARG001 - state is always PROGRESS here
        # A snapshot of what a client polling at this instant would receive.
        published.append({"events": list(meta.get("events") or [])})

    with (
        patch("src.core.jobs.tasks._run_generate_from_url", fake_generate),
        patch.object(generate_from_url_task, "update_state", record),
    ):
        return generate_from_url_task(url="https://github.com/a/one")


def test_a_poll_at_any_moment_sees_every_stage_so_far():
    """The regression: a slow poller must not miss a short stage.

    Reading only the last publish — the worst case for a client that polled
    once, late — still yields the complete ordered log. Before this, that read
    returned a single stage and the five before it were unrecoverable.
    """
    published: List[Dict[str, Any]] = []
    _run_emitting_stages(published)

    assert len(published) == len(STAGES)
    latest = published[-1]["events"]
    assert [event["stage"] for event in latest] == [stage for stage, _ in STAGES]

    # And a client that happened to poll in the middle sees everything up to
    # that point, not just the stage in flight.
    midpoint = published[2]["events"]
    assert [event["stage"] for event in midpoint] == ["clone", "direct", "heuristic"]


def test_the_log_survives_completion():
    """Celery replaces meta with the return value, so the log rides in both."""
    published: List[Dict[str, Any]] = []
    payload = _run_emitting_stages(published)

    assert [event["stage"] for event in payload["events"]] == [
        stage for stage, _ in STAGES
    ]


def test_events_are_ordered_and_numbered():
    published: List[Dict[str, Any]] = []
    payload = _run_emitting_stages(published)

    assert [event["seq"] for event in payload["events"]] == list(range(len(STAGES)))
    fractions = [event["fraction"] for event in payload["events"]]
    assert fractions == sorted(fractions), "progress must not go backwards"
    assert all(event["ts"] for event in payload["events"])


class _FakeResult:
    def __init__(self, state: str, info: Any = None, result: Any = None):
        self.state = state
        self.info = info
        self.result = result


def _events(state: str, *, info=None, result=None, since: int = 0):
    with patch.object(
        generation_jobs,
        "AsyncResult",
        lambda *_a, **_k: _FakeResult(state, info, result),
    ):
        return generation_jobs.get_job_events("job-1", since=since)


LOG = [
    {"seq": 0, "stage": "clone", "fraction": 0.0, "message": None, "ts": "t0"},
    {"seq": 1, "stage": "direct", "fraction": 0.12, "message": None, "ts": "t1"},
    {"seq": 2, "stage": "nlp", "fraction": 0.25, "message": None, "ts": "t2"},
]


def test_since_returns_only_what_the_caller_has_not_seen():
    page = _events("PROGRESS", info={"events": LOG}, since=2)
    assert [event["stage"] for event in page["events"]] == ["nlp"]
    assert page["next_cursor"] == 3


def test_next_cursor_spans_the_whole_log_not_the_page():
    """Otherwise a caller that skipped ahead would re-read events it has."""
    first = _events("PROGRESS", info={"events": LOG})
    assert first["next_cursor"] == 3
    assert (
        _events("PROGRESS", info={"events": LOG}, since=first["next_cursor"])["events"]
        == []
    )


def test_reading_past_the_end_is_an_empty_page_not_an_error():
    page = _events("PROGRESS", info={"events": LOG}, since=99)
    assert page["events"] == []
    assert page["next_cursor"] == 3


def test_events_are_read_from_the_result_once_the_job_succeeds():
    page = _events("SUCCESS", info={}, result={"events": LOG, "manifest": {}})
    assert [event["stage"] for event in page["events"]] == ["clone", "direct", "nlp"]
    assert page["state"] == "SUCCESS"


def test_a_job_with_no_events_yet_reports_an_empty_log():
    page = _events("PENDING", info=None)
    assert page == {
        "job_id": "job-1",
        "state": "PENDING",
        "events": [],
        "next_cursor": 0,
    }
