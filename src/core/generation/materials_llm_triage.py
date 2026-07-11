"""Targeted LLM triage for low-confidence materials."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from .materials_confidence import (
    MaterialReviewItem,
    build_material_review_items,
    score_material,
)
from .materials_filter import normalize_material_key

logger = logging.getLogger(__name__)

MAX_TRIAGE_ITEMS = 40
_CORPUS_SNIPPET_CHARS = 4000


@dataclass
class MaterialTriageDecision:
    """LLM (or deterministic) decision for one low-confidence material."""

    name: str
    action: str  # accept | reject | rename
    new_name: Optional[str] = None


def build_materials_triage_prompt(
    items: Sequence[MaterialReviewItem],
    corpus_snippet: str,
) -> str:
    """Build a bounded accept/reject/rename prompt for low-confidence materials."""
    listed = [
        {"name": i.name, "confidence": i.confidence, "reason": i.reason}
        for i in items[:MAX_TRIAGE_ITEMS]
    ]
    snippet = (corpus_snippet or "")[:_CORPUS_SNIPPET_CHARS]
    return (
        "You triage candidate OKH materials extracted from an open hardware project.\n"
        "For each candidate, decide:\n"
        '- "accept" — it is a real part/material name\n'
        '- "reject" — chat/sales/instruction/tool junk, not a material\n'
        '- "rename" — real part but needs a cleaner name (set new_name)\n\n'
        "Return ONLY a JSON array of objects with keys: name, action, new_name "
        "(new_name null unless action is rename).\n\n"
        f"Candidates:\n{json.dumps(listed, ensure_ascii=False, indent=2)}\n\n"
        f"Doc excerpt:\n{snippet}\n"
    )


def parse_materials_triage_response(
    content: str,
    items: Sequence[MaterialReviewItem],
) -> List[MaterialTriageDecision]:
    """Parse LLM JSON into decisions; unknown names are ignored."""
    known = {normalize_material_key(i.name): i.name for i in items}
    raw = _extract_json_array(content)
    if raw is None:
        logger.warning("Materials LLM triage: could not parse JSON response")
        return []

    decisions: List[MaterialTriageDecision] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        key = normalize_material_key(name)
        if not name or key not in known:
            continue
        action = str(entry.get("action") or "").strip().casefold()
        if action not in {"accept", "reject", "rename"}:
            continue
        new_name = None
        if action == "rename":
            new_name = str(entry.get("new_name") or "").strip() or None
            if not new_name:
                action = "accept"
        decisions.append(
            MaterialTriageDecision(name=known[key], action=action, new_name=new_name)
        )
    return decisions


def apply_material_triage_decisions(
    materials: List[dict],
    decisions: Sequence[MaterialTriageDecision],
    *,
    generate_material_id,
) -> Tuple[List[dict], List[MaterialReviewItem]]:
    """Apply accept/reject/rename; rebuild review queue for remaining low-conf."""
    by_key = {normalize_material_key(d.name): d for d in decisions if d.name}
    out: List[dict] = []
    seen: set[str] = set()
    scored: List[tuple] = []

    for row in materials:
        name = str(row.get("name") or "").strip()
        key = normalize_material_key(name)
        decision = by_key.get(key)
        if decision and decision.action == "reject":
            continue
        if decision and decision.action == "rename" and decision.new_name:
            name = decision.new_name.strip()
            key = normalize_material_key(name)
            row = {
                **row,
                "name": name,
                "material_id": generate_material_id(name),
            }
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(row)

        if decision and decision.action in {"accept", "rename"}:
            confidence, reason = 0.85, "llm_triage_accepted"
        else:
            confidence, reason = score_material(
                name, source="extracted", has_evidence=True
            )
        scored.append((name, confidence, "extracted", reason, row.get("material_id")))

    return out, build_material_review_items(scored)


def _extract_json_array(content: str) -> Optional[List[Any]]:
    text = (content or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("["), text.rfind("]")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


async def triage_low_confidence_materials(
    items: Sequence[MaterialReviewItem],
    corpus_snippet: str,
    llm_service: Any,
) -> List[MaterialTriageDecision]:
    """Call LLM to triage low-confidence materials; empty list on failure."""
    from ..llm.models.requests import LLMRequestConfig, LLMRequestType
    from ..llm.models.responses import LLMResponseStatus

    if not items or llm_service is None:
        return []

    bounded = list(items[:MAX_TRIAGE_ITEMS])
    prompt = build_materials_triage_prompt(bounded, corpus_snippet)
    try:
        from ..services.base import ServiceStatus

        if getattr(llm_service, "status", None) != ServiceStatus.ACTIVE:
            await llm_service.initialize()

        response = await llm_service.generate(
            prompt=prompt,
            request_type=LLMRequestType.ANALYSIS,
            config=LLMRequestConfig(max_tokens=2000, temperature=0.1),
        )
        if response.status != LLMResponseStatus.SUCCESS:
            logger.warning(
                "Materials LLM triage failed: %s",
                getattr(response, "error_message", None)
                or getattr(response, "error", None)
                or "unknown",
            )
            return []
        return parse_materials_triage_response(response.content, bounded)
    except Exception as exc:
        logger.warning("Materials LLM triage error: %s", exc)
        return []
