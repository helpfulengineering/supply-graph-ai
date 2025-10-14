"""
Tests for BOM CLI integration
"""
import pytest
import asyncio
import signal
from pathlib import Path
from click.testing import CliRunner
from src.cli.okh import okh_group
from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Test timed out")


def run_with_timeout(func, timeout_seconds=30):
    """Run a function with a timeout"""
    # Set up signal handler for timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        result = func()
        signal.alarm(0)  # Cancel the alarm
        return result
    except TimeoutError:
        raise
    finally:
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler


class TestBOMCLIIntegration:
    """Test BOM integration in CLI commands"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Use repo-local test-data directory for outputs"""
        base = Path("test-data/tmp_cli")
        # Ensure a clean directory per test
        if base.exists():
            for p in sorted(base.rglob('*'), reverse=True):
                try:
                    if p.is_file():
                        p.unlink()
                    else:
                        p.rmdir()
                except Exception:
                    pass
        base.mkdir(parents=True, exist_ok=True)
        return base

    @pytest.fixture(autouse=True)
    def stub_network(self, monkeypatch):
        """Stub URL routing and GitHub extraction to avoid network calls and hangs"""
        # Stub URLRouter
        from src.core.generation.url_router import URLRouter
        monkeypatch.setattr(URLRouter, "validate_url", lambda *_args, **_kw: True)
        monkeypatch.setattr(URLRouter, "detect_platform", lambda *_args, **_kw: PlatformType.GITHUB)

        # Stub GitHubExtractor.extract_project to return small deterministic data
        from src.core.generation.platforms.github import GitHubExtractor

        async def _fake_extract(_self, url: str) -> ProjectData:
            readme = """
            # Stub Project

            ## Materials
            * 1 head (head.stl)
            * 2 tube (tube.stl)
            """
            bom_md = """
            # Bill of Materials
            * 3 M3 screw
            * 1 Plate
            """
            return ProjectData(
                platform=PlatformType.GITHUB,
                url=url,
                metadata={"name": "stub_project", "description": "stub"},
                files=[
                    FileInfo(path="README.md", size=len(readme), content=readme, file_type="markdown"),
                    FileInfo(path="docs/0_bill_of_materials.md", size=len(bom_md), content=bom_md, file_type="markdown"),
                ],
                documentation=[
                    DocumentInfo(title="README", path="README.md", content=readme, doc_type="readme")
                ],
                raw_content={"README.md": readme}
            )

        monkeypatch.setattr(GitHubExtractor, "extract_project", _fake_extract)
    
    def test_generate_from_url_with_bom_export(self, temp_output_dir):
        """Test generate-from-url command with BOM export"""
        def run_test():
            runner = CliRunner()
            
            # Test with a (stubbed) GitHub URL and BOM export
            result = runner.invoke(okh_group, [
                'generate-from-url',
                'https://github.com/rwb27/openflexure_microscope',
                '--output', str(temp_output_dir),
                '--bom-formats', 'json',
                '--bom-formats', 'md',
                '--bom-formats', 'csv',
                '--no-review'
            ])
            
            # Should succeed
            assert result.exit_code == 0
            
            # Verify output files were created
            assert (temp_output_dir / "manifest.okh.json").exists()
            assert (temp_output_dir / "bom" / "bom.json").exists()
            assert (temp_output_dir / "bom" / "bom.md").exists()
            assert (temp_output_dir / "bom" / "bom.csv").exists()
            
            print(f"✅ CLI BOM export test:")
            print(f"  Exit code: {result.exit_code}")
            print(f"  Output directory: {temp_output_dir}")
            print(f"  Files created: {list(temp_output_dir.rglob('*'))}")
            
            return result
        
        # Run with 30 second timeout
        result = run_with_timeout(run_test, timeout_seconds=30)
    
    def test_generate_from_url_without_output(self):
        """Test generate-from-url command without output directory"""
        def run_test():
            runner = CliRunner()
            
            # Test without --output flag (should not export to built directory)
            result = runner.invoke(okh_group, [
                'generate-from-url',
                'https://github.com/rwb27/openflexure_microscope',
                '--format', 'okh',
                '--no-review'
            ])
            
            # Should succeed
            assert result.exit_code == 0
            
            # Should output manifest to stdout (check for key fields)
            assert "Generated OKH manifest" in result.output
            assert "Generation confidence" in result.output
            
            print(f"✅ CLI without output test:")
            print(f"  Exit code: {result.exit_code}")
            print(f"  Output length: {len(result.output)} characters")
            print(f"  Contains BOM: {'bom' in result.output}")
            
            return result
        
        # Run with 30 second timeout
        result = run_with_timeout(run_test, timeout_seconds=30)
    
    def test_generate_from_url_bom_formats_validation(self, temp_output_dir):
        """Test BOM formats validation"""
        runner = CliRunner()
        
        # Test with invalid BOM format
        result = runner.invoke(okh_group, [
            'generate-from-url',
            'https://github.com/rwb27/openflexure_microscope',
            '--output', str(temp_output_dir),
            '--bom-formats', 'invalid_format',
            '--no-review'
        ])
        
        # Should fail with validation error
        assert result.exit_code != 0
        assert "invalid value" in result.output.lower()
        
        print(f"✅ BOM formats validation test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Error message: {result.output}")
    
    def test_generate_from_url_default_bom_formats(self, temp_output_dir):
        """Test default BOM formats when not specified"""
        runner = CliRunner()
        
        # Test with output but no BOM formats specified
        result = runner.invoke(okh_group, [
            'generate-from-url',
            'https://github.com/rwb27/openflexure_microscope',
            '--output', str(temp_output_dir),
            '--no-review'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Should create default BOM formats (json, md)
        assert (temp_output_dir / "bom" / "bom.json").exists()
        assert (temp_output_dir / "bom" / "bom.md").exists()
        
        # CSV might be created as part of the default export
        
        print(f"✅ Default BOM formats test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  JSON exists: {(temp_output_dir / 'bom' / 'bom.json').exists()}")
        print(f"  Markdown exists: {(temp_output_dir / 'bom' / 'bom.md').exists()}")
        print(f"  CSV exists: {(temp_output_dir / 'bom' / 'bom.csv').exists()}")
    
    def test_generate_from_url_all_bom_formats(self, temp_output_dir):
        """Test all BOM formats"""
        runner = CliRunner()
        
        # Test with all BOM formats
        result = runner.invoke(okh_group, [
            'generate-from-url',
            'https://github.com/rwb27/openflexure_microscope',
            '--output', str(temp_output_dir),
            '--bom-formats', 'json',
            '--bom-formats', 'md',
            '--bom-formats', 'csv',
            '--bom-formats', 'components',
            '--no-review'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Should create all BOM formats
        assert (temp_output_dir / "bom" / "bom.json").exists()
        assert (temp_output_dir / "bom" / "bom.md").exists()
        assert (temp_output_dir / "bom" / "bom.csv").exists()
        assert (temp_output_dir / "bom" / "components").exists()
        
        # Should have individual component files
        components_dir = temp_output_dir / "bom" / "components"
        component_files = list(components_dir.glob("*.json"))
        assert len(component_files) > 0
        
        print(f"✅ All BOM formats test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Component files: {len(component_files)}")
        print(f"  Component files: {[f.name for f in component_files]}")
    
    def test_generate_from_url_help_output(self):
        """Test help output includes BOM options"""
        runner = CliRunner()
        
        # Test help output
        result = runner.invoke(okh_group, [
            'generate-from-url',
            '--help'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Should include BOM-related options
        assert "--output" in result.output
        assert "--bom-formats" in result.output
        assert "json" in result.output
        assert "md" in result.output
        assert "csv" in result.output
        assert "components" in result.output
        
        print(f"✅ Help output test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Contains --output: {'--output' in result.output}")
        print(f"  Contains --bom-formats: {'--bom-formats' in result.output}")
    
    def test_generate_from_url_error_handling(self, temp_output_dir):
        """Test error handling in CLI"""
        runner = CliRunner()
        
        # Test with invalid BOM format (this should fail validation)
        result = runner.invoke(okh_group, [
            'generate-from-url',
            'https://github.com/test/repo',
            '--output', str(temp_output_dir),
            '--bom-formats', 'invalid_format',
            '--no-review'
        ])
        
        # Should fail with validation error
        assert result.exit_code != 0
        assert "invalid value" in result.output.lower()
        
        # Should not create output files
        assert not (temp_output_dir / "manifest.okh.json").exists()
        
        print(f"✅ Error handling test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Error message: {result.output[:200]}...")
    
    def test_generate_from_url_output_directory_creation(self, temp_output_dir):
        """Test that output directory is created if it doesn't exist"""
        # Create a subdirectory that doesn't exist
        sub_dir = temp_output_dir / "subdir" / "nested"
        
        runner = CliRunner()
        
        # Test with non-existent output directory
        result = runner.invoke(okh_group, [
            'generate-from-url',
            'https://github.com/rwb27/openflexure_microscope',
            '--output', str(sub_dir),
            '--no-review'
        ])
        
        # Should succeed and create directory
        assert result.exit_code == 0
        assert sub_dir.exists()
        assert (sub_dir / "manifest.okh.json").exists()
        assert (sub_dir / "bom" / "bom.json").exists()
        
        print(f"✅ Output directory creation test:")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Directory created: {sub_dir.exists()}")
        print(f"  Manifest exists: {(sub_dir / 'manifest.okh.json').exists()}")
