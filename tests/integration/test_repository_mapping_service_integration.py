"""
Integration tests for RepositoryMappingService with real repositories.

Tests the service with actual GitHub repositories to validate functionality.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.services.repository_mapping_service import RepositoryMappingService
from src.core.generation.platforms.github import GitHubExtractor
from src.core.generation.models import PlatformType


class TestRepositoryMappingServiceIntegration:
    """Integration tests for RepositoryMappingService with real repositories."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_assess_nasa_rover_repository(self):
        """Test assessing NASA Open Source Rover repository."""
        service = RepositoryMappingService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
        # Assess repository
        assessment = await service.assess_repository(project_data)
        
        assert assessment is not None
        assert assessment.total_files > 0
        assert assessment.total_directories > 0
        assert len(assessment.file_types) > 0
        assert len(assessment.directory_tree) > 0
        
        # Verify specific directories exist
        assert any("mechanical" in dir_path.lower() for dir_path in assessment.directory_tree.keys())
        assert any("electrical" in dir_path.lower() for dir_path in assessment.directory_tree.keys())
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_routing_table_nasa_rover(self):
        """Test generating routing table for NASA Open Source Rover repository."""
        service = RepositoryMappingService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
        # Generate routing table
        routing_table = await service.generate_routing_table(project_data)
        
        assert routing_table is not None
        # Allow for slight differences due to duplicate paths or filtering
        assert len(routing_table.routes) >= len(project_data.files) - 1
        assert len(routing_table.routes) <= len(project_data.files)
        assert routing_table.metadata["source_url"] == "https://github.com/nasa-jpl/open-source-rover"
        assert routing_table.metadata["platform"] == PlatformType.GITHUB.value
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_assess_openflexure_microscope_repository(self):
        """Test assessing OpenFlexure Microscope repository."""
        service = RepositoryMappingService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/rwb27/openflexure_microscope")
        
        # Assess repository
        assessment = await service.assess_repository(project_data)
        
        assert assessment is not None
        assert assessment.total_files > 0
        assert assessment.total_directories > 0
        
        # Verify file types are detected
        assert len(assessment.file_types) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_generate_routing_table_openflexure_microscope(self):
        """Test generating routing table for OpenFlexure Microscope repository."""
        service = RepositoryMappingService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/rwb27/openflexure_microscope")
        
        # Generate routing table
        routing_table = await service.generate_routing_table(project_data)
        
        assert routing_table is not None
        assert len(routing_table.routes) > 0
        assert routing_table.metadata["source_url"] == "https://github.com/rwb27/openflexure_microscope"

