"""
File processing utilities for generation layers.

This module provides centralized file processing functionality including
file type detection, pattern matching, content extraction, and categorization.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ..models import FileInfo


@dataclass
class FilePattern:
    """Pattern for matching files"""

    pattern: str
    field: str
    confidence: float
    extraction_method: str
    description: str


class FileProcessor:
    """Centralized file processing utilities"""

    def __init__(self):
        self._file_type_extensions = self._initialize_file_type_extensions()
        self._file_patterns = self._initialize_file_patterns()
        self._excluded_directories = self._initialize_excluded_directories()

    def _initialize_file_type_extensions(self) -> Dict[str, Set[str]]:
        """Initialize file type extension mappings"""
        return {
            "markdown": {".md", ".rst", ".txt"},
            "image": {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".svg",
                ".bmp",
                ".tiff",
                ".webp",
            },
            "3d_model": {".stl", ".obj", ".3mf", ".ply", ".dae", ".fbx"},
            "cad_file": {".scad", ".step", ".stp", ".iges", ".iges", ".dxf", ".dwg"},
            "schematic": {".sch", ".brd", ".kicad_pcb", ".kicad_mod", ".pro"},
            "document": {".pdf", ".doc", ".docx", ".odt", ".rtf"},
            "code": {
                ".py",
                ".js",
                ".ts",
                ".cpp",
                ".c",
                ".h",
                ".hpp",
                ".java",
                ".go",
                ".rs",
                ".php",
            },
            "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"},
            "data": {".csv", ".tsv", ".xlsx", ".xls", ".ods"},
            "archive": {".zip", ".tar", ".gz", ".7z", ".rar"},
            "executable": {".exe", ".bin", ".app", ".deb", ".rpm"},
            "other": set(),
        }

    def _initialize_file_patterns(self) -> List[FilePattern]:
        """Initialize file pattern matching rules"""
        return [
            # License files
            FilePattern(
                pattern=r"(?i)^(license|licence)(\.(txt|md))?$",
                field="license",
                confidence=0.9,
                extraction_method="license_file_detection",
                description="License file detection",
            ),
            # BOM files
            FilePattern(
                pattern=r"(?i)^(bom|bill.of.materials|materials)(\.(txt|md|csv|json))?$",
                field="bom",
                confidence=0.8,
                extraction_method="bom_file_detection",
                description="Bill of Materials file detection",
            ),
            # README files
            FilePattern(
                pattern=r"(?i)^readme(\.(md|rst|txt))?$",
                field="readme",
                confidence=0.9,
                extraction_method="readme_detection",
                description="README file detection",
            ),
            # Manufacturing files
            FilePattern(
                pattern=r"(?i)^(manufacturing|production|assembly)(\.(txt|md))?$",
                field="manufacturing_files",
                confidence=0.7,
                extraction_method="manufacturing_file_detection",
                description="Manufacturing instruction file detection",
            ),
            # Design files
            FilePattern(
                pattern=r"(?i)^(design|cad|model)(\.(txt|md))?$",
                field="design_files",
                confidence=0.7,
                extraction_method="design_file_detection",
                description="Design file detection",
            ),
            # Tool lists
            FilePattern(
                pattern=r"(?i)^(tools|equipment|requirements)(\.(txt|md))?$",
                field="tool_list",
                confidence=0.7,
                extraction_method="tool_list_detection",
                description="Tool list file detection",
            ),
            # Assembly instructions
            FilePattern(
                pattern=r"(?i)^(assembly|build|install)(\.(txt|md))?$",
                field="making_instructions",
                confidence=0.7,
                extraction_method="assembly_instruction_detection",
                description="Assembly instruction file detection",
            ),
            # Operating instructions
            FilePattern(
                pattern=r"(?i)^(operating|usage|manual)(\.(txt|md))?$",
                field="operating_instructions",
                confidence=0.7,
                extraction_method="operating_instruction_detection",
                description="Operating instruction file detection",
            ),
            # Quality instructions
            FilePattern(
                pattern=r"(?i)^(quality|testing|validation)(\.(txt|md))?$",
                field="quality_instructions",
                confidence=0.7,
                extraction_method="quality_instruction_detection",
                description="Quality instruction file detection",
            ),
            # Risk assessment
            FilePattern(
                pattern=r"(?i)^(risk|safety|hazard)(\.(txt|md))?$",
                field="risk_assessment",
                confidence=0.7,
                extraction_method="risk_assessment_detection",
                description="Risk assessment file detection",
            ),
            # Tool settings
            FilePattern(
                pattern=r"(?i)^(settings|config|parameters)(\.(txt|md|json|yaml))?$",
                field="tool_settings",
                confidence=0.6,
                extraction_method="tool_settings_detection",
                description="Tool settings file detection",
            ),
        ]

    def _initialize_excluded_directories(self) -> Set[str]:
        """Initialize directories to exclude from processing"""
        return {
            ".git",
            ".github",
            ".vscode",
            ".idea",
            "__pycache__",
            "node_modules",
            ".pytest_cache",
            "venv",
            "env",
            ".env",
        }

    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type based on extension.

        Args:
            file_path: Path to the file

        Returns:
            File type category
        """
        file_path_lower = file_path.lower()
        file_ext = Path(file_path_lower).suffix

        for file_type, extensions in self._file_type_extensions.items():
            if file_ext in extensions:
                return file_type

        return "other"

    def extract_file_content(self, file_info: FileInfo) -> Optional[str]:
        """
        Extract content from a file if it's a text file.

        Args:
            file_info: File information object

        Returns:
            File content as string, or None if not a text file
        """
        if not file_info.content:
            return None

        # Check if file is likely to contain text
        file_type = self.detect_file_type(file_info.path)
        text_types = {"markdown", "document", "code", "config", "data"}

        if file_type in text_types:
            return file_info.content

        # For other types, check if content looks like text
        if isinstance(file_info.content, str) and len(file_info.content) > 0:
            # Simple heuristic: if content is mostly printable characters, treat as text
            printable_ratio = sum(
                1 for c in file_info.content[:1000] if c.isprintable() or c.isspace()
            ) / min(1000, len(file_info.content))
            if printable_ratio > 0.8:
                return file_info.content

        return None

    def find_files_by_pattern(
        self, files: List[FileInfo], pattern: str
    ) -> List[FileInfo]:
        """
        Find files matching a regex pattern.

        Args:
            files: List of file information objects
            pattern: Regex pattern to match against file paths

        Returns:
            List of matching files
        """
        matching_files = []
        compiled_pattern = re.compile(pattern, re.IGNORECASE)

        for file_info in files:
            if compiled_pattern.search(file_info.path):
                matching_files.append(file_info)

        return matching_files

    def find_files_by_extension(
        self, files: List[FileInfo], extensions: List[str]
    ) -> List[FileInfo]:
        """
        Find files with specific extensions.

        Args:
            files: List of file information objects
            extensions: List of extensions to match (with or without dots)

        Returns:
            List of matching files
        """
        matching_files = []
        normalized_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        }

        for file_info in files:
            file_ext = Path(file_info.path).suffix.lower()
            if file_ext in normalized_extensions:
                matching_files.append(file_info)

        return matching_files

    def categorize_files(self, files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
        """
        Categorize files by type.

        Args:
            files: List of file information objects

        Returns:
            Dictionary mapping file types to lists of files
        """
        categorized = {}

        for file_info in files:
            file_type = self.detect_file_type(file_info.path)
            if file_type not in categorized:
                categorized[file_type] = []
            categorized[file_type].append(file_info)

        return categorized

    def match_file_patterns(
        self, files: List[FileInfo]
    ) -> Dict[str, List[Tuple[FileInfo, FilePattern]]]:
        """
        Match files against predefined patterns.

        Args:
            files: List of file information objects

        Returns:
            Dictionary mapping field names to lists of (file, pattern) tuples
        """
        matches = {}

        for file_info in files:
            file_name = Path(file_info.path).name

            for pattern in self._file_patterns:
                if re.match(pattern.pattern, file_name, re.IGNORECASE):
                    if pattern.field not in matches:
                        matches[pattern.field] = []
                    matches[pattern.field].append((file_info, pattern))

        return matches

    def filter_excluded_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        Filter out files in excluded directories.

        Args:
            files: List of file information objects

        Returns:
            Filtered list of files
        """
        filtered_files = []

        for file_info in files:
            path_parts = Path(file_info.path).parts

            # Check if any part of the path is in excluded directories
            if not any(
                part.lower() in self._excluded_directories for part in path_parts
            ):
                filtered_files.append(file_info)

        return filtered_files

    def get_file_type_extensions(self, file_type: str) -> Set[str]:
        """
        Get extensions for a specific file type.

        Args:
            file_type: Type of file

        Returns:
            Set of file extensions
        """
        return self._file_type_extensions.get(file_type, set())

    def is_text_file(self, file_path: str) -> bool:
        """
        Check if a file is likely to contain text.

        Args:
            file_path: Path to the file

        Returns:
            True if file is likely to contain text
        """
        file_type = self.detect_file_type(file_path)
        text_types = {"markdown", "document", "code", "config", "data"}
        return file_type in text_types

    def is_image_file(self, file_path: str) -> bool:
        """
        Check if a file is an image.

        Args:
            file_path: Path to the file

        Returns:
            True if file is an image
        """
        return self.detect_file_type(file_path) == "image"

    def is_design_file(self, file_path: str) -> bool:
        """
        Check if a file is a design file (CAD, 3D model, schematic).

        Args:
            file_path: Path to the file

        Returns:
            True if file is a design file
        """
        file_type = self.detect_file_type(file_path)
        design_types = {"3d_model", "cad_file", "schematic"}
        return file_type in design_types
