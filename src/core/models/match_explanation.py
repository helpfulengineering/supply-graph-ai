"""
Match explanation data model for transparency (Issue 1.2.4).

Provides structured and human-readable explanations for why a facility
matched or did not match a set of requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MatchLayer(str, Enum):
    """Matching layer that produced the match."""

    DIRECT = "direct"
    HEURISTIC = "heuristic"
    NLP = "nlp"
    LLM = "llm"


class MatchStatus(str, Enum):
    """Overall or per-requirement match status."""

    MATCHED = "matched"
    NOT_MATCHED = "not_matched"


@dataclass
class RequirementMatchDetail:
    """Explanation for a single requirement: how it was matched or why not."""

    requirement_value: str
    status: MatchStatus
    confidence: float = 0.0
    matched_capability: Optional[str] = None
    matching_layer: Optional[MatchLayer] = None
    rule_id: Optional[str] = None
    explanation: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    # Optional context for deduplication/display: where the requirement came from in the OKH
    requirement_source: Optional[str] = (
        None  # "process_requirements" | "manufacturing_processes" | "part"
    )
    requirement_part_name: Optional[str] = None  # part name when source is "part"

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "requirement_value": self.requirement_value,
            "status": self.status.value,
            "confidence": self.confidence,
            "matched_capability": self.matched_capability,
            "matching_layer": (
                self.matching_layer.value if self.matching_layer else None
            ),
            "rule_id": self.rule_id,
            "explanation": self.explanation,
            "evidence": self.evidence,
        }
        if self.requirement_source is not None:
            out["requirement_source"] = self.requirement_source
        if self.requirement_part_name is not None:
            out["requirement_part_name"] = self.requirement_part_name
        return out


@dataclass
class MatchExplanation:
    """Complete explanation for a facility match (or non-match)."""

    facility_id: str
    facility_name: str
    overall_status: MatchStatus
    overall_confidence: float
    requirement_matches: List[RequirementMatchDetail]
    why_matched: str = ""
    why_not_matched: str = ""
    matching_layers_used: List[str] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facility_id": self.facility_id,
            "facility_name": self.facility_name,
            "overall_status": self.overall_status.value,
            "overall_confidence": self.overall_confidence,
            "requirement_matches": [m.to_dict() for m in self.requirement_matches],
            "why_matched": self.why_matched,
            "why_not_matched": self.why_not_matched,
            "matching_layers_used": self.matching_layers_used,
            "missing_capabilities": self.missing_capabilities,
        }

    def to_human_readable(self) -> str:
        """Generate human-readable explanation text."""
        if self.overall_status == MatchStatus.MATCHED:
            return self._format_positive()
        return self._format_negative()

    @staticmethod
    def _requirement_label(m: "RequirementMatchDetail") -> str:
        """Human-readable label for one requirement (value + optional source/part context)."""
        base = m.requirement_value
        if m.requirement_source == "part" and m.requirement_part_name:
            return f"{base} (part: {m.requirement_part_name})"
        if m.requirement_source == "process_requirements":
            return f"{base} (from spec)"
        if m.requirement_source == "manufacturing_processes":
            return f"{base} (top-level)"
        return base

    def _format_positive(self) -> str:
        lines = [
            f"✓ {self.facility_name} MATCHED (confidence: {self.overall_confidence:.0%})",
            "",
            "Why this facility matches:",
            f"  {self.why_matched or 'All requirements satisfied.'}",
            "",
            "Requirement breakdown:",
        ]
        for m in self.requirement_matches:
            if m.status == MatchStatus.MATCHED:
                label = self._requirement_label(m)
                lines.append(f"  ✓ {label}")
                layer = m.matching_layer.value if m.matching_layer else "?"
                cap = m.matched_capability or "—"
                lines.append(f"    → Matched via {layer}: {cap} ({m.confidence:.0%})")
                if m.rule_id:
                    lines.append(f"    Rule: {m.rule_id}")
                if m.explanation:
                    lines.append(f"    {m.explanation}")
        if self.matching_layers_used:
            lines.extend(["", "Layers used: " + ", ".join(self.matching_layers_used)])
        return "\n".join(lines)

    def _format_negative(self) -> str:
        lines = [
            f"✗ {self.facility_name} NOT MATCHED",
            "",
            "Why this facility doesn't match:",
            f"  {self.why_not_matched or 'One or more requirements could not be satisfied.'}",
            "",
        ]
        if self.requirement_matches:
            lines.append("Requirement breakdown:")
            for m in self.requirement_matches:
                if m.status == MatchStatus.NOT_MATCHED:
                    label = self._requirement_label(m)
                    lines.append(f"  ✗ {label}")
                    if m.explanation:
                        lines.append(f"    {m.explanation}")
        if self.missing_capabilities:
            lines.extend(["", "Missing or insufficient capabilities:"])
            for cap in self.missing_capabilities:
                lines.append(f"  • {cap}")
        return "\n".join(lines)
