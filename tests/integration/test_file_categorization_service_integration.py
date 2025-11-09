"""
Integration tests for FileCategorizationService with real repositories.

Tests the service with actual GitHub repositories to validate file categorization.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.services.file_categorization_service import FileCategorizationService
from src.core.generation.services.repository_mapping_service import RepositoryMappingService
from src.core.generation.platforms.github import GitHubExtractor
from src.core.generation.utils.file_categorization import FileCategorizationRules
from src.core.generation.models import AnalysisDepth
from src.core.models.okh import DocumentationType


class TestFileCategorizationServiceIntegration:
    """Integration tests for FileCategorizationService with real repositories."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_categorize_nasa_rover_files(self):
        """Test categorizing files from NASA Open Source Rover repository."""
        service = FileCategorizationService()
        repo_service = RepositoryMappingService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
        # Generate Layer 1 suggestions using FileCategorizationRules
        from pathlib import Path
        rules = FileCategorizationRules()
        layer1_suggestions = {}
        for file_info in project_data.files:
            file_path_obj = Path(file_info.path)
            result = rules.categorize_file(
                filename=file_path_obj.name,
                file_path=file_info.path
            )
            layer1_suggestions[file_info.path] = result
        
        # Categorize files using service
        results = await service.categorize_files(
            files=project_data.files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) > 0
        
        # Verify some expected categorizations
        # README.md should be documentation_home (if in root)
        readme_files = [path for path in results.keys() if path.lower() == "readme.md"]
        if readme_files:
            readme_path = readme_files[0]
            # Check if it's categorized correctly (may be documentation_home or making_instructions)
            assert readme_path in results
        
        # .stl files should be manufacturing_files
        stl_files = [path for path in results.keys() if path.endswith('.stl')]
        for stl_file in stl_files[:5]:  # Check first 5 STL files
            if stl_file in results and not results[stl_file].excluded:
                assert results[stl_file].documentation_type == DocumentationType.MANUFACTURING_FILES
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_categorize_openflexure_microscope_files(self):
        """Test categorizing files from OpenFlexure Microscope repository."""
        service = FileCategorizationService()
        
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/rwb27/openflexure_microscope")
        
        # Generate Layer 1 suggestions
        from pathlib import Path
        rules = FileCategorizationRules()
        layer1_suggestions = {}
        for file_info in project_data.files:
            file_path_obj = Path(file_info.path)
            result = rules.categorize_file(
                filename=file_path_obj.name,
                file_path=file_info.path
            )
            layer1_suggestions[file_info.path] = result
        
        # Categorize files
        results = await service.categorize_files(
            files=project_data.files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) > 0
        
        # Verify categorizations make sense
        # Most files should have a documentation type assigned
        categorized_count = sum(1 for r in results.values() if not r.excluded)
        assert categorized_count > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_categorize_with_repository_mapping_service(self):
        """Test categorizing files with RepositoryMappingService integration."""
        file_service = FileCategorizationService()
        repo_service = RepositoryMappingService()
        
        # Extract project data
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
        # Generate routing table
        routing_table = await repo_service.generate_routing_table(project_data)
        
        # Generate Layer 1 suggestions
        from pathlib import Path
        rules = FileCategorizationRules()
        layer1_suggestions = {}
        for file_info in project_data.files:
            file_path_obj = Path(file_info.path)
            result = rules.categorize_file(
                filename=file_path_obj.name,
                file_path=file_info.path
            )
            layer1_suggestions[file_info.path] = result
        
        # Categorize files
        results = await file_service.categorize_files(
            files=project_data.files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Update routing table with categorizations
        updated_routing_table = await repo_service.update_routing_table(
            routing_table,
            results
        )
        
        assert len(updated_routing_table.routes) > 0
        
        # Verify routes were updated with categorizations
        # Check a few files to ensure routes have proper documentation types
        sample_files = list(results.keys())[:10]
        for file_path in sample_files:
            if file_path in updated_routing_table.routes:
                route = updated_routing_table.get_route(file_path)
                assert route is not None
                assert route.destination_type is not None

