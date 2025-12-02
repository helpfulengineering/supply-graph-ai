"""
Repository Mapping Service for managing repository structure and routing.

This service provides functionality for:
- Assessing repository size, structure, and complexity
- Generating directory trees and file type inventories
- Maintaining routing tables between repository contents and OKH destinations
- Supporting iterative discovery and understanding of repositories
"""

import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from ..models import (
    ProjectData,
    RepositoryAssessment,
    RepositoryRoutingTable,
    RouteEntry,
)
from ...models.okh import DocumentationType
from ..utils.file_categorization import FileCategorizationResult

logger = logging.getLogger(__name__)


class RepositoryMappingService:
    """
    Service for managing repository structure mapping and routing.

    This service provides functionality for:
    - Assessing repository size and complexity
    - Generating directory trees and file type inventories
    - Maintaining routing tables between repository contents and OKH destinations
    - Supporting iterative discovery and understanding of repositories
    """

    def __init__(self):
        """Initialize the repository mapping service."""
        self.logger = logging.getLogger(__name__)

    async def assess_repository(
        self, project_data: ProjectData
    ) -> RepositoryAssessment:
        """
        Assess repository size, structure, and complexity.

        Args:
            project_data: Project data containing files and structure

        Returns:
            RepositoryAssessment with size, file counts, directory tree, etc.
        """
        assessment = RepositoryAssessment()

        # Count files and directories
        assessment.total_files = len(project_data.files)

        # Build directory tree and file type inventory
        directories = set()
        file_types = defaultdict(int)
        directory_tree = defaultdict(list)

        for file_info in project_data.files:
            # Count file types
            file_types[file_info.file_type] += 1

            # Extract directory structure
            file_path = Path(file_info.path)
            if len(file_path.parts) > 1:
                # File is in a subdirectory
                directory = str(file_path.parent)
                directories.add(directory)
                directory_tree[directory].append(file_info.path)
            else:
                # File is in root
                directory_tree["."].append(file_info.path)

        assessment.total_directories = len(directories)
        assessment.file_types = dict(file_types)
        assessment.directory_tree = dict(directory_tree)

        self.logger.debug(
            f"Assessed repository: {assessment.total_files} files, "
            f"{assessment.total_directories} directories"
        )

        return assessment

    async def generate_routing_table(
        self, project_data: ProjectData
    ) -> RepositoryRoutingTable:
        """
        Generate initial routing table from repository structure.

        Args:
            project_data: Project data containing files

        Returns:
            RepositoryRoutingTable mapping files to OKH destinations
        """
        routing_table = RepositoryRoutingTable()

        # Add metadata
        routing_table.metadata = {
            "source_url": project_data.url,
            "platform": project_data.platform.value,
            "total_files": len(project_data.files),
        }

        # Generate initial routes for all files
        # Initially, routes will have low confidence and will be updated
        # by categorization processes (Layer 1, Layer 2)
        # Use a set to track processed paths to avoid duplicates
        processed_paths = set()
        for file_info in project_data.files:
            # Skip duplicate paths (if any)
            if file_info.path in processed_paths:
                self.logger.warning(f"Skipping duplicate file path: {file_info.path}")
                continue
            processed_paths.add(file_info.path)

            # Default destination (will be updated by categorization)
            routing_table.add_route(
                source_path=file_info.path,
                destination_type=DocumentationType.DESIGN_FILES,  # Default, will be updated
                destination_path=file_info.path,  # Default, will be updated
                confidence=0.0,  # Low confidence until categorized
            )

        self.logger.debug(
            f"Generated routing table with {len(routing_table.routes)} routes"
        )

        return routing_table

    async def update_routing_table(
        self,
        routing_table: RepositoryRoutingTable,
        categorizations: Dict[str, FileCategorizationResult],
    ) -> RepositoryRoutingTable:
        """
        Update routing table with new categorizations.

        Args:
            routing_table: Current routing table
            categorizations: New file categorizations from Layer 1 or Layer 2

        Returns:
            Updated routing table
        """
        updated_count = 0

        for file_path, categorization in categorizations.items():
            # Skip excluded files
            if categorization.excluded:
                # Remove route for excluded files
                if file_path in routing_table.routes:
                    del routing_table.routes[file_path]
                continue

            # Generate destination path based on documentation type
            destination_path = self._generate_destination_path(
                file_path, categorization.documentation_type
            )

            # Update or add route (only if confidence is higher than existing)
            existing_route = routing_table.get_route(file_path)
            if (
                existing_route is None
                or categorization.confidence > existing_route.confidence
            ):
                routing_table.add_route(
                    source_path=file_path,
                    destination_type=categorization.documentation_type,
                    destination_path=destination_path,
                    confidence=categorization.confidence,
                )
            updated_count += 1

        # Update metadata
        routing_table.metadata["last_updated"] = datetime.now().isoformat()
        routing_table.metadata["updated_routes"] = updated_count

        self.logger.debug(f"Updated routing table with {updated_count} categorizations")

        return routing_table

    def _generate_destination_path(
        self, source_path: str, documentation_type: DocumentationType
    ) -> str:
        """
        Generate destination path based on documentation type.

        Args:
            source_path: Original file path
            documentation_type: Documentation type for destination

        Returns:
            Destination path in OKH structure
        """
        file_path = Path(source_path)
        filename = file_path.name

        # Map documentation type to directory
        type_to_dir = {
            DocumentationType.MAKING_INSTRUCTIONS: "making-instructions",
            DocumentationType.OPERATING_INSTRUCTIONS: "operating-instructions",
            DocumentationType.TECHNICAL_SPECIFICATIONS: "technical-specifications",
            DocumentationType.DESIGN_FILES: "design-files",
            DocumentationType.MANUFACTURING_FILES: "manufacturing-files",
            DocumentationType.PUBLICATIONS: "publications",
            DocumentationType.SOFTWARE: "software",
            DocumentationType.SCHEMATICS: "schematics",
            DocumentationType.MAINTENANCE_INSTRUCTIONS: "maintenance-instructions",
            DocumentationType.DISPOSAL_INSTRUCTIONS: "disposal-instructions",
            DocumentationType.RISK_ASSESSMENT: "risk-assessment",
        }

        destination_dir = type_to_dir.get(documentation_type, "other")

        return f"{destination_dir}/{filename}"
