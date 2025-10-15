"""
Layer 1: Direct Matcher for OKH manifest generation.

This module provides direct field mapping from platform metadata to manifest fields.
It implements high-confidence mappings for fields that can be directly extracted
from platform APIs and file structures.
"""

import re
from typing import Dict, Any, Optional

from ..models import ProjectData, FieldGeneration, GenerationLayer, PlatformType
from .base import BaseGenerationLayer, LayerResult


class DirectMatcher(BaseGenerationLayer):
    """Direct field mapping matcher for Layer 1 generation"""
    
    def __init__(self):
        super().__init__(GenerationLayer.DIRECT)
        self._confidence_threshold = 0.8
    
    async def process(self, project_data: ProjectData) -> LayerResult:
        """Process project data using direct matching"""
        result = LayerResult(self.layer_type)
        
        try:
            # Generate fields using existing logic
            fields = self.generate_fields(project_data)
            
            # Convert to LayerResult format
            for field_name, field_gen in fields.items():
                result.add_field(
                    field_name,
                    field_gen.value,
                    field_gen.confidence,
                    field_gen.generation_method,
                    field_gen.raw_source
                )
            
            result.add_log(f"Direct layer processed {len(fields)} fields")
            
        except Exception as e:
            result.add_error(f"Direct processing failed: {str(e)}")
        
        return result
    
    def generate_fields(self, project_data: ProjectData) -> Dict[str, FieldGeneration]:
        """
        Generate manifest fields using direct mapping from platform metadata.
        
        Args:
            project_data: Raw project data from platform
            
        Returns:
            Dictionary mapping field names to FieldGeneration objects
        """
        fields = {}
        
        # Extract metadata-based fields
        fields.update(self._extract_metadata_fields(project_data))
        
        # Extract file-based fields
        fields.update(self._extract_file_fields(project_data))
        
        return fields
    
    def _extract_metadata_fields(self, project_data: ProjectData) -> Dict[str, FieldGeneration]:
        """Extract fields directly from platform metadata"""
        fields = {}
        metadata = project_data.metadata
        
        # Title mapping
        if "name" in metadata and metadata["name"]:
            fields["title"] = FieldGeneration(
                value=metadata["name"],
                confidence=0.95,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.name"
            )
        
        # Description mapping
        if "description" in metadata and metadata["description"]:
            fields["description"] = FieldGeneration(
                value=metadata["description"],
                confidence=0.95,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.description"
            )
        
        # Repository URL mapping
        repo_url = self._get_repo_url(project_data)
        if repo_url:
            fields["repo"] = FieldGeneration(
                value=repo_url,
                confidence=0.95,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.html_url" if "html_url" in metadata else "url"
            )
        
        # License from metadata
        license_value = self._extract_license_from_metadata(metadata)
        if license_value:
            fields["license"] = FieldGeneration(
                value=license_value,
                confidence=0.9,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.license"
            )
        
        # Version from metadata
        version_value = self._extract_version_from_metadata(metadata)
        if version_value:
            fields["version"] = FieldGeneration(
                value=version_value,
                confidence=0.9,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.version"
            )
        else:
            # Fallback version
            fields["version"] = FieldGeneration(
                value="1.0.0",
                confidence=0.1,
                source_layer=GenerationLayer.DIRECT,
                generation_method="fallback",
                raw_source="no_version_found"
            )
        
        return fields
    
    def _extract_file_fields(self, project_data: ProjectData) -> Dict[str, FieldGeneration]:
        """Extract fields from project files"""
        fields = {}
        
        # README content
        readme_content = self._find_readme_content(project_data.files)
        if readme_content:
            fields["readme"] = FieldGeneration(
                value=readme_content,
                confidence=0.9,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="README.md"
            )
        
        # License from file (if not already found in metadata)
        if "license" not in fields:
            license_from_file = self._extract_license_from_files(project_data.files)
            if license_from_file:
                fields["license"] = FieldGeneration(
                    value=license_from_file,
                    confidence=0.8,
                    source_layer=GenerationLayer.DIRECT,
                    generation_method="direct_mapping",
                    raw_source="LICENSE"
                )
            else:
                # Fallback when no license found
                fields["license"] = FieldGeneration(
                    value="NOASSERTION",
                    confidence=0.1,
                    source_layer=GenerationLayer.DIRECT,
                    generation_method="fallback",
                    raw_source="no_license_found"
                )
        
        return fields
    
    def _get_repo_url(self, project_data: ProjectData) -> Optional[str]:
        """Get repository URL from project data"""
        metadata = project_data.metadata
        
        # Try different URL fields based on platform
        if project_data.platform == PlatformType.GITHUB:
            return metadata.get("html_url") or project_data.url
        elif project_data.platform == PlatformType.GITLAB:
            return metadata.get("web_url") or project_data.url
        else:
            return project_data.url
    
    def _extract_license_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract license information from metadata"""
        license_info = metadata.get("license")
        if not license_info:
            return None
        
        # Handle different license formats
        if isinstance(license_info, dict):
            # GitHub format: {"name": "MIT License", "spdx_id": "MIT"}
            if "spdx_id" in license_info and license_info["spdx_id"]:
                return license_info["spdx_id"]
            elif "name" in license_info and license_info["name"]:
                return license_info["name"]
        elif isinstance(license_info, str):
            return license_info
        
        return None
    
    def _extract_version_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract version information from metadata"""
        # Try different version fields
        version_fields = ["tag_name", "latest_release", "version", "release_tag"]
        
        for field in version_fields:
            version_value = metadata.get(field)
            if version_value:
                # Clean up version string
                cleaned_version = self._clean_version_string(version_value)
                if cleaned_version:
                    return cleaned_version
        
        # Try to extract from releases array
        releases = metadata.get("releases", [])
        if releases and isinstance(releases, list):
            # Find the latest stable release (prefer non-prerelease)
            stable_releases = []
            prerelease_releases = []
            
            for release in releases:
                if isinstance(release, dict):
                    tag_name = release.get("tag_name")
                    if tag_name:
                        cleaned_version = self._clean_version_string(tag_name)
                        if cleaned_version:
                            if release.get("prerelease", False):
                                prerelease_releases.append(cleaned_version)
                            else:
                                stable_releases.append(cleaned_version)
            
            # Return the latest stable release, or fall back to latest prerelease
            if stable_releases:
                return stable_releases[0]  # First is latest
            elif prerelease_releases:
                return prerelease_releases[0]  # Fall back to prerelease
        
        return None
    
    def _clean_version_string(self, version: str) -> Optional[str]:
        """Clean and normalize version string"""
        if not version:
            return None
        
        # Remove common prefixes
        version = version.strip()
        if version.startswith("v"):
            version = version[1:]
        elif version.startswith("release-"):
            version = version[8:]
        
        # Basic validation - should contain at least one dot or be a simple number
        if "." in version or version.isdigit():
            return version
        
        return None
    
    def _find_readme_content(self, files) -> Optional[str]:
        """Find README content from project files"""
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        
        for file_info in files:
            if file_info.path in readme_files:
                return file_info.content
        
        return None
    
    def _extract_license_from_files(self, files) -> Optional[str]:
        """Extract license information from LICENSE files"""
        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "License"]
        
        # Priority order: License (capital L) > LICENSE > others
        license_priority = {"License": 1, "LICENSE": 2, "LICENSE.txt": 3, "LICENSE.md": 4, "COPYING": 5}
        
        # Find all license files and sort by priority
        found_license_files = []
        for file_info in files:
            if file_info.path in license_files:
                priority = license_priority.get(file_info.path, 999)
                found_license_files.append((priority, file_info))
        
        # Sort by priority (lower number = higher priority)
        found_license_files.sort(key=lambda x: x[0])
        
        # Process files in priority order
        for priority, file_info in found_license_files:
            content = file_info.content.upper()
            
            # CERN Open Hardware License detection (highest priority for hardware projects)
            if "CERN" in content and "OPEN HARDWARE" in content:
                if "V1.2" in content:
                    return "CERN-OHL-S-2.0"
                elif "V1.1" in content:
                    return "CERN-OHL-S-1.1"
                elif "V1.0" in content:
                    return "CERN-OHL-S-1.0"
                else:
                    return "CERN-OHL-S-2.0"  # Default to most common version
            
            # Other license detection
            elif "MIT" in content:
                return "MIT"
            elif "APACHE" in content and "2.0" in content:
                return "Apache-2.0"
            elif "GPL" in content and "3.0" in content:
                return "GPL-3.0"
            elif "GPL" in content and "2.0" in content:
                return "GPL-2.0"
            elif "BSD" in content and "3" in content:
                return "BSD-3-Clause"
            elif "BSD" in content and "2" in content:
                return "BSD-2-Clause"
            else:
                # Return the first line as license name
                lines = file_info.content.split('\n')
                if lines:
                    return lines[0].strip()
        
        return None
    
