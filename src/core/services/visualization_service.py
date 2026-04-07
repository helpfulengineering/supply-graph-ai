"""Visualization bundle and report generation service."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.core.models.supply_trees import SupplyTreeSolution


class VisualizationService:
    """Builds canonical visualization artifacts for API/CLI consumers."""

    SCHEMA_VERSION = "3.2.0"

    @classmethod
    def _now_iso(cls) -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def build_match_visualization_bundle(
        cls, match_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build additive visualization contract from match response data."""
        solutions = (
            match_data.get("solutions", []) if isinstance(match_data, dict) else []
        )
        match_summary = (
            match_data.get("match_summary", {}) if isinstance(match_data, dict) else {}
        )
        coverage_gaps = (
            match_data.get("coverage_gaps", []) if isinstance(match_data, dict) else []
        )
        suggestions = (
            match_data.get("suggestions", []) if isinstance(match_data, dict) else []
        )
        suggestion_codes = (
            match_data.get("suggestion_codes", [])
            if isinstance(match_data, dict)
            else []
        )

        bins = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        capability_edges: Dict[str, set[str]] = defaultdict(set)
        facility_locations: Counter[str] = Counter()

        for solution in solutions:
            confidence = float(
                solution.get("confidence", solution.get("score", 0.0)) or 0.0
            )
            if confidence < 0.2:
                bins["0.0-0.2"] += 1
            elif confidence < 0.4:
                bins["0.2-0.4"] += 1
            elif confidence < 0.6:
                bins["0.4-0.6"] += 1
            elif confidence < 0.8:
                bins["0.6-0.8"] += 1
            else:
                bins["0.8-1.0"] += 1

            facility_name = str(
                solution.get("facility_name")
                or (solution.get("facility") or {}).get("name")
                or "Unknown Facility"
            )
            location = (
                solution.get("location")
                or (solution.get("facility") or {}).get("location")
                or "not_provided"
            )
            facility_locations[str(location)] += 1

            tree = solution.get("tree", {}) if isinstance(solution, dict) else {}
            capabilities = (
                tree.get("capabilities_used", []) if isinstance(tree, dict) else []
            )
            for cap in capabilities:
                capability_edges[str(cap)].add(facility_name)

        required = int(match_summary.get("required_process_count", 0) or 0)
        covered = int(match_summary.get("covered_process_count", 0) or 0)
        uncovered = max(required - covered, len(coverage_gaps))

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "source_type": "match_result",
            "generated_at": cls._now_iso(),
            "matching": {
                "overview": {
                    "matching_mode": match_summary.get("matching_mode", "unknown"),
                    "total_solutions": int(
                        match_data.get("total_solutions", len(solutions)) or 0
                    ),
                    "coverage_ratio": float(
                        match_summary.get("coverage_ratio", 0.0) or 0.0
                    ),
                },
                "confidence_distribution": bins,
                "coverage_heatmap": [
                    {
                        "metric": "process_coverage",
                        "covered": covered,
                        "uncovered": uncovered,
                    }
                ],
                "gaps_and_guidance": {
                    "coverage_gaps": [str(gap) for gap in coverage_gaps],
                    "suggestions": [str(item) for item in suggestions],
                    "suggestion_codes": [str(code) for code in suggestion_codes],
                },
                "timeline_capacity": {
                    "status": "not_provided",
                    "note": "Timeline/capacity fields are placeholders until provider data is integrated.",
                },
            },
            "supply_tree": {
                "status": "estimated",
                "derived_from_solution_trees": bool(solutions),
            },
            "network": {
                "facility_distribution": [
                    {"location": location, "facility_count": count}
                    for location, count in facility_locations.items()
                ],
                "capability_network": [
                    {
                        "capability": capability,
                        "facilities": sorted(list(facilities)),
                    }
                    for capability, facilities in capability_edges.items()
                ],
                "route_hints": {
                    "status": "estimated",
                    "note": "Route optimization not yet available in core model.",
                },
            },
            "dashboard": {
                "kpis": {
                    "total_solutions": int(
                        match_data.get("total_solutions", len(solutions)) or 0
                    ),
                    "coverage_ratio": float(
                        match_summary.get("coverage_ratio", 0.0) or 0.0
                    ),
                    "suggestion_count": len(suggestions),
                    "gap_count": len(coverage_gaps),
                }
            },
            "artifacts": {
                "json_bundle": True,
                "graphml": "available_via_supply_tree_exports",
                "html_report": True,
            },
        }

    @classmethod
    def build_solution_visualization_bundle(
        cls, solution: SupplyTreeSolution, solution_id: str
    ) -> Dict[str, Any]:
        """Build visualization bundle from a stored supply tree solution."""
        all_trees = list(solution.all_trees or [])
        dependency_graph = solution.get_dependency_graph()
        if solution.production_sequence:
            sequence = [
                [str(tree_id) for tree_id in stage]
                for stage in solution.production_sequence
            ]
        else:
            sequence_ids = SupplyTreeSolution._calculate_production_sequence(
                dependency_graph
            )
            sequence = [[str(tree_id) for tree_id in stage] for stage in sequence_ids]

        nodes = []
        edges = []
        facility_distribution: Counter[str] = Counter()

        for tree in all_trees:
            tree_id = str(tree.id)
            nodes.append(
                {
                    "id": tree_id,
                    "label": tree.component_name or tree.facility_name,
                    "component_id": tree.component_id,
                    "facility_name": tree.facility_name,
                    "depth": tree.depth,
                    "production_stage": tree.production_stage,
                    "confidence_score": tree.confidence_score,
                    "estimated_cost": tree.estimated_cost,
                    "estimated_time": tree.estimated_time,
                }
            )
            facility_distribution[tree.facility_name or "Unknown Facility"] += 1

            if tree.parent_tree_id:
                edges.append(
                    {
                        "source": str(tree.parent_tree_id),
                        "target": tree_id,
                        "type": "parent-child",
                    }
                )
            for dep_id in tree.depends_on:
                edges.append(
                    {"source": str(dep_id), "target": tree_id, "type": "depends_on"}
                )

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "source_type": "supply_tree_solution",
            "generated_at": cls._now_iso(),
            "matching": {
                "overview": {
                    "matching_mode": solution.metadata.get("matching_mode", "unknown"),
                    "score": solution.score,
                    "tree_count": len(all_trees),
                }
            },
            "supply_tree": {
                "solution_id": solution_id,
                "nodes": nodes,
                "edges": edges,
                "dependency_graph": {
                    str(tree_id): [str(dep_id) for dep_id in deps]
                    for tree_id, deps in dependency_graph.items()
                },
                "production_sequence": sequence,
                "resource_cost": {
                    "total_estimated_cost": solution.total_estimated_cost,
                    "total_estimated_time": solution.total_estimated_time,
                },
            },
            "network": {
                "facility_distribution": [
                    {"facility_name": name, "tree_count": count}
                    for name, count in facility_distribution.items()
                ],
                "route_hints": {
                    "status": "not_provided",
                    "note": "No transport route data exists in current supply tree contract.",
                },
            },
            "dashboard": {
                "kpis": {
                    "tree_count": len(all_trees),
                    "edge_count": len(edges),
                    "stage_count": len(sequence),
                    "solution_score": solution.score,
                }
            },
            "artifacts": {
                "graphml_endpoint": f"/v1/api/supply-tree/solution/{solution_id}/export?format=graphml",
                "json_bundle": True,
                "html_report": True,
            },
        }

    @classmethod
    def render_html_report(cls, bundle: Dict[str, Any], title: str) -> str:
        """Render a lightweight standalone HTML report."""
        escaped_payload = json.dumps(bundle, indent=2)
        generated_at = bundle.get("generated_at", cls._now_iso())
        return (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            f"<title>{title}</title>"
            "<style>"
            "body{font-family:Arial,Helvetica,sans-serif;margin:24px;line-height:1.4;}"
            "h1,h2{margin:0 0 12px 0;} .meta{color:#444;margin-bottom:16px;}"
            "pre{background:#f5f5f5;padding:12px;border-radius:6px;overflow:auto;}"
            ".kpi{display:inline-block;margin-right:18px;padding:8px 10px;background:#f0f4ff;border-radius:6px;}"
            "</style></head><body>"
            f"<h1>{title}</h1>"
            f"<div class='meta'>Generated: {generated_at} | Schema: {bundle.get('schema_version')}</div>"
            "<h2>KPI Summary</h2>"
            f"<div class='kpi'>Source: {bundle.get('source_type')}</div>"
            f"<div class='kpi'>Artifacts: {', '.join(sorted(bundle.get('artifacts', {}).keys()))}</div>"
            "<h2>Bundle Payload</h2>"
            f"<pre>{escaped_payload}</pre>"
            "</body></html>"
        )

    @classmethod
    def normalize_graphml_metadata(
        cls, graphml_content: str, source_type: str, source_id: str
    ) -> str:
        """Inject stable metadata comment for graph export traceability."""
        metadata_comment = (
            f"<!-- ohm_visualization_schema={cls.SCHEMA_VERSION};"
            f"source_type={source_type};source_id={source_id} -->"
        )
        if metadata_comment in graphml_content:
            return graphml_content
        if graphml_content.startswith("<?xml"):
            end_decl = graphml_content.find("?>")
            if end_decl != -1:
                prefix = graphml_content[: end_decl + 2]
                suffix = graphml_content[end_decl + 2 :]
                return f"{prefix}\n{metadata_comment}\n{suffix}"
        return f"{metadata_comment}\n{graphml_content}"
