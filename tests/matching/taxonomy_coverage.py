"""Taxonomy ↔ facility matchability coverage helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence
from uuid import uuid4

from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility
from src.core.taxonomy import taxonomy


@dataclass(frozen=True)
class ProcessCoverageRow:
    canonical_id: str
    display_name: str
    parent: Optional[str]
    facility_count: int
    matched: bool
    sample_facility_names: tuple[str, ...]


def iter_canonical_ids() -> List[str]:
    return sorted(taxonomy.get_all_canonical_ids())


def facilities_claiming_process(
    facilities: Sequence[ManufacturingFacility],
    canonical_id: str,
) -> List[ManufacturingFacility]:
    """Facilities whose declared processes satisfy ``canonical_id`` (incl. hierarchy)."""
    return [f for f in facilities if f.has_process(canonical_id)]


def minimal_okh_for_process(canonical_id: str) -> OKHManifest:
    """Single-process OKH used to probe matchability for one taxonomy id."""
    display = taxonomy.get_display_name(canonical_id) or canonical_id
    return OKHManifest.from_dict(
        {
            "okhv": "0.1.0",
            "id": str(uuid4()),
            "title": f"Coverage probe: {display}",
            "version": "0.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "OHM Match Harness",
            "documentation_language": "en",
            "function": f"Taxonomy coverage probe for {canonical_id}",
            "manufacturing_processes": [canonical_id],
        }
    )


async def probe_match(
    *,
    matching_service: Any,
    canonical_id: str,
    candidates: Sequence[ManufacturingFacility],
    max_candidates: int = 25,
) -> bool:
    """Return True if MatchingService finds ≥1 solution for this process."""
    if not candidates:
        return False
    okh = minimal_okh_for_process(canonical_id)
    solutions = await matching_service.find_matches_with_manifest(
        okh_manifest=okh,
        facilities=list(candidates)[:max_candidates],
    )
    return len(solutions) >= 1


async def build_coverage_report(
    facilities: Sequence[ManufacturingFacility],
    *,
    matching_service: Any | None = None,
    verify_match: bool = True,
    max_candidates: int = 25,
    process_ids: Iterable[str] | None = None,
) -> list[ProcessCoverageRow]:
    """Score every taxonomy process against a facility pool.

    When ``verify_match`` is True and a matching service is provided, processes
    with facility coverage are confirmed via ``find_matches_with_manifest``.
    Zero-coverage processes are reported as not matched without calling the
    matcher.
    """
    rows: list[ProcessCoverageRow] = []
    ids = list(process_ids) if process_ids is not None else iter_canonical_ids()
    for cid in ids:
        claiming = facilities_claiming_process(facilities, cid)
        matched = False
        if claiming and verify_match and matching_service is not None:
            matched = await probe_match(
                matching_service=matching_service,
                canonical_id=cid,
                candidates=claiming,
                max_candidates=max_candidates,
            )
        elif claiming and not verify_match:
            matched = True
        rows.append(
            ProcessCoverageRow(
                canonical_id=cid,
                display_name=taxonomy.get_display_name(cid) or cid,
                parent=taxonomy.get_parent(cid),
                facility_count=len(claiming),
                matched=matched,
                sample_facility_names=tuple(f.name for f in claiming[:3]),
            )
        )
    return rows


def format_coverage_table(rows: Sequence[ProcessCoverageRow]) -> str:
    """Human-readable markdown table + summary counts."""
    matched = [r for r in rows if r.matched]
    uncovered = [r for r in rows if not r.matched]
    lines = [
        f"Taxonomy processes: {len(rows)}",
        f"Matchable: {len(matched)}",
        f"Not matchable: {len(uncovered)}",
        "",
        "| Status | Process | Parent | Facilities | Samples |",
        "|--------|---------|--------|------------|---------|",
    ]
    for r in rows:
        status = "yes" if r.matched else "no"
        samples = ", ".join(r.sample_facility_names) if r.sample_facility_names else "—"
        parent = r.parent or "—"
        lines.append(
            f"| {status} | `{r.canonical_id}` ({r.display_name}) | {parent} "
            f"| {r.facility_count} | {samples} |"
        )
    if uncovered:
        lines.append("")
        lines.append("### Not matchable")
        for r in uncovered:
            lines.append(f"- `{r.canonical_id}` ({r.display_name})")
    return "\n".join(lines)


def write_coverage_json(rows: Sequence[ProcessCoverageRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "process_count": len(rows),
        "matchable_count": sum(1 for r in rows if r.matched),
        "not_matchable_count": sum(1 for r in rows if not r.matched),
        "rows": [asdict(r) for r in rows],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
