"""
Generation layers for OKH manifest extraction.

This module provides different layers of intelligence for extracting
information from project repositories and generating OKH manifests.
"""

from .base import LayerResult
from .heuristic import HeuristicMatcher
from ..models import GenerationLayer

__all__ = [
    'GenerationLayer',
    'LayerResult', 
    'HeuristicMatcher'
]