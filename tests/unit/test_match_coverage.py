"""
Tests for match coverage computation correctness.

Three documented root causes of coverage=0 despite valid matches:
  RC1 - Wikipedia URI vs plain-text mismatch in comparison
  RC2 - Duplicate entries in required_processes inflates required_count
  RC3 - Taxonomy hierarchy not considered (e.g. FDM is a child of 3D Printing)
"""

import os
import sys

import pytest

# Import from the installed package layout (`src.*`), not a top-level `core` name
# (avoids collisions with unrelated third-party modules named `core`).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Import the functions under test directly to unit-test them in isolation.
# We import lazily inside each test to avoid heavy app-init at collection time.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_request_stub(allow_combinations: bool = True):
    """Minimal MatchRequest-like object for _build_match_summary."""

    class _Stub:
        allow_facility_combinations = allow_combinations
        max_facilities_per_solution = 3
        return_alternative_solutions = True
        combination_strategy = "greedy"

    return _Stub()


# ---------------------------------------------------------------------------
# RC1 — Wikipedia URI vs plain-text mismatch
# ---------------------------------------------------------------------------


class TestCoverageURIVsPlainText:
    """Coverage should handle Wikipedia URI capabilities_used vs plain-text requirements."""

    def test_laser_cutting_uri_matches_plain_text_requirement(self):
        """'Laser Cutting' required vs 'https://…/wiki/Laser_cutting' capability."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["Laser Cutting"],
            matched_processes=["https://en.wikipedia.org/wiki/Laser_cutting"],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert (
            summary["covered_process_count"] == 1
        ), "Laser Cutting (plain) should match Laser_cutting (URI slug)"
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_cnc_machining_uri_matches_plain_text_requirement(self):
        """'CNC Machining' required vs 'https://…/wiki/Machining' capability (substring)."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["CNC Machining"],
            matched_processes=["https://en.wikipedia.org/wiki/Machining"],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert (
            summary["covered_process_count"] == 1
        ), "'machining' is a substring of 'cnc machining' so should count as covered"
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_assembly_uri_matches_plain_text_requirement(self):
        """'Assembly' required vs 'https://…/wiki/Assembly_line' capability."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["Assembly"],
            matched_processes=["https://en.wikipedia.org/wiki/Assembly_line"],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert (
            summary["covered_process_count"] == 1
        ), "'assembly' is a substring of 'assembly line' slug"
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_mixed_uri_and_plain_text_capabilities(self):
        """Multiple requirements; some covered via URIs, some via plain text."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["Laser Cutting", "Assembly"],
            matched_processes=[
                "https://en.wikipedia.org/wiki/Laser_cutting",
                "Assembly",  # plain text — should always match
            ],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert summary["covered_process_count"] == 2
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []


# ---------------------------------------------------------------------------
# RC2 — Duplicate required_processes
# ---------------------------------------------------------------------------


class TestCoverageDuplicateRequirements:
    """Duplicate entries in required_processes should not inflate required_count."""

    def test_duplicate_process_names_deduplicated(self):
        """If the extractor returns the same process twice, required_count = 1."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["CNC Machining", "CNC Machining"],  # duplicate
            matched_processes=["CNC Machining"],
            solution_count=1,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert (
            summary["required_process_count"] == 1
        ), "Duplicate required processes should be deduplicated before counting"
        assert summary["covered_process_count"] == 1
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_duplicate_uri_processes_deduplicated(self):
        """Duplicate URI-form capabilities should not inflate counts either."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["Soldering", "Soldering"],
            matched_processes=["https://en.wikipedia.org/wiki/Soldering"],
            solution_count=1,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert summary["required_process_count"] == 1
        assert summary["covered_process_count"] == 1
        assert summary["coverage_ratio"] == 1.0


# ---------------------------------------------------------------------------
# RC3 — Taxonomy hierarchy (child process covers parent requirement)
# ---------------------------------------------------------------------------


class TestCoverageTaxonomyHierarchy:
    """FDM / SLA are subtypes of 3D Printing; matching them should cover the requirement."""

    def test_fdm_uri_covers_3d_printing_requirement(self):
        """'3D Printing' required vs 'https://…/wiki/Fused_filament_fabrication' matched."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["3D Printing"],
            matched_processes=[
                "https://en.wikipedia.org/wiki/Fused_filament_fabrication"
            ],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert summary["covered_process_count"] == 1, (
            "FDM (fused_filament_fabrication) is a child of 3D Printing in the taxonomy; "
            "matching an FDM facility should cover a '3D Printing' requirement"
        )
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_sla_uri_covers_3d_printing_requirement(self):
        """'3D Printing' required vs 'https://…/wiki/Stereolithography' matched."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["3D Printing"],
            matched_processes=["https://en.wikipedia.org/wiki/Stereolithography"],
            solution_count=3,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert (
            summary["covered_process_count"] == 1
        ), "SLA (stereolithography) is a child of 3D Printing"
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []

    def test_3d_printing_plain_text_still_works(self):
        """'3D Printing' required vs '3D Printing' plain-text matched (regression guard)."""
        from src.core.api.routes.match import _build_match_summary

        summary, gaps = _build_match_summary(
            required_processes=["3D Printing"],
            matched_processes=["3D Printing"],
            solution_count=1,
            matching_mode="single-level",
            request=make_request_stub(),
        )
        assert summary["covered_process_count"] == 1
        assert summary["coverage_ratio"] == 1.0
        assert gaps == []
