"""Global pytest configuration: lane markers, network guardrails, timeout diagnostics."""

from __future__ import annotations

import socket
import sys
import threading
import traceback
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent

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
        lane = _lane_for_path(path)
        if lane is None:
            continue
        if lane not in {mark.name for mark in item.iter_markers()}:
            item.add_marker(getattr(pytest.mark, lane))


@pytest.fixture(autouse=True)
def _block_external_network(
    request: pytest.Request, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Block outbound network for contract tests unless explicitly opted out."""
    if request.node.get_closest_marker("allow_network"):
        return
    if not request.node.get_closest_marker("contract"):
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
