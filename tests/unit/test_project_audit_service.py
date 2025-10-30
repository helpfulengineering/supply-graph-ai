"""
Unit tests for the ProjectAuditService.

This module tests the ProjectAuditService in isolation to ensure
it can correctly audit populated OKH projects and identify used/unused files.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.project_audit_service import ProjectAuditService, ProjectAuditResult


class TestProjectAuditService:
    """Unit tests for ProjectAuditService."""
    
    @pytest.fixture
    def audit_service(self):
        """Create ProjectAuditService instance for testing."""
        return ProjectAuditService()
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory structure for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir) / "test-project"
            project_path.mkdir()
            
            # Create some populated files
            (project_path / "README.md").write_text("# Test Project\n\nThis is a real README.")
            (project_path / "okh-manifest.json").write_text('{"title": "test"}')
            
            # Create empty stub files
            (project_path / "design-files").mkdir()
            (project_path / "design-files" / "index.md").write_text("")
            
            # Create a file with minimal content (should be considered empty)
            (project_path / "manufacturing-files").mkdir()
            (project_path / "manufacturing-files" / "index.md").write_text("# Manufacturing Files\n\n[OPTIONAL: Description]")
            
            # Create a populated directory
            (project_path / "bom").mkdir()
            (project_path / "bom" / "bom.csv").write_text("Part,Quantity,Material\nPart1,5,PLA\nPart2,10,ABS")
            (project_path / "bom" / "index.md").write_text("# Bill of Materials\n\nSee bom.csv for details.")
            
            yield project_path
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_audit_scan_basic_directory(self, audit_service, temp_project_dir):
        """Test that the audit service can scan a basic project directory."""
        result = await audit_service.audit_project(str(temp_project_dir))
        
        assert isinstance(result, ProjectAuditResult)
        assert result.project_path == str(temp_project_dir)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_identify_populated_files(self, audit_service, temp_project_dir):
        """Test that populated files are correctly identified."""
        result = await audit_service.audit_project(str(temp_project_dir))
        
        # README.md should be identified as populated (not empty, not stub)
        populated_paths = {f.path for f in result.populated_files}
        assert "README.md" in populated_paths
        
        # Empty files should be in empty_files list
        empty_paths = {f.path for f in result.empty_files}
        assert "design-files/index.md" in empty_paths
        
        # Files with stub placeholders should be identified as stubs
        stub_paths = {f.path for f in result.empty_files if f.is_stub}
        assert "manufacturing-files/index.md" in stub_paths
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_stub_detection(self, audit_service, temp_project_dir):
        """Test that stub content is correctly detected."""
        # Create a file with placeholder content
        stub_file = temp_project_dir / "test-stub.md"
        stub_file.write_text("# Test\n\n[OPTIONAL: Description]")
        
        result = await audit_service.audit_project(str(temp_project_dir))
        
        # Find the stub file in results
        stub_files = [f for f in result.empty_files if f.path == "test-stub.md"]
        assert len(stub_files) == 1
        assert stub_files[0].is_stub == True

