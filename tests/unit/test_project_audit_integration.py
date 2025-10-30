"""
Integration tests for ProjectAuditService with real OKH project structures.

This module tests the ProjectAuditService with more realistic OKH project
structures to ensure it works correctly in practice.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.project_audit_service import ProjectAuditService, ProjectAuditResult
from core.services.scaffold_service import ScaffoldService, ScaffoldOptions


class TestProjectAuditIntegration:
    """Integration tests for ProjectAuditService with real OKH projects."""
    
    @pytest.fixture
    def audit_service(self):
        """Create ProjectAuditService instance for testing."""
        return ProjectAuditService()
    
    @pytest.fixture
    def scaffold_service(self):
        """Create ScaffoldService instance for testing."""
        return ScaffoldService()
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for filesystem tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_audit_scaffolded_project(self, audit_service, scaffold_service, temp_dir):
        """Test auditing a freshly scaffolded project."""
        # Generate a scaffolded project
        options = ScaffoldOptions(
            project_name="test-audit-project",
            version="1.0.0",
            template_level="standard",
            output_format="filesystem",
            output_path=temp_dir,
            include_examples=True
        )
        
        result = await scaffold_service.generate_scaffold(options)
        project_path = result.filesystem_path
        
        # Audit the scaffolded project
        audit_result = await audit_service.audit_project(project_path)
        
        # Verify basic structure
        assert isinstance(audit_result, ProjectAuditResult)
        assert audit_result.project_path == project_path
        
        # Should have populated files (README, manifest, etc.)
        populated_paths = {f.path for f in audit_result.populated_files}
        assert "README.md" in populated_paths
        
        # Check if manifest is populated or empty (it might be a stub)
        manifest_files = [f for f in audit_result.populated_files + audit_result.empty_files if f.path == "okh-manifest.json"]
        assert len(manifest_files) == 1
        manifest_file = manifest_files[0]
        # The manifest should exist but might be considered a stub due to placeholder content
        
        # Should have empty stub files
        empty_paths = {f.path for f in audit_result.empty_files}
        assert len(empty_paths) > 0  # Should have some empty files
        
        # Verify stub detection works
        stub_files = [f for f in audit_result.empty_files if f.is_stub]
        assert len(stub_files) > 0  # Should detect some stub files
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_audit_partially_populated_project(self, audit_service, temp_dir):
        """Test auditing a project that has been partially populated."""
        # Create a project structure manually
        project_path = Path(temp_dir) / "partial-project"
        project_path.mkdir()
        
        # Create some populated files
        (project_path / "README.md").write_text("# Partial Project\n\nThis is a real project with content.")
        (project_path / "okh-manifest.json").write_text(json.dumps({
            "title": "Partial Project",
            "version": "1.0.0",
            "okhv": "OKH-LOSHv1.0"
        }, indent=2))
        
        # Create some populated directories
        (project_path / "bom").mkdir()
        (project_path / "bom" / "bom.csv").write_text("Part,Quantity,Material\nScrew,4,Steel\nBolt,2,Aluminum")
        (project_path / "bom" / "index.md").write_text("# Bill of Materials\n\nSee bom.csv for the complete list.")
        
        # Create empty directories
        (project_path / "design-files").mkdir()
        (project_path / "design-files" / "index.md").write_text("")
        
        # Create stub files
        (project_path / "manufacturing-files").mkdir()
        (project_path / "manufacturing-files" / "index.md").write_text("# Manufacturing Files\n\n[OPTIONAL: Add manufacturing documentation]")
        
        # Audit the project
        audit_result = await audit_service.audit_project(str(project_path))
        
        # Verify populated files
        populated_paths = {f.path for f in audit_result.populated_files}
        assert "README.md" in populated_paths
        assert "okh-manifest.json" in populated_paths
        assert "bom/bom.csv" in populated_paths
        assert "bom/index.md" in populated_paths
        
        # Verify empty files
        empty_paths = {f.path for f in audit_result.empty_files}
        assert "design-files/index.md" in empty_paths
        
        # Verify stub files
        stub_files = [f for f in audit_result.empty_files if f.is_stub]
        stub_paths = {f.path for f in stub_files}
        assert "manufacturing-files/index.md" in stub_paths
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_audit_nonexistent_project(self, audit_service):
        """Test that auditing a nonexistent project raises appropriate error."""
        with pytest.raises(ValueError, match="Project path does not exist"):
            await audit_service.audit_project("/nonexistent/path")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_audit_file_instead_of_directory(self, audit_service, temp_dir):
        """Test that auditing a file instead of directory raises appropriate error."""
        file_path = Path(temp_dir) / "not_a_directory.txt"
        file_path.write_text("This is a file, not a directory")
        
        with pytest.raises(ValueError, match="Project path is not a directory"):
            await audit_service.audit_project(str(file_path))
