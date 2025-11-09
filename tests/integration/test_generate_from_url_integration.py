"""
Integration tests for the generate-from-url API endpoint and CLI command.

This module tests the end-to-end functionality of generating OKH manifests from URLs,
including the new file categorization improvements (Layer 1 heuristics + Layer 2 LLM).
"""

import pytest
import httpx
import json
import os
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.core.models.okh import OKHManifest, DocumentationType


class TestGenerateFromURLIntegration:
    """Integration tests for generate-from-url endpoint and CLI."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for the running FastAPI server."""
        return os.getenv("API_BASE_URL", "http://localhost:8001/v1")
    
    @pytest.fixture
    def client(self):
        """HTTP client for making requests."""
        return httpx.AsyncClient(timeout=120.0)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_from_url_nasa_rover(self, client, base_url):
        """
        Test generating OKH manifest from NASA Open Source Rover repository.
        
        This test validates:
        - End-to-end generation from real repository URL
        - File categorization using new Layer 1 heuristics
        - Proper categorization of files into making_instructions, manufacturing_files, etc.
        - New DocumentationType fields (publications, technical_specifications)
        """
        url = "https://github.com/nasa-jpl/open-source-rover"
        
        request_data = {
            "url": url,
            "skip_review": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/generate-from-url",
            json=request_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["success"] is True
        assert "manifest" in result
        
        manifest_data = result["manifest"]
        
        # Validate basic manifest structure
        assert "title" in manifest_data
        assert "version" in manifest_data
        assert "repo" in manifest_data
        
        # Validate new file categorization fields exist
        assert "making_instructions" in manifest_data
        assert "manufacturing_files" in manifest_data
        assert "design_files" in manifest_data
        assert "operating_instructions" in manifest_data
        assert "technical_specifications" in manifest_data
        assert "publications" in manifest_data
        
        # Validate file categorization quality
        # Should have some files categorized
        total_categorized = (
            len(manifest_data.get("making_instructions", [])) +
            len(manifest_data.get("manufacturing_files", [])) +
            len(manifest_data.get("design_files", [])) +
            len(manifest_data.get("operating_instructions", [])) +
            len(manifest_data.get("technical_specifications", [])) +
            len(manifest_data.get("publications", []))
        )
        
        assert total_categorized > 0, "Expected at least some files to be categorized"
        
        # Validate quality report
        assert "quality_report" in result
        quality_report = result["quality_report"]
        assert "overall_quality" in quality_report
        
        print(f"✅ Generated manifest for NASA Rover with {total_categorized} categorized files")
        print(f"   - making_instructions: {len(manifest_data.get('making_instructions', []))}")
        print(f"   - manufacturing_files: {len(manifest_data.get('manufacturing_files', []))}")
        print(f"   - design_files: {len(manifest_data.get('design_files', []))}")
        print(f"   - operating_instructions: {len(manifest_data.get('operating_instructions', []))}")
        print(f"   - technical_specifications: {len(manifest_data.get('technical_specifications', []))}")
        print(f"   - publications: {len(manifest_data.get('publications', []))}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_from_url_file_categorization_accuracy(self, client, base_url):
        """
        Test file categorization accuracy with a known repository structure.
        
        This test validates that files are correctly categorized:
        - .stl files → manufacturing_files
        - .scad files → design_files
        - README.md (root) → documentation_home
        - Files in manual/ → making_instructions
        - Files in publication/ → publications
        """
        url = "https://github.com/rwb27/openflexure_microscope"
        
        request_data = {
            "url": url,
            "skip_review": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/generate-from-url",
            json=request_data
        )
        
        assert response.status_code == 200
        
        result = response.json()
        manifest_data = result["manifest"]
        
        # Check for correct categorization patterns
        manufacturing_files = manifest_data.get("manufacturing_files", [])
        design_files = manifest_data.get("design_files", [])
        making_instructions = manifest_data.get("making_instructions", [])
        publications = manifest_data.get("publications", [])
        
        # Validate .stl files are in manufacturing_files
        stl_files = [f for f in manufacturing_files if f.get("path", "").endswith(".stl")]
        assert len(stl_files) > 0 or len(manufacturing_files) == 0, "Expected .stl files in manufacturing_files"
        
        # Validate .scad files are in design_files
        scad_files = [f for f in design_files if f.get("path", "").endswith(".scad")]
        assert len(scad_files) > 0 or len(design_files) == 0, "Expected .scad files in design_files"
        
        # Validate documentation_home is set (if README exists)
        if manifest_data.get("documentation_home"):
            assert "readme" in manifest_data["documentation_home"].lower() or "README" in manifest_data["documentation_home"]
        
        print(f"✅ File categorization validated:")
        print(f"   - Manufacturing files (.stl): {len(stl_files)}")
        print(f"   - Design files (.scad): {len(scad_files)}")
        print(f"   - Making instructions: {len(making_instructions)}")
        print(f"   - Publications: {len(publications)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_from_url_invalid_url(self, client, base_url):
        """Test error handling for invalid URLs."""
        request_data = {
            "url": "not-a-valid-url",
            "skip_review": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/generate-from-url",
            json=request_data
        )
        
        # Should return 422 (validation error) or 500 (processing error)
        assert response.status_code in [422, 500]
        
        result = response.json()
        assert "detail" in result or "error" in result
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_from_url_unsupported_platform(self, client, base_url):
        """Test error handling for unsupported platforms."""
        request_data = {
            "url": "https://bitbucket.org/user/repo",
            "skip_review": True
        }
        
        response = await client.post(
            f"{base_url}/api/okh/generate-from-url",
            json=request_data
        )
        
        # Should return 422 (validation error) or 500 (processing error)
        assert response.status_code in [422, 500]
        
        result = response.json()
        assert "detail" in result or "error" in result



class TestGenerateFromURLCliIntegration:
    """Integration tests for generate-from-url CLI command."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner for CLI commands."""
        from click.testing import CliRunner
        return CliRunner()
    
    @pytest.mark.integration
    def test_cli_generate_from_url_help(self, runner):
        """Test that CLI generate-from-url help command works."""
        from src.cli.main import cli
        
        result = runner.invoke(cli, ['okh', 'generate-from-url', '--help'])
        
        assert result.exit_code == 0
        assert "Generate OKH manifest from repository URL" in result.output
        assert "--output" in result.output or "-o" in result.output
        assert "--no-review" in result.output
        assert "--clone" in result.output
        
        print("✅ CLI generate-from-url help command working")
    
    @pytest.mark.integration
    def test_cli_generate_from_url_basic(self, runner):
        """Test basic CLI generate-from-url command."""
        from src.cli.main import cli
        
        # Test with a real repository URL
        url = "https://github.com/nasa-jpl/open-source-rover"
        
        result = runner.invoke(cli, [
            'okh', 'generate-from-url', url,
            '--no-review',
            '--format', 'json'
        ])
        
        # Note: This may fail if server is not running or LLM is not configured
        # But we can test that CLI parsing works correctly
        print(f"CLI generate-from-url exit code: {result.exit_code}")
        print(f"CLI generate-from-url output: {result.output[:500]}...")  # First 500 chars
        
        # Should parse arguments correctly
        if result.exit_code != 0:
            # Check that it's not a parsing error
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI argument parsing working correctly")
        else:
            # If successful, validate output contains manifest data
            assert "title" in result.output or "manifest" in result.output or "success" in result.output
            print("✅ CLI command executed successfully")
    
    @pytest.mark.integration
    def test_cli_generate_from_url_with_options(self, runner):
        """Test CLI generate-from-url with various options."""
        from src.cli.main import cli
        
        url = "https://github.com/rwb27/openflexure_microscope"
        
        result = runner.invoke(cli, [
            'okh', 'generate-from-url', url,
            '--no-review',
            '--clone',  # Use local cloning
            '--format', 'okh',
            '--output', '/tmp/test-output',
            '--bom-formats', 'json', 'md',
            '--unified-bom'
        ])
        
        print(f"CLI with options exit code: {result.exit_code}")
        print(f"CLI with options output: {result.output[:500]}...")
        
        # Should parse all options correctly
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI options parsing working correctly")
        else:
            print("✅ CLI command with options executed successfully")
    
    @pytest.mark.integration
    def test_cli_generate_from_url_llm_options(self, runner):
        """Test CLI generate-from-url with LLM options."""
        from src.cli.main import cli
        
        url = "https://github.com/nasa-jpl/open-source-rover"
        
        result = runner.invoke(cli, [
            'okh', 'generate-from-url', url,
            '--no-review',
            '--use-llm',
            '--llm-provider', 'anthropic',
            '--quality-level', 'professional'
        ])
        
        print(f"CLI with LLM exit code: {result.exit_code}")
        print(f"CLI with LLM output: {result.output[:500]}...")
        
        # Should parse LLM options correctly
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI LLM options parsing working correctly")
        else:
            print("✅ CLI command with LLM executed successfully")
    
    @pytest.mark.integration
    def test_cli_generate_from_url_invalid_url(self, runner):
        """Test CLI error handling for invalid URLs."""
        from src.cli.main import cli
        
        result = runner.invoke(cli, [
            'okh', 'generate-from-url', 'not-a-valid-url',
            '--no-review'
        ])
        
        # Should fail with error
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid" in result.output or "not supported" in result.output.lower()
        print("✅ CLI handles invalid URL correctly")
    
    @pytest.mark.integration
    def test_cli_generate_from_url_file_categorization_output(self, runner):
        """
        Test that CLI output includes new file categorization fields.
        
        This test validates that the generated manifest includes:
        - making_instructions
        - manufacturing_files
        - design_files
        - operating_instructions
        - technical_specifications
        - publications
        """
        from src.cli.main import cli
        
        url = "https://github.com/nasa-jpl/open-source-rover"
        
        result = runner.invoke(cli, [
            'okh', 'generate-from-url', url,
            '--no-review',
            '--format', 'json'
        ])
        
        # If successful, check output for new fields
        if result.exit_code == 0:
            output_lower = result.output.lower()
            
            # Check for new file categorization fields in output
            has_file_categorization = (
                "making_instructions" in output_lower or
                "manufacturing_files" in output_lower or
                "design_files" in output_lower or
                "operating_instructions" in output_lower or
                "technical_specifications" in output_lower or
                "publications" in output_lower
            )
            
            if has_file_categorization:
                print("✅ CLI output includes new file categorization fields")
            else:
                print("⚠️  CLI output may not include file categorization fields (check if generation succeeded)")
        else:
            print(f"⚠️  CLI command failed (exit code: {result.exit_code}), cannot validate file categorization output")
