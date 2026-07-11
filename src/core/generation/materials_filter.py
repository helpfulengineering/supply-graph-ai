"""Shared Materials shape, key, and doc-evidence helpers for normalize + metrics."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence, Tuple

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
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\d+\s*[x×]\s+)?(.+)$", re.I)
# Shopping-list / marketplace lines: "Part name - https://..."
_SHOPPING_LINE_RE = re.compile(
    r"^(?P<name>.{3,100}?)\s+[-–]\s+https?://\S+", re.I | re.M
)
# Heading product refs: "#### SGP40: https://..."
_HASH_PART_RE = re.compile(
    r"^#{2,4}\s+(?P<name>[^:\n]{2,80}?)\s*:\s*https?://", re.I | re.M
)
# GitBuilding parts YAML Name fields
_YAML_NAME_RE = re.compile(r"(?m)^\s*Name:\s*(.+?)\s*$")
# Numbered instruction headings should not be harvested as parts
_INSTRUCTION_HEADING_RE = re.compile(
    r"(?i)^(first of all|\d+[.)]?\s+|install |download |open |add |create |click )"
)

_TOOL_DENYLIST = frozenset(
    {
        "pc",
        "pcs",
        "ide",
        "library",
        "mysensors",
        "arduino ide",
        "arduino-nrf5",
    }
)

_SHORT_MAX_WORDS = 5
_SHORT_MAX_CHARS = 50


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


def is_rejected_material_token(name: str) -> bool:
    """True for software/tool tokens that should never become Materials."""
    key = normalize_material_key(name)
    if not key:
        return True
    if key in _TOOL_DENYLIST:
        return True
    if key.endswith(" ide") or " library" in f" {key} ":
        return True
    if "mysensors" in key or "arduino-nrf" in key:
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
    """Concatenate README / BOM / materials / parts docs already loaded on ProjectData."""
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
        if not content:
            continue
        if any(token in path for token in ("readme", "bom", "material", "parts")):
            parts.append(str(content))
            continue
        # GitBuilding / parts catalogs often live under docs/*.yml
        if path.endswith((".yml", ".yaml")) and "doc" in path:
            parts.append(str(content))
    for doc in getattr(project_data, "documentation", None) or []:
        content = getattr(doc, "content", None) or ""
        if content:
            parts.append(str(content))
    return "\n\n".join(parts)


def _clean_part_name(raw: str) -> str:
    name = raw.strip().strip("*_`")
    name = re.sub(r"\s+", " ", name)
    # Drop trailing qty/price crumbs if present before URL split already handled
    name = re.sub(r"\s*\(\d+\s*pcs?.*$", "", name, flags=re.I).strip()
    return name


def _is_harvestable_part_name(name: str) -> bool:
    if not name or is_prose_like(name) or is_rejected_material_token(name):
        return False
    if _INSTRUCTION_HEADING_RE.match(name):
        return False
    if len(name) < 2 or len(name) > 80:
        return False
    return True


def extract_shopping_list_parts(corpus: str) -> List[str]:
    """Harvest product names from marketplace shopping lines and #### Part: URL headings."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _SHOPPING_LINE_RE.finditer(corpus or ""):
        name = _clean_part_name(match.group("name"))
        key = normalize_material_key(name)
        if key and key not in seen and _is_harvestable_part_name(name):
            seen.add(key)
            found.append(name)
    for match in _HASH_PART_RE.finditer(corpus or ""):
        name = _clean_part_name(match.group("name"))
        # Prefer short product codes / titles before parenthetical aliases
        name = re.split(r"\s*\(", name, maxsplit=1)[0].strip()
        key = normalize_material_key(name)
        if key and key not in seen and _is_harvestable_part_name(name):
            seen.add(key)
            found.append(name)
    return found


