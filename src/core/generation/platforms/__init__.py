"""
Platform extractors for OKH manifest generation.

This module provides platform-specific extractors for different hosting platforms
like GitHub, GitLab, Codeberg, and Hackaday.io. Each extractor is responsible for
converting platform-specific data into a standardized ProjectData format.

The platform extractors support:
- URL validation and parsing
- API authentication and rate limiting
- Caching for improved performance
- Error handling and metrics tracking
- Standardized data extraction
"""

from .base import ProjectExtractor, ExtractionMetrics
from .github import GitHubExtractor
from .gitlab import GitLabExtractor

__all__ = [
    'ProjectExtractor',
    'ExtractionMetrics', 
    'GitHubExtractor',
    'GitLabExtractor'
]
