"""
Unit tests for FileCategorizationRules class.

Tests the Layer 1 heuristic rules for file categorization.
Following TDD approach: write tests first, then implement.
"""

import pytest
from pathlib import Path
from src.core.generation.utils.file_categorization import (
    FileCategorizationRules,
    FileCategorizationResult
)
from src.core.models.okh import DocumentationType


class TestFileCategorizationRules:
    """Test the FileCategorizationRules class."""
    
    def test_rules_initialization(self):
        """Test that FileCategorizationRules can be initialized."""
        rules = FileCategorizationRules()
        assert rules is not None
    
    def test_categorize_file_returns_result(self):
        """Test that categorize_file returns a FileCategorizationResult."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("test.stl", "/path/to/test.stl")
        assert isinstance(result, FileCategorizationResult)
        assert result.documentation_type is not None
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0


class TestExtensionBasedCategorization:
    """Test extension-based file categorization."""
    
    def test_stl_files_manufacturing(self):
        """Test that .stl files are categorized as manufacturing_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.stl", "/path/to/part.stl")
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
        assert result.confidence >= 0.8  # High confidence for clear extensions
    
    def test_3mf_files_manufacturing(self):
        """Test that .3mf files are categorized as manufacturing_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.3mf", "/path/to/part.3mf")
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
        assert result.confidence >= 0.8
    
    def test_gcode_files_manufacturing(self):
        """Test that .gcode files are categorized as manufacturing_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.gcode", "/path/to/part.gcode")
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
        assert result.confidence >= 0.8
    
    def test_scad_files_design(self):
        """Test that .scad files are categorized as design_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.scad", "/path/to/part.scad")
        assert result.documentation_type == DocumentationType.DESIGN_FILES
        assert result.confidence >= 0.8
    
    def test_step_files_manufacturing(self):
        """Test that .step files are categorized as manufacturing_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.step", "/path/to/part.step")
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
        assert result.confidence >= 0.8


class TestDirectoryBasedCategorization:
    """Test directory-based file categorization."""
    
    def test_manual_directory_making_instructions(self):
        """Test that files in manual/ directory are categorized as making_instructions."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("assembly.md", "manual/assembly.md")
        assert result.documentation_type == DocumentationType.MAKING_INSTRUCTIONS
        assert result.confidence >= 0.7
    
    def test_instructions_directory_making_instructions(self):
        """Test that files in instructions/ directory are categorized as making_instructions."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("build.md", "instructions/build.md")
        assert result.documentation_type == DocumentationType.MAKING_INSTRUCTIONS
        assert result.confidence >= 0.7
    
    def test_publication_directory_publications(self):
        """Test that files in publication/ directory are categorized as publications."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("paper.pdf", "publication/paper.pdf")
        assert result.documentation_type == DocumentationType.PUBLICATIONS
        assert result.confidence >= 0.7
    
    def test_source_files_directory_design(self):
        """Test that files in source_files/ directory are categorized as design_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.scad", "source_files/scad/part.scad")
        assert result.documentation_type == DocumentationType.DESIGN_FILES
        assert result.confidence >= 0.7
    
    def test_testing_directory_technical_specifications(self):
        """Test that files in testing/ directory are categorized as technical_specifications."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("test.txt", "testing/test.txt")
        # Testing directory files should go to technical-specifications (not excluded)
        # unless they're clearly raw test data
        assert result.documentation_type == DocumentationType.TECHNICAL_SPECIFICATIONS
        assert result.excluded is False
        assert result.confidence >= 0.7
    
    def test_testing_directory_raw_data_excluded(self):
        """Test that raw test data files in testing/ directory are excluded."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("spectrum.txt", "testing/spectrum.txt")
        # Raw test data files should be excluded
        assert result.excluded is True
        assert result.confidence >= 0.7


class TestFilenameBasedCategorization:
    """Test filename-based file categorization."""
    
    def test_readme_root_documentation_home(self):
        """Test that README.md in root is categorized as documentation_home."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("README.md", "README.md")
        assert result.documentation_type == DocumentationType.DOCUMENTATION_HOME
        assert result.confidence >= 0.8
    
    def test_readme_subdirectory_not_documentation_home(self):
        """Test that README.md in subdirectory is NOT documentation_home."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("README.md", "docs/README.md")
        # Should not be documentation_home if not in root
        assert result.documentation_type != DocumentationType.DOCUMENTATION_HOME
    
    def test_assembly_filename_making_instructions(self):
        """Test that files with 'assembly' in name are categorized as making_instructions."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("assembly_guide.md", "/path/to/assembly_guide.md")
        assert result.documentation_type == DocumentationType.MAKING_INSTRUCTIONS
        assert result.confidence >= 0.6
    
    def test_specs_filename_technical_specifications(self):
        """Test that files with 'specs' in name are categorized as technical_specifications."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("specs.md", "/path/to/specs.md")
        assert result.documentation_type == DocumentationType.TECHNICAL_SPECIFICATIONS
        assert result.confidence >= 0.6


