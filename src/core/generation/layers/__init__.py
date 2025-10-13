"""
Generation layers for OKH manifest generation.

This module provides different layers of intelligence for generating manifest fields:
1. Direct matching - exact field mappings from platform metadata
2. Heuristic matching - rule-based pattern recognition (future)
3. NLP matching - semantic understanding of content (future)
4. LLM matching - AI-powered content understanding (future)
"""

from .base import GenerationLayer
from .direct import DirectMatcher

__all__ = ['GenerationLayer', 'DirectMatcher']
