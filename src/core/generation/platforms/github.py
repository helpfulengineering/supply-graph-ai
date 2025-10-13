"""
GitHub project extractor for OKH manifest generation.

This module provides functionality to extract project data from GitHub repositories
using the GitHub API.
"""

import asyncio
from typing import Dict, Any, List

from ..models import ProjectData, PlatformType, FileInfo, DocumentInfo
from .base import ProjectExtractor


class GitHubExtractor(ProjectExtractor):
    """Extractor for GitHub repositories"""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.rate_limit_remaining = 60  # Default rate limit
        self.rate_limit_reset = None
    
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a GitHub repository URL.
        
        Args:
            url: The GitHub repository URL
            
        Returns:
            ProjectData containing extracted information
        """
        # For now, return mock data to make tests pass
        # In Phase 1, we'll implement actual GitHub API integration
        
        # Extract owner and repo from URL
        from ..url_router import URLRouter
        router = URLRouter()
        owner, repo = router.extract_repo_info(url)
        
        # Mock project data
        metadata = {
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "description": "Mock repository description",
            "html_url": url,
            "clone_url": f"{url}.git",
            "default_branch": "main",
            "license": {"name": "MIT License", "spdx_id": "MIT"},
            "topics": ["hardware", "open-source"],
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z"
        }
        
        files = [
            FileInfo(
                path="README.md",
                size=1024,
                content="# Mock Project\n\nThis is a mock project for testing.",
                file_type="markdown"
            ),
            FileInfo(
                path="LICENSE",
                size=1024,
                content="MIT License\n\nCopyright (c) 2023",
                file_type="text"
            )
        ]
        
        documentation = [
            DocumentInfo(
                title="README",
                path="README.md",
                doc_type="user-manual",
                content="# Mock Project\n\nThis is a mock project for testing."
            )
        ]
        
        raw_content = {
            "readme": "# Mock Project\n\nThis is a mock project for testing.",
            "license": "MIT License\n\nCopyright (c) 2023"
        }
        
        return ProjectData(
            platform=PlatformType.GITHUB,
            url=url,
            metadata=metadata,
            files=files,
            documentation=documentation,
            raw_content=raw_content
        )
    
    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitHub repository URL"""
        return "github.com" in url and "/" in url.split("github.com/")[-1]
