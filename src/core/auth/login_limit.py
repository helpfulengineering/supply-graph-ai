"""Per-username login slowdown (#570).

Five failures inside fifteen minutes, then one attempt a minute until fifteen
quiet minutes. This is a slowdown, not a lockout: a correct password still
works, once a minute. In-process, same limit as the IP counters — two
replicas each keep their own count (#414).
"""

from __future__ import annotations

import time

_WINDOW_SECONDS = 15 * 60
_SLOWDOWN_SECONDS = 60
_FAILURES_BEFORE_SLOWDOWN = 5

_attempts: dict[str, list[float]] = {}


def _now(now: float | None) -> float:
    return time.monotonic() if now is None else now


def _recent(username: str, now: float) -> list[float]:
    kept = [t for t in _attempts.get(username, []) if now - t < _WINDOW_SECONDS]
    _attempts[username] = kept
    return kept


def login_blocked(username: str, now: float | None = None) -> bool:
    moment = _now(now)
    recent = _recent(username, moment)
    if len(recent) < _FAILURES_BEFORE_SLOWDOWN:
        return False
    return moment - recent[-1] < _SLOWDOWN_SECONDS


def note_login_failure(username: str, now: float | None = None) -> None:
    moment = _now(now)
    _recent(username, moment)
    _attempts.setdefault(username, []).append(moment)


def clear_login_attempts(username: str | None = None) -> None:
    if username is None:
        _attempts.clear()
    else:
        _attempts.pop(username, None)
