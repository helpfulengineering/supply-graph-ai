"""
File Categorization Rules for Layer 1 heuristic categorization.

This module provides rule-based file categorization for OKH manifest generation.
It implements the first layer of categorization using file patterns, extensions,
and directory structure to provide initial categorization suggestions.
"""

import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from ...models.okh import DocumentationType


@dataclass
class FileCategorizationResult:
    """Result of file categorization."""
    documentation_type: DocumentationType
    confidence: float  # 0.0 to 1.0
    excluded: bool = False
    reason: str = ""  # Explanation for the categorization


class FileCategorizationRules:
    """
    Rule-based file categorization for Layer 1 heuristic categorization.
    
    This class provides fast, rule-based categorization using:
    - File extensions
    - Directory paths
    - Filename patterns
    - Exclusion rules
    
    It always produces valid categorizations (for fallback mode when LLM unavailable).
    """
    
    def __init__(self):
        """Initialize file categorization rules."""
        self._init_extension_patterns()
        self._init_directory_patterns()
        self._init_filename_patterns()
        self._init_exclusion_patterns()
    
    def _init_extension_patterns(self) -> None:
        """Initialize extension-based categorization patterns."""
        # Manufacturing files (for machines)
        self.manufacturing_extensions = {
            '.3mf', '.stl', '.step', '.stp', '.gcode', '.nc', '.amf'
        }
        
        # Design files (source CAD)
        self.design_extensions = {
            '.scad', '.fcstd', '.blend', '.f3d', '.iges', '.dxf', '.dwg',
            '.kicad_pcb', '.kicad_mod', '.sch', '.brd'
        }
        
        # Documentation files (require content analysis)
        self.documentation_extensions = {
            '.md', '.rst', '.txt', '.pdf', '.doc', '.docx'
        }
        
        # Software files
        self.software_extensions = {
            '.py', '.js', '.ts', '.cpp', '.c', '.h', '.java', '.rb', '.go', '.rs'
        }
    
    def _init_directory_patterns(self) -> None:
        """Initialize directory-based categorization patterns."""
        # Making instructions (for humans)
        self.making_instructions_dirs = {
            'manual', 'manuals', 'instructions', 'instruction', 'build', 'assembly',
            'assemblies', 'making', 'fabrication'
        }
        
        # Design files
        self.design_dirs = {
            'source_files', 'source', 'cad', 'design', 'designs', 'model', 'models',
            '3d', 'openscad', 'freecad', 'fusion', 'solidworks', 'inventor', 'sketchup'
        }
        
        # Publications
        self.publications_dirs = {
            'publication', 'publications', 'papers', 'paper', 'research', 'academic'
        }
        
        # Technical specifications (includes quality instructions)
        self.technical_specs_dirs = {
            'testing', 'test', 'validation', 'quality', 'specs', 'specifications',
            'technical_specs', 'technical-specs'
        }
        
        # Software
        self.software_dirs = {
            'code', 'software', 'firmware', 'src', 'scripts', 'programs'
        }
        
        # Operating instructions
        self.operating_instructions_dirs = {
            'user_manual', 'user-manual', 'operating', 'operation', 'usage', 'guide', 'guides'
        }
        
        # Documentation home
        self.documentation_home_dirs = {
            'docs', 'documentation', 'doc'
        }
    
    def _init_filename_patterns(self) -> None:
        """Initialize filename-based categorization patterns."""
        # Making instructions
        self.making_instructions_patterns = [
            r'(?i)(assembly|build|instructions?|making|fabrication|manufacturing)',
        ]
        
        # Technical specifications
        self.technical_specs_patterns = [
            r'(?i)(spec|specs|specification|technical_spec|technical-spec)',
        ]
        
        # Publications
        self.publications_patterns = [
            r'(?i)(publication|paper|research|academic)',
        ]
        
        # Design files
        self.design_patterns = [
            r'(?i)(design|cad|model|openscad|freecad)',
        ]
        
        # Documentation home (README in root)
        self.documentation_home_patterns = [
            r'(?i)^readme',
        ]
    
    def _init_exclusion_patterns(self) -> None:
        """Initialize exclusion patterns."""
        # Testing data (raw data files, not documentation)
        self.excluded_testing_patterns = [
            r'(?i)(spectrum|test_data|test_results?|\.csv|\.tsv)',
        ]
        
        # Correspondence
        self.excluded_correspondence_patterns = [
            r'(?i)(cover_letter|response_to_reviewers?|correspondence)',
        ]
        
        # Workflow files
        self.excluded_workflow_dirs = {
            '.github', '.gitlab', '.git', '.vscode', '.idea', '.vs'
        }
        
        self.excluded_workflow_patterns = [
            r'(?i)(workflow|\.github|\.gitlab|\.gitignore|\.gitattributes)',
        ]
    
    def categorize_file(self, filename: str, file_path: str) -> FileCategorizationResult:
        """
        Categorize a file based on its path, extension, and name.
        
        Args:
            filename: The filename (e.g., "part.stl")
            file_path: The full file path (e.g., "manual/part.stl")
            
        Returns:
            FileCategorizationResult with documentation_type, confidence, and exclusion status
        """
        path_lower = file_path.lower()
        filename_lower = filename.lower()
        file_ext = Path(filename).suffix.lower()
        
        # Check exclusion rules first (highest priority)
        if self._should_exclude(path_lower, filename_lower, file_ext):
            return FileCategorizationResult(
                documentation_type=DocumentationType.DESIGN_FILES,  # Dummy value
                confidence=0.9,
                excluded=True,
                reason="File matches exclusion pattern"
            )
        
        # Extension-based categorization (high confidence)
        ext_result = self._categorize_by_extension(file_ext, path_lower)
        if ext_result and ext_result.confidence >= 0.8:
            return ext_result
        
        # Directory-based categorization (medium confidence)
        dir_result = self._categorize_by_directory(path_lower)
        if dir_result and dir_result.confidence >= 0.7:
            return dir_result
        
        # Filename-based categorization (lower confidence)
        filename_result = self._categorize_by_filename(filename_lower, file_path)
        if filename_result:
            return filename_result
        
        # Default fallback (low confidence)
        return FileCategorizationResult(
            documentation_type=DocumentationType.DESIGN_FILES,
            confidence=0.3,
            excluded=False,
            reason="No clear pattern matched, defaulting to design_files"
        )
    
    def _should_exclude(self, path_lower: str, filename_lower: str, file_ext: str) -> bool:
        """Check if file should be excluded."""
        # Check workflow directories
        for excluded_dir in self.excluded_workflow_dirs:
            if excluded_dir in path_lower:
                return True
        
        # Check workflow patterns
        for pattern in self.excluded_workflow_patterns:
            if re.search(pattern, path_lower) or re.search(pattern, filename_lower):
                return True
        
        # Check testing data patterns (but not in publication directory)
        if 'publication' not in path_lower:
            for pattern in self.excluded_testing_patterns:
                if re.search(pattern, filename_lower):
                    # Only exclude if it's clearly test data (spectrum files, etc.)
                    if 'spectrum' in filename_lower or file_ext in {'.csv', '.tsv'}:
                        return True
        
        # Check correspondence patterns
        for pattern in self.excluded_correspondence_patterns:
            if re.search(pattern, filename_lower):
                return True
        
        return False
    
    def _categorize_by_extension(self, file_ext: str, path_lower: str) -> Optional[FileCategorizationResult]:
        """Categorize file by extension."""
        # Manufacturing files (high confidence)
        if file_ext in self.manufacturing_extensions:
            return FileCategorizationResult(
                documentation_type=DocumentationType.MANUFACTURING_FILES,
                confidence=0.9,
                excluded=False,
                reason=f"File extension {file_ext} indicates manufacturing file"
            )
        
        # Design files (high confidence)
        if file_ext in self.design_extensions:
            return FileCategorizationResult(
                documentation_type=DocumentationType.DESIGN_FILES,
                confidence=0.9,
                excluded=False,
                reason=f"File extension {file_ext} indicates design file"
            )
        
        # Software files (medium-high confidence)
        if file_ext in self.software_extensions:
            # Context-aware: check if it's in a design directory (CAD scripts)
            if any(design_dir in path_lower for design_dir in self.design_dirs):
                return FileCategorizationResult(
                    documentation_type=DocumentationType.DESIGN_FILES,
                    confidence=0.7,
                    excluded=False,
                    reason=f"Software file {file_ext} in design directory"
                )
            else:
                return FileCategorizationResult(
                    documentation_type=DocumentationType.SOFTWARE,
                    confidence=0.8,
                    excluded=False,
                    reason=f"File extension {file_ext} indicates software"
                )
        
        # Documentation files need content analysis (low confidence for extension alone)
        if file_ext in self.documentation_extensions:
            return None  # Let directory/filename patterns handle this
        
        return None
    
    def _categorize_by_directory(self, path_lower: str) -> Optional[FileCategorizationResult]:
        """Categorize file by directory path."""
        # Making instructions
        if any(dir_name in path_lower for dir_name in self.making_instructions_dirs):
            return FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.8,
                excluded=False,
                reason="File in making instructions directory"
            )
        
        # Design files
        if any(dir_name in path_lower for dir_name in self.design_dirs):
            return FileCategorizationResult(
                documentation_type=DocumentationType.DESIGN_FILES,
                confidence=0.8,
                excluded=False,
                reason="File in design directory"
            )
        
        # Publications
        if any(dir_name in path_lower for dir_name in self.publications_dirs):
            return FileCategorizationResult(
                documentation_type=DocumentationType.PUBLICATIONS,
                confidence=0.8,
                excluded=False,
                reason="File in publication directory"
            )
        
        # Technical specifications (testing/validation directories)
        # But exclude raw test data files (spectrum files, CSV data)
        if any(dir_name in path_lower for dir_name in self.technical_specs_dirs):
            # Check if it's raw test data (should be excluded)
            filename_lower = Path(path_lower).name.lower()
            if any(pattern in filename_lower for pattern in ['spectrum', 'test_data', 'test_results']):
                return FileCategorizationResult(
                    documentation_type=DocumentationType.DESIGN_FILES,  # Dummy value
                    confidence=0.8,
                    excluded=True,
                    reason="Raw test data file, not OKH documentation"
                )
            # Otherwise, it's technical specifications documentation
            return FileCategorizationResult(
                documentation_type=DocumentationType.TECHNICAL_SPECIFICATIONS,
                confidence=0.7,
                excluded=False,
                reason="File in technical specifications directory"
            )
        
        # Software
        if any(dir_name in path_lower for dir_name in self.software_dirs):
            return FileCategorizationResult(
                documentation_type=DocumentationType.SOFTWARE,
                confidence=0.7,
                excluded=False,
                reason="File in software directory"
            )
        
        # Operating instructions
        if any(dir_name in path_lower for dir_name in self.operating_instructions_dirs):
            return FileCategorizationResult(
                documentation_type=DocumentationType.OPERATING_INSTRUCTIONS,
                confidence=0.7,
                excluded=False,
                reason="File in operating instructions directory"
            )
        
        return None
    
    def _categorize_by_filename(self, filename_lower: str, file_path: str) -> Optional[FileCategorizationResult]:
        """Categorize file by filename patterns."""
        # Documentation home (README in root only)
        if any(re.search(pattern, filename_lower) for pattern in self.documentation_home_patterns):
            # Check if it's in root (no directory separators, just filename)
            path_parts = Path(file_path).parts
            # Root means just the filename, no parent directories
            if len(path_parts) == 1 or (len(path_parts) == 2 and path_parts[0] == '.'):
                return FileCategorizationResult(
                    documentation_type=DocumentationType.DOCUMENTATION_HOME,
                    confidence=0.9,
                    excluded=False,
                    reason="README file in root directory"
                )
        
        # Making instructions
        if any(re.search(pattern, filename_lower) for pattern in self.making_instructions_patterns):
            return FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.6,
                excluded=False,
                reason="Filename suggests making instructions"
            )
        
        # Technical specifications
        if any(re.search(pattern, filename_lower) for pattern in self.technical_specs_patterns):
            return FileCategorizationResult(
                documentation_type=DocumentationType.TECHNICAL_SPECIFICATIONS,
                confidence=0.6,
                excluded=False,
                reason="Filename suggests technical specifications"
            )
        
        # Publications
        if any(re.search(pattern, filename_lower) for pattern in self.publications_patterns):
            return FileCategorizationResult(
                documentation_type=DocumentationType.PUBLICATIONS,
                confidence=0.6,
                excluded=False,
                reason="Filename suggests publication"
            )
        
        # Design files
        if any(re.search(pattern, filename_lower) for pattern in self.design_patterns):
            return FileCategorizationResult(
                documentation_type=DocumentationType.DESIGN_FILES,
                confidence=0.6,
                excluded=False,
                reason="Filename suggests design file"
            )
        
        return None

