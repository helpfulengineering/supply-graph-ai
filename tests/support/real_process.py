"""Real-process test support (#539 D10).

Some behavior lives in the process boundary itself: clean shutdown vs a `kill
-9`, whether the CLI (a separate, short-lived process) can see what a running
API is doing. An in-process ASGI `TestClient` cannot see any of that — it
never has a second process, and it has no clean-vs-killed distinction. So
these tests run an actual `uvicorn` server as a subprocess and an actual CLI
invocation as a subprocess, exactly like an operator would.

Poll, don't sleep: every wait here is `wait_until` against a real condition,
not a fixed delay, so these tests are fast when the state changes quickly
(sub-second heartbeats in test env vars) and don't flake when it doesn't.
"""

from __future__ import annotations

import json
import select
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAUNCHER = Path(__file__).resolve().with_name("_api_launcher.py")


@dataclass
class ApiProcess:
    process: subprocess.Popen
    port: int

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self, timeout: float = 15.0) -> int:
        """Clean shutdown: SIGTERM, then wait for the real exit. Idempotent."""
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
        return self.process.wait(timeout=timeout)

    def kill(self, timeout: float = 15.0) -> int:
        """Simulate a crash: no lifespan shutdown runs, nothing is cleaned up."""
        if self.process.poll() is None:
            self.process.kill()
        return self.process.wait(timeout=timeout)

    def output(self) -> str:
        try:
            out = self.process.stdout.read() if self.process.stdout else ""
            err = self.process.stderr.read() if self.process.stderr else ""
        except ValueError:
            return "(streams already closed)"
        return f"{out}\n{err}"


def _read_line_with_deadline(pipe, deadline: float) -> str:
    """`pipe.readline()`, but bounded by a wall-clock deadline via `select`.

    A plain `readline()` blocks indefinitely if the process hangs before
    writing anything, which would turn a real bug into a stuck test suite
    instead of a clear timeout.
    """
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return ""
        ready, _, _ = select.select([pipe], [], [], min(remaining, 0.5))
        if ready:
            line = pipe.readline()
            if line:
                return line


def start_api(env: Dict[str, str], timeout: float = 30.0) -> ApiProcess:
    """Start the real API as a subprocess on an OS-assigned port.

    Reads the port back from the launcher's own report rather than guessing
    one and racing another process for it.
    """
    proc = subprocess.Popen(
        [sys.executable, str(_LAUNCHER)],
        cwd=_REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + timeout
    line = _read_line_with_deadline(proc.stdout, deadline)
    if not line:
        output = proc.stderr.read() if proc.poll() is not None else "(still running)"
        proc.kill()
        proc.wait(timeout=10)
        raise TimeoutError(f"API process never reported a port. stderr: {output}")

    try:
        port = json.loads(line)["port"]
    except (json.JSONDecodeError, KeyError) as exc:
        proc.kill()
        raise RuntimeError(
            f"Could not parse port from launcher output: {line!r}"
        ) from exc

    return ApiProcess(process=proc, port=port)


def run_cli(
    *args: str, env: Dict[str, str], timeout: float = 30.0
) -> subprocess.CompletedProcess:
    """Run the CLI exactly as an operator would: `python -m src.cli ...`."""
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def wait_until(
    predicate: Callable[[], bool], timeout: float = 10.0, interval: float = 0.05
) -> bool:
    """Poll `predicate` until true or `timeout`. Always evaluates at least once."""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)
