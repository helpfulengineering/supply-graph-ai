"""
Matching layers for the Open Hardware Manager (OHM).

This module provides the 4-layer matching architecture that aligns with the
generation system. Each layer implements progressively sophisticated matching
methods from direct string matching to LLM-enhanced semantic matching.

Layers:
- Direct: Exact string matching with near-miss detection
- Heuristic: Rule-based matching using domain knowledge
- NLP: Natural language processing for semantic understanding
- LLM: Large language model enhanced matching (optional)
"""

from .base import (
    BaseMatchingLayer,
    MatchingLayer,
    MatchingMetrics,
    MatchingResult,
    MatchMetadata,
    MatchQuality,
)

__all__ = [
    "BaseMatchingLayer",
    "MatchingResult",
    "MatchingMetrics",
    "MatchQuality",
    "MatchMetadata",
    "MatchingLayer",
]
