"""
GitHub project extractor for OKH manifest generation.

This module provides functionality to extract project data from GitHub repositories
using the GitHub API with caching to avoid rate limits.
"""

import json
import hashlib
import os
import base64
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..models import ProjectData, PlatformType, FileInfo, DocumentInfo
from .base import ProjectExtractor


class GitHubExtractor(ProjectExtractor):
    """
    Extractor for GitHub repositories with caching and authentication support.
    
    This extractor provides GitHub repository data extraction including:
    - Repository metadata (name, description, license, topics, etc.)
    - File contents (README, LICENSE, BOM files, source code)
    - Documentation parsing
    - Release information
    - Rate limiting and caching
    
    Attributes:
        base_url: GitHub API base URL
        max_scan_depth: Maximum directory depth to scan
        max_file_size: Maximum file size to fetch content for
        github_token: GitHub API token for authentication
        is_authenticated: Whether authentication is enabled
        cache_dir: Directory for caching API responses
    """
    
    # Class-level flag to track if authentication message has been printed
    _auth_message_printed = False
    
    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_hours: int = 24, github_token: Optional[str] = None):
        """
        Initialize the GitHub extractor.
        
        Args:
            cache_dir: Directory for caching API responses
            cache_ttl_hours: Cache time-to-live in hours
            github_token: GitHub API token for authentication
        """
        super().__init__(cache_enabled=True, cache_ttl_hours=cache_ttl_hours)
        
        self.base_url = "https://api.github.com"
        self.max_scan_depth = 6  # Maximum directory depth to scan
        self.max_file_size = 8 * 1024 * 1024  # 8MB file size limit
        
        # Authentication
        self.github_token = github_token or self._load_github_token_from_env()
        self.is_authenticated = bool(self.github_token)
        
        # Update rate limit expectations based on authentication
        if self.is_authenticated:
            self.rate_limit_remaining = 5000  # Authenticated rate limit
            if not GitHubExtractor._auth_message_printed:
                print("✅ GitHub authentication enabled - using 5,000 requests/hour rate limit")
                GitHubExtractor._auth_message_printed = True
        else:
            if not GitHubExtractor._auth_message_printed:
                print("⚠️  GitHub authentication not found - using 60 requests/hour rate limit")
                print("   To increase rate limits, set GITHUB_TOKEN environment variable or use --github-token flag")
                GitHubExtractor._auth_message_printed = True
        
        # Caching configuration
        # Use provided cache_dir, or environment variable, or fall back to /tmp in containers
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            cache_dir_env = os.getenv("CACHE_DIR")
            if cache_dir_env:
                self.cache_dir = Path(cache_dir_env) / "supply-graph-ai" / "github"
            else:
                # Try home directory first, fall back to /tmp if home doesn't exist (e.g., in containers)
                try:
                    home_dir = Path.home()
                    if home_dir.exists():
                        self.cache_dir = home_dir / ".cache" / "supply-graph-ai" / "github"
                    else:
                        self.cache_dir = Path("/tmp") / ".cache" / "supply-graph-ai" / "github"
                except (RuntimeError, OSError):
                    # If Path.home() fails (e.g., no home directory), use /tmp
                    self.cache_dir = Path("/tmp") / ".cache" / "supply-graph-ai" / "github"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_github_token_from_env(self) -> Optional[str]:
        """Load GitHub token from environment variables"""
        
        # Load .env file if it exists
        try:
            load_dotenv()
        except ImportError:
            pass  # python-dotenv not available, continue without it
        
        # Try multiple environment variable names
        token_names = ['GITHUB_TOKEN', 'GITHUB_PAT', 'GITHUB_ACCESS_TOKEN']
        
        for token_name in token_names:
            token = os.getenv(token_name)
            if token:
                return token
        
        return None
    
    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a GitHub repository URL.
        
        Args:
            url: The GitHub repository URL
            
        Returns:
            ProjectData containing extracted information
            
        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to connect to GitHub API
        """
        # Start tracking metrics
        self.start_extraction(url)
        
        try:
            # Validate URL
            if not self.validate_url(url):
                raise ValueError(f"Invalid GitHub URL: {url}")
            
            # Extract owner and repo from URL
            from ..url_router import URLRouter
            router = URLRouter()
            owner, repo = router.extract_repo_info(url)
            
            # Fetch real data from GitHub API with caching
            import httpx
            
            # Set up authentication headers
            headers = {}
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
                headers['Accept'] = 'application/vnd.github.v3+json'
            
            async with httpx.AsyncClient(headers=headers) as client:
                # Get repository information (cached)
                repo_url = f"{self.base_url}/repos/{owner}/{repo}"
                repo_cache_key = f"repo_{owner}_{repo}"
                repo_data = await self._cached_api_request(client, repo_url, repo_cache_key)
                
                if repo_data is None:
                    raise Exception("GitHub API error: Unable to fetch repository data")
                
                # Get repository contents (files) (cached)
                contents_url = f"{self.base_url}/repos/{owner}/{repo}/contents"
                contents_cache_key = f"contents_{owner}_{repo}"
                contents_data = await self._cached_api_request(client, contents_url, contents_cache_key) or []
                
                # Get releases information (cached)
                releases_url = f"{self.base_url}/repos/{owner}/{repo}/releases"
                releases_cache_key = f"releases_{owner}_{repo}"
                releases_data = await self._cached_api_request(client, releases_url, releases_cache_key) or []
                
                # Get README content (cached)
                readme_content = ""
                readme_url = f"{self.base_url}/repos/{owner}/{repo}/readme"
                readme_cache_key = f"readme_{owner}_{repo}"
                readme_data = await self._cached_api_request(client, readme_url, readme_cache_key)
                
                if readme_data:
                    try:
                        readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
                    except:
                        pass
                
                # Get LICENSE content (try multiple variations) (cached)
                license_content = ""
                license_path = None
                license_paths = ["LICENSE", "License", "LICENSE.txt", "LICENSE.md"]
                
                for path in license_paths:
                    license_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
                    license_cache_key = f"license_{owner}_{repo}_{path}"
                    license_data = await self._cached_api_request(client, license_url, license_cache_key)
                    
                    if license_data:
                        try:
                            import base64
                            license_content = base64.b64decode(license_data["content"]).decode("utf-8")
                            license_path = path  # Store the actual path found
                            break  # Use the first license file found
                        except:
                            continue

                # Get BOM content (try common BOM file locations) (cached)
                bom_content = ""
                bom_paths = [
                    "docs/0_bill_of_materials.md",
                    "docs/bom.md", 
                    "bom.md",
                    "bill_of_materials.md"
                ]
                
                for bom_path in bom_paths:
                    bom_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{bom_path}"
                    bom_cache_key = f"bom_{owner}_{repo}_{bom_path.replace('/', '_')}"
                    bom_data = await self._cached_api_request(client, bom_url, bom_cache_key)
                    
                    if bom_data:
                        try:
                            import base64
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
                
                # Also scan the docs directory specifically for file discovery
                try:
                    docs_response = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contents/docs?ref=master")
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
                        doc_type="operating-instructions",
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
            error_msg = f"GitHub API failed ({e}), using fallback data"
            print(f"Warning: {error_msg}")
            self.add_error(error_msg)
            
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
        
        # Create ProjectData and end metrics tracking
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url=url,
            metadata=metadata,
            files=files,
            documentation=documentation,
            raw_content=raw_content
        )
        
        # End metrics tracking
        self.end_extraction(success=True, files_count=len(files))
        
        return project_data
    
    
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
                
                # Skip LICENSE files we already have (README.md should be processed here)
                if file_path in ["LICENSE", "License"]:
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
        text_extensions = [".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".html", ".css", ".scad"]
        image_extensions = [".svg", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".ico"]
        
        file_path_lower = file_path.lower()
        
        # Exclude image files (including SVG)
        if any(file_path_lower.endswith(ext) for ext in image_extensions):
            return False
        
        return any(file_path_lower.endswith(ext) for ext in text_extensions)
    
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
        elif file_path_lower.endswith(('.sch', '.brd', '.kicad_pcb', '.kicad_mod')):
            return "schematic"
        else:
            return "other"

    def validate_url(self, url: str) -> bool:
        """Validate that the URL is a GitHub repository URL"""
        return "github.com" in url and "/" in url.split("github.com/")[-1]
    
    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key for a URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if a cache file is still valid"""
        if not cache_path.exists():
            return False
        
        # Check if cache is within TTL
        cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - cache_time < self.cache_ttl
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load data from cache if valid"""
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If cache is corrupted, remove it
            cache_path.unlink(missing_ok=True)
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Save data to cache"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError:
            # If we can't write to cache, continue without caching
            pass
    
    async def _cached_api_request(self, client, url: str, cache_key: str) -> Optional[Dict[str, Any]]:
        """Make an API request with caching"""
        # Try to load from cache first
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Make API request
        try:
            response = await client.get(url)
            
            # Update rate limit info from response headers
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in response.headers:
                self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
            
            if response.status_code == 200:
                data = response.json()
                # Save to cache
                self._save_to_cache(cache_key, data)
                return data
            elif response.status_code == 403:
                # Rate limited - try to get rate limit info
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
                rate_limit_reset = response.headers.get('X-RateLimit-Reset', '0')
                print(f"GitHub API rate limited. Remaining: {rate_limit_remaining}, Reset: {rate_limit_reset}")
                if not self.is_authenticated:
                    print("💡 Tip: Set GITHUB_TOKEN environment variable to increase rate limit from 60 to 5,000 requests/hour")
                return None
            elif response.status_code == 401:
                print("GitHub API authentication failed - check your token")
                return None
            elif response.status_code == 404:
                # 404 is expected for non-existent directories/files - don't print as error
                return None
            else:
                print(f"GitHub API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"GitHub API request failed: {e}")
            return None
