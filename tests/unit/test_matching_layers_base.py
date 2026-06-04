"""Characterization tests for matching/layers/base.py.

Tests current behavior of BaseMatchingLayer utilities via a minimal concrete subclass,
plus MatchingMetrics, MatchMetadata, and MatchingResult data classes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import pytest

from src.core.matching.layers.base import (
    BaseMatchingLayer,
    MatchingLayer,
    MatchingMetrics,
    MatchMetadata,
    MatchingResult,
    MatchQuality,
)

# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing abstract methods
# ---------------------------------------------------------------------------


class _StubLayer(BaseMatchingLayer):
    """Minimal concrete implementation for testing base class methods."""

    def __init__(self, domain="general"):
        super().__init__(MatchingLayer.DIRECT, domain)

    async def match(self, requirements, capabilities):
        return []


# ---------------------------------------------------------------------------
# MatchingMetrics
# ---------------------------------------------------------------------------


class TestMatchingMetrics:
    def test_duration_none_before_end(self):
        m = MatchingMetrics(start_time=datetime.now())
        assert m.duration is None

    def test_duration_after_end(self):
        start = datetime.now()
        m = MatchingMetrics(start_time=start)
        m.end_time = start + timedelta(milliseconds=500)
        assert m.duration is not None
        assert m.duration.total_seconds() == pytest.approx(0.5, abs=0.01)

    def test_match_rate_zero_when_no_requirements(self):
        m = MatchingMetrics(
            start_time=datetime.now(), total_requirements=0, matches_found=0
        )
        assert m.match_rate == 0.0

    def test_match_rate_calculated_correctly(self):
        m = MatchingMetrics(
            start_time=datetime.now(), total_requirements=4, matches_found=3
        )
        assert m.match_rate == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# MatchMetadata
# ---------------------------------------------------------------------------


class TestMatchMetadata:
    def test_to_dict_contains_expected_keys(self):
        meta = MatchMetadata(
            method="direct_general",
            confidence=0.9,
            reasons=["exact match"],
        )
        d = meta.to_dict()
        assert "method" in d
        assert "confidence" in d
        assert "quality" in d
        assert "timestamp" in d
        assert d["quality"] == "no_match"

    def test_to_dict_rule_used_none_by_default(self):
        meta = MatchMetadata(method="x", confidence=0.5, reasons=[])
        assert meta.to_dict()["rule_used"] is None

    def test_to_dict_semantic_similarity_none_by_default(self):
        meta = MatchMetadata(method="x", confidence=0.5, reasons=[])
        assert meta.to_dict()["semantic_similarity"] is None


# ---------------------------------------------------------------------------
# MatchingResult
# ---------------------------------------------------------------------------


class TestMatchingResult:
    def _result(self, matched=True, confidence=1.0, quality=MatchQuality.PERFECT):
        meta = MatchMetadata(
            method="direct_general",
            confidence=confidence,
            reasons=["test"],
            quality=quality,
        )
        return MatchingResult(
            requirement="milling",
            capability="cnc machining",
            matched=matched,
            confidence=confidence,
            metadata=meta,
            layer_type=MatchingLayer.DIRECT,
        )

    def test_to_dict_shape(self):
        d = self._result().to_dict()
        assert set(d.keys()) == {
            "requirement",
            "capability",
            "matched",
            "confidence",
            "metadata",
            "layer_type",
        }
        assert d["layer_type"] == "direct"
        assert d["matched"] is True

    def test_to_dict_no_match(self):
        d = self._result(
            matched=False, confidence=0.0, quality=MatchQuality.NO_MATCH
        ).to_dict()
        assert d["matched"] is False
        assert d["confidence"] == 0.0


# ---------------------------------------------------------------------------
# BaseMatchingLayer — metrics lifecycle
# ---------------------------------------------------------------------------


class TestMetricsLifecycle:
    def test_start_matching_initialises_metrics(self):
        layer = _StubLayer()
        assert layer.metrics is None
        layer.start_matching(["milling"], ["cnc machining"])
        assert layer.metrics is not None
        assert layer.metrics.total_requirements == 1
        assert layer.metrics.total_capabilities == 1

    def test_start_matching_handles_none_inputs(self):
        layer = _StubLayer()
        layer.start_matching(None, None)
        assert layer.metrics.total_requirements == 0
        assert layer.metrics.total_capabilities == 0

    def test_end_matching_sets_success(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        layer.end_matching(success=True, matches_found=1)
        assert layer.metrics.success is True
        assert layer.metrics.matches_found == 1

    def test_end_matching_computes_processing_time(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        layer.end_matching(success=True, matches_found=0)
        assert layer.metrics.processing_time_ms >= 0

    def test_reset_metrics_clears(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        layer.reset_metrics()
        assert layer.metrics is None

    def test_get_metrics_returns_current(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        m = layer.get_metrics()
        assert m is layer.metrics

    def test_add_error_appends_to_metrics(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        layer.add_error("test error")
        assert "test error" in layer.metrics.errors


# ---------------------------------------------------------------------------
# BaseMatchingLayer — validate_inputs
# ---------------------------------------------------------------------------


class TestValidateInputs:
    def test_valid_inputs_returns_true(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], ["c1"])
        assert layer.validate_inputs(["milling"], ["cnc machining"]) is True

    def test_none_requirements_returns_false(self):
        layer = _StubLayer()
        layer.start_matching([], [])
        assert layer.validate_inputs(None, ["c1"]) is False

    def test_none_capabilities_returns_false(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], [])
        assert layer.validate_inputs(["r1"], None) is False

    def test_empty_requirements_list_returns_false(self):
        layer = _StubLayer()
        layer.start_matching([], ["c1"])
        assert layer.validate_inputs([], ["c1"]) is False

    def test_empty_capabilities_list_returns_false(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], [])
        assert layer.validate_inputs(["r1"], []) is False

    def test_empty_string_requirement_returns_false(self):
        layer = _StubLayer()
        layer.start_matching([""], ["c1"])
        assert layer.validate_inputs([""], ["c1"]) is False

    def test_whitespace_only_requirement_returns_false(self):
        layer = _StubLayer()
        layer.start_matching(["  "], ["c1"])
        assert layer.validate_inputs(["  "], ["c1"]) is False

    def test_empty_capability_returns_false(self):
        layer = _StubLayer()
        layer.start_matching(["r1"], [""])
        assert layer.validate_inputs(["r1"], [""]) is False


# ---------------------------------------------------------------------------
# BaseMatchingLayer — create_matching_result
# ---------------------------------------------------------------------------


class TestCreateMatchingResult:
    def test_creates_result_with_correct_layer_type(self):
        layer = _StubLayer()
        result = layer.create_matching_result(
            requirement="milling",
            capability="cnc machining",
            matched=True,
            confidence=0.95,
            method="direct_match",
            reasons=["exact"],
            quality=MatchQuality.PERFECT,
        )
        assert result.layer_type == MatchingLayer.DIRECT
        assert result.matched is True
        assert result.confidence == 0.95

    def test_confidence_clamped_below_zero(self):
        layer = _StubLayer()
        result = layer.create_matching_result(
            requirement="r",
            capability="c",
            matched=False,
            confidence=-0.5,
            method="m",
            reasons=[],
        )
        assert result.confidence == 0.0

    def test_confidence_clamped_above_one(self):
        layer = _StubLayer()
        result = layer.create_matching_result(
            requirement="r",
            capability="c",
            matched=True,
            confidence=1.5,
            method="m",
            reasons=[],
        )
        assert result.confidence == 1.0

    def test_method_includes_domain(self):
        layer = _StubLayer(domain="manufacturing")
        result = layer.create_matching_result(
            requirement="r",
            capability="c",
            matched=True,
            confidence=1.0,
            method="direct_match",
            reasons=[],
        )
        assert "manufacturing" in result.metadata.method


# ---------------------------------------------------------------------------
# BaseMatchingLayer — calculate_levenshtein_distance
# ---------------------------------------------------------------------------


class TestLevenshtein:
    def test_identical_strings(self):
        layer = _StubLayer()
        assert layer.calculate_levenshtein_distance("abc", "abc") == 0

    def test_one_substitution(self):
        layer = _StubLayer()
        assert layer.calculate_levenshtein_distance("cat", "car") == 1

    def test_empty_vs_nonempty(self):
        layer = _StubLayer()
        assert layer.calculate_levenshtein_distance("", "abc") == 3
        assert layer.calculate_levenshtein_distance("abc", "") == 3

    def test_completely_different(self):
        layer = _StubLayer()
        dist = layer.calculate_levenshtein_distance("milling", "welding")
        assert dist > 2

    def test_symmetric(self):
        layer = _StubLayer()
        assert layer.calculate_levenshtein_distance(
            "milling", "turning"
        ) == layer.calculate_levenshtein_distance("turning", "milling")


# ---------------------------------------------------------------------------
# BaseMatchingLayer — has_whitespace_difference
# ---------------------------------------------------------------------------


class TestWhitespaceDifference:
    def test_no_difference(self):
        layer = _StubLayer()
        assert layer.has_whitespace_difference("milling", "milling") is False

    def test_extra_space_detected(self):
        layer = _StubLayer()
        assert (
            layer.has_whitespace_difference("cnc machining", "cnc  machining") is True
        )

    def test_leading_trailing_space(self):
        layer = _StubLayer()
        assert layer.has_whitespace_difference(" milling", "milling") is True

    def test_different_content_not_whitespace_diff(self):
        layer = _StubLayer()
        assert layer.has_whitespace_difference("milling", "welding") is False


# ---------------------------------------------------------------------------
# BaseMatchingLayer — normalize_process_name
# ---------------------------------------------------------------------------


class TestNormalizeProcessName:
    def test_empty_string_returns_empty(self):
        layer = _StubLayer()
        assert layer.normalize_process_name("") == ""

    def test_lowercases_unknown_input(self):
        layer = _StubLayer()
        result = layer.normalize_process_name("XYZ_UNKNOWN_PROCESS")
        assert result == result.lower()

    def test_strips_whitespace(self):
        layer = _StubLayer()
        result = layer.normalize_process_name("  milling  ")
        assert result == result.strip()

    def test_wikipedia_uri_extracted(self):
        layer = _StubLayer()
        result = layer.normalize_process_name(
            "https://en.wikipedia.org/wiki/Milling_(machining)"
        )
        assert "wikipedia.org" not in result
        assert result != ""

    def test_underscores_converted_to_spaces_in_fallback(self):
        # Only the fallback path (unrecognized by taxonomy) converts underscores.
        # Use a string that taxonomy will never recognize.
        layer = _StubLayer()
        result = layer.normalize_process_name("zzzz_unknown_xyzzy_12345")
        assert "_" not in result
