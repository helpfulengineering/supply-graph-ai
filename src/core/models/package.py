import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class BuildOptions:
    """Options for building OKH packages"""

    include_design_files: bool = True
    include_manufacturing_files: bool = True
    include_making_instructions: bool = True
    include_software: bool = True
    include_parts: bool = True
    include_operating_instructions: bool = True
    include_quality_instructions: bool = True
    include_risk_assessment: bool = True
    include_schematics: bool = True
    include_tool_settings: bool = True
    verify_downloads: bool = True
    max_concurrent_downloads: int = 5
    output_dir: Optional[str] = None  # Defaults to packages/ in repo root

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization"""
        return {
            "include_design_files": self.include_design_files,
            "include_manufacturing_files": self.include_manufacturing_files,
            "include_making_instructions": self.include_making_instructions,
            "include_software": self.include_software,
            "include_parts": self.include_parts,
            "include_operating_instructions": self.include_operating_instructions,
            "include_quality_instructions": self.include_quality_instructions,
            "include_risk_assessment": self.include_risk_assessment,
            "include_schematics": self.include_schematics,
            "include_tool_settings": self.include_tool_settings,
            "verify_downloads": self.verify_downloads,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "output_dir": self.output_dir,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildOptions":
        """Create from dictionary"""
        return cls(
            include_design_files=data.get("include_design_files", True),
            include_manufacturing_files=data.get("include_manufacturing_files", True),
            include_making_instructions=data.get("include_making_instructions", True),
            include_software=data.get("include_software", True),
            include_parts=data.get("include_parts", True),
            include_operating_instructions=data.get(
                "include_operating_instructions", True
            ),
            include_quality_instructions=data.get("include_quality_instructions", True),
            include_risk_assessment=data.get("include_risk_assessment", True),
            include_schematics=data.get("include_schematics", True),
            include_tool_settings=data.get("include_tool_settings", True),
            verify_downloads=data.get("verify_downloads", True),
            max_concurrent_downloads=data.get("max_concurrent_downloads", 5),
            output_dir=data.get("output_dir"),
        )


@dataclass
class FileInfo:
    """Information about a downloaded file"""

    original_url: str
    local_path: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    downloaded_at: datetime
    file_type: str  # e.g., "design-files", "manufacturing-files", etc.
    part_name: Optional[str] = None  # For part-specific files

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "original_url": self.original_url,
            "local_path": self.local_path,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "downloaded_at": self.downloaded_at.isoformat(),
            "file_type": self.file_type,
            "part_name": self.part_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileInfo":
        """Create from dictionary"""
        return cls(
            original_url=data["original_url"],
            local_path=data["local_path"],
            content_type=data["content_type"],
            size_bytes=data["size_bytes"],
            checksum_sha256=data["checksum_sha256"],
            downloaded_at=datetime.fromisoformat(data["downloaded_at"]),
            file_type=data["file_type"],
            part_name=data.get("part_name"),
        )


@dataclass
class PackageMetadata:
    """Metadata for a built OKH package"""

    package_name: str  # e.g., "org/arduino-iot-sensor"
    version: str  # e.g., "1.2.4"
    okh_manifest_id: UUID
    build_timestamp: datetime
    ome_version: str
    total_files: int
    total_size_bytes: int
    file_inventory: List[FileInfo]
    build_options: BuildOptions
    package_path: str  # Path to the built package

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "package_name": self.package_name,
            "version": self.version,
            "okh_manifest_id": str(self.okh_manifest_id),
            "build_timestamp": self.build_timestamp.isoformat(),
            "ome_version": self.ome_version,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "file_inventory": [f.to_dict() for f in self.file_inventory],
            "build_options": self.build_options.to_dict(),
            "package_path": self.package_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageMetadata":
        """Create from dictionary"""
        return cls(
            package_name=data["package_name"],
            version=data["version"],
            okh_manifest_id=UUID(data["okh_manifest_id"]),
            build_timestamp=datetime.fromisoformat(data["build_timestamp"]),
            ome_version=data["ome_version"],
            total_files=data["total_files"],
            total_size_bytes=data["total_size_bytes"],
            file_inventory=[FileInfo.from_dict(f) for f in data["file_inventory"]],
            build_options=BuildOptions.from_dict(data["build_options"]),
            package_path=data["package_path"],
        )


@dataclass
class ResolvedFile:
    """Result of file resolution and download"""

    success: bool
    file_info: Optional[FileInfo] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "file_info": self.file_info.to_dict() if self.file_info else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


@dataclass
class DownloadOptions:
    """Options for file downloading"""

    max_retries: int = 3
    timeout_seconds: int = 120
    verify_ssl: bool = True
    follow_redirects: bool = True
    user_agent: str = "OME-Package-Builder/1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "verify_ssl": self.verify_ssl,
            "follow_redirects": self.follow_redirects,
            "user_agent": self.user_agent,
        }


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def sanitize_package_name(name: str) -> str:
    """Sanitize a name for use in package paths"""
    # Convert to lowercase, replace spaces and special chars with hyphens
    import re

    sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", name.lower())
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing hyphens
    return sanitized.strip("-")
