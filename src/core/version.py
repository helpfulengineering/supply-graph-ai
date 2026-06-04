"""
Version information for Open Hardware Manager (OHM).

Package version is defined in pyproject.toml. At runtime we read the installed
distribution metadata; when running from a checkout without install, we parse
pyproject.toml from the repository root.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_PACKAGE_NAME = "supply-graph-ai"
_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the current OHM package version (e.g. ``0.8.0``)."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        pass
    except Exception:
        pass

    if not _PYPROJECT_PATH.is_file():
        raise RuntimeError(
            f"Could not determine version: {_PACKAGE_NAME} is not installed "
            f"and {_PYPROJECT_PATH} was not found"
        )
    text = _PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"No version field found in {_PYPROJECT_PATH}")
    return match.group(1)


def get_version_tuple() -> tuple[int, int, int]:
    """Return version as ``(major, minor, patch)``."""
    major, minor, patch = get_version().split(".")[:3]
    return int(major), int(minor), int(patch)


# Back-compat for modules that import __version__ from this package.
__version__ = get_version()
