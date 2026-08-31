"""One storage setup, shared by every caller (#372).

Connecting to a provider, proving the connection works, and establishing the
top-level prefixes was implemented three times over: a standalone bootstrap
script, a CLI helper module, and a CLI command — with a configuration API about
to become a fourth. The copies had drifted in ways that mattered:

- The script created three prefixes and never ``packages/``.
- The script re-stamped every placeholder on each run, giving established
  directories a new ``created_at`` for no gain; the organizer had already been
  fixed not to.
- The script skipped the metadata sanitisation blob backends need.
- The two in-app callers went through ``StorageService.configure``, which
  **swallows connection failures by design** so the API can boot degraded.
  Setup inherited that and reported success on a backend it had never reached:
  against an unusable path it printed "✅ Storage directory structure created
  successfully!" and "Created 0 directories" and exited 0.

So verification here is explicit and is the point. ``configure`` is not used:
this connects the manager directly and then proves the connection with a real
round trip — write a probe object, read it back, compare, delete it. Credentials
that authenticate but cannot write are caught by that, and a listing call would
not catch them.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ...config.storage_config import StorageConfig
from ..storage.manager import StorageManager
from ..storage.organizer import StorageOrganizer
from ..utils.logging import get_logger

logger = get_logger(__name__)

# The probe object's key. Deliberately flat rather than under a prefix: the
# local backend creates a real directory per key prefix and deleting the object
# does not remove it, so a namespaced probe left an empty `_ohm-setup-probe/`
# behind on every run. Blob backends have no directories and do not care either
# way.
_PROBE_KEY_PREFIX = "_ohm-setup-probe-"


class StorageSetupError(RuntimeError):
    """Setup could not reach, or could not write to, the configured backend."""


@dataclass
class StorageSetupResult:
    """What setup found and what it had to do.

    ``prefixes_found`` versus ``prefixes_created`` is the distinction callers
    need: a second run against the same backend finds everything and creates
    nothing, which is a successful no-op rather than a failure to act.
    """

    provider: str
    bucket: str
    location: str
    verified: bool
    prefixes_found: List[str] = field(default_factory=list)
    prefixes_created: List[str] = field(default_factory=list)

    @property
    def initialized(self) -> bool:
        """True when this run established at least one prefix."""
        return bool(self.prefixes_created)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "bucket": self.bucket,
            "storage_location": self.location,
            "verified": self.verified,
            "prefixes_found": list(self.prefixes_found),
            "prefixes_created": list(self.prefixes_created),
            "total_found": len(self.prefixes_found),
            "total_created": len(self.prefixes_created),
        }


def _resolve_location(config: StorageConfig) -> str:
    """The bucket, or the absolute path for local storage.

    Local setup is otherwise reported as a relative path, which is ambiguous
    the moment the caller's working directory is not the repo root.
    """
    if config.provider == "local":
        return str(Path(config.bucket_name).resolve())
    return config.bucket_name


async def _verify_round_trip(manager: StorageManager) -> None:
    """Write a probe object, read it back, and remove it.

    A connect that succeeds proves the client was constructed, not that the
    bucket exists or that the credentials may write to it. Only a round trip
    does, which is why setup does this and ``StorageService.configure`` does
    not.
    """
    key = f"{_PROBE_KEY_PREFIX}{uuid.uuid4().hex}.json"
    payload = json.dumps(
        {"probe": "ohm-storage-setup", "at": datetime.now(timezone.utc).isoformat()}
    ).encode("utf-8")

    try:
        await manager.put_object(key=key, data=payload, content_type="application/json")
    except Exception as exc:
        raise StorageSetupError(
            f"Connected, but could not write to the backend: {exc}"
        ) from exc

    try:
        read_back = await manager.get_object(key)
    except Exception as exc:
        raise StorageSetupError(
            f"Wrote a probe object but could not read it back: {exc}"
        ) from exc

    if bytes(read_back) != payload:
        raise StorageSetupError(
            "Probe object read back with different content than was written; "
            "the backend is not storing objects faithfully."
        )

    try:
        await manager.delete_object(key)
    except Exception as exc:
        # The backend works — it is writable and readable — so setup succeeds.
        # Leaving one probe object behind is untidy, not a failure.
        logger.warning("Could not remove the setup probe object %s: %s", key, exc)


async def setup_storage(config: StorageConfig) -> StorageSetupResult:
    """Connect, verify, and validate-or-initialize the directory structure.

    Raises:
        StorageSetupError: the backend could not be reached, or could not be
            written to and read back. Never returns a result describing a
            backend it did not prove.
    """
    manager = StorageManager(config)

    try:
        await manager.connect()
    except Exception as exc:
        raise StorageSetupError(
            f"Could not connect to {config.provider} storage "
            f"'{config.bucket_name}': {exc}"
        ) from exc

    try:
        await _verify_round_trip(manager)

        structure = await StorageOrganizer(manager).create_directory_structure()
        return StorageSetupResult(
            provider=config.provider,
            bucket=config.bucket_name,
            location=_resolve_location(config),
            verified=True,
            prefixes_found=list(structure.get("existing_directories", [])),
            prefixes_created=list(structure.get("created_directories", [])),
        )
    finally:
        try:
            await manager.disconnect()
        except Exception as exc:  # noqa: BLE001 — teardown must not mask a result
            logger.warning("Storage disconnect after setup failed: %s", exc)
