"""
End-to-End Tests for OKH Manifest Generation Workflow.

These tests validate the complete workflow from URL input to final manifest output,
covering both CLI and API integration paths.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock
import asyncio


class TestEndToEndGeneration:
    """End-to-end tests for the complete generation workflow"""
    
    def test_complete_workflow_cli_mode(self):
        """Test complete workflow in CLI mode with fallback (direct service calls)"""
        from src.core.generation.url_router import URLRouter
        from src.core.generation.engine import GenerationEngine
        from src.core.generation.models import PlatformType
        
        # Test URL
        url = "https://github.com/GliaX/Stethoscope"
        
        # Step 1: URL validation and platform detection
        router = URLRouter()
        assert router.validate_url(url), "URL should be valid"
        
        platform = router.detect_platform(url)
        assert platform == PlatformType.GITHUB, "Should detect GitHub platform"
        
        # Step 2: Project data extraction (mocked for testing)
        with patch('src.core.generation.platforms.github.GitHubExtractor.extract_project') as mock_extract:
            from src.core.generation.models import ProjectData, FileInfo, DocumentInfo
            
            mock_project_data = ProjectData(
                url=url,
                platform=PlatformType.GITHUB,
                metadata={
                    "name": "Stethoscope",
                    "description": "A digital stethoscope project",
                    "license": "MIT"
                },
                files=[
                    FileInfo(
                        path="README.md",
                        size=len("Mock README content"),
                        content="Mock README content",
                        file_type="markdown"
                    ),
                    FileInfo(
                        path="LICENSE",
                        size=len("MIT License"),
                        content="MIT License",
                        file_type="text"
                    )
                ],
                documentation=[
                    DocumentInfo(
                        title="README",
                        path="README.md",
                        content="Mock README content",
                        doc_type="readme"
                    )
                ],
                raw_content={
                    "README.md": "Mock README content",
                    "LICENSE": "MIT License"
                }
            )
            mock_extract.return_value = mock_project_data
            
            # Step 3: Manifest generation
            engine = GenerationEngine()
            result = asyncio.run(engine.generate_manifest_async(mock_project_data))
            
            # Step 4: Validate generation result
            assert result is not None, "Generation should produce a result"
            assert len(result.generated_fields) > 0, "Should generate some fields"
            assert result.quality_report is not None, "Should have quality report"
            
            # Step 5: Validate specific fields
            assert "title" in result.generated_fields, "Should generate title field"
            assert "repo" in result.generated_fields, "Should generate repo field"
            assert result.generated_fields["title"].value == "Stethoscope", "Title should match"
            assert result.generated_fields["repo"].value == url, "Repo should match URL"
            
            # Step 6: Validate quality assessment
            assert result.quality_report.overall_quality > 0, "Should have positive quality score"
            assert isinstance(result.quality_report.missing_required_fields, list), "Should have missing fields list"
            assert isinstance(result.quality_report.recommendations, list), "Should have recommendations"
    
    def test_complete_workflow_api_mode(self):
        """Test complete workflow in API mode"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        # Test API endpoint
        response = client.post("/okh/generate-from-url", json={
            "url": "https://github.com/GliaX/Stethoscope",
            "skip_review": True
        })
        
        # Validate API response
        assert response.status_code == 200, f"API should return 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] is True, "API should return success"
        assert "manifest" in data, "API should return manifest"
        assert "quality_report" in data, "API should return quality report"
        
        # Validate manifest structure
        manifest = data["manifest"]
        assert "title" in manifest, "Manifest should have title"
        assert "repo" in manifest, "Manifest should have repo"
        assert "confidence_scores" in manifest, "Manifest should have confidence scores"
        assert "missing_fields" in manifest, "Manifest should have missing fields"
        
        # Validate quality report structure
        quality_report = data["quality_report"]
        assert "overall_quality" in quality_report, "Quality report should have overall_quality"
        assert "required_fields_complete" in quality_report, "Quality report should have required_fields_complete"
        assert "missing_required_fields" in quality_report, "Quality report should have missing_required_fields"
        assert "recommendations" in quality_report, "Quality report should have recommendations"
    
    def test_cli_command_end_to_end(self):
        """Test CLI command end-to-end with file output"""
        import tempfile
        import subprocess
        import sys
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Run CLI command
            result = subprocess.run([
                sys.executable, "ome", "okh", "generate-from-url",
                "https://github.com/GliaX/Stethoscope",
                "--output", tmp_path,
                "--no-review"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            # Validate command execution
            assert result.returncode == 0, f"CLI command should succeed, got: {result.stderr}"
            
            # Validate output file was created
            assert os.path.exists(tmp_path), "Output file should be created"
            
            # Validate file content
            with open(tmp_path, 'r') as f:
                data = json.load(f)
            
            assert data["success"] is True, "CLI output should indicate success"
            assert "manifest" in data, "CLI output should contain manifest"
            assert "quality_report" in data, "CLI output should contain quality report"
            
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_workflow_with_different_platforms(self):
        """Test workflow with different supported platforms"""
        from src.core.generation.url_router import URLRouter
        from src.core.generation.models import PlatformType
        
        router = URLRouter()
        
        # Test GitHub URL
        github_url = "https://github.com/user/repo"
        assert router.validate_url(github_url), "GitHub URL should be valid"
        assert router.detect_platform(github_url) == PlatformType.GITHUB, "Should detect GitHub"
        
        # Test GitLab URL
        gitlab_url = "https://gitlab.com/user/repo"
        assert router.validate_url(gitlab_url), "GitLab URL should be valid"
        assert router.detect_platform(gitlab_url) == PlatformType.GITLAB, "Should detect GitLab"
        
        # Test invalid URL
        invalid_url = "not-a-valid-url"
        assert not router.validate_url(invalid_url), "Invalid URL should be rejected"
        assert router.detect_platform(invalid_url) == PlatformType.UNKNOWN, "Should detect unknown platform"
    
    def test_quality_assessment_accuracy(self):
        """Test that quality assessment provides meaningful feedback"""
        from src.core.generation.engine import GenerationEngine
        from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
        
        # Create test project data with missing required fields
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={
                "name": "Test Project",
                "description": "A test project"
                # Missing: license, version, etc.
            },
            files=[],
            documentation=[],
            raw_content={}
        )
        
        engine = GenerationEngine()
        result = asyncio.run(engine.generate_manifest_async(project_data))
        
        # Validate quality assessment
        quality_report = result.quality_report
        assert quality_report.overall_quality < 1.0, "Quality should be less than perfect for incomplete data"
        assert len(quality_report.missing_required_fields) > 0, "Should identify missing required fields"
        assert len(quality_report.recommendations) > 0, "Should provide recommendations"
        
        # Validate that missing fields are actually required
        required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
        for field in quality_report.missing_required_fields:
            assert field in required_fields, f"Missing field {field} should be in required fields list"
    
    def test_confidence_scoring(self):
        """Test that confidence scoring works correctly"""
        from src.core.generation.engine import GenerationEngine
        from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
        
        # Create test project data with good metadata
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={
                "name": "Well Documented Project",
                "description": "A well-documented project with clear information",
                "license": "MIT"
            },
            files=[
                FileInfo(
                    path="README.md",
                    size=len("Comprehensive README with detailed information"),
                    content="Comprehensive README with detailed information",
                    file_type="markdown"
                )
            ],
            documentation=[
                DocumentInfo(
                    title="README",
                    path="README.md",
                    content="Comprehensive README with detailed information",
                    doc_type="readme"
                )
            ],
            raw_content={
                "README.md": "Comprehensive README with detailed information"
            }
        )
        
        engine = GenerationEngine()
        result = asyncio.run(engine.generate_manifest_async(project_data))
        
        # Validate confidence scores
        confidence_scores = result.confidence_scores
        assert len(confidence_scores) > 0, "Should have confidence scores"
        
        for field, score in confidence_scores.items():
            assert 0.0 <= score <= 1.0, f"Confidence score for {field} should be between 0 and 1, got {score}"
        
        # Fields with good data should have high confidence
        if "title" in confidence_scores:
            assert confidence_scores["title"] > 0.8, "Title with good data should have high confidence"
        
        if "description" in confidence_scores:
            assert confidence_scores["description"] > 0.8, "Description with good data should have high confidence"
    
    def test_error_handling_invalid_url(self):
        """Test error handling for invalid URLs"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        # Test with invalid URL
        response = client.post("/okh/generate-from-url", json={
            "url": "not-a-valid-url",
            "skip_review": True
        })
        
        # Should return validation error
        assert response.status_code == 422, f"Should return 422 for invalid URL, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        assert "Invalid URL" in data["detail"], "Error should mention invalid URL"
    
    def test_error_handling_unsupported_platform(self):
        """Test error handling for unsupported platforms"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        # Test with unsupported platform
        response = client.post("/okh/generate-from-url", json={
            "url": "https://unsupported-platform.com/user/repo",
            "skip_review": True
        })
        
        # Should return validation error
        assert response.status_code == 422, f"Should return 422 for unsupported platform, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        assert "Unsupported platform" in data["detail"], "Error should mention unsupported platform"
    
    def test_manifest_structure_consistency(self):
        """Test that generated manifests have consistent structure"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        # Generate manifest
        response = client.post("/okh/generate-from-url", json={
            "url": "https://github.com/GliaX/Stethoscope",
            "skip_review": True
        })
        
        assert response.status_code == 200, "Should generate manifest successfully"
        
        data = response.json()
        manifest = data["manifest"]
        
        # Validate required structure
        required_manifest_fields = ["title", "version", "repo", "license", "description", "confidence_scores", "missing_fields"]
        for field in required_manifest_fields:
            assert field in manifest, f"Manifest should have {field} field"
        
        # Validate data types
        assert isinstance(manifest["title"], str), "Title should be string"
        assert isinstance(manifest["version"], str), "Version should be string"
        assert isinstance(manifest["repo"], str), "Repo should be string"
        assert isinstance(manifest["confidence_scores"], dict), "Confidence scores should be dict"
        assert isinstance(manifest["missing_fields"], list), "Missing fields should be list"
        
        # Validate quality report structure
        quality_report = data["quality_report"]
        required_quality_fields = ["overall_quality", "required_fields_complete", "missing_required_fields", "recommendations"]
        for field in required_quality_fields:
            assert field in quality_report, f"Quality report should have {field} field"
        
        # Validate data types
        assert isinstance(quality_report["overall_quality"], (int, float)), "Overall quality should be number"
        assert isinstance(quality_report["required_fields_complete"], bool), "Required fields complete should be boolean"
        assert isinstance(quality_report["missing_required_fields"], list), "Missing required fields should be list"
        assert isinstance(quality_report["recommendations"], list), "Recommendations should be list"
    
    def test_performance_basic(self):
        """Test basic performance requirements"""
        import time
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        # Measure generation time
        start_time = time.time()
        
        response = client.post("/okh/generate-from-url", json={
            "url": "https://github.com/GliaX/Stethoscope",
            "skip_review": True
        })
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should complete within reasonable time (5 seconds for basic generation)
        assert generation_time < 5.0, f"Generation should complete within 5 seconds, took {generation_time:.2f}s"
        assert response.status_code == 200, "Should generate successfully"
    
    def test_cli_api_consistency(self):
        """Test that CLI and API produce consistent results"""
        import tempfile
        import subprocess
        import sys
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.core.api.routes.okh import router
        
        # Generate via API
        app = FastAPI()
        app.include_router(router, prefix="/okh")
        client = TestClient(app)
        
        api_response = client.post("/okh/generate-from-url", json={
            "url": "https://github.com/GliaX/Stethoscope",
            "skip_review": True
        })
        
        assert api_response.status_code == 200, "API should work"
        api_data = api_response.json()
        
        # Generate via CLI
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            cli_result = subprocess.run([
                sys.executable, "ome", "okh", "generate-from-url",
                "https://github.com/GliaX/Stethoscope",
                "--output", tmp_path,
                "--no-review"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            assert cli_result.returncode == 0, "CLI should work"
            
            with open(tmp_path, 'r') as f:
                cli_data = json.load(f)
            
            # Compare key fields (allowing for minor differences in metadata)
            assert api_data["success"] == cli_data["success"], "Success status should match"
            assert api_data["manifest"]["title"] == cli_data["manifest"]["title"], "Title should match"
            assert api_data["manifest"]["repo"] == cli_data["manifest"]["repo"], "Repo should match"
            
            # Quality reports should be similar
            api_quality = api_data["quality_report"]["overall_quality"]
            cli_quality = cli_data["quality_report"]["overall_quality"]
            assert abs(api_quality - cli_quality) < 0.1, "Quality scores should be similar"
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
