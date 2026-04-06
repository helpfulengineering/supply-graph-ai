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
    summary_profile: str = "balanced",
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

    key_insights: Dict[str, List[str]] = {
        "risks": [],
        "opportunities": [],
        "recommendations": [],
    }

    if solution_count == 0:
        key_insights["risks"].append(
            "No candidate solutions were found for the current requirements."
        )

    if coverage_gaps:
        gap_preview = ", ".join(str(g) for g in coverage_gaps[:3])
        extra = len(coverage_gaps) - 3
        suffix = f", +{extra} more" if extra > 0 else ""
        key_insights["risks"].append(
            f"Coverage gap detected for {len(coverage_gaps)} process requirement(s): {gap_preview}{suffix}."
        )

    if warnings:
        key_insights["risks"].append(
            f"{len(warnings)} matching warning(s) emitted; review detailed summary for context."
        )

    if solution_count > 0:
        key_insights["opportunities"].append(
            f"{solution_count} candidate solution(s) available for further evaluation."
        )

    if top_labels:
        key_insights["opportunities"].append(
            "Top candidate facilities: " + "; ".join(top_labels)
        )

    if coverage_gaps and not combinations_requested:
        key_insights["recommendations"].append(
            "Set `allow_facility_combinations=true` to improve aggregate process coverage."
        )
    if combinations_requested and not combinations_applied:
        key_insights["recommendations"].append(
            "Increase `max_facilities_per_solution` or broaden facility inputs to help combination matching apply."
        )
    if coverage_gaps:
        key_insights["recommendations"].append(
            "Add facilities that cover missing processes or relax restrictive filters."
        )

    profile = (
        summary_profile
        if summary_profile in {"balanced", "executive", "analyst"}
        else "balanced"
    )

    if profile == "executive":
        executive_details: List[str] = []
        if top_labels:
            executive_details.append("Top facility: " + top_labels[0])
        if coverage_gaps:
            executive_details.append(
                f"Coverage gaps: {len(coverage_gaps)} process requirement(s) remain uncovered."
            )
        detailed = executive_details
    elif profile == "analyst":
        analyst_details = list(detailed)
        analyst_details.append(
            f"Profile focus: analyst; required={required}; covered={covered}; uncovered={max(required - covered, 0)}."
        )
        analyst_details.append(
            f"Coverage ratio: {coverage_ratio:.3f}; candidate_solutions={solution_count}."
        )
        analyst_details.append(f"Warning count: {len(warnings)}.")
        detailed = analyst_details

    return {
        "profile": profile,
        "executive": executive,
        "technical": technical,
        "detailed": detailed,
        "key_insights": key_insights,
    }
