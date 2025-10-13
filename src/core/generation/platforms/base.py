"""
Base classes for platform extractors.

This module defines the abstract base class that all platform-specific extractors
must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import ProjectData


class ProjectExtractor(ABC):
    """Abstract base class for platform-specific project extractors"""
    
    @abstractmethod
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a platform URL.
        
        Args:
            url: The project URL
            
        Returns:
            ProjectData containing extracted information
            
        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to connect to platform
        """
        pass
    
    def validate_url(self, url: str) -> bool:
        """
        Validate that the URL is appropriate for this extractor.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if valid for this platform
        """
        # Default implementation - can be overridden by subclasses
        return True
    
    def get_platform_name(self) -> str:
        """
        Get the name of the platform this extractor handles.
        
        Returns:
            Platform name string
        """
        return self.__class__.__name__.replace('Extractor', '').lower()
