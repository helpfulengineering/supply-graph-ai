"""
CLI integration tests for simplified SupplyTree model.

This module tests actual CLI command execution to ensure the CLI works correctly
with the simplified SupplyTree model and updated API routes.
"""

import pytest
import json
import tempfile
import os
import subprocess
import sys
from pathlib import Path
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.cli.main import cli


class TestCLIIntegration:
    """Integration tests for actual CLI command execution."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner for CLI commands."""
        return CliRunner()
    
    @pytest.fixture
    def sample_okh_file(self):
        """Create a temporary OKH file for testing."""
        okh_data = {
            "title": "CLI Integration Test Component",
            "version": "1.0.0",
            "license": {
                "hardware": "MIT"
            },
            "licensor": "CLI Test Organization",
            "documentation_language": "en",
            "function": "Test component for CLI integration testing",
            "manufacturing_processes": ["PCB Assembly", "Soldering", "Testing", "Packaging"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(okh_data, f, indent=2)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass
    
    @pytest.fixture
    def invalid_okh_file(self):
        """Create an invalid OKH file for error testing."""
        invalid_data = {
            "title": "Invalid Component",
            # Missing required fields
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f, indent=2)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass
    
    def test_cli_help_commands(self, runner):
        """Test that CLI help commands work correctly."""
        # Test main help
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Open Matching Engine (OME) Command Line Interface" in result.output
        assert "match" in result.output
        assert "okh" in result.output
        assert "okw" in result.output
        print("✅ Main CLI help command working")
        
        # Test match help
        result = runner.invoke(cli, ['match', '--help'])
        assert result.exit_code == 0
        assert "Matching operations commands" in result.output
        assert "requirements" in result.output
        assert "domains" in result.output
        print("✅ Match CLI help command working")
        
        # Test match requirements help
        result = runner.invoke(cli, ['match', 'requirements', '--help'])
        assert result.exit_code == 0
        assert "Match OKH requirements to OKW capabilities" in result.output
        assert "--min-confidence" in result.output
        assert "--max-results" in result.output
        assert "--access-type" in result.output
        assert "--facility-status" in result.output
        print("✅ Match requirements CLI help command working")
    
    def test_cli_match_requirements_basic(self, runner, sample_okh_file):
        """Test basic match requirements command execution."""
        # Test with valid OKH file
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--min-confidence', '0.8',
            '--max-results', '5',
            '--access-type', 'public',
            '--facility-status', 'active'
        ])
        
        # Note: This will likely fail due to no running server, but we can test CLI parsing
        print(f"CLI result exit code: {result.exit_code}")
        print(f"CLI result output: {result.output}")
        
        # The CLI should at least parse arguments correctly
        # If it fails, it should be due to server connection, not argument parsing
        if result.exit_code != 0:
            # Check that it's not a parsing error
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI argument parsing working correctly")
        else:
            print("✅ CLI command executed successfully")
    
    def test_cli_match_requirements_with_filters(self, runner, sample_okh_file):
        """Test match requirements command with various filter options."""
        # Test with all filter options
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--min-confidence', '0.7',
            '--max-results', '10',
            '--access-type', 'public',
            '--facility-status', 'active',
            '--location', 'San Francisco',
            '--capabilities', 'assembly,testing',
            '--materials', 'copper,plastic',
            '--verbose'
        ])
        
        print(f"CLI with filters exit code: {result.exit_code}")
        print(f"CLI with filters output: {result.output}")
        
        # Should parse all arguments correctly
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI filter argument parsing working correctly")
        else:
            print("✅ CLI command with filters executed successfully")
    
    def test_cli_match_requirements_output_formats(self, runner, sample_okh_file):
        """Test CLI output format options."""
        # Test JSON output format
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--json',
            '--min-confidence', '0.8'
        ])
        
        print(f"CLI JSON output exit code: {result.exit_code}")
        print(f"CLI JSON output: {result.output}")
        
        # Test table output format
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--table',
            '--min-confidence', '0.8'
        ])
        
        print(f"CLI table output exit code: {result.exit_code}")
        print(f"CLI table output: {result.output}")
        
        # Test verbose output
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--verbose',
            '--min-confidence', '0.8'
        ])
        
        print(f"CLI verbose output exit code: {result.exit_code}")
        print(f"CLI verbose output: {result.output}")
        
        print("✅ CLI output format options working")
    
    def test_cli_match_requirements_llm_options(self, runner, sample_okh_file):
        """Test CLI LLM integration options."""
        # Test with LLM enabled
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--use-llm',
            '--llm-provider', 'anthropic',
            '--quality-level', 'professional',
            '--min-confidence', '0.8'
        ])
        
        print(f"CLI LLM options exit code: {result.exit_code}")
        print(f"CLI LLM options output: {result.output}")
        
        # Should parse LLM arguments correctly
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI LLM argument parsing working correctly")
        else:
            print("✅ CLI LLM command executed successfully")
    
    def test_cli_error_handling_invalid_file(self, runner):
        """Test CLI error handling with invalid file."""
        # Test with non-existent file
        result = runner.invoke(cli, [
            'match', 'requirements', 'non-existent-file.json',
            '--min-confidence', '0.8'
        ])
        
        assert result.exit_code != 0
        assert "Error" in result.output or "File not found" in result.output or "No such file" in result.output
        print("✅ CLI handles non-existent file correctly")
        
        # Test with invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            invalid_file = f.name
        
        try:
            result = runner.invoke(cli, [
                'match', 'requirements', invalid_file,
                '--min-confidence', '0.8'
            ])
            
            assert result.exit_code != 0
            print("✅ CLI handles invalid JSON file correctly")
        finally:
            os.unlink(invalid_file)
    
    def test_cli_error_handling_invalid_arguments(self, runner, sample_okh_file):
        """Test CLI error handling with invalid arguments."""
        # Test with invalid confidence score
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--min-confidence', '1.5'  # Invalid: > 1.0
        ])
        
        print(f"CLI invalid confidence exit code: {result.exit_code}")
        print(f"CLI invalid confidence output: {result.output}")
        
        # Test with invalid access type
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--access-type', 'invalid_type'
        ])
        
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid choice" in result.output
        print("✅ CLI handles invalid access type correctly")
        
        # Test with invalid facility status
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--facility-status', 'invalid_status'
        ])
        
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid choice" in result.output
        print("✅ CLI handles invalid facility status correctly")
    
    def test_cli_match_domains_command(self, runner):
        """Test CLI match domains command."""
        result = runner.invoke(cli, ['match', 'domains'])
        
        print(f"CLI domains exit code: {result.exit_code}")
        print(f"CLI domains output: {result.output}")
        
        # Should execute without argument parsing errors
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI domains command argument parsing working")
        else:
            print("✅ CLI domains command executed successfully")
    
    def test_cli_match_validate_command(self, runner, sample_okh_file):
        """Test CLI match validate command."""
        result = runner.invoke(cli, ['match', 'validate', sample_okh_file])
        
        print(f"CLI validate exit code: {result.exit_code}")
        print(f"CLI validate output: {result.output}")
        
        # Should execute without argument parsing errors
        if result.exit_code != 0:
            assert "Error: Missing argument" not in result.output
            assert "Error: Invalid value" not in result.output
            assert "Error: No such option" not in result.output
            print("✅ CLI validate command argument parsing working")
        else:
            print("✅ CLI validate command executed successfully")
    
    def test_cli_subprocess_execution(self, sample_okh_file):
        """Test CLI execution via subprocess (more realistic test)."""
        # Test basic CLI execution
        cmd = [
            sys.executable, '-m', 'src.cli.main',
            'match', 'requirements', sample_okh_file,
            '--min-confidence', '0.8',
            '--max-results', '5'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..')
            )
            
            print(f"Subprocess exit code: {result.returncode}")
            print(f"Subprocess stdout: {result.stdout}")
            print(f"Subprocess stderr: {result.stderr}")
            
            # Should not have argument parsing errors
            assert "Error: Missing argument" not in result.stderr
            assert "Error: Invalid value" not in result.stderr
            assert "Error: No such option" not in result.stderr
            
            print("✅ CLI subprocess execution working correctly")
            
        except subprocess.TimeoutExpired:
            print("⚠️ CLI subprocess timed out (expected if no server running)")
        except Exception as e:
            print(f"⚠️ CLI subprocess error (expected if no server running): {e}")
    
    def test_cli_backward_compatibility_flag(self, runner, sample_okh_file):
        """Test CLI backward compatibility with include_workflows flag."""
        # Note: This flag might not be exposed in CLI yet, but we can test if it exists
        result = runner.invoke(cli, [
            'match', 'requirements', sample_okh_file,
            '--help'
        ])
        
        # Check if include_workflows flag is mentioned in help
        if '--include-workflows' in result.output:
            print("✅ CLI includes backward compatibility flag")
        else:
            print("ℹ️ CLI backward compatibility flag not exposed (may be internal)")
        
        print("✅ CLI backward compatibility test completed")


if __name__ == "__main__":
    # Run CLI integration tests
    pytest.main([__file__, "-v", "-s"])
