"""
URL router for OKH manifest generation system.

This module provides URL validation, platform detection, and routing to appropriate
extractors for different platforms.
"""

import re
from typing import Tuple, TYPE_CHECKING
from urllib.parse import urlparse
from .models import PlatformType

if TYPE_CHECKING:
    from src.core.generation.platforms.base import ProjectExtractor


class URLRouter:
    """Router for detecting platforms and routing to appropriate extractors"""

    def __init__(self):
        # Platform detection patterns
        self._platform_patterns = {
            PlatformType.GITHUB: [
                r"github\.com/([^/]+)/([^/]+)",
                r"github\.com/([^/]+)/([^/]+)\.git",
            ],
            PlatformType.GITLAB: [
                r"gitlab\.com/([^/]+)/([^/]+)",
                r"gitlab\.com/([^/]+)/([^/]+)\.git",
                r"gitlab\.com/([^/]+)/([^/]+)/([^/]+)",
                r"gitlab\.com/([^/]+)/([^/]+)/([^/]+)\.git",
            ],
            PlatformType.CODEBERG: [
                r"codeberg\.org/([^/]+)/([^/]+)",
                r"codeberg\.org/([^/]+)/([^/]+)\.git",
            ],
            PlatformType.HACKADAY: [r"hackaday\.io/project/(\d+)"],
        }

        # Initialize extractors (only GitHub and GitLab for Phase 1)
        self._extractors = {}
        self._initialize_extractors()

    def _initialize_extractors(self):
        """Initialize available extractors"""
        # Import here to avoid circular imports
        try:
            from .platforms.github import GitHubExtractor

            self._extractors[PlatformType.GITHUB] = GitHubExtractor()
        except ImportError:
            pass  # Will be implemented later

        try:
            from .platforms.gitlab import GitLabExtractor

            self._extractors[PlatformType.GITLAB] = GitLabExtractor()
        except ImportError:
            pass  # Will be implemented later

        try:
            from .platforms.local_git import LocalGitExtractor

            self._local_git_extractor = LocalGitExtractor()
        except ImportError:
            self._local_git_extractor = None

    def detect_platform(self, url: str) -> PlatformType:
        """
        Detect the platform type from a URL.

        Args:
            url: The URL to analyze

        Returns:
            PlatformType enum value
        """
        if not url:
            return PlatformType.UNKNOWN

        # Normalize URL for pattern matching
        normalized_url = self.normalize_url(url)

        # Check each platform pattern
        for platform, patterns in self._platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, normalized_url):
                    return platform

        return PlatformType.UNKNOWN

    def validate_url(self, url: str) -> bool:
        """
        Validate that a URL is properly formatted.

        Args:
            url: The URL to validate

        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Basic URL validation
        try:
            parsed = urlparse(url)
            # Must have scheme and netloc, or be a bare domain with path
            if parsed.scheme and parsed.netloc:
                return parsed.scheme in ["http", "https"]
            elif parsed.netloc and parsed.path:
                return True
            else:
                return False
        except Exception:
            return False

    def normalize_url(self, url: str) -> str:
        """
        Normalize a URL for consistent processing.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL string
        """
        if not url:
            return ""

        # Remove .git suffix first
        if url.endswith(".git"):
            url = url[:-4]

        # Add https:// if no scheme, or convert http:// to https://
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        elif url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        return url

    def extract_repo_info(self, url: str) -> Tuple[str, str]:
        """
        Extract owner and repository name from a URL.

        Args:
            url: The repository URL

        Returns:
            Tuple of (owner, repo)

        Raises:
            ValueError: If repo info cannot be extracted
        """
        platform = self.detect_platform(url)

        if platform == PlatformType.UNKNOWN:
            raise ValueError("Cannot extract repo info from URL: unknown platform")

        normalized_url = self.normalize_url(url)

        # Extract using platform-specific patterns
        if platform in [PlatformType.GITHUB, PlatformType.CODEBERG]:
            pattern = self._platform_patterns[platform][0]  # Use first pattern
            match = re.search(pattern, normalized_url)
            if match:
                return match.group(1), match.group(2)

        elif platform == PlatformType.GITLAB:
            # Try patterns in order of specificity (most specific first)
            # We need to try the 3-group patterns first, then fall back to 2-group patterns
            patterns_to_try = [
                r"gitlab\.com/([^/]+)/([^/]+)/([^/]+)\.git",
                r"gitlab\.com/([^/]+)/([^/]+)/([^/]+)",
                r"gitlab\.com/([^/]+)/([^/]+)\.git",
                r"gitlab\.com/([^/]+)/([^/]+)",
            ]

            for pattern in patterns_to_try:
                match = re.search(pattern, normalized_url)
                if match:
                    if len(match.groups()) == 2:
                        # Simple owner/repo structure
                        return match.group(1), match.group(2)
                    elif len(match.groups()) == 3:
                        # Nested group structure: group/subgroup/project
                        # For GitLab API, we need to URL-encode the full path
                        group_path = f"{match.group(1)}/{match.group(2)}"
                        project_name = match.group(3)
                        return group_path, project_name

        elif platform == PlatformType.HACKADAY:
            pattern = self._platform_patterns[platform][0]
            match = re.search(pattern, normalized_url)
            if match:
                project_id = match.group(1)
                return "hackaday", f"project-{project_id}"

        raise ValueError("Cannot extract repo info from URL: invalid format")

    def route_to_extractor(self, platform: PlatformType) -> "ProjectExtractor":
        """
        Route to the appropriate extractor for a platform.

        Args:
            platform: The platform type

        Returns:
            ProjectExtractor instance

        Raises:
            ValueError: If no extractor is available for the platform
        """
        if platform not in self._extractors:
            raise ValueError(f"No extractor available for platform: {platform.value}")

        return self._extractors[platform]

    def route_to_local_git_extractor(self) -> "ProjectExtractor":
        """
        Route to the local Git extractor for cloning-based extraction.

        Returns:
            LocalGitExtractor instance

        Raises:
            ValueError: If local Git extractor is not available
        """
        if not self._local_git_extractor:
            raise ValueError("Local Git extractor is not available")

        return self._local_git_extractor

    def supports_local_cloning(self, url: str) -> bool:
        """
        Check if a URL supports local Git cloning.

        Args:
            url: Repository URL to check

        Returns:
            True if URL can be cloned locally
        """
        if not self._local_git_extractor:
            return False

        return self._local_git_extractor.validate_url(url)
