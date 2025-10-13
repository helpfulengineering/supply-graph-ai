"""
Layer 1: Direct Matcher for OKH manifest generation.

This module provides direct field mapping from platform metadata to manifest fields.
It implements high-confidence mappings for fields that can be directly extracted
from platform APIs and file structures.
"""

import re
from typing import Dict, Any, Optional

from ..models import ProjectData, FieldGeneration, GenerationLayer, PlatformType
from .base import BaseLayerMatcher


class DirectMatcher(BaseLayerMatcher):
    """Direct field mapping matcher for Layer 1 generation"""
    
    def __init__(self):
        self._confidence_threshold = 0.8
    
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
    
    def _find_readme_content(self, files) -> Optional[str]:
        """Find README content from project files"""
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        
        for file_info in files:
            if file_info.path in readme_files:
                return file_info.content
        
        return None
    
    def _extract_license_from_files(self, files) -> Optional[str]:
        """Extract license information from LICENSE files"""
        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]
        
        for file_info in files:
            if file_info.path in license_files:
                content = file_info.content.upper()
                
                # Simple license detection
                if "MIT" in content:
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
    
    def get_layer_type(self) -> GenerationLayer:
        """Get the type of this generation layer"""
        return GenerationLayer.DIRECT
    
    def get_confidence_threshold(self) -> float:
        """Get the minimum confidence threshold for this layer"""
        return self._confidence_threshold
