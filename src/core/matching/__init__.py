"""
Matching system for the Open Matching Engine (OME).

This module provides a 4-layer matching system that aligns with the generation
system architecture. The matching system is responsible for matching requirements
to capabilities across different domains using progressively sophisticated methods.

Architecture:
- Layer 1: Direct Matching - Exact string matching with near-miss detection
- Layer 2: Heuristic Matching - Rule-based matching using domain knowledge
- Layer 3: NLP Matching - Natural language processing for semantic understanding
- Layer 4: LLM Matching - Large language model enhanced matching (optional)

The matching system supports:
- Multi-domain rule management (manufacturing, cooking, etc.)
- Capability-centric matching rules
- Detailed match metadata and confidence scoring
- Performance metrics and error tracking
- Optional LLM integration with human review fallback
"""

from .direct_matcher import DirectMatcher
from .heuristic_matcher import HeuristicMatcher
from .nlp_matcher import NLPMatcher
from .llm_matcher import LLMMatcher
from .layers.base import (
    MatchingResult,
    MatchMetadata,
    MatchQuality,
    MatchingLayer,
    MatchingMetrics,
)

from .capability_rules import (
    CapabilityRule,
    CapabilityRuleSet,
    CapabilityRuleManager,
    CapabilityMatcher,
    CapabilityMatchResult,
    RuleType,
    RuleDirection,
)

# Factory functions for global instances
from .capability_rules import (
    get_rule_manager,
    get_capability_matcher,
    create_rule_manager,
    create_capability_matcher,
)

__all__ = [
    # Base matching components
    "MatchingResult",
    "MatchMetadata",
    "MatchQuality",
    "MatchingLayer",
    "MatchingMetrics",
    # Matching layer implementations
    "DirectMatcher",
    "HeuristicMatcher",
    "NLPMatcher",
    "LLMMatcher",
    # Capability rules components
    "CapabilityRule",
    "CapabilityRuleSet",
    "CapabilityRuleManager",
    "CapabilityMatcher",
    "CapabilityMatchResult",
    "RuleType",
    "RuleDirection",
    # Factory functions
    "get_rule_manager",
    "get_capability_matcher",
    "create_rule_manager",
    "create_capability_matcher",
]
