"""Moving and erasing storage contents (#381).

Switching providers points an instance at an empty backend and leaves the old
data where it is, invisible. #377 shipped that — the honest simple case. These
are the other two answers an operator needs, so the switch is an explicit
choice rather than a silent one.

Two things here are safety properties rather than features:

**Order.** Validate the destination, copy, verify the copy, and only then swap.
The instance keeps serving from the old backend until the copy verifies, so a
failed or abandoned migration leaves a working instance rather than a
half-empty one. Never swap first.

**The wipe guard survives the trip to HTTP.** ``scripts/clear_storage.py``
protects itself with a dry-run flag and an interactive "type DELETE to confirm"
prompt. A prompt does not translate to an API, and a boolean ``confirm=true``
is not a guard — it is a checkbox that any client sets by default. So the
caller must echo the exact bucket being wiped: a mismatch deletes nothing, and
getting it right requires having read what you are about to destroy.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..storage.manager import StorageManager
from ..utils.logging import get_logger

logger = get_logger(__name__)

ProgressFn = Callable[[str, float, Optional[str]], None]


class StorageTransferError(RuntimeError):
    """A copy or wipe could not be completed. Nothing was swapped."""


class WipeGuardError(StorageTransferError):
    """The echoed bucket name did not match. Nothing was deleted."""


@dataclass
class CopyReport:
    """What a migration moved, and whether the destination agrees."""

    objects_copied: int = 0
    bytes_copied: int = 0
    objects_verified: int = 0
    failures: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures and self.objects_copied == self.objects_verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objects_copied": self.objects_copied,
            "bytes_copied": self.bytes_copied,
            "objects_verified": self.objects_verified,
            "failures": list(self.failures),
            "ok": self.ok,
        }


@dataclass
class WipeReport:
    """What a wipe removed, or would remove on a dry run."""

    dry_run: bool
    objects: int = 0
    bytes: int = 0
    keys: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "objects": self.objects,
            "bytes": self.bytes,
            # Capped: a wipe report is for a human deciding whether to proceed,
            # and a hundred thousand keys in a response body helps nobody.
            "keys": self.keys[:100],
            "keys_truncated": len(self.keys) > 100,
            "failures": list(self.failures),
        }


async def _all_keys(manager: StorageManager) -> List[Dict[str, Any]]:
    """Every object in the bucket, as listing entries."""
    entries: List[Dict[str, Any]] = []
    async for obj in manager.list_objects():
        key = obj.get("key")
        if key:
            entries.append(obj)
    return entries


async def copy_all_objects(
    source: StorageManager,
    destination: StorageManager,
    progress: Optional[ProgressFn] = None,
) -> CopyReport:
    """Copy every object from ``source`` to ``destination``, then verify.

    Provider-agnostic: it uses only list/get/put from the storage abstraction,
    so any supported provider can be copied to any other. The existing
    ``copy_container_blobs.py`` is Azure-to-Azure because it reaches for the
    Azure provider directly; this is the same loop written once against the
    abstraction instead.

    Verification re-reads each destination object and compares its digest to
    the source's. That doubles the reads, which is the right trade for a
    one-time migration whose failure mode is silent data loss — an operator
    who is told the copy verified should be able to believe it.
    """
    report = CopyReport()

    entries = await _all_keys(source)
    total = len(entries)
    if progress:
        progress("scan", 0.05, f"{total} object(s) to copy")

    digests: Dict[str, str] = {}

    for index, entry in enumerate(entries, start=1):
        key = entry["key"]
        try:
            data = await source.get_object(key)
            payload = bytes(data)
            await destination.put_object(
                key=key,
                data=payload,
                content_type=entry.get("content_type"),
            )
            digests[key] = hashlib.sha256(payload).hexdigest()
            report.objects_copied += 1
            report.bytes_copied += len(payload)
        except Exception as exc:  # noqa: BLE001 — collected, not swallowed
            report.failures.append(f"{key}: {exc}")
            logger.error("Failed to copy %s: %s", key, exc)

        if progress and total:
            progress("copy", 0.05 + 0.65 * (index / total), f"{index}/{total} copied")

    if report.failures:
        # No point verifying a copy already known to be incomplete, and the
        # caller must not swap on it either way.
        if progress:
            progress("failed", 1.0, f"{len(report.failures)} object(s) failed to copy")
        return report

    for index, (key, expected) in enumerate(digests.items(), start=1):
        try:
            actual = hashlib.sha256(
                bytes(await destination.get_object(key))
            ).hexdigest()
            if actual != expected:
                report.failures.append(f"{key}: digest mismatch after copy")
            else:
                report.objects_verified += 1
        except Exception as exc:  # noqa: BLE001
            report.failures.append(f"{key}: unreadable at destination ({exc})")

        if progress and digests:
            progress(
                "verify",
                0.70 + 0.30 * (index / len(digests)),
                f"{index}/{len(digests)} verified",
            )

    if progress:
        progress(
            "done" if report.ok else "failed",
            1.0,
            f"{report.objects_verified}/{total} verified",
        )
    return report


async def wipe_storage(
    manager: StorageManager,
    bucket_name: str,
    echoed_name: str,
    dry_run: bool = False,
) -> WipeReport:
    """Erase every object in ``manager``'s bucket, behind an echo guard.

    Args:
        bucket_name: the bucket this manager is actually pointed at.
        echoed_name: what the caller believes it is destroying. It must match
            exactly. A caller who cannot name the bucket has not read what they
            are about to erase, and a boolean flag would not have established
            that.
        dry_run: report what would be destroyed and delete nothing.

    Raises:
        WipeGuardError: the names did not match. Nothing was deleted.
    """
    if echoed_name != bucket_name:
        raise WipeGuardError(
            f"Refusing to wipe: the request named {echoed_name!r} but this "
            f"instance's storage is {bucket_name!r}. Nothing was deleted."
        )

    entries = await _all_keys(manager)
    report = WipeReport(
        dry_run=dry_run,
        objects=len(entries),
        bytes=sum(int(e.get("size") or 0) for e in entries),
        keys=[e["key"] for e in entries],
    )

    if dry_run:
        return report

    for entry in entries:
        try:
            await manager.delete_object(entry["key"])
        except Exception as exc:  # noqa: BLE001
            report.failures.append(f"{entry['key']}: {exc}")
            logger.error("Failed to delete %s: %s", entry["key"], exc)

    logger.warning(
        "Wiped %s object(s) from %s (%s failure(s))",
        report.objects - len(report.failures),
        bucket_name,
        len(report.failures),
    )
    return report
