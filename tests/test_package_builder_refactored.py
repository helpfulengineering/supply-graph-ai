import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.core.models.okh import OKHManifest, License, Person
from src.core.models.package import BuildOptions
from src.core.packaging.builder import PackageBuilder


class TestPackageBuilderRefactored:
    """Test the refactored PackageBuilder with decoupled functionality"""
    
    @pytest.fixture
    def sample_manifest(self):
        """Create a minimal OKH manifest for testing"""
        return OKHManifest(
            title="Test Project",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function"
        )
    
    @pytest.fixture
    def package_builder(self):
        """Create a PackageBuilder instance"""
        return PackageBuilder()
    
    @pytest.mark.asyncio
    async def test_create_directory_structure(self, package_builder, sample_manifest, tmp_path):
        """Test that directory structure is created correctly"""
        package_path = tmp_path / "test-package" / "1.0.0"
        
        # Create directory structure
        await package_builder._create_directory_structure(package_path)
        
        # Verify all expected directories exist
        expected_dirs = [
            "design-files",
            "manufacturing-files", 
            "making-instructions",
            "operating-instructions",
            "quality-instructions",
            "risk-assessment",
            "software",
            "tool-settings",
            "schematics",
            "parts",
            "metadata"
        ]
        
        for dir_name in expected_dirs:
            assert (package_path / dir_name).exists()
            assert (package_path / dir_name).is_dir()
    
    @pytest.mark.asyncio
    async def test_save_manifest(self, package_builder, sample_manifest, tmp_path):
        """Test that manifest is saved correctly"""
        package_path = tmp_path / "test-package" / "1.0.0"
        package_path.mkdir(parents=True)
        
        manifest_path = package_path / "okh-manifest.json"
        
        # Save manifest
        await package_builder._save_manifest(sample_manifest, manifest_path)
        
        # Verify manifest file exists and contains correct data
        assert manifest_path.exists()
        
        import json
        with open(manifest_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["title"] == sample_manifest.title
        assert saved_data["version"] == sample_manifest.version
        assert saved_data["function"] == sample_manifest.function
    
    def test_generate_package_name(self, package_builder, sample_manifest):
        """Test package name generation"""
        package_name = package_builder._generate_package_name(sample_manifest)
        expected_name = "community/test-project"
        assert package_name == expected_name
    
    def test_generate_package_name_with_organization(self, package_builder):
        """Test package name generation with organization"""
        from src.core.models.okh import Organization
        
        manifest = OKHManifest(
            title="Test Project",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function",
            organization=Organization(name="Test Organization")
        )
        
        package_name = package_builder._generate_package_name(manifest)
        expected_name = "test-organization/test-project"
        assert package_name == expected_name
    
    @pytest.mark.asyncio
    async def test_build_package_structure_only(self, package_builder, sample_manifest, tmp_path):
        """Test building package structure without downloading files"""
        output_dir = tmp_path / "packages"
        options = BuildOptions(output_dir=str(output_dir))
        
        # Mock the file resolver to avoid actual downloads
        with patch.object(package_builder, 'file_resolver') as mock_resolver:
            mock_resolver.__aenter__ = AsyncMock(return_value=mock_resolver)
            mock_resolver.__aexit__ = AsyncMock(return_value=None)
            
            # Build package structure only
            package_path = output_dir / "community" / "test-project" / "1.0.0"
            await package_builder._create_directory_structure(package_path)
            await package_builder._save_manifest(sample_manifest, package_path / "okh-manifest.json")
        
        # Verify package structure was created
        assert package_path.exists()
        assert (package_path / "okh-manifest.json").exists()
        
        # Verify all expected directories exist
        expected_dirs = [
            "design-files", "manufacturing-files", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "metadata"
        ]
        
        for dir_name in expected_dirs:
            assert (package_path / dir_name).exists()
            assert (package_path / dir_name).is_dir()
    
    def test_sanitize_part_name(self, package_builder):
        """Test part name sanitization"""
        assert package_builder._sanitize_part_name("Main Body") == "main-body"
        assert package_builder._sanitize_part_name("Stage Assembly") == "stage-assembly"
        assert package_builder._sanitize_part_name("Part@#$%") == "part"
    
    def test_guess_extension_from_url(self, package_builder):
        """Test extension guessing from URLs"""
        assert package_builder._guess_extension_from_url("https://example.com/file.pdf") == ".pdf"
        assert package_builder._guess_extension_from_url("https://example.com/file.stl") == ".stl"
        assert package_builder._guess_extension_from_url("https://example.com/file") == ".bin"
    
    @pytest.mark.asyncio
    async def test_generate_package_metadata(self, package_builder, sample_manifest, tmp_path):
        """Test package metadata generation"""
        package_path = tmp_path / "test-package" / "1.0.0"
        package_name = "community/test-project"
        
        # Create some mock file info
        from src.core.models.package import FileInfo
        from datetime import datetime
        
        file_info = FileInfo(
            original_url="https://example.com/test.pdf",
            local_path=str(package_path / "test.pdf"),
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=datetime.now(),
            file_type="manufacturing-files"
        )
        
        options = BuildOptions()
        metadata = await package_builder._generate_package_metadata(
            sample_manifest, package_path, package_name, [file_info], options
        )
        
        assert metadata.package_name == package_name
        assert metadata.version == sample_manifest.version
        assert metadata.okh_manifest_id == sample_manifest.id
        assert metadata.total_files == 1
        assert metadata.total_size_bytes == 1024
        assert len(metadata.file_inventory) == 1
        assert metadata.package_path == str(package_path)
