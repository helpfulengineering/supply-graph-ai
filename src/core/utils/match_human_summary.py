from typing import Any, Dict, List


def _solution_label(solution: Dict[str, Any]) -> str:
    tree = solution.get("tree") or {}
    facility_name = solution.get("facility_name")
    if not facility_name and isinstance(solution.get("facility"), dict):
        facility_name = solution["facility"].get("name")
    if not facility_name and isinstance(tree, dict):
        facility_name = tree.get("facility_name")
    if not facility_name:
        facility_name = "Unknown Facility"

    confidence = solution.get("confidence", solution.get("score"))
    if confidence is None and isinstance(tree, dict):
        confidence = tree.get("confidence_score")
    if isinstance(confidence, (int, float)):
        return f"{facility_name} (confidence={confidence:.2f})"
    return facility_name


def build_match_human_summary(
    match_summary: Dict[str, Any],
    coverage_gaps: List[str],
    solutions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build deterministic multi-level human summaries for match responses.

    The output is additive and stable so clients can safely parse it:
    - executive: non-technical one-line summary
    - technical: concise practitioner-facing line
    - detailed: bullet-like detail list for deep inspection
    """
    mode = str(match_summary.get("matching_mode", "unknown"))
    solution_count = int(match_summary.get("solution_count") or 0)
    covered = int(match_summary.get("covered_process_count") or 0)
    required = int(match_summary.get("required_process_count") or 0)
    coverage_ratio = float(match_summary.get("coverage_ratio") or 0.0)
    combinations_requested = bool(match_summary.get("facility_combination_requested"))
    combinations_applied = bool(match_summary.get("facility_combination_applied"))
    warnings = [str(w) for w in (match_summary.get("warnings") or [])]
    top_labels = [_solution_label(s) for s in solutions[:3]]

    if required > 0:
        executive = (
            f"{solution_count} candidate solution(s) found; "
            f"coverage {covered}/{required} ({coverage_ratio:.3f})."
        )
    else:
        executive = f"{solution_count} candidate solution(s) found."

    technical = (
        f"mode={mode}; solutions={solution_count}; "
        f"covered_processes={covered}/{required}; "
        f"facility_combinations=requested:{combinations_requested},"
        f"applied:{combinations_applied}"
    )

    detailed: List[str] = []
    if top_labels:
        detailed.append("Top facilities: " + "; ".join(top_labels))
    if coverage_gaps:
        detailed.append("Coverage gaps: " + ", ".join(str(g) for g in coverage_gaps))
    if warnings:
        detailed.append("Warnings: " + " | ".join(warnings))

    return {
        "executive": executive,
        "technical": technical,
        "detailed": detailed,
    }
