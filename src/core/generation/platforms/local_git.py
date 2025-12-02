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

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
            Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "ome_clones"
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

        return any(pattern in url.lower() for pattern in git_patterns)

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

            print(f"Cloning repository: {url}")
            print(f"Target directory: {clone_dir}")

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
                print(f"Successfully cloned repository to {clone_dir}")
                return clone_dir
            else:
                print(f"Git clone failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"Git clone timed out after 2 minutes for {url}")
            return None
        except Exception as e:
            print(f"Git clone error: {e}")
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
            print(f"Cleanup error: {e}")

    def _detect_platform(self, url: str) -> PlatformType:
        """
        Detect platform type from URL.

        Args:
            url: Repository URL

        Returns:
            PlatformType enum value
        """
        if "github.com" in url.lower():
            return PlatformType.GITHUB
        elif "gitlab.com" in url.lower():
            return PlatformType.GITLAB
        else:
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

    def _find_files_by_pattern(self, repo_path: Path, pattern: str) -> List[Path]:
        """
        Find files matching pattern in repository.

        Args:
            repo_path: Path to repository
            pattern: Pattern to match (e.g., "README*", "*.md")

        Returns:
            List of matching file paths
        """
        matches = []
        try:
            for file_path in repo_path.rglob(pattern):
                if file_path.is_file():
                    matches.append(file_path)
        except Exception as e:
            print(f"Error finding files: {e}")

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
            print(f"Error extracting Git metadata: {e}")

        return metadata

    async def extract_project(self, url: str) -> ProjectData:
        """
        Extract project data from a Git repository URL by cloning locally.

        Args:
            url: The Git repository URL

        Returns:
            ProjectData containing extracted information

        Raises:
            ValueError: If URL is invalid or extraction fails
            ConnectionError: If unable to clone repository
        """
        # Start tracking metrics
        self.start_extraction(url)

        repo_path = None
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
            metadata = {
                "name": repo,
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

            return project_data

        except Exception as e:
            self.add_error(str(e))
            raise
        finally:
            # Clean up cloned repository
            if repo_path:
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

    def cleanup_all(self):
        """Clean up all temporary cloned repositories."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")


# Import hashlib for the hash function
import hashlib
