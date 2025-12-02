"""
Base classes for platform extractors.

This module defines the abstract base class that all platform-specific extractors
must implement. Platform extractors are responsible for extracting project data
from various hosting platforms (GitHub, GitLab, etc.) and converting it into
a standardized ProjectData format for the generation engine.

The base class provides common functionality for:
- URL validation
- Error handling
- Rate limiting
- Caching
- Authentication
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..models import ProjectData

logger = logging.getLogger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics for tracking extraction performance and usage."""

    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    files_extracted: int = 0
    api_calls_made: int = 0
    cache_hits: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def duration(self) -> Optional[timedelta]:
        """Get extraction duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class ProjectExtractor(ABC):
    """
    Abstract base class for platform-specific project extractors.

    This class defines the interface that all platform extractors must implement.
    It provides common functionality for URL validation, error handling, and
    metrics tracking.

    Attributes:
        platform_name: Name of the platform this extractor handles
        rate_limit_remaining: Number of API calls remaining in current window
        rate_limit_reset: Timestamp when rate limit resets
        cache_enabled: Whether caching is enabled for this extractor
        metrics: Current extraction metrics
    """

    def __init__(self, cache_enabled: bool = True, cache_ttl_hours: int = 24):
        """
        Initialize the platform extractor.

        Args:
            cache_enabled: Whether to enable caching for API responses
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.platform_name = self.get_platform_name()
        self.rate_limit_remaining = 60  # Default rate limit
        self.rate_limit_reset = None
        self.cache_enabled = cache_enabled
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.metrics: Optional[ExtractionMetrics] = None

        logger.info(
            f"Initialized {self.platform_name} extractor with cache={'enabled' if cache_enabled else 'disabled'}"
        )

    @abstractmethod
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a platform URL.

        This method should:
        1. Validate the URL format
        2. Make API calls to fetch project data
        3. Parse and normalize the data
        4. Return a ProjectData object

        Args:
            url: The project URL to extract data from

        Returns:
            ProjectData containing extracted information

        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to connect to platform
            RateLimitError: If API rate limit is exceeded
        """
        pass

    def validate_url(self, url: str) -> bool:
        """
        Validate that the URL is appropriate for this extractor.

        Args:
            url: The URL to validate

        Returns:
            True if valid for this platform, False otherwise
        """
        # Default implementation - can be overridden by subclasses
        return True

    def get_platform_name(self) -> str:
        """
        Get the name of the platform this extractor handles.

        Returns:
            Platform name string (e.g., 'github', 'gitlab')
        """
        return self.__class__.__name__.replace("Extractor", "").lower()

    def start_extraction(self, url: str) -> None:
        """
        Start tracking extraction metrics.

        Args:
            url: The URL being extracted
        """
        self.metrics = ExtractionMetrics(start_time=datetime.now())
        logger.info(f"Starting {self.platform_name} extraction for: {url}")

    def end_extraction(self, success: bool, files_count: int = 0) -> None:
        """
        End tracking extraction metrics.

        Args:
            success: Whether extraction was successful
            files_count: Number of files extracted
        """
        if self.metrics:
            self.metrics.end_time = datetime.now()
            self.metrics.success = success
            self.metrics.files_extracted = files_count

            duration = self.metrics.duration
            if duration:
                logger.info(
                    f"Extraction completed in {duration.total_seconds():.2f}s - "
                    f"Success: {success}, Files: {files_count}"
                )

    def add_error(self, error: str) -> None:
        """
        Add an error to the current extraction metrics.

        Args:
            error: Error message to add
        """
        if self.metrics:
            self.metrics.errors.append(error)
        logger.error(f"{self.platform_name} extraction error: {error}")

    def increment_api_calls(self) -> None:
        """Increment the API calls counter."""
        if self.metrics:
            self.metrics.api_calls_made += 1

    def increment_cache_hits(self) -> None:
        """Increment the cache hits counter."""
        if self.metrics:
            self.metrics.cache_hits += 1

    def get_metrics(self) -> Optional[ExtractionMetrics]:
        """
        Get current extraction metrics.

        Returns:
            Current ExtractionMetrics or None if no extraction in progress
        """
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset extraction metrics."""
        self.metrics = None
