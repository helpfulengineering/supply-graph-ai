"""
Unit tests for RepositoryMappingService.

Tests the service for managing repository structure mapping and routing.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.services.repository_mapping_service import RepositoryMappingService
from src.core.generation.models import (
    ProjectData,
    PlatformType,
    FileInfo,
    RepositoryAssessment,
    RepositoryRoutingTable
)


class TestRepositoryMappingService:
    """Test the RepositoryMappingService class."""
    
    def test_service_initialization(self):
        """Test that RepositoryMappingService can be initialized."""
        service = RepositoryMappingService()
        assert service is not None
    
    @pytest.mark.asyncio
    async def test_assess_repository(self):
        """Test assessing repository size and structure."""
        service = RepositoryMappingService()
        
        # Create sample project data
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/repo",
            metadata={},
            files=[
                FileInfo(path="README.md", size=100, content="# Test", file_type="markdown"),
                FileInfo(path="docs/manual.md", size=200, content="# Manual", file_type="markdown"),
                FileInfo(path="src/main.py", size=300, content="print('hello')", file_type="python"),
                FileInfo(path="design/part.stl", size=400, content="", file_type="stl"),
            ],
            documentation=[],
            raw_content={}
        )
        
        assessment = await service.assess_repository(project_data)
        
        assert assessment is not None
        assert isinstance(assessment, RepositoryAssessment)
        assert assessment.total_files == 4
        assert assessment.total_directories >= 2  # docs, src, design
        assert "markdown" in assessment.file_types
        assert "python" in assessment.file_types
    
    @pytest.mark.asyncio
    async def test_generate_routing_table(self):
        """Test generating initial routing table from repository structure."""
        service = RepositoryMappingService()
        
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/repo",
            metadata={},
            files=[
                FileInfo(path="README.md", size=100, content="# Test", file_type="markdown"),
                FileInfo(path="docs/manual.md", size=200, content="# Manual", file_type="markdown"),
                FileInfo(path="design/part.stl", size=400, content="", file_type="stl"),
            ],
            documentation=[],
            raw_content={}
        )
        
        routing_table = await service.generate_routing_table(project_data)
        
        assert routing_table is not None
        assert isinstance(routing_table, RepositoryRoutingTable)
        assert len(routing_table.routes) > 0
    
    @pytest.mark.asyncio
    async def test_update_routing_table(self):
        """Test updating routing table with new categorizations."""
        service = RepositoryMappingService()
        
        # Create initial routing table
        routing_table = RepositoryRoutingTable()
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=None,  # Will be set from categorization
            destination_path="",
            confidence=0.5
        )
        
        # Create categorizations (using FileCategorizationResult structure)
        from src.core.generation.utils.file_categorization import FileCategorizationResult
        from src.core.models.okh import DocumentationType
        
        categorizations = {
            "docs/manual.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.9,
                excluded=False,
                reason="Directory-based categorization"
            )
        }
        
        updated_table = await service.update_routing_table(routing_table, categorizations)
        
        assert updated_table is not None
        route = updated_table.get_route("docs/manual.md")
        assert route is not None
        assert route.destination_type == DocumentationType.MAKING_INSTRUCTIONS
        assert route.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_assess_empty_repository(self):
        """Test assessing an empty repository."""
        service = RepositoryMappingService()
        
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/empty",
            metadata={},
            files=[],
            documentation=[],
            raw_content={}
        )
        
        assessment = await service.assess_repository(project_data)
        
        assert assessment.total_files == 0
        assert assessment.total_directories == 0
        assert len(assessment.file_types) == 0
    
    @pytest.mark.asyncio
    async def test_generate_routing_table_large_repository(self):
        """Test generating routing table for large repository."""
        service = RepositoryMappingService()
        
        # Create a repository with many files
        files = []
        for i in range(100):
            files.append(FileInfo(
                path=f"file_{i}.txt",
                size=100,
                content=f"Content {i}",
                file_type="text"
            ))
        
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/large",
            metadata={},
            files=files,
            documentation=[],
            raw_content={}
        )
        
        routing_table = await service.generate_routing_table(project_data)
        
        assert routing_table is not None
        # Should handle large repositories efficiently
        assert len(routing_table.routes) == 100

