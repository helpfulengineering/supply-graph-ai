import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.core.models.okh import OKHManifest, License, Person, DocumentRef, DocumentationType, PartSpec, Software
from src.core.models.package import BuildOptions
from src.core.services.package_service import PackageService
from src.core.packaging.builder import PackageBuilder
from src.core.packaging.file_resolver import FileResolver


class TestPackageIntegration:
    """Integration tests for package building using synthetic OKH data"""
    
    @pytest.fixture
    def sample_manifest_data(self):
        """Create sample OKH manifest data similar to synthetic data"""
        return {
            "okhv": "OKH-LOSHv1.0",
            "id": str(uuid4()),
            "title": "Arduino-based IoT Sensor Node",
            "repo": "https://github.com/example/arduino-iot-sensor",
            "version": "1.2.4",
            "license": {
                "hardware": "CERN-OHL-S-2.0",
                "documentation": "CC-BY-4.0",
                "software": "GPL-3.0-or-later"
            },
            "licensor": {
                "name": "John Doe",
                "email": "john@example.com",
                "affiliation": "Test Organization"
            },
            "documentation_language": "en",
            "function": "Environmental monitoring device with temperature, humidity, and air quality sensors",
            "description": "A test IoT sensor node for integration testing",
            "organization": {
                "name": "Test Organization",
                "url": "https://test.org",
                "email": "contact@test.org"
            },
            "development_stage": "production",
            "manufacturing_files": [
                {
                    "title": "Assembly Guide",
                    "path": "https://github.com/example/project/raw/main/docs/assembly_guide.pdf",
                    "type": "manufacturing-files",
                    "metadata": {"version": "v1.0"}
                },
                {
                    "title": "Bill of Materials",
                    "path": "https://github.com/example/project/raw/main/docs/bom.csv",
                    "type": "manufacturing-files",
                    "metadata": {"version": "v1.0"}
                }
            ],
            "design_files": [
                {
                    "title": "3D Model",
                    "path": "https://github.com/example/project/raw/main/models/housing.stl",
                    "type": "design-files",
                    "metadata": {"version": "v1.0"}
                }
            ],
            "making_instructions": [
                {
                    "title": "Assembly Instructions",
                    "path": "https://github.com/example/project/raw/main/docs/assembly.md",
                    "type": "manufacturing-files",
                    "metadata": {"version": "v1.0"}
                }
            ],
            "parts": [
                {
                    "name": "Housing",
                    "id": str(uuid4()),
                    "source": ["https://github.com/example/project/raw/main/models/housing.stl"],
                    "export": ["https://github.com/example/project/raw/main/exports/housing.step"],
                    "auxiliary": ["https://github.com/example/project/raw/main/docs/housing_notes.md"],
                    "image": "https://github.com/example/project/raw/main/images/housing.jpg",
                    "tsdc": ["3DP"],
                    "material": "PLA",
                    "outer_dimensions": {"length": 100, "width": 50, "height": 25},
                    "mass": 50.0,
                    "manufacturing_params": {"layer_height": "0.2mm", "infill": "20%"}
                }
            ],
            "software": [
                {
                    "release": "https://github.com/example/project/raw/main/software/firmware.bin",
                    "installation_guide": "https://github.com/example/project/raw/main/docs/firmware_install.md"
                }
            ],
            "bom": "https://github.com/example/project/raw/main/docs/bom.csv",
            "image": "https://github.com/example/project/raw/main/images/project.jpg"
        }
    
    @pytest.fixture
    def mock_http_responses(self):
        """Mock HTTP responses for file downloads"""
        responses = {
            "https://github.com/example/project/raw/main/docs/assembly_guide.pdf": b"PDF content",
            "https://github.com/example/project/raw/main/docs/bom.csv": b"CSV content",
            "https://github.com/example/project/raw/main/models/housing.stl": b"STL content",
            "https://github.com/example/project/raw/main/docs/assembly.md": b"Markdown content",
            "https://github.com/example/project/raw/main/exports/housing.step": b"STEP content",
            "https://github.com/example/project/raw/main/docs/housing_notes.md": b"Notes content",
            "https://github.com/example/project/raw/main/images/housing.jpg": b"Image content",
            "https://github.com/example/project/raw/main/software/firmware.bin": b"Firmware content",
            "https://github.com/example/project/raw/main/docs/firmware_install.md": b"Install guide content",
            "https://github.com/example/project/raw/main/images/project.jpg": b"Project image content"
        }
        return responses
    
    @pytest.mark.asyncio
    async def test_full_package_build(self, sample_manifest_data, mock_http_responses, tmp_path):
        """Test complete package building process"""
        # Create manifest from data
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        
        def mock_read():
            # Get the URL from the request context
            # This is a simplified approach for testing
            return b"Mock content"
        
        mock_response.read = AsyncMock(side_effect=mock_read)
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Create package service
            package_service = await PackageService.get_instance()
            
            # Build package with default options
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
        
        # Verify package structure
        package_path = Path(metadata.package_path)
        assert package_path.exists()
        
        # Check main manifest file
        manifest_file = package_path / "okh-manifest.json"
        assert manifest_file.exists()
        
        # Verify manifest content
        with open(manifest_file, 'r') as f:
            saved_manifest_data = json.load(f)
        assert saved_manifest_data["title"] == manifest.title
        assert saved_manifest_data["version"] == manifest.version
        
        # Check directory structure
        expected_dirs = [
            "design-files",
            "manufacturing-files",
            "making-instructions",
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
        
        # Check metadata files
        build_info = package_path / "metadata" / "build-info.json"
        file_manifest = package_path / "metadata" / "file-manifest.json"
        assert build_info.exists()
        assert file_manifest.exists()
        
        # Verify metadata content
        with open(build_info, 'r') as f:
            build_data = json.load(f)
        assert build_data["package_name"] == metadata.package_name
        assert build_data["version"] == metadata.version
        assert build_data["total_files"] == metadata.total_files
        
        with open(file_manifest, 'r') as f:
            file_data = json.load(f)
        assert file_data["total_files"] == metadata.total_files
        assert len(file_data["files"]) == metadata.total_files
    
    @pytest.mark.asyncio
    async def test_package_naming(self, sample_manifest_data):
        """Test package naming generation"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Test package name generation
        package_name = manifest.get_package_name()
        expected_name = "test-organization/arduino-based-iot-sensor-node"
        assert package_name == expected_name
        
        # Test package path generation
        package_path = manifest.get_package_path()
        expected_path = f"packages/{expected_name}/1.2.4"
        assert package_path == expected_path
    
    @pytest.mark.asyncio
    async def test_selective_file_inclusion(self, sample_manifest_data, tmp_path):
        """Test building packages with selective file inclusion"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.read = AsyncMock(return_value=b"Mock content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            package_service = await PackageService.get_instance()
            
            # Build package excluding design files and software
            options = BuildOptions(
                output_dir=str(tmp_path),
                include_design_files=False,
                include_software=False
            )
            metadata = await package_service.build_package_from_manifest(manifest, options)
        
        # Verify that design files and software directories are empty or don't exist
        package_path = Path(metadata.package_path)
        
        # Check that some files were still downloaded
        assert metadata.total_files > 0
        
        # Verify file inventory doesn't include excluded types
        for file_info in metadata.file_inventory:
            assert file_info.file_type not in ["design-files", "software"]
    
    @pytest.mark.asyncio
    async def test_package_verification(self, sample_manifest_data, tmp_path):
        """Test package verification functionality"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.read = AsyncMock(return_value=b"Mock content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            package_service = await PackageService.get_instance()
            
            # Build package
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
            
            # Verify package
            verification_results = await package_service.verify_package(
                metadata.package_name, metadata.version
            )
        
        # Check verification results
        assert verification_results["valid"] is True
        assert verification_results["package_name"] == metadata.package_name
        assert verification_results["version"] == metadata.version
        assert verification_results["total_files"] == metadata.total_files
        assert len(verification_results["missing_files"]) == 0
        assert len(verification_results["corrupted_files"]) == 0
    
    @pytest.mark.asyncio
    async def test_package_listing(self, sample_manifest_data, tmp_path):
        """Test package listing functionality"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.read = AsyncMock(return_value=b"Mock content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            package_service = await PackageService.get_instance()
            
            # Build package
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
            
            # List packages
            packages = await package_service.list_built_packages()
        
        # Check that our package is in the list
        assert len(packages) >= 1
        package_names = [pkg.package_name for pkg in packages]
        assert metadata.package_name in package_names
        
        # Find our specific package
        our_package = next(pkg for pkg in packages if pkg.package_name == metadata.package_name)
        assert our_package.version == metadata.version
        assert our_package.total_files == metadata.total_files
    
    @pytest.mark.asyncio
    async def test_package_deletion(self, sample_manifest_data, tmp_path):
        """Test package deletion functionality"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.read = AsyncMock(return_value=b"Mock content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            package_service = await PackageService.get_instance()
            
            # Build package
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
            
            # Verify package exists
            package_path = Path(metadata.package_path)
            assert package_path.exists()
            
            # Delete package
            success = await package_service.delete_package(
                metadata.package_name, metadata.version
            )
        
        # Check deletion result
        assert success is True
        assert not package_path.exists()
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_manifest(self, tmp_path):
        """Test error handling with invalid manifest"""
        package_service = await PackageService.get_instance()
        
        # Create invalid manifest data (missing required fields)
        invalid_data = {
            "title": "Invalid Manifest",
            # Missing required fields like version, license, etc.
        }
        
        with pytest.raises(ValueError, match="Invalid OKH manifest"):
            await package_service.build_package_from_dict(invalid_data)
    
    @pytest.mark.asyncio
    async def test_error_handling_network_failures(self, sample_manifest_data, tmp_path):
        """Test error handling with network failures"""
        manifest = OKHManifest.from_dict(sample_manifest_data)
        
        # Mock network failure
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            package_service = await PackageService.get_instance()
            
            # Build package - should handle network errors gracefully
            options = BuildOptions(output_dir=str(tmp_path))
            metadata = await package_service.build_package_from_manifest(manifest, options)
        
        # Package should still be created, but with fewer files
        package_path = Path(metadata.package_path)
        assert package_path.exists()
        
        # Manifest should still be saved
        manifest_file = package_path / "okh-manifest.json"
        assert manifest_file.exists()
        
        # Some files may have failed to download
        assert metadata.total_files >= 0  # At least manifest should be saved
