"""The requirement-aware prefilter must respect its cap on every path.

When no facility advertises a required process the prefilter falls back to the
full pool — correct, since returning nothing would make the design unmatchable.
But that path used to return the pool *unbounded*, ignoring ``max_candidates``:
the one route by which an entire network (3,193 facilities in production) could
reach heavy matching with no ceiling at all.

This is not hypothetical. MoM advertises zero facilities for soldering,
assembly and drilling, so every electronics design takes this path.
"""

from __future__ import annotations

from src.core.api.routes.match import _prefilter_facilities_by_required_processes


class Facility:
    def __init__(self, processes):
        self.manufacturing_processes = processes


def pool(n: int, processes):
    return [Facility(list(processes)) for _ in range(n)]


def test_the_no_overlap_fallback_respects_the_cap():
    facilities = pool(3193, ["knitting"])

    kept = _prefilter_facilities_by_required_processes(
        facilities, ["soldering"], "req-1", 200
    )

    assert len(kept) == 200


def test_the_no_overlap_fallback_keeps_everything_when_uncapped():
    facilities = pool(50, ["knitting"])

    kept = _prefilter_facilities_by_required_processes(
        facilities, ["soldering"], "req-1", None
    )

    assert len(kept) == 50, "an absent cap must not silently truncate"


def test_the_cap_applies_on_the_scored_path_too():
    facilities = pool(500, ["3d printing"])

    kept = _prefilter_facilities_by_required_processes(
        facilities, ["3d printing"], "req-1", 25
    )

    assert len(kept) == 25


def test_an_empty_pool_stays_empty():
    assert _prefilter_facilities_by_required_processes([], ["soldering"], "r", 10) == []
