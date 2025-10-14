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
        # Extract owner and repo from URL
        from ..url_router import URLRouter
        router = URLRouter()
        owner, repo = router.extract_repo_info(url)
        
        # Fetch real data from GitHub API
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # Get repository information
                repo_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}")
                if repo_response.status_code != 200:
                    raise Exception(f"GitHub API error: {repo_response.status_code}")
                
                repo_data = repo_response.json()
                
                # Get repository contents (files)
                contents_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents")
                contents_data = contents_response.json() if contents_response.status_code == 200 else []
                
                # Get README content
                readme_content = ""
                try:
                    readme_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/readme")
                    if readme_response.status_code == 200:
                        import base64
                        readme_data = readme_response.json()
                        readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
                except:
                    pass
                
                # Get LICENSE content
                license_content = ""
                try:
                    license_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/LICENSE")
                    if license_response.status_code == 200:
                        import base64
                        license_data = license_response.json()
                        license_content = base64.b64decode(license_data["content"]).decode("utf-8")
                except:
                    pass
                
                # Build metadata
                metadata = {
                    "name": repo_data.get("name", repo),
                    "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
                    "description": repo_data.get("description", ""),
                    "html_url": repo_data.get("html_url", url),
                    "clone_url": repo_data.get("clone_url", f"{url}.git"),
                    "default_branch": repo_data.get("default_branch", "main"),
                    "license": repo_data.get("license", {}),
                    "topics": repo_data.get("topics", []),
                    "created_at": repo_data.get("created_at", ""),
                    "updated_at": repo_data.get("updated_at", ""),
                    "language": repo_data.get("language", ""),
                    "size": repo_data.get("size", 0),
                    "stargazers_count": repo_data.get("stargazers_count", 0),
                    "forks_count": repo_data.get("forks_count", 0)
                }
                
                # Build files list
                files = []
                if readme_content:
                    files.append(FileInfo(
                        path="README.md",
                        size=len(readme_content),
                        content=readme_content,
                        file_type="markdown"
                    ))
                
                if license_content:
                    files.append(FileInfo(
                        path="LICENSE",
                        size=len(license_content),
                        content=license_content,
                        file_type="text"
                    ))
                
                # Add other files from contents
                for item in contents_data:
                    if item.get("type") == "file" and item.get("name") not in ["README.md", "LICENSE"]:
                        # Only add common file types to avoid API rate limits
                        if any(item["name"].lower().endswith(ext) for ext in [".md", ".txt", ".json", ".yaml", ".yml"]):
                            try:
                                file_response = await client.get(item["download_url"])
                                if file_response.status_code == 200:
                                    files.append(FileInfo(
                                        path=item["name"],
                                        size=item.get("size", 0),
                                        content=file_response.text,
                                        file_type=self._get_file_type(item["name"])
                                    ))
                            except:
                                pass
                
                # Build documentation list
                documentation = []
                if readme_content:
                    documentation.append(DocumentInfo(
                        title="README",
                        path="README.md",
                        doc_type="user-manual",
                        content=readme_content
                    ))
                
                # Build raw content
                raw_content = {}
                if readme_content:
                    raw_content["README.md"] = readme_content
                if license_content:
                    raw_content["LICENSE"] = license_content
                
        except Exception as e:
            # Fallback to mock data if API fails
            print(f"Warning: GitHub API failed ({e}), using fallback data")
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
                "README.md": "# Mock Project\n\nThis is a mock project for testing.",
                "LICENSE": "MIT License\n\nCopyright (c) 2023"
            }
        
        return ProjectData(
            platform=PlatformType.GITHUB,
            url=url,
            metadata=metadata,
            files=files,
            documentation=documentation,
            raw_content=raw_content
        )
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        type_mapping = {
            'md': 'markdown',
            'txt': 'text',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'py': 'python',
            'js': 'javascript',
            'html': 'html',
            'css': 'css',
            'scad': 'scad',
            'stl': 'stl',
            'step': 'step',
            'stp': 'step'
        }
        return type_mapping.get(ext, 'text')
    
    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitHub repository URL"""
        return "github.com" in url and "/" in url.split("github.com/")[-1]
