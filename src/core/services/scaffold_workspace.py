"""Sandbox for scaffold/cleanup filesystem writes (#512).

`ScaffoldService._write_filesystem`, `_create_and_store_zip`'s optional
`output_path`, and `CleanupService.clean`'s `project_path` each used to
resolve a caller-supplied path directly — `Path(candidate).expanduser().
resolve()` — with nothing constraining where it could point: an arbitrary
file write (scaffold) or delete (cleanup) anywhere the API process could
reach, reachable anonymously until #485 and unconstrained for any
authenticated caller after it.

Both `output_path`/`filesystem` writes and zip's caller-directed variant
only ever made sense when the caller and the server share a filesystem —
zip's `download_url` is a raw `file://` URI, never served over HTTP by any
route, so a remote caller could not retrieve the archive it names anyway.
This is the one place both services now resolve a caller-supplied path
against that same-machine assumption, made explicit rather than implicit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def resolve_scaffold_path(candidate: Optional[str]) -> Path:
    """Resolve ``candidate`` against ``SCAFFOLD_OUTPUT_ROOT``.

    Fails closed: no root configured means the feature is off, not
    "anywhere is fine" — the same posture ``RELAXED_ENVIRONMENTS`` takes in
    ``src/config/schema.py``, derived the same way on purpose so it fails
    closed rather than open. ``candidate`` omitted resolves to the root
    itself (matches ``CleanupOptions``/``ScaffoldOptions`` treating "no
    path given" as "operate at the workspace root").

    Raises ``ValueError`` — the same exception both callers already handle
    as a 422 — when no root is configured, or when the resolved path is not
    the root or a descendant of it.
    """
    from src.config.schema import get_settings

    root_setting = get_settings().scaffold_output_root
    if not root_setting:
        raise ValueError(
            "Filesystem output is disabled until SCAFFOLD_OUTPUT_ROOT is "
            "configured. Set it to the directory scaffold/cleanup "
            "operations may write to or delete from."
        )

    root = Path(root_setting).expanduser().resolve()
    resolved = Path(candidate).expanduser().resolve() if candidate else root

    if not resolved.is_relative_to(root):
        raise ValueError(
            f"Path must be inside the configured scaffold workspace ({root})"
        )

    return resolved
