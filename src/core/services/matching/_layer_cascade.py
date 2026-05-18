"""
Shared orchestration for the direct → heuristic → NLP matching cascade.

Supports cascade mode (legacy short-circuit) and veto mode (NLP second opinion
on fuzzy direct and heuristic hits).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal, Optional, Tuple

LayerKind = Literal["direct", "heuristic", "nlp", "none"]
DirectPath = Literal["strong", "fuzzy", "none"]
CascadeMode = Literal["cascade", "veto"]


@dataclass
class LayerEvaluation:
    """Outcome of evaluating req vs cap through layers 1–3."""

    matched: bool
    layer: LayerKind
    confidence: float
    direct_path: DirectPath = "none"
    rule_id: Optional[str] = None
    nlp_similarity: Optional[float] = None
    nlp_confirmed: bool = False
    notes: list[str] = field(default_factory=list)


async def evaluate_layers(
    *,
    direct_eval: Callable[[], Awaitable[Tuple[bool, DirectPath]]],
    heuristic_eval: Callable[[], Awaitable[Tuple[bool, Optional[str]]]],
    nlp_match: Callable[[], Awaitable[bool]],
    nlp_similarity: Callable[[], Awaitable[Optional[float]]],
    mode: CascadeMode = "cascade",
    veto_threshold: float = 0.2,
) -> LayerEvaluation:
    """Run direct → heuristic → NLP with optional NLP veto on fuzzy/heuristic hits."""
    notes_veto: list[str] = []

    dm, dpath = await direct_eval()

    if mode == "cascade":
        if dm:
            return LayerEvaluation(
                matched=True,
                layer="direct",
                confidence=0.95,
                direct_path=dpath,
            )
        hm, rule_id = await heuristic_eval()
        if hm:
            return LayerEvaluation(
                matched=True,
                layer="heuristic",
                confidence=0.9,
                direct_path="none",
                rule_id=rule_id,
            )
        if await nlp_match():
            return LayerEvaluation(
                matched=True,
                layer="nlp",
                confidence=0.7,
                direct_path="none",
            )
        return LayerEvaluation(
            matched=False,
            layer="none",
            confidence=0.0,
            direct_path="none",
        )

    # veto mode
    if dm and dpath == "strong":
        return LayerEvaluation(
            matched=True,
            layer="direct",
            confidence=0.95,
            direct_path="strong",
            nlp_confirmed=False,
        )

    if dm and dpath == "fuzzy":
        sim = await nlp_similarity()
        if sim is not None and sim < veto_threshold:
            dm = False
            dpath = "none"
            notes_veto.append("nlp_veto:fuzzy_direct")
        else:
            return LayerEvaluation(
                matched=True,
                layer="direct",
                confidence=0.95,
                direct_path="fuzzy",
                nlp_similarity=sim,
                nlp_confirmed=True,
                notes=notes_veto,
            )

    hm, rule_id = await heuristic_eval()
    if hm:
        sim = await nlp_similarity()
        if sim is not None and sim < veto_threshold:
            notes_veto.append("nlp_veto:heuristic")
        else:
            return LayerEvaluation(
                matched=True,
                layer="heuristic",
                confidence=0.9,
                direct_path="none",
                rule_id=rule_id,
                nlp_similarity=sim,
                nlp_confirmed=True,
                notes=notes_veto,
            )

    if await nlp_match():
        return LayerEvaluation(
            matched=True,
            layer="nlp",
            confidence=0.7,
            direct_path="none",
            notes=notes_veto,
        )

    return LayerEvaluation(
        matched=False,
        layer="none",
        confidence=0.0,
        direct_path="none",
        notes=notes_veto,
    )


async def evaluate_layers_supply_tree(
    *,
    direct_eval: Callable[[], Awaitable[Tuple[bool, DirectPath]]],
    heuristic_eval: Callable[[], Awaitable[Tuple[bool, Optional[str]]]],
    nlp_match: Callable[[], Awaitable[bool]],
    nlp_similarity: Callable[[], Awaitable[Optional[float]]],
    partial_similarity: Callable[[], float],
    require_direct_match: bool,
    mode: CascadeMode = "cascade",
    veto_threshold: float = 0.2,
    veto_enabled: bool = False,
) -> Tuple[float, str]:
    """
    Supply-tree scoring: layers + optional partial similarity fallback.

    When require_direct_match is True, only direct matching applies (URI safety).

    Returns:
        (confidence, match_type) where match_type is
        direct|heuristic|nlp|partial|no_match
    """
    dm, dpath = await direct_eval()

    if require_direct_match:
        if dm:
            return (1.0, "direct")
        return (0.0, "no_match")

    use_veto = veto_enabled and mode == "veto"

    if use_veto:
        if dm and dpath == "strong":
            return (1.0, "direct")
        if dm and dpath == "fuzzy":
            sim = await nlp_similarity()
            if sim is not None and sim < veto_threshold:
                dm = False
            else:
                return (1.0, "direct")

    if dm:
        return (1.0, "direct")

    hm, _ = await heuristic_eval()
    if use_veto and hm:
        sim = await nlp_similarity()
        if sim is not None and sim < veto_threshold:
            hm = False

    if hm:
        return (0.8, "heuristic")

    if await nlp_match():
        return (0.7, "nlp")

    sim_partial = partial_similarity()
    if sim_partial >= 0.3:
        return (sim_partial * 0.6, "partial")

    return (0.0, "no_match")
