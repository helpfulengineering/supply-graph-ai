import pytest
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from src.core.models.package import (
    BuildOptions, PackageMetadata, FileInfo, ResolvedFile, 
    DownloadOptions, calculate_file_checksum, sanitize_package_name
)


class TestBuildOptions:
    """Test BuildOptions model"""
    
    def test_default_options(self):
        """Test default build options"""
        options = BuildOptions()
        
        assert options.include_design_files is True
        assert options.include_manufacturing_files is True
        assert options.include_making_instructions is True
        assert options.include_software is True
        assert options.include_parts is True
        assert options.include_operating_instructions is True
        assert options.verify_downloads is True
        assert options.max_concurrent_downloads == 5
        assert options.output_dir is None
    
    def test_custom_options(self):
        """Test custom build options"""
        options = BuildOptions(
            include_design_files=False,
            include_software=False,
            max_concurrent_downloads=10,
            output_dir="/custom/path"
        )
        
        assert options.include_design_files is False
        assert options.include_software is False
        assert options.max_concurrent_downloads == 10
        assert options.output_dir == "/custom/path"
    
    def test_to_dict(self):
        """Test serialization to dictionary"""
        options = BuildOptions(include_design_files=False, max_concurrent_downloads=3)
        data = options.to_dict()
        
        assert data["include_design_files"] is False
        assert data["max_concurrent_downloads"] == 3
        assert "include_manufacturing_files" in data
    
    def test_from_dict(self):
        """Test deserialization from dictionary"""
        data = {
            "include_design_files": False,
            "include_software": False,
            "max_concurrent_downloads": 8,
            "output_dir": "/test/path"
        }
        
        options = BuildOptions.from_dict(data)
        
        assert options.include_design_files is False
        assert options.include_software is False
        assert options.max_concurrent_downloads == 8
        assert options.output_dir == "/test/path"


class TestFileInfo:
    """Test FileInfo model"""
    
    def test_file_info_creation(self):
        """Test FileInfo creation"""
        now = datetime.now()
        file_info = FileInfo(
            original_url="https://example.com/file.pdf",
            local_path="/local/path/file.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=now,
            file_type="manufacturing-files",
            part_name="housing"
        )
        
        assert file_info.original_url == "https://example.com/file.pdf"
        assert file_info.local_path == "/local/path/file.pdf"
        assert file_info.content_type == "application/pdf"
        assert file_info.size_bytes == 1024
        assert file_info.checksum_sha256 == "abc123"
        assert file_info.downloaded_at == now
        assert file_info.file_type == "manufacturing-files"
        assert file_info.part_name == "housing"
    
    def test_file_info_to_dict(self):
        """Test FileInfo serialization"""
        now = datetime.now()
        file_info = FileInfo(
            original_url="https://example.com/file.pdf",
            local_path="/local/path/file.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=now,
            file_type="manufacturing-files"
        )
        
        data = file_info.to_dict()
        
        assert data["original_url"] == "https://example.com/file.pdf"
        assert data["local_path"] == "/local/path/file.pdf"
        assert data["content_type"] == "application/pdf"
        assert data["size_bytes"] == 1024
        assert data["checksum_sha256"] == "abc123"
        assert data["downloaded_at"] == now.isoformat()
        assert data["file_type"] == "manufacturing-files"
        assert data["part_name"] is None
    
    def test_file_info_from_dict(self):
        """Test FileInfo deserialization"""
        now = datetime.now()
        data = {
            "original_url": "https://example.com/file.pdf",
            "local_path": "/local/path/file.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "checksum_sha256": "abc123",
            "downloaded_at": now.isoformat(),
            "file_type": "manufacturing-files",
            "part_name": "housing"
        }
        
        file_info = FileInfo.from_dict(data)
        
        assert file_info.original_url == "https://example.com/file.pdf"
        assert file_info.local_path == "/local/path/file.pdf"
        assert file_info.content_type == "application/pdf"
        assert file_info.size_bytes == 1024
        assert file_info.checksum_sha256 == "abc123"
        assert file_info.downloaded_at == now
        assert file_info.file_type == "manufacturing-files"
        assert file_info.part_name == "housing"


