"""
Direct Matching Layer Implementation

This module implements the Direct Matching layer for the Open Matching Engine (OME).
It provides exact, case-insensitive string matching with detailed metadata tracking
and confidence scoring for both cooking and manufacturing domains.

This layer is part of the 4-layer matching architecture and inherits from
BaseMatchingLayer to ensure consistent interfaces and error handling.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .layers.base import BaseMatchingLayer, MatchingLayer, MatchingResult, MatchQuality


class DirectMatcher(BaseMatchingLayer):
    """
    Direct string matching layer for requirements and capabilities.

    This layer provides exact, case-insensitive string matching with detailed
    metadata tracking and confidence scoring. It supports near-miss detection
    using Levenshtein distance for close matches.

    Features:
    - Exact string matching (case-insensitive)
    - Near-miss detection with configurable threshold
    - Detailed match quality indicators
    - Comprehensive metadata tracking
    - Performance metrics and error handling

    Attributes:
        near_miss_threshold: Maximum character differences for near-miss detection
    """

    def __init__(self, domain: str = "general", near_miss_threshold: int = 2):
        """
        Initialize the direct matcher.

        Args:
            domain: The domain this matcher operates in (e.g., 'cooking', 'manufacturing')
            near_miss_threshold: Maximum character differences to consider as near-miss
        """
        super().__init__(MatchingLayer.DIRECT, domain)
        self.near_miss_threshold = near_miss_threshold

    async def match(
        self, requirements: List[str], capabilities: List[str]
    ) -> List[MatchingResult]:
        """
        Match requirements to capabilities using direct string matching.

        Args:
            requirements: List of requirement strings to match
            capabilities: List of capability strings to match against

        Returns:
            List of MatchingResult objects with detailed metadata

        Raises:
            ValueError: If requirements or capabilities are invalid
            RuntimeError: If matching fails due to configuration issues
        """
        # Start tracking metrics
        self.start_matching(requirements, capabilities)
        self.log_matching_start(requirements, capabilities)

        try:
            # Validate inputs
            if not self.validate_inputs(requirements, capabilities):
                self.end_matching(success=False)
                return []

            results = []

            # Match each requirement against each capability
            for requirement in requirements:
                for capability in capabilities:
                    result = await self._match_single(requirement, capability)
                    results.append(result)

            # End metrics tracking
            matches_found = sum(1 for r in results if r.matched)
            self.end_matching(success=True, matches_found=matches_found)
            self.log_matching_end(results)

            return results

        except Exception as e:
            return self.handle_matching_error(e, [])

    async def _match_single(self, requirement: str, capability: str) -> MatchingResult:
        """
        Match a single requirement against a single capability.

        Args:
            requirement: Original requirement string
            capability: Capability string to match against

        Returns:
            MatchingResult with detailed metadata
        """
        requirement_lower = requirement.lower()
        capability_lower = capability.lower()

        # Check for exact match (case-insensitive)
        if requirement_lower == capability_lower:
            # Calculate additional match quality indicators
            case_difference = requirement != capability
            whitespace_difference = self.has_whitespace_difference(
                requirement, capability
            )

            # Determine quality and confidence
            if not case_difference and not whitespace_difference:
                quality = MatchQuality.PERFECT
                confidence = 1.0
                reasons = ["Exact string match (case and whitespace identical)"]
            elif case_difference and not whitespace_difference:
                quality = MatchQuality.CASE_DIFFERENCE
                confidence = 0.95
                reasons = ["Exact string match (case-insensitive)"]
            elif not case_difference and whitespace_difference:
                quality = MatchQuality.WHITESPACE_DIFFERENCE
                confidence = 0.95
                reasons = ["Exact string match (whitespace difference)"]
            else:
                quality = MatchQuality.CASE_DIFFERENCE  # Both differences
                confidence = 0.9
                reasons = ["Exact string match (case and whitespace differences)"]

            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=True,
                confidence=confidence,
                method="direct_match",
                reasons=reasons,
                quality=quality,
                case_difference=case_difference,
                whitespace_difference=whitespace_difference,
            )
        else:
            # Check for near-miss using Levenshtein distance
            char_diff = self.calculate_levenshtein_distance(
                requirement_lower, capability_lower
            )

            if char_diff <= self.near_miss_threshold:
                # Near miss detected
                return self.create_matching_result(
                    requirement=requirement,
                    capability=capability,
                    matched=False,  # Not considered a match by direct matcher
                    confidence=0.8,
                    method="direct_match",
                    reasons=[f"Near match with {char_diff} character differences"],
                    quality=MatchQuality.NEAR_MISS,
                    character_difference=char_diff,
                )
            else:
                # No match
                return self.create_matching_result(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=0.0,
                    method="direct_match",
                    reasons=[f"No match (Levenshtein distance: {char_diff})"],
                    quality=MatchQuality.NO_MATCH,
                    character_difference=char_diff,
                )

    def get_domain_specific_confidence_adjustments(
        self, requirement: str, capability: str
    ) -> float:
        """
        Get domain-specific confidence adjustments for direct matching.

        This method can be overridden by subclasses to provide domain-specific
        confidence adjustments based on the requirement and capability strings.

        Args:
            requirement: The requirement string
            capability: The capability string

        Returns:
            Confidence adjustment factor (0.0 to 1.0)
        """
        # Default implementation - no domain-specific adjustments
        # Subclasses can override this for domain-specific logic
        return 1.0
