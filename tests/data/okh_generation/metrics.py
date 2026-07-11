"""Deterministic OKH generation quality heuristics (no LLM).

``heuristic_manifest_quality`` returns keys required by batch / chunked eval scripts,
plus Materials extensions from the generation quality spec:

- ``materials_near_dup_pairs`` — case/plural/whitespace near-duplicates
- ``materials_prose_like_count`` — sentences, markdown table rows, URLs, instructions
- ``materials_quality_score`` — ``max(0, 1 - 0.15 * near_dup_pairs - 0.2 * prose_like_count)``
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

_LICENSE_LEAK_RE = re.compile(
    r"\b(mit|gpl|agpl|lgpl|apache|bsd|cern[- ]?ohl|cc[- ]?by|mozilla|mpl)\b",
    re.I,
)
_INSTRUCTION_OPENERS = (
    "make sure",
    "in case you",
    "you could",
    "you will",
    "you can also",
)


def heuristic_manifest_quality(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Score a generated OKH manifest with presence, leak, and Materials heuristics."""
    title = _as_str(manifest.get("title"))
    version = _as_str(manifest.get("version"))
    function = _as_str(manifest.get("function"))
    description = _as_str(manifest.get("description"))

    has_title = bool(title)
    has_version = bool(version)
    has_function = bool(function)
    has_description = bool(description)

    presence = [has_title, has_version, has_function, has_description]
    generation_confidence = sum(1.0 for p in presence if p) / len(presence)

    names = _material_names(manifest.get("materials") or [])
    near_dups = _near_dup_pair_count(names)
    prose_count = sum(1 for n in names if _is_prose_like(n))
    materials_count = len(names)
    materials_quality_score = _materials_quality_score(
        materials_count, near_dups, prose_count
    )

    return {
        "generation_confidence": round(generation_confidence, 4),
        "function_suspected_license_leak": _function_looks_like_license(function),
        "has_title": has_title,
        "has_version": has_version,
        "has_function": has_function,
        "has_description": has_description,
        "materials_count": materials_count,
        "materials_near_dup_pairs": near_dups,
        "materials_prose_like_count": prose_count,
        "materials_quality_score": round(materials_quality_score, 4),
    }


def heuristic_layer_comparison(
    m3: Dict[str, Any], m4: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare 3L vs 4L manifests using the same heuristic dict."""
    q3 = heuristic_manifest_quality(m3)
    q4 = heuristic_manifest_quality(m4)
    return {
        "3L": q3,
        "4L": q4,
        "confidence_delta": round(
            float(q4["generation_confidence"]) - float(q3["generation_confidence"]), 4
        ),
        "materials_quality_delta": round(
            float(q4["materials_quality_score"]) - float(q3["materials_quality_score"]),
            4,
        ),
        "materials_near_dup_delta": int(q4["materials_near_dup_pairs"])
        - int(q3["materials_near_dup_pairs"]),
        "materials_prose_delta": int(q4["materials_prose_like_count"])
        - int(q3["materials_prose_like_count"]),
    }


def _material_names(materials: Sequence[Any]) -> List[str]:
    names: List[str] = []
    for item in materials:
        if isinstance(item, dict):
            name = item.get("name") or item.get("material_id") or ""
            names.append(str(name).strip())
        elif item is not None:
            names.append(str(item).strip())
    return [n for n in names if n]


def _normalize_material_key(name: str) -> str:
    key = " ".join(name.casefold().split())
    if len(key) > 1 and key.endswith("s") and not key.endswith("ss"):
        key = key[:-1]
    return key


def _near_dup_pair_count(names: Sequence[str]) -> int:
    """Count unordered pairs with the same normalized key but different surface forms."""
    indexed: List[Tuple[str, str]] = [(n, _normalize_material_key(n)) for n in names]
    count = 0
    for i, (a_raw, a_key) in enumerate(indexed):
        for b_raw, b_key in indexed[i + 1 :]:
            if a_key and a_key == b_key and a_raw != b_raw:
                count += 1
    return count


def _is_prose_like(name: str) -> bool:
    text = name.strip()
    if not text:
        return False
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


def _materials_quality_score(count: int, near_dups: int, prose: int) -> float:
    if count <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - 0.15 * near_dups - 0.2 * prose))


def _function_looks_like_license(function: str) -> bool:
    if not function or len(function) < 40:
        return False
    if len(_LICENSE_LEAK_RE.findall(function)) >= 2:
        return True
    lower = function.casefold()
    return "licensed under" in lower or "permission is hereby granted" in lower


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
