"""Deterministic OKH generation quality heuristics (no LLM).

``heuristic_manifest_quality`` returns keys required by batch / chunked eval scripts,
plus Materials extensions from the generation quality spec:

- ``materials_near_dup_pairs`` — case/plural/whitespace near-duplicates
- ``materials_prose_like_count`` — sentences, markdown table rows, URLs, instructions
- ``materials_quality_score`` — ``max(0, 1 - 0.15 * near_dup_pairs - 0.2 * prose_like_count)``
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from src.core.generation.materials_filter import (
    is_prose_like,
    near_dup_pair_count,
)

_LICENSE_LEAK_RE = re.compile(
    r"\b(mit|gpl|agpl|lgpl|apache|bsd|cern[- ]?ohl|cc[- ]?by|mozilla|mpl)\b",
    re.I,
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
    near_dups = near_dup_pair_count(names)
    prose_count = sum(1 for n in names if is_prose_like(n))
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
