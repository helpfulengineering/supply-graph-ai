"""Match coverage must be read from the matcher's own verdict.

The summary reported ``coverage 0/N`` and listed every requirement as a gap on
*every* match, while the result cards beside it said "Meets every requirement".
Both were rendering the same response.

``_collect_matched_processes_from_solutions`` read ``tree.capabilities_used``,
a key that is present on every tree and always empty, so nothing was ever
counted as matched. The summary was not describing a failed match — it was
describing a field nobody populates.

This fires in the worst direction: a successful match is presented as a total
failure, in a warning-styled banner naming the exact capabilities the user
needs, above ten facilities that can in fact build the design.
"""

from __future__ import annotations

from src.core.api.routes.match import (
    _build_match_summary,
    _collect_matched_processes_from_solutions,
)


class Request:
    """The fields _build_match_summary reads off the request."""

    allow_facility_combinations = False
    max_facilities_per_solution = None
    return_alternative_solutions = False
    combination_strategy = None


def solution(*matches, composite=False, facilities=()):
    if composite:
        return {
            "is_composite": True,
            "facility_details": [
                {"facility": {"manufacturing_processes": list(p)}} for p in facilities
            ],
        }
    return {
        "tree": {"capabilities_used": []},  # always empty in practice
        "explanation": {
            "requirement_matches": [
                {
                    "requirement_value": value,
                    "matched_capability": capability,
                    "status": status,
                }
                for value, capability, status in matches
            ]
        },
    }


def summarise(required, solutions):
    return _build_match_summary(
        required_processes=required,
        matched_processes=_collect_matched_processes_from_solutions(solutions),
        solution_count=len(solutions),
        matching_mode="single-level",
        request=Request(),
    )


class TestCoverageReflectsTheMatch:
    def test_a_fully_matched_design_reports_full_coverage(self):
        """The reported bug: this said 0/3 with every process listed as a gap."""
        solutions = [
            solution(
                ("3D Printing", "3d_printing", "matched"),
                ("Laser Cutting", "laser_cutting", "matched"),
                ("Assembly", "electronics_assembly", "matched"),
            )
        ]

        summary, gaps = summarise(
            ["3D Printing", "Laser Cutting", "Assembly"], solutions
        )

        assert summary["covered_process_count"] == 3
        assert summary["required_process_count"] == 3
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_an_unmatched_requirement_is_still_reported_as_a_gap(self):
        """The fix must not make every match look complete instead."""
        solutions = [
            solution(
                ("3D Printing", "3d_printing", "matched"),
                ("Soldering", None, "not_matched"),
            )
        ]

        summary, gaps = summarise(["3D Printing", "Soldering"], solutions)

        assert summary["covered_process_count"] == 1
        assert gaps == ["Soldering"]

    def test_coverage_is_the_union_across_solutions(self):
        """No single facility covers everything, but the network does."""
        solutions = [
            solution(("3D Printing", "3d_printing", "matched")),
            solution(("Laser Cutting", "laser_cutting", "matched")),
        ]

        summary, gaps = summarise(["3D Printing", "Laser Cutting"], solutions)

        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_duplicate_requirements_are_counted_once(self):
        """Designs declaring a process in both sources must not report 6 of 3."""
        solutions = [
            solution(
                ("3D Printing", "3d_printing", "matched"),
                ("3D Printing", "3d_printing", "matched"),
            )
        ]

        summary, _ = summarise(["3D Printing", "3D Printing"], solutions)

        assert summary["required_process_count"] == 1
        assert summary["covered_process_count"] == 1

    def test_no_solutions_means_no_coverage(self):
        summary, gaps = summarise(["3D Printing"], [])

        assert summary["covered_process_count"] == 0
        assert gaps == ["3D Printing"]

    def test_composite_solutions_still_use_facility_processes(self):
        """A composite's coverage is the union of its members, not one verdict."""
        solutions = [
            solution(
                composite=True,
                facilities=(["3D Printing"], ["Laser Cutting"]),
            )
        ]

        summary, gaps = summarise(["3D Printing", "Laser Cutting"], solutions)

        assert summary["coverage_ratio"] == 1.0
        assert gaps == []


class TestCollection:
    def test_only_matched_requirements_are_collected(self):
        collected = _collect_matched_processes_from_solutions(
            [
                solution(
                    ("3D Printing", "3d_printing", "matched"),
                    ("Soldering", None, "not_matched"),
                )
            ]
        )

        assert "Soldering" not in collected
        assert "3D Printing" in collected

    def test_both_the_requirement_and_the_capability_are_kept(self):
        """Either form may be the one the taxonomy recognises."""
        collected = _collect_matched_processes_from_solutions(
            [solution(("Assembly", "electronics_assembly", "matched"))]
        )

        assert set(collected) == {"Assembly", "electronics_assembly"}

    def test_a_solution_without_an_explanation_contributes_nothing(self):
        assert _collect_matched_processes_from_solutions([{"tree": {}}]) == []
