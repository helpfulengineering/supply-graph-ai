"""
Integration tests for the OKH project scaffolding endpoint.

This module tests the /api/okh/scaffold endpoint against the running FastAPI server
to ensure end-to-end functionality works correctly.
"""

import pytest
import httpx
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.api.models.scaffold.request import ScaffoldRequest
from core.api.models.scaffold.response import ScaffoldResponse


class TestScaffoldEndpoint:
    """Integration tests for the scaffold endpoint."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for the running FastAPI server."""
        return "http://localhost:8001/v1"
    
    @pytest.fixture
    def client(self):
        """HTTP client for making requests."""
        return httpx.AsyncClient(timeout=30.0)
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for filesystem output tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir
    
    @pytest.fixture
    def sample_scaffold_request(self):
        """Sample scaffold request for testing."""
        return {
            "project_name": "test-hardware-project",
            "version": "1.0.0",
            "organization": "Test Organization",
            "template_level": "standard",
            "output_format": "json",
            "include_examples": True,
            "okh_version": "OKH-LOSHv1.0"
        }
    
    async def test_scaffold_json_output(self, client, base_url, sample_scaffold_request):
        """Test scaffold generation with JSON output format."""
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=sample_scaffold_request
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate response structure
        assert "status" in data
        assert "message" in data
        assert "project_name" in data
        assert "structure" in data
        assert "manifest_template" in data
        
        # Validate response content
        assert data["status"] == "success"
        assert data["project_name"] == "test-hardware-project"
        assert isinstance(data["structure"], dict)
        assert isinstance(data["manifest_template"], dict)
        
        # Validate directory structure
        structure = data["structure"]
        assert "test-hardware-project" in structure
        project_root = structure["test-hardware-project"]
        
        # Check required directories
        required_dirs = [
            "design-files", "manufacturing-files", "bom", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "docs"
        ]
        
        for dir_name in required_dirs:
            assert dir_name in project_root, f"Missing directory: {dir_name}"
            assert isinstance(project_root[dir_name], dict), f"Directory {dir_name} should be a dict"
        
        # Check required files
        required_files = [
            "okh-manifest.json", "README.md", "LICENSE", "CONTRIBUTING.md", "mkdocs.yml"
        ]
        
        for file_name in required_files:
            assert file_name in project_root, f"Missing file: {file_name}"
            assert isinstance(project_root[file_name], str), f"File {file_name} should be a string"
        
        # Validate manifest template
        manifest = data["manifest_template"]
        assert "okhv" in manifest
        assert "title" in manifest
        assert "version" in manifest
        assert manifest["okhv"] == "OKH-LOSHv1.0"
        assert manifest["title"] == "test-hardware-project"
        assert manifest["version"] == "1.0.0"
        
        print("✅ JSON output test passed")
    
    async def test_scaffold_filesystem_output(self, client, base_url, temp_dir):
        """Test scaffold generation with filesystem output format."""
        request_data = {
            "project_name": "filesystem-test-project",
            "version": "0.2.0",
            "template_level": "minimal",
            "output_format": "filesystem",
            "output_path": temp_dir,
            "include_examples": False
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate response
        assert data["status"] == "success"
        assert data["project_name"] == "filesystem-test-project"
        assert "filesystem_path" in data
        assert data["filesystem_path"] is not None
        
        # Validate filesystem output
        project_path = Path(data["filesystem_path"])
        assert project_path.exists(), f"Project directory should exist: {project_path}"
        assert project_path.is_dir(), f"Project path should be a directory: {project_path}"
        
        # Check required files exist
        required_files = [
            "okh-manifest.json", "README.md", "LICENSE", "CONTRIBUTING.md", "mkdocs.yml"
        ]
        
        for file_name in required_files:
            file_path = project_path / file_name
            assert file_path.exists(), f"Required file should exist: {file_path}"
            assert file_path.is_file(), f"Required file should be a file: {file_path}"
        
        # Check required directories exist
        required_dirs = [
            "design-files", "manufacturing-files", "bom", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "docs"
        ]
        
        for dir_name in required_dirs:
            dir_path = project_path / dir_name
            assert dir_path.exists(), f"Required directory should exist: {dir_path}"
            assert dir_path.is_dir(), f"Required directory should be a directory: {dir_path}"
        
        # Validate manifest file content
        manifest_path = project_path / "okh-manifest.json"
        with open(manifest_path, 'r') as f:
            manifest_content = json.load(f)
        
        assert manifest_content["okhv"] == "OKH-LOSHv1.0"
        assert manifest_content["title"] == "filesystem-test-project"
        assert manifest_content["version"] == "0.2.0"
        
        # Validate README content
        readme_path = project_path / "README.md"
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        assert "filesystem-test-project" in readme_content
        assert "minimal" in readme_content.lower()
        
        print("✅ Filesystem output test passed")
    
    async def test_scaffold_zip_output(self, client, base_url, temp_dir):
        """Test scaffold generation with ZIP output format."""
        request_data = {
            "project_name": "zip-test-project",
            "version": "0.3.0",
            "template_level": "detailed",
            "output_format": "zip",
            "output_path": temp_dir,
            "include_examples": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate response
        assert data["status"] == "success"
        assert data["project_name"] == "zip-test-project"
        assert "download_url" in data
        assert data["download_url"] is not None
        
        # Validate ZIP file exists
        download_url = data["download_url"]
        assert download_url.startswith("file://"), f"Download URL should be a file URL: {download_url}"
        
        zip_path = Path(download_url.replace("file://", ""))
        assert zip_path.exists(), f"ZIP file should exist: {zip_path}"
        assert zip_path.is_file(), f"ZIP file should be a file: {zip_path}"
        assert zip_path.suffix == ".zip", f"File should have .zip extension: {zip_path}"
        
        print("✅ ZIP output test passed")
    
    async def test_scaffold_template_levels(self, client, base_url):
        """Test scaffold generation with different template levels."""
        template_levels = ["minimal", "standard", "detailed"]
        
        for level in template_levels:
            request_data = {
                "project_name": f"template-{level}-test",
                "version": "1.0.0",
                "template_level": level,
                "output_format": "json",
                "include_examples": True
            }
            
            response = await client.post(
                f"{base_url}/api/okh/scaffold",
                json=request_data
            )
            
            assert response.status_code == 200, f"Expected 200 for {level}, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert data["status"] == "success"
            assert data["project_name"] == f"template-{level}-test"
            
            # Validate template-specific content
            structure = data["structure"]
            project_root = structure[f"template-{level}-test"]
            
            # Check README content varies by template level
            readme_content = project_root["README.md"]
            
            if level == "minimal":
                assert "[Project description]" in readme_content
            elif level == "standard":
                assert "Quick Start" in readme_content
                assert "Project Structure" in readme_content
            elif level == "detailed":
                assert "Overview" in readme_content
                assert "Development" in readme_content
                assert "Contributing" in readme_content
            
            print(f"✅ Template level {level} test passed")
    
    async def test_scaffold_validation_errors(self, client, base_url):
        """Test scaffold endpoint validation error handling."""
        # Test missing required field
        invalid_request = {
            "version": "1.0.0",
            "template_level": "standard",
            "output_format": "json"
            # Missing project_name
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=invalid_request
        )
        
        assert response.status_code == 422, f"Expected 422 for validation error, got {response.status_code}"
        
        # Test invalid template level
        invalid_request = {
            "project_name": "test-project",
            "template_level": "invalid-level",
            "output_format": "json"
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=invalid_request
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid template level, got {response.status_code}"
        
        # Test invalid output format
        invalid_request = {
            "project_name": "test-project",
            "template_level": "standard",
            "output_format": "invalid-format"
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=invalid_request
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid output format, got {response.status_code}"
        
        print("✅ Validation error handling test passed")
    
    async def test_scaffold_filesystem_path_required(self, client, base_url):
        """Test that filesystem output requires output_path."""
        request_data = {
            "project_name": "test-project",
            "template_level": "standard",
            "output_format": "filesystem"
            # Missing output_path
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        
        assert response.status_code == 422, f"Expected 422 for missing output_path, got {response.status_code}"
        
        print("✅ Filesystem path requirement test passed")
    
    async def test_scaffold_bom_content(self, client, base_url):
        """Test BOM-specific content generation."""
        request_data = {
            "project_name": "bom-test-project",
            "version": "1.0.0",
            "template_level": "detailed",
            "output_format": "json",
            "include_examples": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        structure = data["structure"]
        project_root = structure["bom-test-project"]
        
        # Check BOM directory structure
        bom_dir = project_root["bom"]
        assert "index.md" in bom_dir
        assert "bom.csv" in bom_dir
        assert "bom.md" in bom_dir
        
        # Check BOM content for detailed template
        bom_index = bom_dir["index.md"]
        assert "Bill of Materials" in bom_index
        assert "File Formats" in bom_index
        assert "Integration" in bom_index
        
        bom_csv = bom_dir["bom.csv"]
        assert "item,quantity,unit,notes,supplier,part_number,cost" in bom_csv
        assert "Arduino Uno" in bom_csv
        
        bom_md = bom_dir["bom.md"]
        assert "Components" in bom_md
        assert "Electronics" in bom_md
        assert "Materials" in bom_md
        assert "Total Estimated Cost" in bom_md
        
        print("✅ BOM content test passed")
    
    async def test_scaffold_mkdocs_integration(self, client, base_url):
        """Test MkDocs integration in scaffold output."""
        request_data = {
            "project_name": "mkdocs-test-project",
            "version": "1.0.0",
            "template_level": "standard",
            "output_format": "json",
            "include_examples": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        structure = data["structure"]
        project_root = structure["mkdocs-test-project"]
        
        # Check MkDocs configuration
        mkdocs_yml = project_root["mkdocs.yml"]
        assert "site_name:" in mkdocs_yml
        assert "nav:" in mkdocs_yml
        assert "Home:" in mkdocs_yml
        assert "Getting Started:" in mkdocs_yml
        
        # Check docs directory structure
        docs_dir = project_root["docs"]
        assert "index.md" in docs_dir
        assert "getting-started.md" in docs_dir
        assert "development.md" in docs_dir
        assert "manufacturing.md" in docs_dir
        assert "assembly.md" in docs_dir
        assert "maintenance.md" in docs_dir
        
        # Check README points to MkDocs
        readme_content = project_root["README.md"]
        assert "MkDocs" in readme_content
        assert "mkdocs serve" in readme_content
        
        print("✅ MkDocs integration test passed")
    
    async def test_scaffold_performance(self, client, base_url):
        """Test scaffold generation performance."""
        import time
        
        request_data = {
            "project_name": "performance-test-project",
            "version": "1.0.0",
            "template_level": "detailed",
            "output_format": "json",
            "include_examples": True
        }
        
        start_time = time.time()
        response = await client.post(
            f"{base_url}/api/okh/scaffold",
            json=request_data
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert processing_time < 5.0, f"Scaffold generation took too long: {processing_time:.3f}s"
        
        data = response.json()
        assert data["status"] == "success"
        
        print(f"✅ Performance test passed: {processing_time:.3f}s")
    
    async def test_scaffold_concurrent_requests(self, client, base_url):
        """Test handling of concurrent scaffold requests."""
        import asyncio
        
        async def make_request(i):
            request_data = {
                "project_name": f"concurrent-test-{i}",
                "version": "1.0.0",
                "template_level": "standard",
                "output_format": "json",
                "include_examples": False
            }
            
            response = await client.post(
                f"{base_url}/api/okh/scaffold",
                json=request_data
            )
            return response
        
        # Make 5 concurrent requests
        tasks = [make_request(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
            
            data = response.json()
            assert data["status"] == "success"
            assert data["project_name"] == f"concurrent-test-{i}"
        
        print("✅ Concurrent requests test passed")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])
