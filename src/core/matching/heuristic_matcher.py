"""
Heuristic Matching Layer Implementation

This module implements the Heuristic Matching layer for the Open Matching Engine (OME).
It provides rule-based matching using domain knowledge stored in capability rules.

This layer is part of the 4-layer matching architecture and inherits from
BaseMatchingLayer to ensure consistent interfaces and error handling.
"""

import logging
from typing import Any, Dict, List, Optional

from .capability_rules import CapabilityRule, CapabilityRuleManager
from .layers.base import BaseMatchingLayer, MatchingLayer, MatchingResult, MatchQuality

logger = logging.getLogger(__name__)


class HeuristicMatcher(BaseMatchingLayer):
    """
    Heuristic matching layer using capability-centric rules.

    This layer provides rule-based matching using domain knowledge stored in
    capability rules. It matches requirements to capabilities based on predefined
    rules that specify which capabilities can satisfy which requirements.

    Features:
    - Rule-based matching using domain knowledge
    - Capability-centric rule system
    - Configurable confidence scoring
    - Support for multiple domains
    - Comprehensive metadata tracking

    Attributes:
        rule_manager: Manager for capability rules
        _initialized: Whether the matcher has been initialized
    """

    def __init__(
        self,
        domain: str = "general",
        rule_manager: Optional[CapabilityRuleManager] = None,
    ):
        """
        Initialize the heuristic matcher.

        Args:
            domain: The domain this matcher operates in (e.g., 'manufacturing', 'cooking')
            rule_manager: Optional rule manager instance. If None, creates a new one.
        """
        super().__init__(MatchingLayer.HEURISTIC, domain)
        self.rule_manager = rule_manager or CapabilityRuleManager()
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the matcher by loading rules.

        Raises:
            RuntimeError: If rule loading fails
        """
        if self._initialized:
            return

        try:
            await self.rule_manager.initialize()
            self._initialized = True
            logger.info(f"HeuristicMatcher initialized for domain: {self.domain}")
        except Exception as e:
            error_msg = f"Failed to initialize HeuristicMatcher: {e}"
            self.add_error(error_msg)
            raise RuntimeError(error_msg) from e

    async def ensure_initialized(self) -> None:
        """Ensure matcher is initialized."""
        if not self._initialized:
            await self.initialize()

    async def match(
        self, requirements: List[str], capabilities: List[str]
    ) -> List[MatchingResult]:
        """
        Match requirements to capabilities using heuristic rules.

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
            # Ensure matcher is initialized
            await self.ensure_initialized()

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
        Match a single requirement against a single capability using rules.

        Args:
            requirement: The requirement string
            capability: The capability string

        Returns:
            MatchingResult with detailed metadata
        """
        # Find matching rules
        rules = self.rule_manager.find_rules_for_capability_requirement(
            self.domain, capability, requirement
        )

        if rules:
            # Use the rule with highest confidence
            best_rule = max(rules, key=lambda r: r.confidence)

            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=True,
                confidence=best_rule.confidence,
                method="heuristic_rule_match",
                reasons=[f"Matched by rule: {best_rule.id}"],
                quality=MatchQuality.RULE_MATCH,
                rule_used=best_rule.id,
            )
        else:
            # No matching rule found
            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=False,
                confidence=0.0,
                method="heuristic_rule_match",
                reasons=["No matching rule found"],
                quality=MatchQuality.NO_MATCH,
            )

    async def capability_can_satisfy_requirement(
        self, capability: str, requirement: str
    ) -> bool:
        """
        Check if a capability can satisfy a requirement using rules.

        Args:
            capability: The capability to check
            requirement: The requirement to check

        Returns:
            True if the capability can satisfy the requirement
        """
        await self.ensure_initialized()

        rules = self.rule_manager.find_rules_for_capability_requirement(
            self.domain, capability, requirement
        )
        return len(rules) > 0

    async def get_matching_rules(
        self, capability: str, requirement: str
    ) -> List[CapabilityRule]:
        """
        Get all rules that match a capability-requirement pair.

        Args:
            capability: The capability string
            requirement: The requirement string

        Returns:
            List of matching CapabilityRule objects
        """
        await self.ensure_initialized()

        return self.rule_manager.find_rules_for_capability_requirement(
            self.domain, capability, requirement
        )

    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded rules.

        Returns:
            Dictionary with rule statistics
        """
        return self.rule_manager.get_rule_statistics()
