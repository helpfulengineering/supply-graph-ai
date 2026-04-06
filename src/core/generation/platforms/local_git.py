"""
Local Git Repository Extractor for OKH manifest generation.

This module provides functionality to extract project data from locally cloned
Git repositories, offering a more reliable and faster alternative to API-based
extraction for GitHub and GitLab projects.

Benefits:
- No API rate limits
- Faster processing (local file access)
- Complete data access (all files, not just API-exposed)
- Offline capability after cloning
- Better file structure analysis
- Eliminates network timeouts and API failures
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class _RetryWithoutAuth(Exception):
    """Sentinel raised inside _fetch_github_supplementary_metadata to trigger an unauthenticated retry."""


from ..models import DocumentInfo, FileInfo, PlatformType, ProjectData
from .base import ProjectExtractor


class LocalGitExtractor(ProjectExtractor):
    """
    Extractor for locally cloned Git repositories.

    This extractor clones Git repositories locally and processes them using
    direct file system access, providing more reliable and comprehensive
    data extraction than API-based methods.

    Attributes:
        temp_dir: Temporary directory for cloned repositories
        max_file_size: Maximum file size to read content for
        supported_platforms: Platforms that support Git cloning
    """

    def __init__(
        self, temp_dir: Optional[str] = None, max_file_size: int = 1024 * 1024
    ):
        """
        Initialize the local Git extractor.

        Args:
            temp_dir: Directory for temporary cloned repositories
            max_file_size: Maximum file size to read content for (bytes)
        """
        super().__init__()
        self.temp_dir = (
            Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "ohm_clones"
        )
        self.max_file_size = max_file_size
        self.supported_platforms = {PlatformType.GITHUB, PlatformType.GITLAB}

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is suitable for Git cloning.

        Args:
            url: Repository URL to validate

        Returns:
            True if URL can be cloned with Git
        """
        # Check if it's a Git URL (https://, git://, or SSH format)
        git_patterns = [
            "https://github.com/",
            "https://gitlab.com/",
            "git@github.com:",
            "git@gitlab.com:",
            "git://",
        ]

        low = url.lower()
        if any(pattern in low for pattern in git_patterns):
            return True
        from ..gitlab_instance import is_gitlab_http_clone_url, normalize_http_url

        try:
            return is_gitlab_http_clone_url(normalize_http_url(url))
        except Exception:
            return False

    def _clone_repository(self, url: str) -> Optional[Path]:
        """
        Clone repository to temporary directory with timeout protection.

        Args:
            url: Repository URL to clone

        Returns:
            Path to cloned repository or None if cloning failed
        """
        try:
            # Create unique directory name based on URL and timestamp
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clone_dir = self.temp_dir / f"repo_{url_hash}_{timestamp}"

            logger.info(f"Cloning repository: {url}")
            logger.info(f"Target directory: {clone_dir}")

            # Clone repository with timeout
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--single-branch",
                    url,
                    str(clone_dir),
                ],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"Successfully cloned repository to {clone_dir}")
                return clone_dir
            else:
                logger.warning(f"Git clone failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning(f"Git clone timed out after 2 minutes for {url}")
            return None
        except Exception as e:
            logger.warning(f"Git clone error: {e}")
            return None

    def _cleanup_repository(self, repo_path: Path):
        """
        Clean up cloned repository directory.

        Args:
            repo_path: Path to repository to clean up
        """
        try:
            if repo_path.exists():
                shutil.rmtree(repo_path)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

    def _detect_platform(self, url: str) -> PlatformType:
        """
        Detect platform type from URL.

        Args:
            url: Repository URL

        Returns:
            PlatformType enum value
        """
        low = url.lower()
        if "github.com" in low:
            return PlatformType.GITHUB
        from ..gitlab_instance import is_gitlab_http_clone_url, normalize_http_url

        try:
            if is_gitlab_http_clone_url(normalize_http_url(url)):
                return PlatformType.GITLAB
        except Exception:
            pass
        return PlatformType.UNKNOWN

    def _extract_repo_info(self, url: str) -> tuple[str, str]:
        """
        Extract owner and repository name from URL.

        Args:
            url: Repository URL

        Returns:
            Tuple of (owner, repo)
        """
        # Handle different URL formats
        if url.endswith(".git"):
            url = url[:-4]

        # Extract owner/repo from URL
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1]
            return owner, repo

        raise ValueError(f"Cannot extract repo info from URL: {url}")

    def _read_file_content(self, file_path: Path) -> str:
        """
        Read file content with size limit.

        Args:
            file_path: Path to file

        Returns:
            File content as string
        """
        try:
            if file_path.stat().st_size > self.max_file_size:
                return f"[File too large: {file_path.stat().st_size} bytes]"

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            return f"[Error reading file: {e}]"

    def _extract_readme_title(self, readme_content: str) -> Optional[str]:
        """
        Extract the first H1 heading from README content for use as the project title.

        Args:
            readme_content: Raw README file content

        Returns:
            Title string if an H1 heading is found, otherwise None
        """
        if not readme_content:
            return None
        match = re.search(r"^#\s+(.+)", readme_content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Reject titles that are just badges, links, or image markup
            if title and not title.startswith("[") and not title.startswith("!"):
                return title
        return None

    def _load_github_token_from_env(self) -> Optional[str]:
        """Load GitHub API token from .env file and common environment variable names."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        for token_name in ("GITHUB_TOKEN", "GITHUB_PAT", "GITHUB_ACCESS_TOKEN"):
            token = os.getenv(token_name)
            if token:
                return token
        return None

    async def _fetch_github_supplementary_metadata(
        self, owner: str, repo: str
    ) -> Dict[str, Any]:
        """
        Fetch lightweight metadata from the GitHub API to supplement local clone extraction.

        Retrieves repository topics (used for keywords) and the latest release tag
        (used for version).  This is a single additional API round-trip that fills in
        fields that are not stored inside a git clone.

        Fails gracefully — returns an empty dict on any network or auth error so the
        rest of the extraction is never blocked.

        Args:
            owner: Repository owner/organisation name
            repo: Repository name

        Returns:
            Dict with any of: ``topics`` (list[str]), ``tag_name`` (str)
        """
        result: Dict[str, Any] = {}
        token = self._load_github_token_from_env()

        async def _do_fetch(auth_token: Optional[str]) -> Dict[str, Any]:
            headers = {"Accept": "application/vnd.github+json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            partial: Dict[str, Any] = {}
            import httpx

            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                repo_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}"
                )
                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    topics = repo_data.get("topics", [])
                    if topics:
                        partial["topics"] = topics
                elif repo_response.status_code == 401 and auth_token:
                    # Invalid token — retry without auth to get unauthenticated response
                    raise _RetryWithoutAuth()
                elif repo_response.status_code == 403:
                    logger.warning(
                        "GitHub supplementary fetch: rate-limited "
                        f"(HTTP 403) — skipping"
                    )
                    return partial

                release_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                )
                if release_response.status_code == 200:
                    release_data = release_response.json()
                    tag = release_data.get("tag_name")
                    if tag:
                        partial["tag_name"] = tag
            return partial

        try:
            result = await _do_fetch(token)
        except _RetryWithoutAuth:
            logger.warning(
                "GitHub token rejected (HTTP 401) — retrying without authentication"
            )
            try:
                result = await _do_fetch(None)
            except Exception as e:
                logger.warning(
                    f"GitHub supplementary metadata fetch failed (non-fatal): {e}"
                )
        except Exception as e:
            logger.warning(
                f"GitHub supplementary metadata fetch failed (non-fatal): {e}"
            )

        return result

    def _load_gitlab_token_from_env(self) -> Optional[str]:
        """Load GitLab API token from .env file and common environment variable names."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        for token_name in ("GITLAB_TOKEN", "GITLAB_PAT", "GITLAB_ACCESS_TOKEN"):
            token = os.getenv(token_name)
            if token:
                return token
        return None

    async def _fetch_gitlab_supplementary_metadata(
        self,
        owner: str,
        repo: str,
        *,
        api_base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch lightweight metadata from the GitLab API to supplement local clone extraction.

        Retrieves repository topics (``tag_list``, used for keywords) and the latest
        release tag (used for version).  Fails gracefully — returns an empty dict on
        any network or auth error.

        Args:
            owner: Repository namespace/group name
            repo: Repository name

        Returns:
            Dict with any of: ``topics`` (list[str]), ``tag_name`` (str)
        """
        result: Dict[str, Any] = {}
        token = self._load_gitlab_token_from_env()
        # Align with GitLabExtractor (Bearer) and common PAT style (PRIVATE-TOKEN).
        auth_headers: Dict[str, str] = {}
        if token:
            auth_headers["PRIVATE-TOKEN"] = token
            auth_headers["Authorization"] = f"Bearer {token}"

        # GitLab requires URL-encoded project path (owner%2Frepo)
        from urllib.parse import quote

        encoded_path = quote(f"{owner}/{repo}", safe="")
        base = (api_base_url or "https://gitlab.com/api/v4").rstrip("/")
        proj_url = f"{base}/projects/{encoded_path}"
        rel_url = f"{base}/projects/{encoded_path}/releases"

        # Try authenticated first, then unauthenticated (public projects on self-hosted
        # often reject a gitlab.com token with 401; unauthenticated API may still work).
        header_attempts = (auth_headers, {}) if token else ({},)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                proj_data = None
                for hdr in header_attempts:
                    proj_response = await client.get(proj_url, headers=hdr)
                    if proj_response.status_code == 200:
                        proj_data = proj_response.json()
                        break
                    if proj_response.status_code in (401, 403) and hdr and token:
                        logger.debug(
                            "GitLab supplementary: project fetch rejected auth; "
                            "retrying without token (public project?)"
                        )
                        continue
                    if proj_response.status_code in (401, 403):
                        logger.warning(
                            f"GitLab supplementary fetch: HTTP {proj_response.status_code} "
                            f"for project metadata — skipping"
                        )
                        return result

                if proj_data:
                    topics = proj_data.get("tag_list", []) or proj_data.get(
                        "topics", []
                    )
                    if topics:
                        result["topics"] = topics

                for hdr in header_attempts:
                    rel_response = await client.get(
                        rel_url, params={"per_page": 1}, headers=hdr
                    )
                    if rel_response.status_code == 200:
                        releases = rel_response.json()
                        if releases and isinstance(releases, list):
                            tag = releases[0].get("tag_name")
                            if tag:
                                result["tag_name"] = tag
                        break
                    if rel_response.status_code in (401, 403) and hdr and token:
                        continue

        except Exception as e:
            logger.warning(
                f"GitLab supplementary metadata fetch failed (non-fatal): {e}"
            )

        return result

    def _find_files_by_pattern(self, repo_path: Path, pattern: str) -> List[Path]:
        """
        Find files matching pattern in repository with case-insensitive matching.

        Python's Path.rglob() is case-sensitive even on macOS HFS+, so repos
        that use mixed-case filenames (e.g. "License" vs "LICENSE") need special
        handling.  This method normalises both the pattern stem and each candidate
        filename to lowercase before comparing.

        Args:
            repo_path: Path to repository
            pattern: Glob pattern to match (e.g., "README*", "LICENSE*", "*bom*")

        Returns:
            List of matching file paths, deduplicated and sorted
        """
        import fnmatch

        pattern_lower = pattern.lower()
        seen: set = set()
        matches: List[Path] = []

        try:
            # First pass: standard rglob (fast, handles most cases)
            for file_path in repo_path.rglob(pattern):
                if file_path.is_file() and file_path not in seen:
                    seen.add(file_path)
                    matches.append(file_path)

            # Second pass: case-insensitive scan of root-level files only
            # (covers mixed-case names like "License", "Readme.md", etc.)
            for file_path in repo_path.iterdir():
                if (
                    file_path.is_file()
                    and file_path not in seen
                    and fnmatch.fnmatch(file_path.name.lower(), pattern_lower)
                ):
                    seen.add(file_path)
                    matches.append(file_path)

        except Exception as e:
            logger.warning(f"Error finding files: {e}")

        return matches

    def _extract_git_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """
        Extract Git metadata from repository.

        Args:
            repo_path: Path to repository

        Returns:
            Dictionary of Git metadata
        """
        metadata = {}

        try:
            # Get Git remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                metadata["remote_url"] = result.stdout.strip()

            # Get latest commit info
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%H|%an|%ae|%ad|%s"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                commit_info = result.stdout.strip().split("|")
                if len(commit_info) >= 5:
                    metadata["latest_commit"] = {
                        "hash": commit_info[0],
                        "author": commit_info[1],
                        "email": commit_info[2],
                        "date": commit_info[3],
                        "message": commit_info[4],
                    }

            # Get branch info
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                metadata["branch"] = result.stdout.strip()

        except Exception as e:
            logger.warning(f"Error extracting Git metadata: {e}")

        return metadata

    async def extract_project(
        self, url: str, persist_path: Optional[Path] = None
    ) -> ProjectData:
        """
        Extract project data from a Git repository URL by cloning locally.

        Args:
            url: The Git repository URL
            persist_path: If provided, move the cloned repository to this path after
                successful extraction instead of deleting it.  Useful for caching clones
                so subsequent runs (e.g. with --use-llm) can skip re-cloning.

        Returns:
            ProjectData containing extracted information

        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to clone repository
        """
        # Start tracking metrics
        self.start_extraction(url)

        repo_path = None
        extraction_succeeded = False
        try:
            # Validate URL
            if not self.validate_url(url):
                raise ValueError(f"URL not suitable for Git cloning: {url}")

            # Detect platform
            platform = self._detect_platform(url)
            if platform == PlatformType.UNKNOWN:
                raise ValueError(f"Unsupported platform for Git cloning: {url}")

            # Extract repo info
            owner, repo = self._extract_repo_info(url)

            # Clone repository
            repo_path = self._clone_repository(url)
            if not repo_path:
                raise ConnectionError(f"Failed to clone repository: {url}")

            # Extract Git metadata
            git_metadata = self._extract_git_metadata(repo_path)

            # Find and read README files
            readme_files = self._find_files_by_pattern(repo_path, "README*")
            readme_content = ""
            if readme_files:
                readme_content = self._read_file_content(readme_files[0])

            # Find and read LICENSE files
            license_files = self._find_files_by_pattern(repo_path, "LICENSE*")
            license_content = ""
            if license_files:
                license_content = self._read_file_content(license_files[0])

            # Find BOM files
            bom_files = self._find_files_by_pattern(repo_path, "*bom*")
            bom_content = ""
            if bom_files:
                bom_content = self._read_file_content(bom_files[0])

            # Collect all files
            files = []
            for file_path in repo_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    relative_path = file_path.relative_to(repo_path)
                    content = self._read_file_content(file_path)

                    # Use intelligent categorization based on directory structure
                    file_type, doc_type = self._categorize_file_by_structure(file_path)

                    files.append(
                        FileInfo(
                            path=str(relative_path),
                            content=content,
                            size=file_path.stat().st_size,
                            file_type=file_type,
                        )
                    )

            # Create project metadata
            readme_title = self._extract_readme_title(readme_content)
            metadata = {
                "name": readme_title or repo,
                "owner": owner,
                "description": "",
                "url": url,
                "platform": platform.value,
                "readme_content": readme_content,
                "license_content": license_content,
                "bom_content": bom_content,
                "files_count": len(files),
                "extraction_method": "local_git_clone",
                **git_metadata,
            }

            # Supplement with platform API metadata (topics, latest release) when available
            if platform == PlatformType.GITHUB:
                supplementary = await self._fetch_github_supplementary_metadata(
                    owner, repo
                )
                if supplementary:
                    metadata.update(supplementary)
            elif platform == PlatformType.GITLAB:
                from ..gitlab_instance import gitlab_api_v4_base_url
                from ..url_router import URLRouter

                gl_base = gitlab_api_v4_base_url(URLRouter().normalize_url(url))
                supplementary = await self._fetch_gitlab_supplementary_metadata(
                    owner, repo, api_base_url=gl_base
                )
                if supplementary:
                    metadata.update(supplementary)

            # Create ProjectData
            project_data = ProjectData(
                platform=platform,
                url=url,
                metadata=metadata,
                files=files,
                documentation=self._build_documentation_list(files),
                raw_content={"clone_path": str(repo_path)},
            )

            # End tracking metrics
            self.end_extraction(True, len(files))
            extraction_succeeded = True
            return project_data

        except Exception as e:
            self.add_error(str(e))
            raise
        finally:
            if repo_path:
                if persist_path and extraction_succeeded:
                    try:
                        persist_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(repo_path), str(persist_path))
                        logger.info(f"Saved clone to {persist_path}")
                    except Exception as e:
                        logger.warning(
                            f"Could not persist clone to {persist_path}: {e}"
                        )
                        self._cleanup_repository(repo_path)
                else:
                    self._cleanup_repository(repo_path)

    def _categorize_file_by_structure(self, file_path: Path) -> tuple[str, str]:
        """
        Categorize file based on directory structure and filename patterns.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (file_type, documentation_type)
        """
        path_str = str(file_path).lower()
        filename = file_path.name.lower()
        parent_dirs = [p.name.lower() for p in file_path.parents]

        # Directory-based categorization (strongest clues)
        if any(
            dir_name in path_str
            for dir_name in ["schematics", "circuit", "electrical", "pcb"]
        ):
            return "schematics", "schematics"
        elif any(
            dir_name in path_str
            for dir_name in ["docs", "documentation", "manual", "guide"]
        ):
            return "documentation", "operating-instructions"
        elif any(
            dir_name in path_str
            for dir_name in ["manufacturing", "production", "assembly", "build"]
        ):
            return "manufacturing", "manufacturing-files"
        elif any(dir_name in path_str for dir_name in ["design", "cad", "model", "3d"]):
            return "design", "design-files"
        elif any(
            dir_name in path_str for dir_name in ["software", "code", "src", "firmware"]
        ):
            return "code", "software"
        elif any(
            dir_name in path_str for dir_name in ["maintenance", "repair", "service"]
        ):
            return "maintenance", "maintenance-instructions"
        elif any(
            dir_name in path_str
            for dir_name in ["quality", "testing", "test", "validation"]
        ):
            return "quality", "technical-specifications"
        elif any(dir_name in path_str for dir_name in ["safety", "risk", "hazard"]):
            return "safety", "risk-assessment"
        elif any(
            dir_name in path_str for dir_name in ["tools", "tool", "settings", "config"]
        ):
            return "config", "making-instructions"
        elif any(dir_name in path_str for dir_name in ["disposal", "recycle", "waste"]):
            return "disposal", "disposal-instructions"

        # Filename-based categorization (secondary clues)
        if any(
            pattern in filename
            for pattern in ["readme", "manual", "guide", "instructions"]
        ):
            return "documentation", "operating-instructions"
        elif any(
            pattern in filename for pattern in ["schematic", "circuit", "pcb", "wiring"]
        ):
            return "schematics", "schematics"
        elif any(
            pattern in filename
            for pattern in ["bom", "bill_of_materials", "parts_list"]
        ):
            return "data", "manufacturing-files"
        elif any(
            pattern in filename for pattern in ["assembly", "build", "manufacturing"]
        ):
            return "manufacturing", "manufacturing-files"
        elif any(pattern in filename for pattern in ["design", "model", "cad"]):
            return "design", "design-files"
        elif any(
            pattern in filename for pattern in ["maintenance", "repair", "service"]
        ):
            return "maintenance", "maintenance-instructions"
        elif any(pattern in filename for pattern in ["quality", "test", "validation"]):
            return "quality", "technical-specifications"
        elif any(pattern in filename for pattern in ["safety", "risk", "hazard"]):
            return "safety", "risk-assessment"
        elif any(pattern in filename for pattern in ["tool", "settings", "config"]):
            return "config", "making-instructions"
        elif any(pattern in filename for pattern in ["disposal", "recycle"]):
            return "disposal", "disposal-instructions"

        # Extension-based categorization (fallback)
        if file_path.suffix.lower() in [".md", ".rst", ".txt", ".pdf"]:
            return "documentation", "operating-instructions"
        elif file_path.suffix.lower() in [
            ".py",
            ".js",
            ".ts",
            ".cpp",
            ".c",
            ".h",
            ".java",
        ]:
            return "code", "software"
        elif file_path.suffix.lower() in [
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".ini",
            ".cfg",
        ]:
            return "config", "making-instructions"
        elif file_path.suffix.lower() in [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".bmp",
        ]:
            return "image", "design-files"
        elif file_path.suffix.lower() in [".csv", ".xlsx", ".xls", ".tsv"]:
            return "data", "manufacturing-files"
        elif file_path.suffix.lower() in [
            ".stl",
            ".obj",
            ".3mf",
            ".step",
            ".stp",
            ".scad",
        ]:
            return "design", "design-files"
        elif file_path.suffix.lower() in [".kicad_pcb", ".kicad_mod", ".sch", ".brd"]:
            return "schematics", "schematics"

        # Default fallback
        return "unknown", "design-files"

    def _build_documentation_list(self, files: List[FileInfo]) -> List[DocumentInfo]:
        """
        Build documentation list from files.

        Parses documentation files and creates DocumentInfo objects.
        Identifies documentation types based on filename, path, and content.

        Args:
            files: List of FileInfo objects from repository

        Returns:
            List of DocumentInfo objects
        """
        documentation = []
        # Order matters: more specific patterns first
        documentation_patterns = [
            # README files (most specific first)
            (r"(?i)^readme(\.(md|txt|rst))?$", "documentation-home"),
            (r"(?i)readme", "documentation-home"),
            # Operating instructions (more specific than manual)
            (
                r"(?i)(user[_\s]?manual|operating[_\s]?guide|usage)",
                "operating-instructions",
            ),
            (r"(?i)^(how[_\s]?to[_\s]?use|usage)", "operating-instructions"),
            # Technical specifications
            (
                r"(?i)(spec|specs|specification|technical[_\s]?spec)",
                "technical-specifications",
            ),
            (r"(?i)^(dimensions?|tolerances?)", "technical-specifications"),
            # Maintenance
            (r"(?i)(maintenance|repair|servicing)", "maintenance-instructions"),
            # Disposal
            (
                r"(?i)(disposal|recycling|end[_\s]?of[_\s]?life)",
                "disposal-instructions",
            ),
            # Risk assessment
            (r"(?i)(risk[_\s]?assessment|safety|hazard)", "risk-assessment"),
            # Manual files (less specific, checked last)
            (r"(?i)(manual|guide|instructions?)", "making-instructions"),
            (r"(?i)^(assembly|build|making|fabrication)", "making-instructions"),
        ]

        # Documentation directories
        documentation_dirs = {
            "docs/": "documentation-home",
            "documentation/": "documentation-home",
            "manual/": "making-instructions",
            "manuals/": "making-instructions",
            "guides/": "making-instructions",
            "instructions/": "making-instructions",
        }

        for file_info in files:
            # Skip non-documentation file types (but allow markdown, document, text, and documentation)
            # Also check file extension as fallback
            file_path = Path(file_info.path)
            is_doc_file = file_info.file_type in [
                "markdown",
                "document",
                "text",
                "documentation",
            ] or file_path.suffix.lower() in [
                ".md",
                ".txt",
                ".rst",
                ".pdf",
                ".docx",
                ".doc",
            ]
            if not is_doc_file:
                continue

            file_path = Path(file_info.path)
            file_name = file_path.name.lower()
            file_dir = str(file_path.parent).lower() + "/"

            # Determine documentation type
            doc_type = None
            title = file_path.stem.replace("_", " ").replace("-", " ").title()

            # Check directory patterns first
            for dir_pattern, type_name in documentation_dirs.items():
                if dir_pattern in file_dir:
                    doc_type = type_name
                    break

            # Check filename patterns (order matters - more specific first)
            if not doc_type:
                for pattern, type_name in documentation_patterns:
                    # Use search instead of match to allow patterns anywhere in filename
                    if re.search(pattern, file_name):
                        doc_type = type_name
                        break

            # Default to making-instructions if in docs directory
            if not doc_type and ("docs/" in file_dir or "documentation/" in file_dir):
                doc_type = "making-instructions"

            # Skip if not identified as documentation
            if not doc_type:
                continue

            # Extract title from content if available
            if file_info.content:
                # Try to extract title from first heading
                title_match = re.search(r"^#+\s+(.+)$", file_info.content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
                # Or from first line if no heading and it looks like a title
                elif file_info.content.strip():
                    first_line = file_info.content.strip().split("\n")[0]
                    # Remove markdown formatting
                    first_line = re.sub(r"^#+\s*", "", first_line)
                    first_line = re.sub(r"\*\*([^*]+)\*\*", r"\1", first_line)
                    # Only use first line as title if it's very short and looks like a title
                    # (starts with capital, single phrase, etc.)
                    first_line_clean = first_line.strip()
                    # Check if it looks like a title: short, starts with capital, no lowercase words in middle
                    looks_like_title = (
                        len(first_line_clean) <= 20  # Very short
                        and first_line_clean
                        and first_line_clean[0].isupper()  # Starts with capital
                    )
                    if looks_like_title:
                        title = first_line_clean
                    # Otherwise keep filename-derived title (already set above)

            # Limit content size for very large files
            content = file_info.content or ""
            max_content_size = 50000  # 50KB limit
            if len(content) > max_content_size:
                content = content[:max_content_size] + "\n\n... (truncated)"

            documentation.append(
                DocumentInfo(
                    title=title, path=file_info.path, doc_type=doc_type, content=content
                )
            )

        return documentation

    async def extract_from_local_path(self, local_path: Path) -> ProjectData:
        """
        Extract project data from an already-cloned local repository directory.

        Unlike extract_project, this method skips cloning entirely and processes
        the provided directory directly.  It never deletes or moves the directory.
        The source URL and platform are inferred from the git remote if available.

        Args:
            local_path: Path to the root of a locally cloned Git repository.

        Returns:
            ProjectData containing extracted information

        Raises:
            ValueError: If the path does not exist or is not a directory
        """
        self.start_extraction(str(local_path))
        try:
            if not local_path.exists() or not local_path.is_dir():
                raise ValueError(
                    f"Local path does not exist or is not a directory: {local_path}"
                )

            git_metadata = self._extract_git_metadata(local_path)
            remote_url = git_metadata.get("remote_url", "")

            if remote_url:
                platform = self._detect_platform(remote_url)
                try:
                    owner, repo = self._extract_repo_info(remote_url)
                except ValueError:
                    owner = "unknown"
                    repo = local_path.name
                source_url = remote_url
            else:
                platform = PlatformType.UNKNOWN
                owner = "unknown"
                repo = local_path.name
                source_url = str(local_path)

            readme_files = self._find_files_by_pattern(local_path, "README*")
            readme_content = (
                self._read_file_content(readme_files[0]) if readme_files else ""
            )

            license_files = self._find_files_by_pattern(local_path, "LICENSE*")
            license_content = (
                self._read_file_content(license_files[0]) if license_files else ""
            )

            bom_files = self._find_files_by_pattern(local_path, "*bom*")
            bom_content = self._read_file_content(bom_files[0]) if bom_files else ""

            files = []
            for file_path in local_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    relative_path = file_path.relative_to(local_path)
                    content = self._read_file_content(file_path)
                    file_type, _ = self._categorize_file_by_structure(file_path)
                    files.append(
                        FileInfo(
                            path=str(relative_path),
                            content=content,
                            size=file_path.stat().st_size,
                            file_type=file_type,
                        )
                    )

            readme_title = self._extract_readme_title(readme_content)
            metadata = {
                "name": readme_title or repo,
                "owner": owner,
                "description": "",
                "url": source_url,
                "platform": platform.value,
                "readme_content": readme_content,
                "license_content": license_content,
                "bom_content": bom_content,
                "files_count": len(files),
                "extraction_method": "local_path",
                **git_metadata,
            }

            # Supplement with platform API metadata (topics, latest release) when available
            if platform == PlatformType.GITHUB:
                supplementary = await self._fetch_github_supplementary_metadata(
                    owner, repo
                )
                if supplementary:
                    metadata.update(supplementary)
            elif platform == PlatformType.GITLAB:
                gl_base = None
                if source_url.startswith(("http://", "https://")):
                    from ..gitlab_instance import gitlab_api_v4_base_url
                    from ..url_router import URLRouter

                    gl_base = gitlab_api_v4_base_url(
                        URLRouter().normalize_url(source_url)
                    )
                supplementary = await self._fetch_gitlab_supplementary_metadata(
                    owner, repo, api_base_url=gl_base
                )
                if supplementary:
                    metadata.update(supplementary)

            project_data = ProjectData(
                platform=platform,
                url=source_url,
                metadata=metadata,
                files=files,
                documentation=self._build_documentation_list(files),
                raw_content={"local_path": str(local_path)},
            )

            self.end_extraction(True, len(files))
            return project_data

        except Exception as e:
            self.add_error(str(e))
            raise

    def cleanup_all(self):
        """Clean up all temporary cloned repositories."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Error cleaning up temp directory: {e}")


# Import hashlib for the hash function
import hashlib
