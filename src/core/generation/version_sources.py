"""Where a generated manifest's version may come from (#564).

A version is never invented. It is read, verbatim, from a place where the
author declared one, in this order:

1. a release or tag on the hosting platform;
2. a version file at the repository root (``VERSION``, ``package.json``,
   ``pyproject.toml``, ``library.properties``);
3. the title-block revision of a KiCad project's schematic.

Anything else that looks like a version (README prose, file names such as
``frugal_iot_v02``) is a hint for the person filling the field, never a value:
"V0.2" and "revision 4" in one README is how 0.2.4 was once invented.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

from .models import ProjectData

DeclaredVersion = Tuple[str, str]

_VERSION_FILES = ("VERSION", "VERSION.txt")
_TITLE_BLOCK = re.compile(r"\(title_block\b")
_REV = re.compile(r'\(rev\s+"([^"]+)"\)')
_HINT = re.compile(r"(?i)(?<![a-z])(?:version|revision|rev|v)[\s_.-]?\d+(?:\.\d+)*")


def declared_version(project: ProjectData) -> Optional[DeclaredVersion]:
    """The version the author declared, and where, or None."""
    files = {f.path: f.content or "" for f in project.files}
    return (
        _from_release(project.metadata or {})
        or _from_version_file(files)
        or _from_kicad_project(files)
    )


def missing_version_warning(project: ProjectData) -> str:
    """The quality warning for a blank version, naming any hints seen."""
    message = (
        "No version found: no release or tag, no version file (VERSION, "
        "package.json, pyproject.toml, library.properties) and no KiCad "
        "title-block revision."
    )
    hints = _hints(project)
    if hints:
        message += f" Seen elsewhere: {'; '.join(hints)}."
    return message + " Enter the version, or declare it in one of those places."


def _from_release(metadata: Dict) -> Optional[DeclaredVersion]:
    tags = [metadata.get(k) for k in ("tag_name", "latest_release", "release_tag")]
    releases = [r for r in metadata.get("releases") or [] if isinstance(r, dict)]
    releases.sort(key=lambda r: bool(r.get("prerelease")))
    tags += [r.get("tag_name") for r in releases]
    for tag in tags:
        if isinstance(tag, str) and tag.strip():
            tag = tag.strip()
            return re.sub(r"^[vV](?=\d)", "", tag), f"release tag {tag}"
    return None


def _from_version_file(files: Dict[str, str]) -> Optional[DeclaredVersion]:
    for name in _VERSION_FILES:
        words = files.get(name, "").split()
        if words:
            return words[0], name
    readers = {
        "package.json": lambda text: json.loads(text).get("version"),
        "pyproject.toml": lambda text: tomllib.loads(text)
        .get("project", {})
        .get("version"),
        "library.properties": lambda text: dict(
            line.split("=", 1) for line in text.splitlines() if "=" in line
        ).get("version"),
    }
    for name, read in readers.items():
        if name not in files:
            continue
        try:
            value = read(files[name])
        except (ValueError, AttributeError):
            continue
        if isinstance(value, str) and value.strip():
            return value.strip(), f"{name}: version"
    return None


def _from_kicad_project(files: Dict[str, str]) -> Optional[DeclaredVersion]:
    """A schematic counts only beside its ``.kicad_pro``; generated copies don't."""
    found = {}
    for path in files:
        if path.endswith(".kicad_pro"):
            schematic = path[: -len(".kicad_pro")] + ".kicad_sch"
            rev = _title_block_rev(files.get(schematic, ""))
            if rev:
                found[schematic] = rev
    if len(set(found.values())) != 1:
        return None
    schematic, rev = next(iter(found.items()))
    return rev, f"{schematic}: title_block rev"


def _title_block_rev(content: str) -> Optional[str]:
    block = _TITLE_BLOCK.search(content)
    if not block:
        return None
    rev = _REV.search(content, block.end(), block.end() + 2000)
    return rev.group(1).strip() if rev and rev.group(1).strip() else None


def _hints(project: ProjectData) -> List[str]:
    seen: List[str] = []
    names = sorted(
        {m for f in project.files for m in _HINT.findall(PurePosixPath(f.path).name)}
    )
    if names:
        seen.append(f"{', '.join(names[:3])} in file names")
    readme = next(
        (f.content for f in project.files if f.path.lower() == "readme.md"), ""
    )
    heading = next((l for l in (readme or "").splitlines() if l.startswith("#")), "")
    found = _HINT.findall(heading)
    if found:
        seen.append(f"{', '.join(found)} in the README heading")
    return seen
