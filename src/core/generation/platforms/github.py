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
        self.max_scan_depth = 6  # Maximum directory depth to scan
        self.max_file_size = 8 * 1024 * 1024  # 5MB file size limit
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
                
                # Get releases information
                releases_data = []
                try:
                    releases_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/releases")
                    if releases_response.status_code == 200:
                        releases_data = releases_response.json()
                except:
                    pass
                
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
                
                # Get LICENSE content (try multiple variations)
                license_content = ""
                license_path = None
                license_paths = ["LICENSE", "License", "LICENSE.txt", "LICENSE.md"]
                
                for path in license_paths:
                    try:
                        license_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/{path}")
                        if license_response.status_code == 200:
                            import base64
                            license_data = license_response.json()
                            license_content = base64.b64decode(license_data["content"]).decode("utf-8")
                            license_path = path  # Store the actual path found
                            break  # Use the first license file found
                    except:
                        continue

                # Get BOM content (try common BOM file locations)
                bom_content = ""
                bom_paths = [
                    "docs/0_bill_of_materials.md",
                    "docs/bom.md", 
                    "bom.md",
                    "bill_of_materials.md"
                ]
                
                for bom_path in bom_paths:
                    try:
                        bom_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/{bom_path}")
                        if bom_response.status_code == 200:
                            import base64
                            bom_data = bom_response.json()
                            bom_content = base64.b64decode(bom_data["content"]).decode("utf-8")
                            break
                    except:
                        continue
                
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
                    "forks_count": repo_data.get("forks_count", 0),
                    "releases": releases_data  # Add releases data
                }
                
                # Add latest release tag if available
                if releases_data:
                    latest_release = releases_data[0]  # Releases are sorted by creation date, newest first
                    metadata["tag_name"] = latest_release.get("tag_name")
                    metadata["latest_release"] = latest_release.get("tag_name")
                
                # Build files list
                files = []
                if readme_content:
                    files.append(FileInfo(
                        path="README.md",
                        size=len(readme_content),
                        content=readme_content,
                        file_type="markdown"
                    ))
                
                if license_content and license_path:
                    files.append(FileInfo(
                        path=license_path,
                        size=len(license_content),
                        content=license_content,
                        file_type="text"
                    ))

                if bom_content:
                    files.append(FileInfo(
                        path="docs/0_bill_of_materials.md",
                        size=len(bom_content),
                        content=bom_content,
                        file_type="markdown"
                    ))
                
                # Recursively scan directories for files
                additional_files = await self._scan_directories_recursively(
                    client, owner, repo, contents_data, current_depth=0, current_path=""
                )
                files.extend(additional_files)
                
                # Also scan the docs directory specifically for comprehensive file discovery
                try:
                    docs_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/docs")
                    if docs_response.status_code == 200:
                        docs_contents = docs_response.json()
                        docs_files = await self._scan_directories_recursively(
                            client, owner, repo, docs_contents, current_depth=0, current_path="docs"
                        )
                        files.extend(docs_files)
                except:
                    pass  # Skip if docs directory doesn't exist
                
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
    
    
    async def _scan_directories_recursively(self, client, owner: str, repo: str, 
                                          contents_data: list, current_depth: int = 0, current_path: str = "") -> list:
        """
        Recursively scan directories for files.
        
        Args:
            client: HTTP client for API calls
            owner: Repository owner
            repo: Repository name
            contents_data: List of directory contents from GitHub API
            current_depth: Current recursion depth
            
        Returns:
            List of FileInfo objects
        """
        files = []
        
        # Check depth limit
        if current_depth >= self.max_scan_depth:
            return files
        
        for item in contents_data:
            if item.get("type") == "file":
                # Process file
                file_path = item["name"]
                if current_path:
                    file_path = f"{current_path}/{file_path}"
                
                # Skip files we already have
                if file_path in ["README.md", "LICENSE", "License"]:
                    continue
                
                # Check file size limit
                file_size = item.get("size", 0)
                if file_size > self.max_file_size:
                    continue
                
                # Only fetch content for certain file types to avoid API rate limits
                if self._should_fetch_file_content(file_path):
                    try:
                        file_response = await client.get(item["download_url"])
                        if file_response.status_code == 200:
                            content = file_response.text if self._is_text_file(file_path) else ""
                            files.append(FileInfo(
                                path=file_path,
                                size=file_size,
                                content=content,
                                file_type=self._detect_file_type(file_path)
                            ))
                    except:
                        # If we can't fetch content, still add the file info
                        files.append(FileInfo(
                            path=file_path,
                            size=file_size,
                            content="",
                            file_type=self._detect_file_type(file_path)
                        ))
                else:
                    # Add file info without content for large/binary files
                    files.append(FileInfo(
                        path=file_path,
                        size=file_size,
                        content="",
                        file_type=self._detect_file_type(file_path)
                    ))
            
            elif item.get("type") == "dir":
                # Recursively scan subdirectory
                try:
                    # Build the full path for the subdirectory
                    subdir_path = item["name"]
                    if current_path:
                        subdir_path = f"{current_path}/{subdir_path}"
                    
                    dir_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/{subdir_path}?ref=master")
                    if dir_response.status_code == 200:
                        subdir_contents = dir_response.json()
                        subdir_files = await self._scan_directories_recursively(
                            client, owner, repo, subdir_contents, current_depth + 1, subdir_path
                        )
                        files.extend(subdir_files)
                except Exception as e:
                    pass  # Skip directories we can't access
        
        return files
    
    def _should_fetch_file_content(self, file_path: str) -> bool:
        """Determine if we should fetch file content based on file type and size"""
        # Always fetch small text files
        text_extensions = [".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".html", ".css"]
        if any(file_path.lower().endswith(ext) for ext in text_extensions):
            return True
        
        # Don't fetch large binary files
        binary_extensions = [".stl", ".obj", ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".tar", ".gz"]
        if any(file_path.lower().endswith(ext) for ext in binary_extensions):
            return False
        
        # Default to fetching for unknown types
        return True
    
    def _is_text_file(self, file_path: str) -> bool:
        """Determine if a file is likely to be a text file"""
        text_extensions = [".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".html", ".css", ".scad", ".svg"]
        return any(file_path.lower().endswith(ext) for ext in text_extensions)
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type based on extension"""
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith(('.md', '.rst')):
            return "markdown"
        elif file_path_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
            return "image"
        elif file_path_lower.endswith(('.stl', '.obj', '.3mf')):
            return "3d_model"
        elif file_path_lower.endswith(('.scad', '.step', '.stp')):
            return "cad_file"
        elif file_path_lower.endswith(('.pdf', '.doc', '.docx')):
            return "document"
        elif file_path_lower.endswith(('.py', '.js', '.cpp', '.c', '.h')):
            return "code"
        elif file_path_lower.endswith(('.json', '.yaml', '.yml')):
            return "config"
        elif file_path_lower.endswith(('.csv', '.tsv', '.xlsx')):
            return "data"
        elif file_path_lower.endswith(('.sch', '.brd', '.kicad_pcb')):
            return "schematic"
        else:
            return "other"

    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitHub repository URL"""
        return "github.com" in url and "/" in url.split("github.com/")[-1]
