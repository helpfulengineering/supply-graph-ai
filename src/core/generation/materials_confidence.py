"""Per-material confidence scoring and review-queue helpers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .materials_filter import normalize_material_key

# Align with QualityAssessor field threshold
LOW_MATERIAL_CONFIDENCE = 0.7

_CHAT_SALES_RE = re.compile(
    r"(?i)("
    r"telegram|телеграм|чат\b|продаж|diy\s*devices|"
    r"you\s+can\s+make|make\s+your\s+own\s+pcb|"
    r"нou\s+can"  # mojibake of "You can"
    r")"
)

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")

_GENERIC_SINGLE = frozenset(
    {
        "led",
        "resin",
        "pla",
        "filament",
        "capacitor",
        "resistor",
        "connector",
        "motor",
        "screw",
        "cable",
        "wire",
        "pcb",
    }
)


@dataclass
class MaterialReviewItem:
    """One material flagged for LLM and/or human review."""

    name: str
    confidence: float
    source: str
    reason: str
    needs_review: bool = True
    material_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def is_chat_or_sales_line(name: str) -> bool:
    """True for community/chat/sales blurbs that are not part names."""
    text = (name or "").strip()
    if not text:
        return False
    if _CHAT_SALES_RE.search(text):
        return True
    cyr = len(_CYRILLIC_RE.findall(text))
    return cyr >= 3 and cyr >= len(text) // 3


def score_material(
    name: str,
    *,
    source: str = "extracted",
    has_evidence: bool = False,
) -> Tuple[float, str]:
    """Return ``(confidence, reason)`` for a kept material name."""
    text = (name or "").strip()
    if not text:
        return 0.0, "empty"
    if is_chat_or_sales_line(text):
        return 0.2, "chat_or_sales_line"

    src = (source or "extracted").casefold()
    if src.startswith("harvest"):
        return 0.9, "harvested_part"
    if src == "bom":
        return 0.85, "bom_component"

    key = normalize_material_key(text)
    words = text.split()
    if key in _GENERIC_SINGLE and len(words) == 1:
        return (
            (0.55, "generic_token_with_evidence")
            if has_evidence
            else (0.45, "generic_token")
        )
    if has_evidence:
        if len(words) >= 2 or len(text) >= 8:
            return 0.75, "evidence_backed"
        return 0.65, "short_evidence_token"
    if len(words) >= 2 and len(text) >= 10:
        return 0.55, "multiword_no_evidence"
    return 0.45, "weak_extraction"


def build_material_review_items(
    scored: Sequence[Tuple[str, float, str, str, Optional[str]]],
) -> List[MaterialReviewItem]:
    """Build review items from ``(name, confidence, source, reason, material_id)``."""
    return [
        MaterialReviewItem(
            name=name,
            confidence=round(confidence, 3),
            source=source,
            reason=reason,
            material_id=material_id,
        )
        for name, confidence, source, reason, material_id in scored
        if confidence < LOW_MATERIAL_CONFIDENCE
    ]
