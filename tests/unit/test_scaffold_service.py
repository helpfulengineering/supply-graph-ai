"""
Unit tests for the ScaffoldService.

This module tests the ScaffoldService in isolation to ensure
all functionality works correctly without external dependencies.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.scaffold_service import ScaffoldService, ScaffoldOptions, ScaffoldResult


class TestScaffoldService:
    """Unit tests for ScaffoldService."""
    
    @pytest.fixture
    def scaffold_service(self):
        """Create ScaffoldService instance for testing."""
        return ScaffoldService()
    
    @pytest.fixture
    def sample_options(self):
        """Sample ScaffoldOptions for testing."""
        return ScaffoldOptions(
            project_name="test-project",
            version="1.0.0",
            organization="Test Org",
            template_level="standard",
            output_format="json",
            include_examples=True,
            okh_version="OKH-LOSHv1.0"
        )
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for filesystem tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir
    
    def test_scaffold_options_validation(self, scaffold_service):
        """Test ScaffoldOptions validation."""
        # Valid options should not raise
        valid_options = ScaffoldOptions(
            project_name="valid-project",
            template_level="minimal",
            output_format="json"
        )
        scaffold_service._validate_options(valid_options)
        
        # Invalid template level should raise
        with pytest.raises(ValueError, match="template_level must be one of"):
            invalid_options = ScaffoldOptions(
                project_name="test",
                template_level="invalid"
            )
            scaffold_service._validate_options(invalid_options)
        
        # Invalid output format should raise
        with pytest.raises(ValueError, match="output_format must be one of"):
            invalid_options = ScaffoldOptions(
                project_name="test",
                output_format="invalid"
            )
            scaffold_service._validate_options(invalid_options)
        
        # Missing output_path for filesystem should raise
        with pytest.raises(ValueError, match="output_path is required"):
            invalid_options = ScaffoldOptions(
                project_name="test",
                output_format="filesystem"
            )
            scaffold_service._validate_options(invalid_options)
        
        # Empty project name should raise
        with pytest.raises(ValueError, match="project_name is required"):
            invalid_options = ScaffoldOptions(
                project_name="",
                output_format="json"
            )
            scaffold_service._validate_options(invalid_options)
    
    def test_normalize_project_root_name(self, scaffold_service):
        """Test project root name normalization."""
        # Basic normalization
        assert scaffold_service._normalize_project_root_name("Test Project") == "test-project"
        assert scaffold_service._normalize_project_root_name("Test_Project") == "test-project"
        assert scaffold_service._normalize_project_root_name("TestProject") == "testproject"
        
        # Edge cases
        assert scaffold_service._normalize_project_root_name("  Test Project  ") == "test-project"
        assert scaffold_service._normalize_project_root_name("Test---Project") == "test-project"
        assert scaffold_service._normalize_project_root_name("Test   Project") == "test-project"
    
    def test_create_directory_blueprint(self, scaffold_service, sample_options):
        """Test directory blueprint creation."""
        blueprint = scaffold_service._create_directory_blueprint("test-project", sample_options)
        
        # Should have single top-level project directory
        assert len(blueprint.keys()) == 1
        assert "test-project" in blueprint
        
        project_root = blueprint["test-project"]
        
        # Check required files
        required_files = [
            "okh-manifest.json", "README.md", "LICENSE", "CONTRIBUTING.md", "mkdocs.yml"
        ]
        for file_name in required_files:
            assert file_name in project_root
            assert isinstance(project_root[file_name], str)
        
        # Check required directories
        required_dirs = [
            "design-files", "manufacturing-files", "bom", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "docs"
        ]
        for dir_name in required_dirs:
            assert dir_name in project_root
            assert isinstance(project_root[dir_name], dict)
    
    def test_create_manifest_template(self, scaffold_service, sample_options):
        """Test manifest template creation."""
        template = scaffold_service._create_manifest_template(sample_options)
        
        # Check required fields
        assert "okhv" in template
        assert "title" in template
        assert "version" in template
        assert "license" in template
        assert "licensor" in template
        assert "documentation_language" in template
        assert "function" in template
        
        # Check values
        assert template["okhv"] == "OKH-LOSHv1.0"
        assert template["title"] == "test-project"
        assert template["version"] == "1.0.0"
        assert template["documentation_language"] == "en"
        
        # Check license structure
        assert isinstance(template["license"], dict)
        assert "hardware" in template["license"]
        assert "documentation" in template["license"]
        assert "software" in template["license"]
    
    def test_template_levels(self, scaffold_service):
        """Test different template levels."""
        levels = ["minimal", "standard", "detailed"]
        
        for level in levels:
            options = ScaffoldOptions(
                project_name="test-project",
                template_level=level,
                output_format="json"
            )
            
            # Test README template
            readme = scaffold_service._template_readme(options)
            assert "test-project" in readme
            
            if level == "minimal":
                assert "[Project description]" in readme
            elif level == "standard":
                assert "Quick Start" in readme
            elif level == "detailed":
                assert "Overview" in readme
                assert "Development" in readme
            
            # Test index template
            index = scaffold_service._template_index("Test Directory", options)
            assert "Test Directory" in index
            
            if level == "minimal":
                assert "[Add test directory documentation]" in index
            elif level == "standard":
                assert "Purpose" in index
            elif level == "detailed":
                assert "Organization" in index
                assert "Best Practices" in index
    
    def test_bom_templates(self, scaffold_service):
        """Test BOM-specific templates."""
        levels = ["minimal", "standard", "detailed"]
        
        for level in levels:
            options = ScaffoldOptions(
                project_name="test-project",
                template_level=level,
                output_format="json"
            )
            
            # Test BOM index
            bom_index = scaffold_service._template_bom_index(options)
            assert "Bill of Materials" in bom_index
            
            if level == "detailed":
                assert "File Formats" in bom_index
                assert "Integration" in bom_index
            
            # Test BOM CSV
            bom_csv = scaffold_service._template_bom_csv(options)
            assert "item,quantity,unit,notes" in bom_csv
            
            if level == "detailed":
                assert "supplier,part_number,cost" in bom_csv
            
            # Test BOM Markdown
            bom_md = scaffold_service._template_bom_md(options)
            assert "BOM" in bom_md
            
            if level == "detailed":
                assert "Electronics" in bom_md
                assert "Materials" in bom_md
                assert "Total Estimated Cost" in bom_md
    
    def test_inject_stub_documents(self, scaffold_service, sample_options):
        """Test stub document injection."""
        blueprint = scaffold_service._create_directory_blueprint("test-project", sample_options)
        scaffold_service._inject_stub_documents(blueprint, sample_options)
        
        project_root = blueprint["test-project"]
        
        # Check that files have content
        assert len(project_root["README.md"]) > 0
        assert len(project_root["LICENSE"]) > 0
        assert len(project_root["CONTRIBUTING.md"]) > 0
        assert len(project_root["mkdocs.yml"]) > 0
        
        # Check directory index files
        assert len(project_root["design-files"]["index.md"]) > 0
        assert len(project_root["bom"]["index.md"]) > 0
        assert len(project_root["docs"]["index.md"]) > 0
        
        # Check BOM files
        assert len(project_root["bom"]["bom.csv"]) > 0
        assert len(project_root["bom"]["bom.md"]) > 0
    
    def test_write_filesystem(self, scaffold_service, sample_options, temp_dir):
        """Test filesystem writing."""
        # Create blueprint
        blueprint = scaffold_service._create_directory_blueprint("test-project", sample_options)
        manifest_template = scaffold_service._create_manifest_template(sample_options)
        scaffold_service._inject_stub_documents(blueprint, sample_options)
        
        # Set output path
        sample_options.output_path = temp_dir
        
        # Write to filesystem
        result_path = scaffold_service._write_filesystem(blueprint, sample_options, manifest_template)
        
        # Validate result
        assert isinstance(result_path, str)
        project_path = Path(result_path)
        assert project_path.exists()
        assert project_path.is_dir()
        assert project_path.name == "test-project"
        
        # Check files exist
        required_files = [
            "okh-manifest.json", "README.md", "LICENSE", "CONTRIBUTING.md", "mkdocs.yml"
        ]
        for file_name in required_files:
            file_path = project_path / file_name
            assert file_path.exists()
            assert file_path.is_file()
        
        # Check directories exist
        required_dirs = [
            "design-files", "manufacturing-files", "bom", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "docs"
        ]
        for dir_name in required_dirs:
            dir_path = project_path / dir_name
            assert dir_path.exists()
            assert dir_path.is_dir()
        
        # Validate manifest file
        manifest_path = project_path / "okh-manifest.json"
        with open(manifest_path, 'r') as f:
            manifest_content = json.load(f)
        
        assert manifest_content["okhv"] == "OKH-LOSHv1.0"
        assert manifest_content["title"] == "test-project"
    
    @pytest.mark.asyncio
    async def test_create_and_store_zip(self, scaffold_service, sample_options, temp_dir):
        """Test ZIP file creation."""
        # Create blueprint
        blueprint = scaffold_service._create_directory_blueprint("test-project", sample_options)
        manifest_template = scaffold_service._create_manifest_template(sample_options)
        scaffold_service._inject_stub_documents(blueprint, sample_options)
        
        # Set output path
        sample_options.output_path = temp_dir
        
        # Create ZIP
        zip_url = await scaffold_service._create_and_store_zip(blueprint, sample_options, manifest_template)
        
        # Validate result
        assert isinstance(zip_url, str)
        assert zip_url.startswith("file://")
        
        zip_path = Path(zip_url.replace("file://", ""))
        assert zip_path.exists()
        assert zip_path.is_file()
        assert zip_path.suffix == ".zip"
        
        # Check ZIP contains project name
        assert "test-project" in zip_path.name
    
    @pytest.mark.asyncio
    async def test_generate_scaffold_json(self, scaffold_service, sample_options):
        """Test full scaffold generation with JSON output."""
        result = await scaffold_service.generate_scaffold(sample_options)
        
        # Validate result
        assert isinstance(result, ScaffoldResult)
        assert result.project_name == "test-project"
        assert isinstance(result.structure, dict)
        assert isinstance(result.manifest_template, dict)
        assert result.filesystem_path is None
        assert result.download_url is None
        
        # Validate structure
        assert "test-project" in result.structure
        project_root = result.structure["test-project"]
        
        # Check required files and directories
        assert "README.md" in project_root
        assert "okh-manifest.json" in project_root
        assert "bom" in project_root
        assert "docs" in project_root
    
    @pytest.mark.asyncio
    async def test_generate_scaffold_filesystem(self, scaffold_service, temp_dir):
        """Test full scaffold generation with filesystem output."""
        options = ScaffoldOptions(
            project_name="filesystem-test",
            version="2.0.0",
            template_level="detailed",
            output_format="filesystem",
            output_path=temp_dir,
            include_examples=True
        )
        
        result = await scaffold_service.generate_scaffold(options)
        
        # Validate result
        assert isinstance(result, ScaffoldResult)
        assert result.project_name == "filesystem-test"
        assert result.filesystem_path is not None
        assert result.download_url is None
        
        # Validate filesystem output
        project_path = Path(result.filesystem_path)
        assert project_path.exists()
        assert project_path.is_dir()
        
        # Check manifest
        manifest_path = project_path / "okh-manifest.json"
        with open(manifest_path, 'r') as f:
            manifest_content = json.load(f)
        
        assert manifest_content["title"] == "filesystem-test"
        assert manifest_content["version"] == "2.0.0"
    
    @pytest.mark.asyncio
    async def test_generate_scaffold_zip(self, scaffold_service, temp_dir):
        """Test full scaffold generation with ZIP output."""
        options = ScaffoldOptions(
            project_name="zip-test",
            version="3.0.0",
            template_level="minimal",
            output_format="zip",
            output_path=temp_dir,
            include_examples=False
        )
        
        result = await scaffold_service.generate_scaffold(options)
        
        # Validate result
        assert isinstance(result, ScaffoldResult)
        assert result.project_name == "zip-test"
        assert result.filesystem_path is None
        assert result.download_url is not None
        
        # Validate ZIP file
        zip_url = result.download_url
        assert zip_url.startswith("file://")
        
        zip_path = Path(zip_url.replace("file://", ""))
        assert zip_path.exists()
        assert zip_path.is_file()
        assert zip_path.suffix == ".zip"
    
    def test_field_template_generation(self, scaffold_service):
        """Test field template generation for different types."""
        options = ScaffoldOptions(
            project_name="test-project",
            template_level="standard",
            output_format="json"
        )
        
        # Test string field
        from dataclasses import Field as DataclassField
        string_field = DataclassField(name="test_string", type=str)
        template = scaffold_service._generate_field_template("test_string", string_field, options, True)
        assert isinstance(template, str)
        assert "[REQUIRED:" in template
        
        # Test optional field
        template = scaffold_service._generate_field_template("test_string", string_field, options, False)
        assert "[OPTIONAL:" in template
        
        # Test special field handling
        title_template = scaffold_service._generate_field_template("title", string_field, options, True)
        assert title_template == "test-project"
        
        version_template = scaffold_service._generate_field_template("version", string_field, options, True)
        assert version_template == "1.0.0"
    
    def test_placeholder_generation(self, scaffold_service):
        """Test placeholder text generation."""
        options_minimal = ScaffoldOptions(
            project_name="test",
            template_level="minimal",
            output_format="json"
        )
        options_standard = ScaffoldOptions(
            project_name="test",
            template_level="standard",
            output_format="json"
        )
        options_detailed = ScaffoldOptions(
            project_name="test",
            template_level="detailed",
            output_format="json"
        )
        
        # Test minimal level
        placeholder = scaffold_service._get_placeholder("Test description", True, options_minimal)
        assert placeholder == "[Test description]"
        
        # Test standard level
        placeholder = scaffold_service._get_placeholder("Test description", True, options_standard)
        assert "[REQUIRED: Test description]" in placeholder
        
        placeholder = scaffold_service._get_placeholder("Test description", False, options_standard)
        assert "[OPTIONAL: Test description]" in placeholder
        
        # Test detailed level
        placeholder = scaffold_service._get_placeholder("Test description", True, options_detailed)
        assert "[REQUIRED: Test description]" in placeholder


if __name__ == "__main__":
    # Run unit tests
    pytest.main([__file__, "-v", "-s"])