class TestPackageMetadata:
    """Test PackageMetadata model"""
    
    def test_package_metadata_creation(self):
        """Test PackageMetadata creation"""
        manifest_id = uuid4()
        now = datetime.now()
        options = BuildOptions()
        
        file_info = FileInfo(
            original_url="https://example.com/file.pdf",
            local_path="/local/path/file.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=now,
            file_type="manufacturing-files"
        )
        
        metadata = PackageMetadata(
            package_name="org/project",
            version="1.0.0",
            okh_manifest_id=manifest_id,
            build_timestamp=now,
            ome_version="1.0.0",
            total_files=1,
            total_size_bytes=1024,
            file_inventory=[file_info],
            build_options=options,
            package_path="/packages/org/project/1.0.0"
        )
        
        assert metadata.package_name == "org/project"
        assert metadata.version == "1.0.0"
        assert metadata.okh_manifest_id == manifest_id
        assert metadata.build_timestamp == now
        assert metadata.ome_version == "1.0.0"
        assert metadata.total_files == 1
        assert metadata.total_size_bytes == 1024
        assert len(metadata.file_inventory) == 1
        assert metadata.build_options == options
        assert metadata.package_path == "/packages/org/project/1.0.0"
    
    def test_package_metadata_serialization(self):
        """Test PackageMetadata serialization and deserialization"""
        manifest_id = uuid4()
        now = datetime.now()
        options = BuildOptions(include_design_files=False)
        
        file_info = FileInfo(
            original_url="https://example.com/file.pdf",
            local_path="/local/path/file.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=now,
            file_type="manufacturing-files"
        )
        
        metadata = PackageMetadata(
            package_name="org/project",
            version="1.0.0",
            okh_manifest_id=manifest_id,
            build_timestamp=now,
            ome_version="1.0.0",
            total_files=1,
            total_size_bytes=1024,
            file_inventory=[file_info],
            build_options=options,
            package_path="/packages/org/project/1.0.0"
        )
        
        # Test serialization
        data = metadata.to_dict()
        
        assert data["package_name"] == "org/project"
        assert data["version"] == "1.0.0"
        assert data["okh_manifest_id"] == str(manifest_id)
        assert data["build_timestamp"] == now.isoformat()
        assert data["ome_version"] == "1.0.0"
        assert data["total_files"] == 1
        assert data["total_size_bytes"] == 1024
        assert len(data["file_inventory"]) == 1
        assert data["build_options"]["include_design_files"] is False
        assert data["package_path"] == "/packages/org/project/1.0.0"
        
        # Test deserialization
        restored_metadata = PackageMetadata.from_dict(data)
        
        assert restored_metadata.package_name == metadata.package_name
        assert restored_metadata.version == metadata.version
        assert restored_metadata.okh_manifest_id == metadata.okh_manifest_id
        assert restored_metadata.build_timestamp == metadata.build_timestamp
        assert restored_metadata.ome_version == metadata.ome_version
        assert restored_metadata.total_files == metadata.total_files
        assert restored_metadata.total_size_bytes == metadata.total_size_bytes
        assert len(restored_metadata.file_inventory) == len(metadata.file_inventory)
        assert restored_metadata.build_options.include_design_files == metadata.build_options.include_design_files
        assert restored_metadata.package_path == metadata.package_path


class TestResolvedFile:
    """Test ResolvedFile model"""
    
    def test_successful_resolution(self):
        """Test successful file resolution"""
        file_info = FileInfo(
            original_url="https://example.com/file.pdf",
            local_path="/local/path/file.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="abc123",
            downloaded_at=datetime.now(),
            file_type="manufacturing-files"
        )
        
        resolved = ResolvedFile(success=True, file_info=file_info)
        
        assert resolved.success is True
        assert resolved.file_info == file_info
        assert resolved.error_message is None
        assert resolved.retry_count == 0
    
    def test_failed_resolution(self):
        """Test failed file resolution"""
        resolved = ResolvedFile(
            success=False,
            error_message="Network timeout",
            retry_count=3
        )
        
        assert resolved.success is False
        assert resolved.file_info is None
        assert resolved.error_message == "Network timeout"
        assert resolved.retry_count == 3


class TestDownloadOptions:
    """Test DownloadOptions model"""
    
    def test_default_download_options(self):
        """Test default download options"""
        options = DownloadOptions()
        
        assert options.max_retries == 3
        assert options.timeout_seconds == 30
        assert options.verify_ssl is True
        assert options.follow_redirects is True
        assert options.user_agent == "OME-Package-Builder/1.0"
    
    def test_custom_download_options(self):
        """Test custom download options"""
        options = DownloadOptions(
            max_retries=5,
            timeout_seconds=60,
            verify_ssl=False,
            user_agent="Custom-Agent/1.0"
        )
        
        assert options.max_retries == 5
        assert options.timeout_seconds == 60
        assert options.verify_ssl is False
        assert options.user_agent == "Custom-Agent/1.0"


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_sanitize_package_name(self):
        """Test package name sanitization"""
        # Test basic sanitization
        assert sanitize_package_name("My Project") == "my-project"
        assert sanitize_package_name("Arduino-based IoT Sensor") == "arduino-based-iot-sensor"
        
        # Test special characters
        assert sanitize_package_name("Project@#$%") == "project"
        assert sanitize_package_name("Test/Project\\Name") == "test-project-name"
        
        # Test multiple hyphens
        assert sanitize_package_name("Test---Project") == "test-project"
        
        # Test leading/trailing hyphens
        assert sanitize_package_name("-Test-Project-") == "test-project"
    
    def test_calculate_file_checksum(self, tmp_path):
        """Test file checksum calculation"""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)
        
        # Calculate checksum
        checksum = calculate_file_checksum(test_file)
        
        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)
        
        # Verify it's deterministic
        checksum2 = calculate_file_checksum(test_file)
        assert checksum == checksum2
