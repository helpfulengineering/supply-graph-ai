import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.core.models.okh import OKHManifest, License, Person
from src.core.models.package import BuildOptions
from src.core.services.package_service import PackageService


class TestSimplePackageBuild:
    """Test simple package building with mocked downloads"""
    
    @pytest.fixture
    def simple_manifest(self):
        """Create a simple manifest with minimal files"""
        return OKHManifest(
            title="Simple Test Project",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Simple test function"
        )
    
    @pytest.mark.asyncio
    async def test_build_package_structure_only(self, simple_manifest, tmp_path):
        """Test building package structure without any file downloads"""
        package_service = await PackageService.get_instance()
        
        # Build with no files to download
        options = BuildOptions(output_dir=str(tmp_path))
        metadata = await package_service.build_package_from_manifest(simple_manifest, options)
        
        # Verify package was created
        package_path = Path(metadata.package_path)
        assert package_path.exists()
        
        # Verify manifest was saved
        manifest_file = package_path / "okh-manifest.json"
        assert manifest_file.exists()
        
        # Verify directory structure
        expected_dirs = [
            "design-files", "manufacturing-files", "making-instructions",
            "operating-instructions", "quality-instructions", "risk-assessment",
            "software", "tool-settings", "schematics", "parts", "metadata"
        ]
        
        for dir_name in expected_dirs:
            assert (package_path / dir_name).exists()
            assert (package_path / dir_name).is_dir()
        
        # Verify metadata files
        build_info = package_path / "metadata" / "build-info.json"
        file_manifest = package_path / "metadata" / "file-manifest.json"
        assert build_info.exists()
        assert file_manifest.exists()
        
        # Verify metadata content
        assert metadata.package_name == "community/simple-test-project"
        assert metadata.version == "1.0.0"
        assert metadata.total_files == 0  # No files to download
        assert metadata.total_size_bytes == 0
    
    @pytest.mark.asyncio
    async def test_build_package_with_mock_downloads(self, tmp_path):
        """Test building package with mocked successful downloads"""
        # Create manifest with some files
        from src.core.models.okh import DocumentRef, DocumentationType
        
        manifest = OKHManifest(
            title="Test Project with Files",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function",
            manufacturing_files=[
                DocumentRef(
                    title="Test Document",
                    path="https://example.com/test.pdf",
                    type=DocumentationType.MANUFACTURING_FILES
                )
            ]
        )
        
        package_service = await PackageService.get_instance()
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.read = AsyncMock(return_value=b"Test PDF content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
        
        # Verify package was created
        package_path = Path(metadata.package_path)
        assert package_path.exists()
        
        # Verify file was downloaded
        downloaded_file = package_path / "manufacturing-files" / "test.pdf"
        assert downloaded_file.exists()
        assert downloaded_file.read_bytes() == b"Test PDF content"
        
        # Verify metadata
        assert metadata.total_files == 1
        assert metadata.total_size_bytes > 0
        assert len(metadata.file_inventory) == 1
        
        file_info = metadata.file_inventory[0]
        assert file_info.original_url == "https://example.com/test.pdf"
        assert file_info.local_path == str(downloaded_file)
        assert file_info.size_bytes == len(b"Test PDF content")
    
    @pytest.mark.asyncio
    async def test_build_package_with_failed_downloads(self, tmp_path):
        """Test building package when some downloads fail"""
        from src.core.models.okh import DocumentRef, DocumentationType
        
        manifest = OKHManifest(
            title="Test Project with Failed Downloads",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function",
            manufacturing_files=[
                DocumentRef(
                    title="Good Document",
                    path="https://example.com/good.pdf",
                    type=DocumentationType.MANUFACTURING_FILES
                ),
                DocumentRef(
                    title="Bad Document",
                    path="https://example.com/bad.pdf",
                    type=DocumentationType.MANUFACTURING_FILES
                )
            ]
        )
        
        package_service = await PackageService.get_instance()
        
        # Mock mixed responses: one success, one failure
        def mock_responses():
            # First call succeeds
            success_response = AsyncMock()
            success_response.status = 200
            success_response.headers = {"content-type": "application/pdf"}
            success_response.read = AsyncMock(return_value=b"Good PDF content")
            yield success_response
            
            # Second call fails
            fail_response = AsyncMock()
            fail_response.status = 404
            yield fail_response
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.side_effect = mock_responses()
            
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
        
        # Verify package was still created
        package_path = Path(metadata.package_path)
        assert package_path.exists()
        
        # Verify only the successful file was downloaded
        good_file = package_path / "manufacturing-files" / "good.pdf"
        bad_file = package_path / "manufacturing-files" / "bad.pdf"
        
        assert good_file.exists()
        assert not bad_file.exists()
        
        # Verify metadata reflects partial success
        assert metadata.total_files == 1  # Only one successful download
        assert len(metadata.file_inventory) == 1
