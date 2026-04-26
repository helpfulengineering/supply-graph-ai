"""
Blob key layout for built OKH packages in remote object storage.

Top-level prefix (default ``packages/``) is parallel to ``okh/`` and ``okw/``.
Legacy uploads used ``okh/packages/``; readers check both.
"""

import os
from typing import List, Optional, Tuple


# New canonical prefix (single path segment, no slashes)
def default_package_prefix() -> str:
    return (
        os.environ.get("OHM_PACKAGE_STORAGE_PREFIX", "packages").strip().strip("/")
        or "packages"
    )


LEGACY_PACKAGE_PREFIX = "okh/packages"


def package_prefixes_for_list() -> List[str]:
    """Prefix strings used when listing remote packages (new first, then legacy)."""
    p = default_package_prefix()
    return [f"{p}/", f"{LEGACY_PACKAGE_PREFIX}/"]


def build_info_key_candidates(org: str, project: str, version: str) -> List[str]:
    """Keys to try when reading a package (prefer new layout)."""
    p = default_package_prefix()
    return [
        f"{p}/{org}/{project}/{version}/build-info.json",
        f"{LEGACY_PACKAGE_PREFIX}/{org}/{project}/{version}/build-info.json",
    ]


def parse_org_project_version_from_build_info_key(
    key: str,
) -> Optional[Tuple[str, str, str, str]]:
    """
    If ``key`` is ``.../build-info.json`` under a known layout, return
    ``(org, project, version, layout_tag)`` where ``layout_tag`` is ``"new"`` or ``"legacy"``.
    """
    if not key.endswith("/build-info.json"):
        return None
    body = key[: -len("/build-info.json")].strip("/")
    parts = [x for x in body.split("/") if x]
    p = default_package_prefix()
    if len(parts) >= 5 and parts[0] == "okh" and parts[1] == "packages":
        return parts[2], parts[3], parts[4], "legacy"
    if len(parts) >= 4 and parts[0] == p:
        return parts[1], parts[2], parts[3], "new"
    return None
