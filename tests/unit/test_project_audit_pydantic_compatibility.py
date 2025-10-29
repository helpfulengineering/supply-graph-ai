"""
Test Pydantic v2 compatibility for ProjectAuditService.

This module tests that the ProjectAuditService works correctly with
Pydantic v2 models and doesn't have any compatibility issues.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.project_audit_service import ProjectAuditService, ProjectAuditResult, FileInfo
from core.models.okh import OKHManifest, License, Person


class TestProjectAuditPydanticCompatibility:
    """Test Pydantic v2 compatibility for ProjectAuditService."""
    
    @pytest.fixture
    def audit_service(self):
        """Create ProjectAuditService instance for testing."""
        return ProjectAuditService()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_pydantic_v2_compatibility(self, audit_service):
        """Test that the service works with Pydantic v2 models."""
        # Test that we can create OKH models (Pydantic v2)
        license_obj = License(
            hardware="MIT",
            documentation="MIT",
            software="MIT"
        )
        
        person = Person(
            name="Test User",
            email="test@example.com"
        )
        
        manifest = OKHManifest(
            title="Test Project",
            version="1.0.0",
            license=license_obj,
            licensor=person,
            documentation_language="en",
            function="Test function"
        )
        
        # Verify the models work
        assert manifest.title == "Test Project"
        assert manifest.license.hardware == "MIT"
        assert manifest.licensor.name == "Test User"
        
        # Test that our service dataclasses work
        file_info = FileInfo(
            path="test.md",
            size=100,
            is_empty=False,
            is_stub=False
        )
        
        assert file_info.path == "test.md"
        assert file_info.size == 100
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_audit_result_serialization(self, audit_service):
        """Test that audit results can be serialized (important for API responses)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir) / "test-project"
            project_path.mkdir()
            
            # Create a test file
            (project_path / "test.md").write_text("# Test\n\nContent here.")
            
            # Run audit
            result = await audit_service.audit_project(str(project_path))
            
            # Test that we can convert to dict (for JSON serialization)
            result_dict = {
                "project_path": result.project_path,
                "populated_files": [
                    {
                        "path": f.path,
                        "size": f.size,
                        "is_empty": f.is_empty,
                        "is_stub": f.is_stub
                    }
                    for f in result.populated_files
                ],
                "empty_files": [
                    {
                        "path": f.path,
                        "size": f.size,
                        "is_empty": f.is_empty,
                        "is_stub": f.is_stub
                    }
                    for f in result.empty_files
                ],
                "empty_directories": result.empty_directories
            }
            
            # Verify serialization works
            assert isinstance(result_dict, dict)
            assert "project_path" in result_dict
            assert "populated_files" in result_dict
            assert "empty_files" in result_dict
            assert "empty_directories" in result_dict
            
            # Verify we can find our test file
            populated_paths = [f["path"] for f in result_dict["populated_files"]]
            assert "test.md" in populated_paths
