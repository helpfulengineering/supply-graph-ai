"""Containment checks for paths and object keys derived from untrusted input.

Package building takes file locations from OKH manifest content, which any
writer can supply, and from the path segments of remote URLs. Joining either to
a directory without checking the result is how a manifest gets to read a file
outside its own package, or write to an object key outside its own prefix
(#418).

Both helpers **reject** rather than sanitise. A manifest asking for a file
outside its package is not a manifest to quietly fix up: rewriting the path
would hide the attempt and leave the caller believing it got what it asked for.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


class UnsafePathError(ValueError):
    """A derived path or key escaped the base it had to stay inside."""


def safe_join(base: Path, relative: str) -> Path:
    """Join ``relative`` onto ``base``, or raise if it escapes.

    Resolves both sides before comparing, so ``..`` segments, absolute paths and
    symlinked bases are all judged on where they actually land rather than on
    how they are spelled.
    """
    base_resolved = Path(base).resolve()
    candidate = (base_resolved / relative).resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise UnsafePathError(
            f"{relative!r} resolves outside {base_resolved} (to {candidate})"
        )
    return candidate


def safe_key(prefix: str, relative: str) -> str:
    """Build an object key under ``prefix``, or raise if ``relative`` escapes.

    Object keys are POSIX-style and have no filesystem to resolve against, so
    this normalises textually. An absolute-looking segment, a backslash (which
    some backends treat as a separator), and any ``..`` that walks above the
    prefix are all refused.
    """
    if "\\" in relative:
        raise UnsafePathError(f"{relative!r} contains a backslash separator")
    if relative.startswith("/"):
        # Stripping the slash would silently reinterpret an absolute request as
        # a relative one, which is the sanitising this module exists to avoid.
        raise UnsafePathError(f"{relative!r} is absolute; keys are prefix-relative")
    cleaned = PurePosixPath(prefix.strip("/")) / relative
    parts: list[str] = []
    for part in cleaned.parts:
        if part == "..":
            if not parts:
                raise UnsafePathError(f"{relative!r} walks above {prefix!r}")
            parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    key = "/".join(parts)
    if not key.startswith(prefix.strip("/")):
        raise UnsafePathError(f"{relative!r} resolves outside {prefix!r}")
    return key
