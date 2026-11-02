"""
Layer 1: Direct Matcher for OKH manifest generation.

This module provides direct field mapping from platform metadata to manifest fields.
It implements high-confidence mappings for fields that can be directly extracted
from platform APIs and file structures.
"""

from typing import Any, Dict, Optional

from ..models import (
    FieldGeneration,
    GenerationLayer,
    LayerConfig,
    PlatformType,
    ProjectData,
)
from ..version_sources import declared_version
from .base import BaseGenerationLayer, LayerResult


class DirectMatcher(BaseGenerationLayer):
    """Direct field mapping matcher for Layer 1 generation"""

    def __init__(self, layer_config: Optional[LayerConfig] = None):
        super().__init__(GenerationLayer.DIRECT, layer_config)
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
                    field_gen.raw_source,
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

    def _extract_metadata_fields(
        self, project_data: ProjectData
    ) -> Dict[str, FieldGeneration]:
        """Extract fields directly from platform metadata"""
        fields = {}
        metadata = project_data.metadata

        # Title mapping
        if "name" in metadata and metadata["name"]:
            confidence = self.calculate_confidence(
                "title", metadata["name"], "direct_mapping"
            )
            fields["title"] = FieldGeneration(
                value=metadata["name"],
                confidence=confidence,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.name",
            )

        # Note: Description extraction is handled by NLP/LLM layers for better content analysis

        # Repository URL mapping
        repo_url = self._get_repo_url(project_data)
        if repo_url:
            confidence = self.calculate_confidence("repo", repo_url, "direct_mapping")
            fields["repo"] = FieldGeneration(
                value=repo_url,
                confidence=confidence,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.html_url" if "html_url" in metadata else "url",
            )

        # License from metadata
        license_value = self._extract_license_from_metadata(metadata)
        if license_value:
            confidence = self.calculate_confidence(
                "license", license_value, "metadata_extraction"
            )
            fields["license"] = FieldGeneration(
                value=license_value,
                confidence=confidence,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="metadata.license",
            )

        declared = declared_version(project_data)
        if declared:
            version_value, source = declared
            fields["version"] = FieldGeneration(
                value=version_value,
                confidence=self.calculate_confidence(
                    "version", version_value, "metadata_extraction"
                ),
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source=source,
            )

        # Keywords from repository topics (GitHub/GitLab API field)
        topics = metadata.get("topics", [])
        if topics and isinstance(topics, list):
            clean_topics = [t.strip() for t in topics if t and t.strip()]
            if clean_topics:
                confidence = self.calculate_confidence(
                    "keywords", clean_topics, "direct_mapping"
                )
                fields["keywords"] = FieldGeneration(
                    value=clean_topics,
                    confidence=confidence,
                    source_layer=GenerationLayer.DIRECT,
                    generation_method="direct_mapping",
                    raw_source="metadata.topics",
                )

        return fields

    def _extract_file_fields(
        self, project_data: ProjectData
    ) -> Dict[str, FieldGeneration]:
        """Extract fields from project files"""
        fields = {}

        # README content
        readme_content = self._find_readme_content(project_data.files)
        if readme_content:
            confidence = self.calculate_confidence(
                "readme", readme_content, "readme_extraction"
            )
            fields["readme"] = FieldGeneration(
                value=readme_content,
                confidence=confidence,
                source_layer=GenerationLayer.DIRECT,
                generation_method="direct_mapping",
                raw_source="README.md",
            )

        # License from file (if not already found in metadata)
        if "license" not in fields:
            license_from_file = self._extract_license_from_files(project_data.files)
            if license_from_file:
                confidence = self.calculate_confidence(
                    "license", license_from_file, "license_file_detection"
                )
                fields["license"] = FieldGeneration(
                    value=license_from_file,
                    confidence=confidence,
                    source_layer=GenerationLayer.DIRECT,
                    generation_method="direct_mapping",
                    raw_source="LICENSE",
                )
            else:
                # Fallback when no license found
                confidence = self.calculate_confidence(
                    "license", "NOASSERTION", "fallback"
                )
                fields["license"] = FieldGeneration(
                    value="NOASSERTION",
                    confidence=confidence,
                    source_layer=GenerationLayer.DIRECT,
                    generation_method="fallback",
                    raw_source="no_license_found",
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
        """Find README content from project files using shared utilities"""
        # Use shared utility to find README files
        readme_files = self.find_readme_files(files)

        # Return content from the first README file found
        for file_info in readme_files:
            if file_info.content:
                return file_info.content

        return None

    def _extract_license_from_files(self, files) -> Optional[str]:
        """Extract license information from LICENSE files using shared utilities"""
        # Use shared utility to find license files
        license_files = self.find_license_files(files)

        # Priority order: License (capital L) > LICENSE > others
        license_priority = {
            "License": 1,
            "LICENSE": 2,
            "LICENSE.txt": 3,
            "LICENSE.md": 4,
            "COPYING": 5,
        }

        # Find all license files and sort by priority
        found_license_files = []
        for file_info in license_files:
            file_name = file_info.path.split("/")[-1]  # Get just the filename
            priority = license_priority.get(file_name, 999)
            found_license_files.append((priority, file_info))

        # Sort by priority (lower number = higher priority)
        found_license_files.sort(key=lambda x: x[0])

        # Extract license from the highest priority file using shared utility
        for priority, file_info in found_license_files:
            if file_info.content:
                license_type = self.extract_license_type(file_info.content)
                if license_type:
                    return license_type

        return None
