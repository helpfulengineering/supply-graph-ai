"""Whether an API is really running, seen without asking it over HTTP (#544).

Under the restart-to-apply contract (#539 D1), a saved configuration only takes
effect at the next boot. Two tools need to answer "is there a running API, and
what is it actually serving?" without an HTTP round trip: the CLI, because it
has no way to authenticate to the API (``get_client`` sets no Authorization
header), and both tools while the API is stopped, when there is nothing to ask.

So the API writes a heartbeat marker to local disk, beside the saved
configuration, and this module is the only thing that writes or reads it. The
worker gets no marker: after #543 it never reads or writes the object store,
so it has nothing to report.

**Fails closed.** A marker that cannot be parsed is read as ``running`` — the
one wrong answer that cannot cause data loss. The alternative, reading it as
absent, is what let a separate CLI process wipe a backend a live API was
serving (#543's motivating incident); an unreadable marker must never look
safer than a readable one.

**Single-replica assumption.** Two API processes sharing a marker directory
would overwrite each other's heartbeat; #539's decisions assume switching is a
single-replica operation, and this does not change that.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..utils.logging import get_logger
from .storage_config_store import config_path

logger = get_logger(__name__)

#: Bumped only if the on-disk shape changes incompatibly.
SCHEMA_VERSION = 1

DEFAULT_HEARTBEAT_SECONDS = 15.0

#: A heartbeat older than this many intervals reads as stale rather than
#: running (#544 acceptance criteria).
STALE_INTERVALS = 3

_FILE_MODE = 0o600
_DIR_MODE = 0o700


def heartbeat_seconds() -> float:
    """The beat interval, env-tunable so tests can run it sub-second."""
    override = os.getenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS")
    if override and override.strip():
        try:
            value = float(override)
            if value > 0:
                return value
        except ValueError:
            logger.warning(
                "Ignoring invalid OHM_STORAGE_MARKER_HEARTBEAT_SECONDS=%r",
                override,
            )
    return DEFAULT_HEARTBEAT_SECONDS


def marker_path() -> Path:
    """Where the marker lives: beside the saved storage configuration.

    ``OHM_STORAGE_MARKER_PATH`` overrides it directly, for tests that want a
    marker without a full storage-config fixture.
    """
    override = os.getenv("OHM_STORAGE_MARKER_PATH")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return config_path().parent / "api-live.json"


class LivenessStatus(str, Enum):
    RUNNING = "running"
    STALE = "stale"
    ABSENT = "absent"


@dataclass
class LivenessInfo:
    status: LivenessStatus
    age_seconds: Optional[float]
    provider: Optional[str] = None
    bucket: Optional[str] = None
    pid: Optional[int] = None
    host: Optional[str] = None
    started_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "age_seconds": self.age_seconds,
            "provider": self.provider,
            "bucket": self.bucket,
            "pid": self.pid,
            "host": self.host,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "error": self.error,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=_DIR_MODE)
    if os.stat(path.parent).st_mode & 0o777 != _DIR_MODE:
        os.chmod(path.parent, _DIR_MODE)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.chmod(_FILE_MODE)
    tmp.replace(
        path
    )  # atomic on the same filesystem: a reader never sees a partial file


class MarkerWriter:
    """Owns one API process's heartbeat: written at connect, refreshed on a
    timer, updated on an inline switch, and removed on clean shutdown."""

    def __init__(self, provider: str, bucket: str) -> None:
        self._provider = provider
        self._bucket = bucket
        self._started_at = _now().isoformat()
        self._pid = os.getpid()
        self._host = socket.gethostname()
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    def update_backend(self, provider: str, bucket: str) -> None:
        """Called after an inline switch (#539 D9): the marker must not keep
        reporting the backend this process just left."""
        self._provider = provider
        self._bucket = bucket
        self.beat()

    def beat(self) -> None:
        _atomic_write(
            marker_path(),
            {
                "schema_version": SCHEMA_VERSION,
                "role": "api",
                "provider": self._provider,
                "bucket": self._bucket,
                "pid": self._pid,
                "host": self._host,
                "started_at": self._started_at,
                "heartbeat_at": _now().isoformat(),
            },
        )

    async def _loop(self) -> None:
        interval = heartbeat_seconds()
        while not self._stop.is_set():
            self.beat()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        self.beat()  # visible immediately; the loop's first beat is one interval away
        self._task = asyncio.ensure_future(self._loop())

    async def stop(self, remove: bool = True) -> None:
        """Stop the heartbeat. ``remove=False`` on a crash path would leave the
        marker to age into ``stale`` on its own; every caller here uses the
        default, since this only runs from a clean shutdown."""
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        if remove:
            try:
                marker_path().unlink()
            except FileNotFoundError:
                pass


# One writer per process, matching the single-API-replica assumption (#539).
_active: Optional[MarkerWriter] = None


def start(provider: str, bucket: str) -> MarkerWriter:
    """Start this process's marker. Replaces any writer already running here
    (defensive; production calls this once, at boot)."""
    global _active
    if _active is not None:
        logger.warning("Replacing an already-active storage marker writer")
    _active = MarkerWriter(provider, bucket)
    _active.start()
    return _active


def refresh_backend(provider: str, bucket: str) -> None:
    """Update the active marker after an inline switch. A no-op in a process
    with no marker (the CLI, which never starts one)."""
    if _active is not None:
        _active.update_backend(provider, bucket)


async def stop() -> None:
    global _active
    if _active is not None:
        await _active.stop()
        _active = None


def read(now_fn: Callable[[], datetime] = _now) -> LivenessInfo:
    """The marker's state: running, stale, or absent. Never raises — an
    unreadable marker is reported as ``running`` (fail closed), not surfaced
    as an exception the caller has to remember to treat the same way.
    """
    path = marker_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return LivenessInfo(status=LivenessStatus.ABSENT, age_seconds=None)
    except OSError as exc:
        return LivenessInfo(
            status=LivenessStatus.RUNNING, age_seconds=None, error=str(exc)
        )

    try:
        payload = json.loads(raw)
        heartbeat_at = payload["heartbeat_at"]
        heartbeat_time = datetime.fromisoformat(heartbeat_at)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return LivenessInfo(
            status=LivenessStatus.RUNNING,
            age_seconds=None,
            error=f"unreadable marker: {exc}",
        )

    age = (now_fn() - heartbeat_time).total_seconds()
    stale_after = heartbeat_seconds() * STALE_INTERVALS
    status = LivenessStatus.RUNNING if age < stale_after else LivenessStatus.STALE

    return LivenessInfo(
        status=status,
        age_seconds=age,
        provider=payload.get("provider"),
        bucket=payload.get("bucket"),
        pid=payload.get("pid"),
        host=payload.get("host"),
        started_at=payload.get("started_at"),
        heartbeat_at=heartbeat_at,
    )


def forget() -> bool:
    """Remove a marker known to be dead. True when a file was removed.

    Callers (the CLI's ``--forget``) are expected to have already checked
    ``read()`` reports ``stale`` — this itself does not judge liveness, it
    only performs the deletion, same shape as ``storage_config_store.clear_config``.
    """
    try:
        marker_path().unlink()
        return True
    except FileNotFoundError:
        return False
