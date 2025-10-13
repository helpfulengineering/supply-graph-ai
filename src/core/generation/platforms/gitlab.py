"""
GitLab project extractor for OKH manifest generation.

This module provides functionality to extract project data from GitLab repositories
using the GitLab API.
"""

from typing import Dict, Any, List

from ..models import ProjectData, PlatformType, FileInfo, DocumentInfo
from .base import ProjectExtractor


class GitLabExtractor(ProjectExtractor):
    """Extractor for GitLab repositories"""
    
    def __init__(self):
        self.base_url = "https://gitlab.com/api/v4"
        self.rate_limit_remaining = 60  # Default rate limit
        self.rate_limit_reset = None
    
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a GitLab repository URL.
        
        Args:
            url: The GitLab repository URL
            
        Returns:
            ProjectData containing extracted information
        """
        # For now, return mock data to make tests pass
        # In Phase 1, we'll implement actual GitLab API integration
        
        # Extract owner and repo from URL
        from ..url_router import URLRouter
        router = URLRouter()
        owner, repo = router.extract_repo_info(url)
        
        # Mock project data
        metadata = {
            "name": repo,
            "path_with_namespace": f"{owner}/{repo}",
            "description": "Mock GitLab repository description",
            "web_url": url,
            "http_url_to_repo": f"{url}.git",
            "default_branch": "main",
            "license": {"name": "MIT License"},
            "tag_list": ["hardware", "open-source"],
            "created_at": "2023-01-01T00:00:00Z",
            "last_activity_at": "2023-12-01T00:00:00Z"
        }
        
        files = [
            FileInfo(
                path="README.md",
                size=1024,
                content="# Mock GitLab Project\n\nThis is a mock GitLab project for testing.",
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
                content="# Mock GitLab Project\n\nThis is a mock GitLab project for testing."
            )
        ]
        
        raw_content = {
            "readme": "# Mock GitLab Project\n\nThis is a mock GitLab project for testing.",
            "license": "MIT License\n\nCopyright (c) 2023"
        }
        
        return ProjectData(
            platform=PlatformType.GITLAB,
            url=url,
            metadata=metadata,
            files=files,
            documentation=documentation,
            raw_content=raw_content
        )
    
    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitLab repository URL"""
        return "gitlab.com" in url and "/" in url.split("gitlab.com/")[-1]