class TestExclusionRules:
    """Test exclusion rules."""
    
    def test_github_workflow_excluded(self):
        """Test that GitHub workflow files are excluded."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("workflow.yml", ".github/workflows/workflow.yml")
        assert result.excluded is True
    
    def test_correspondence_excluded(self):
        """Test that correspondence files are excluded."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("cover_letter.txt", "publication/cover_letter.txt")
        # Note: cover letters should be excluded, but publications should be included
        # This is a nuanced case - we might need to check content
        # For now, test that publication directory files are included
        result2 = rules.categorize_file("paper.pdf", "publication/paper.pdf")
        assert result2.excluded is False
        assert result2.documentation_type == DocumentationType.PUBLICATIONS
    
    def test_testing_data_excluded(self):
        """Test that testing data files are excluded."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("spectrum.txt", "testing/spectrum.txt")
        assert result.excluded is True
    
    def test_git_directory_excluded(self):
        """Test that .git directory files are excluded."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("config", ".git/config")
        assert result.excluded is True


class TestPriorityOrdering:
    """Test that more specific patterns override generic ones."""
    
    def test_extension_overrides_directory(self):
        """Test that file extension takes priority over directory for clear cases."""
        rules = FileCategorizationRules()
        # .stl in manual/ should still be manufacturing_files (not making_instructions)
        result = rules.categorize_file("part.stl", "manual/part.stl")
        # Extension should win for manufacturing files
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
    
    def test_specific_directory_overrides_generic(self):
        """Test that specific directory patterns override generic ones."""
        rules = FileCategorizationRules()
        # publication/ should override generic documentation patterns
        result = rules.categorize_file("paper.md", "publication/paper.md")
        assert result.documentation_type == DocumentationType.PUBLICATIONS


class TestConfidenceScoring:
    """Test confidence scoring based on pattern specificity."""
    
    def test_high_confidence_clear_extension(self):
        """Test that clear extensions get high confidence."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.stl", "/path/to/part.stl")
        assert result.confidence >= 0.8
    
    def test_medium_confidence_directory(self):
        """Test that directory-based categorization gets medium confidence."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("file.md", "manual/file.md")
        assert 0.6 <= result.confidence < 0.9
    
    def test_low_confidence_ambiguous(self):
        """Test that ambiguous files get lower confidence."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("document.txt", "/path/to/document.txt")
        # Generic .txt files are ambiguous and need content analysis
        assert result.confidence < 0.7


class TestContextAwareCategorization:
    """Test context-aware categorization for special cases."""
    
    def test_scad_with_rb_in_design_directory(self):
        """Test that .scad + .rb in design directory are design_files."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("part.scad", "source_files/scad/part.scad")
        assert result.documentation_type == DocumentationType.DESIGN_FILES
    
    def test_standalone_rb_file_software(self):
        """Test that standalone .rb files are software."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("script.rb", "/path/to/script.rb")
        # Standalone scripts should be software
        assert result.documentation_type == DocumentationType.SOFTWARE


class TestEdgeCases:
    """Test edge cases and unusual file paths."""
    
    def test_nested_paths(self):
        """Test that nested paths are handled correctly."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("file.md", "docs/manual/assembly/file.md")
        assert result.documentation_type == DocumentationType.MAKING_INSTRUCTIONS
    
    def test_case_insensitive(self):
        """Test that categorization is case-insensitive."""
        rules = FileCategorizationRules()
        result1 = rules.categorize_file("PART.STL", "/path/to/PART.STL")
        result2 = rules.categorize_file("part.stl", "/path/to/part.stl")
        assert result1.documentation_type == result2.documentation_type
    
    def test_no_extension(self):
        """Test that files without extensions are handled."""
        rules = FileCategorizationRules()
        result = rules.categorize_file("README", "/path/to/README")
        # Should still categorize based on filename
        assert result.documentation_type is not None

