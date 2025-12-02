"""
Service for auditing populated OKH projects.

This module provides functionality to scan populated OKH project directories,
identify which files contain actual content (vs empty stubs), and map them
to OKH manifest fields for manifest optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a file in the project."""

    path: str
    size: int
    is_empty: bool
    is_stub: bool


@dataclass
class ProjectAuditResult:
    """Result of a project audit.

    Attributes:
        project_path: Path to the project root directory
        populated_files: List of files that contain actual content
        empty_files: List of files that are empty or contain only stubs
        empty_directories: List of directories that are empty or only contain empty files
    """

    project_path: str
    populated_files: List[FileInfo] = field(default_factory=list)
    empty_files: List[FileInfo] = field(default_factory=list)
    empty_directories: List[str] = field(default_factory=list)


class ProjectAuditService:
    """Service for auditing populated OKH projects.

    This service scans project directories to identify:
    - Files with actual content vs empty stubs
    - Unused directories that can be removed
    - Files that should be referenced in the OKH manifest
    """

    def __init__(self):
        """Initialize the ProjectAuditService."""
        pass

    async def audit_project(self, project_path: str) -> ProjectAuditResult:
        """Audit a populated OKH project directory.

        Args:
            project_path: Path to the project root directory

        Returns:
            ProjectAuditResult containing information about files and directories
        """
        project_root = Path(project_path)

        if not project_root.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        if not project_root.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        populated_files = []
        empty_files = []

        # Scan all files in the project
        for file_path in project_root.rglob("*"):
            if file_path.is_file():
                file_info = self._analyze_file(file_path, project_root)
                if file_info.is_empty or file_info.is_stub:
                    empty_files.append(file_info)
                else:
                    populated_files.append(file_info)

        return ProjectAuditResult(
            project_path=project_path,
            populated_files=populated_files,
            empty_files=empty_files,
        )

    def _analyze_file(self, file_path: Path, project_root: Path) -> FileInfo:
        """Analyze a single file to determine if it contains actual content.

        Args:
            file_path: Path to the file to analyze
            project_root: Root directory of the project

        Returns:
            FileInfo with analysis results
        """
        size = file_path.stat().st_size
        is_empty = size == 0

        # Read file content to check if it's a stub
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        is_stub = self._is_stub_content(content)

        # Calculate relative path from project root
        rel_path = str(file_path.relative_to(project_root))

        return FileInfo(path=rel_path, size=size, is_empty=is_empty, is_stub=is_stub)

    def _is_stub_content(self, content: str) -> bool:
        """Check if file content is just a stub/placeholder.

        Args:
            content: File content to check

        Returns:
            True if content appears to be a stub/placeholder
        """
        # Check for empty content
        if not content.strip():
            return True

        # Check for common stub patterns (placeholders like [OPTIONAL: ...], [REQUIRED: ...])
        stub_patterns = [
            "[OPTIONAL:",
            "[REQUIRED:",
            "[String value]",
            "[Integer value]",
        ]

        # If content contains stub placeholders, check if it's mostly placeholder content
        content_lower = content.lower()
        if any(pattern.lower() in content_lower for pattern in stub_patterns):
            # Check if the content is mostly placeholders
            # Count lines that contain placeholders
            lines = [line for line in content.split("\n") if line.strip()]
            if not lines:
                return True

            placeholder_lines = sum(
                1
                for line in lines
                if any(pattern.lower() in line.lower() for pattern in stub_patterns)
            )

            # If at least 40% of lines contain placeholders, consider it a stub
            # Or if the file is very small (3 or fewer meaningful lines) and contains any placeholder
            if placeholder_lines / len(lines) >= 0.4 or (
                len(lines) <= 3 and placeholder_lines > 0
            ):
                return True

        return False