def extract_gitbuilding_yaml_parts(content: str) -> List[str]:
    """Harvest ``Name:`` fields from GitBuilding-style parts YAML."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _YAML_NAME_RE.finditer(content or ""):
        name = _clean_part_name(match.group(1))
        key = normalize_material_key(name)
        if key and key not in seen and _is_harvestable_part_name(name):
            seen.add(key)
            found.append(name)
    return found


def harvest_materials_from_project(project_data: Any) -> List[str]:
    """Collect attested part names from shopping lists and parts YAML in ProjectData."""
    corpus = build_materials_corpus(project_data)
    found = extract_shopping_list_parts(corpus)
    seen = {normalize_material_key(n) for n in found}
    if project_data is None:
        return found
    for f in getattr(project_data, "files", None) or []:
        path = str(getattr(f, "path", "") or "").casefold()
        content = getattr(f, "content", None) or ""
        if not content:
            continue
        if not (path.endswith((".yml", ".yaml")) and ("part" in path or "doc" in path)):
            continue
        for name in extract_gitbuilding_yaml_parts(content):
            key = normalize_material_key(name)
            if key not in seen:
                seen.add(key)
                found.append(name)
    return found


def _is_short_candidate(name: str) -> bool:
    text = name.strip()
    return len(text) <= _SHORT_MAX_CHARS and len(text.split()) <= _SHORT_MAX_WORDS


def _line_looks_instructional(line: str) -> bool:
    lower = line.strip().casefold()
    if not lower:
        return False
    if any(
        lower.startswith(op) or f" {op} " in f" {lower} " for op in _INSTRUCTION_OPENERS
    ):
        return True
    return len(lower.split()) >= 8


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


def _key_in_text(key: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(key)}\b", text.casefold()))


def _line_is_shopping_ref(line: str, key: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    # Instruction openers still disqualify even on URL-ish lines
    lower = stripped.casefold()
    if any(
        lower.startswith(op) or f" {op} " in f" {lower} " for op in _INSTRUCTION_OPENERS
    ):
        return False
    body = stripped.lstrip("#").strip()
    if _INSTRUCTION_HEADING_RE.match(body):
        return False
    shop = _SHOPPING_LINE_RE.match(stripped)
    if shop and _key_in_text(key, shop.group("name")):
        return True
    heading = _HASH_PART_RE.match(stripped)
    if heading and _key_in_text(key, heading.group("name")):
        return True
    return False


def _line_is_discrete_part_ref(line: str, key: str) -> bool:
    """True when ``key`` appears on a list/table/shopping/short part line."""
    stripped = line.strip()
    if not stripped:
        return False

    # Shopping / #### Part: URL first (these lines are often long)
    if _line_is_shopping_ref(stripped, key):
        return True

    if _line_looks_instructional(stripped):
        return False

    match = _LIST_ITEM_RE.match(stripped)
    if match and _key_in_text(key, match.group(1)):
        return True

    if "|" in stripped:
        for cell in stripped.split("|"):
            cell = cell.strip()
            if not cell or len(cell.split()) > 6:
                continue
            if _key_in_text(key, cell):
                return True
        return False

    if len(stripped.split()) <= 6 and _key_in_text(key, stripped):
        if re.match(r"^\d+\s*[x×]\s+", stripped, re.I):
            return True
        if normalize_material_key(stripped) == key or stripped.casefold().startswith(
            key
        ):
            return True
    return False


def has_part_reference_evidence(
    name: str,
    corpus: str,
    bom_component_names: Optional[Sequence[str]] = None,
) -> bool:
    """True when ``name`` is attested as a part/material reference in docs or BOM.

    Policy:
    - Structured BOM / harvested part names always count.
    - Hits under BOM/Materials/Parts headings always count.
    - Shopping-list and #### Part: URL lines count for matching keys.
    - Short candidates may also use discrete list/table lines anywhere.
    - Longer candidates require BOM-section, shopping, or component hit.
    """
    if is_rejected_material_token(name):
        return False
    key = normalize_material_key(name)
    if not key:
        return False

    if bom_component_names:
        for component in bom_component_names:
            ckey = normalize_material_key(str(component))
            if re.search(rf"\b{re.escape(key)}\b", ckey) or key == ckey:
                return True

    if not corpus.strip():
        return False

    for body in _bom_section_bodies(corpus):
        if _key_in_text(key, body):
            return True

    # Shopping / #### Part lines (any length candidate)
    for line in corpus.splitlines():
        if _line_is_shopping_ref(line, key):
            return True

    if not _is_short_candidate(name):
        return False

    for line in corpus.splitlines():
        if _line_is_discrete_part_ref(line, key):
            return True
    return False
