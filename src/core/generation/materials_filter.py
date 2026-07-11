"""Shared Materials shape, key, and doc-evidence helpers for normalize + metrics."""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence, Tuple

_INSTRUCTION_OPENERS = (
    "make sure",
    "in case you",
    "you could",
    "you will",
    "you can also",
)

_BOM_HEADING_RE = re.compile(
    r"(?i)^(#{1,6}\s*)?(bill of materials|materials|parts|bom)\b"
)
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+")


def normalize_material_key(name: str) -> str:
    """Casefold, collapse whitespace, light English plural strip for near-dup keys."""
    key = " ".join(name.casefold().split())
    if len(key) > 1 and key.endswith("s") and not key.endswith("ss"):
        key = key[:-1]
    return key


def is_prose_like(name: str) -> bool:
    """True when a material name looks like prose, a table row, URL, or instruction."""
    text = name.strip()
    if not text:
        return False
    if text.isdigit():
        return True
    if text.startswith("(*") or (
        text.startswith("(") and text.endswith(")") and len(text.split()) >= 2
    ):
        return True
    lower = text.casefold()
    words = text.split()
    if len(words) >= 8 or len(text) > 90:
        return True
    if "|" in text:
        return True
    if "http://" in lower or "https://" in lower:
        return True
    if text.endswith(".") and len(words) >= 5:
        return True
    if any(
        lower.startswith(op) or f" {op} " in f" {lower} " for op in _INSTRUCTION_OPENERS
    ):
        return True
    return False


def near_dup_pair_count(names: Sequence[str]) -> int:
    """Count unordered pairs with the same normalized key but different surface forms."""
    indexed: list[Tuple[str, str]] = [(n, normalize_material_key(n)) for n in names]
    count = 0
    for i, (a_raw, a_key) in enumerate(indexed):
        for b_raw, b_key in indexed[i + 1 :]:
            if a_key and a_key == b_key and a_raw != b_raw:
                count += 1
    return count


def build_materials_corpus(project_data: Any) -> str:
    """Concatenate README / BOM / materials docs already loaded on ProjectData."""
    if project_data is None:
        return ""
    parts: list[str] = []
    meta = getattr(project_data, "metadata", None) or {}
    readme = meta.get("readme_content")
    if readme:
        parts.append(str(readme))
    for f in getattr(project_data, "files", None) or []:
        path = str(getattr(f, "path", "") or "").casefold()
        content = getattr(f, "content", None) or ""
        if content and any(
            token in path for token in ("readme", "bom", "material", "parts")
        ):
            parts.append(str(content))
    for doc in getattr(project_data, "documentation", None) or []:
        content = getattr(doc, "content", None) or ""
        if content:
            parts.append(str(content))
    return "\n\n".join(parts)


def _bom_section_bodies(corpus: str) -> list[str]:
    bodies: list[str] = []
    buf: list[str] = []
    collecting = False
    for line in corpus.splitlines():
        stripped = line.strip()
        if _BOM_HEADING_RE.match(stripped):
            if buf:
                bodies.append("\n".join(buf))
            buf = []
            collecting = True
            continue
        if collecting and _MD_HEADING_RE.match(line):
            bodies.append("\n".join(buf))
            buf = []
            collecting = False
            continue
        if collecting:
            buf.append(line)
    if buf:
        bodies.append("\n".join(buf))
    return bodies


def has_part_reference_evidence(
    name: str,
    corpus: str,
    bom_component_names: Optional[Sequence[str]] = None,
) -> bool:
    """True when ``name`` appears as a part/material reference in docs or BOM components."""
    key = normalize_material_key(name)
    if not key:
        return False

    if bom_component_names:
        for component in bom_component_names:
            ckey = normalize_material_key(str(component))
            if re.search(rf"\b{re.escape(key)}\b", ckey):
                return True

    if not corpus.strip():
        return False

    key_needle = re.escape(key)
    for body in _bom_section_bodies(corpus):
        if re.search(rf"\b{key_needle}\b", body.casefold()):
            return True
    return False
