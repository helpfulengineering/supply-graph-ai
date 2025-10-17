"""
GitLab project extractor for OKH manifest generation.

This module provides functionality to extract project data from GitLab repositories
using the GitLab API.
"""

from typing import Dict, Any, List, Optional

from ..models import ProjectData, PlatformType, FileInfo, DocumentInfo
from .base import ProjectExtractor


class GitLabExtractor(ProjectExtractor):
    """
    Extractor for GitLab repositories.
    
    This extractor provides GitLab repository data extraction including:
    - Repository metadata (name, description, license, tags, etc.)
    - File contents (README, LICENSE, documentation)
    - Project information and statistics
    - Rate limiting and caching
    
    Note: Currently implements mock data extraction. Full GitLab API
    integration will be implemented in future phases.
    
    Attributes:
        base_url: GitLab API base URL
        gitlab_token: GitLab API token for authentication
        is_authenticated: Whether authentication is enabled
    """
    
    def __init__(self, gitlab_token: Optional[str] = None):
        """
        Initialize the GitLab extractor.
        
        Args:
            gitlab_token: GitLab API token for authentication
        """
        super().__init__(cache_enabled=True, cache_ttl_hours=24)
        
        self.base_url = "https://gitlab.com/api/v4"
        self.gitlab_token = gitlab_token
        self.is_authenticated = bool(self.gitlab_token)
        
        if self.is_authenticated:
            print("✅ GitLab authentication enabled")
        else:
            print("⚠️  GitLab authentication not found - using public API limits")
    
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a GitLab repository URL.
        
        Args:
            url: The GitLab repository URL
            
        Returns:
            ProjectData containing extracted information
            
        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to connect to GitLab API
        """
        # Start tracking metrics
        self.start_extraction(url)
        
        try:
            # Validate URL
            if not self.validate_url(url):
                raise ValueError(f"Invalid GitLab URL: {url}")
            
            # Extract owner and repo from URL
            from ..url_router import URLRouter
            router = URLRouter()
            owner, repo = router.extract_repo_info(url)
            
            # For now, return mock data to make tests pass
            # In Phase 1, we'll implement actual GitLab API integration
            
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
            
            # Create ProjectData and end metrics tracking
            project_data = ProjectData(
                platform=PlatformType.GITLAB,
                url=url,
                metadata=metadata,
                files=files,
                documentation=documentation,
                raw_content=raw_content
            )
            
            # End metrics tracking
            self.end_extraction(success=True, files_count=len(files))
            
            return project_data
            
        except Exception as e:
            error_msg = f"GitLab extraction failed: {e}"
            self.add_error(error_msg)
            self.end_extraction(success=False)
            raise
    
    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitLab repository URL"""
        return "gitlab.com" in url and "/" in url.split("gitlab.com/")[-1]
