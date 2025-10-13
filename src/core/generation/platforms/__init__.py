"""
Platform extractors for OKH manifest generation.

This module provides platform-specific extractors for different hosting platforms
like GitHub, GitLab, Codeberg, and Hackaday.io.
"""

from .base import ProjectExtractor

__all__ = ['ProjectExtractor']
