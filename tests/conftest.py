"""Global pytest configuration: lane markers, network guardrails, timeout diagnostics."""

from __future__ import annotations

import os
import socket
import sys
import threading
import traceback
from pathlib import Path

import pytest

# Force hermetic local storage for the entire test session, BEFORE any app module
# (and its import-time `load_dotenv()`) is imported by test collection. The
# project `.env` sets `STORAGE_PROVIDER=azure_blob` pointed at a live container;
# `load_dotenv()` uses override=False, so winning the race here keeps the whole
# suite off live Azure. Without this, integration/contract tests hit live storage
# — slow enough to trip the pytest timeout and hang `make ready`. Individual
# tests that exercise other providers still override via monkeypatch (env vars
# take precedence and `get_settings()` is uncached).
os.environ["STORAGE_PROVIDER"] = "local"

_TESTS_ROOT = Path(__file__).resolve().parent

_LANE_MARKERS = frozenset({"unit", "contract", "integration", "e2e", "benchmark"})

_LANE_BY_DIR = {
    "unit": _TESTS_ROOT / "unit",
    "contract": None,  # api + cli handled below
    "integration": _TESTS_ROOT / "integration",
}


def _lane_for_path(path: Path) -> str | None:
    rel = path.resolve()
    try:
        rel = rel.relative_to(_TESTS_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    top = parts[0]
    if top == "api" or top == "cli":
        return "contract"
    if top == "federation":
        return "unit"
    if top == "performance" or top == "services":
        return "unit"
    if top == "integration":
        return "integration"
    if top == "unit":
        return "unit"
    return None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        path = Path(str(item.fspath))
        existing = {mark.name for mark in item.iter_markers()}
        # Respect explicit lane markers (e.g. integration tests under tests/api/).
        if existing & _LANE_MARKERS:
            continue
        lane = _lane_for_path(path)
        if lane is None:
            continue
        if lane not in existing:
            item.add_marker(getattr(pytest.mark, lane))


@pytest.fixture(autouse=True)
def _block_external_network(
    request: pytest.Request, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Block outbound network for contract + integration tests unless opted out.

    Integration tests run the app in-process and must stay hermetic (local
    storage, no live Azure). Guarding them here turns an accidental live-storage
    call into a fast, actionable failure instead of a multi-minute hang that
    trips the pytest timeout. Loopback (localhost) stays allowed, so the
    RUN_LIVE_API_TESTS lane against a local dev server is unaffected. Mark a test
    with @pytest.mark.allow_network to opt out.
    """
    if request.node.get_closest_marker("allow_network"):
        return
    if not (
        request.node.get_closest_marker("contract")
        or request.node.get_closest_marker("integration")
    ):
        return

    real_connect = socket.socket.connect

    def guarded_connect(self, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "::1", "localhost"):
            pytest.fail(
                f"External network access blocked in {request.node.nodeid} "
                f"(connect to {host!r}). Mark with @pytest.mark.allow_network if intentional."
            )
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not call.excinfo:
        return
    exc = call.excinfo.value
    if exc.__class__.__name__ != "Failed":
        return
    msg = str(exc)
    if "Timeout" not in msg and "timeout" not in msg.lower():
        return
    threads = []
    for thread in threading.enumerate():
        if thread is threading.current_thread():
            continue
        stack = "".join(traceback.format_stack(sys._current_frames()[thread.ident]))
        threads.append(f"Thread {thread.name} (id={thread.ident}):\n{stack}")
    if threads:
        report.longrepr = (
            f"{report.longrepr}\n\nActive threads at timeout:\n" + "\n".join(threads)
        )
