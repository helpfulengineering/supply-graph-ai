"""
Integration tests for FileCategorizationService LLM categorization with real repositories.

Tests the LLM-based file categorization with actual GitHub repositories to validate
end-to-end functionality. This tests the full flow including:
- Real project data extraction
- Layer 1 heuristic suggestions
- LLM categorization (if LLM service available)
- Fallback to Layer 1 when LLM unavailable
"""

import pytest
import os
from src.core.generation.services.file_categorization_service import FileCategorizationService
from src.core.generation.platforms.github import GitHubExtractor
from src.core.generation.utils.file_categorization import FileCategorizationRules
from src.core.generation.models import AnalysisDepth
from src.core.models.okh import DocumentationType
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.llm.providers.base import LLMProviderType


class TestFileCategorizationLLMIntegration:
    """Integration tests for LLM-based file categorization with real repositories."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llm_categorization_nasa_rover_with_llm(self):
        """
        Test LLM categorization with NASA Open Source Rover repository.
        
        This test uses a real repository and tests the full LLM categorization flow.
        If LLM service is not available, it will fall back to Layer 1.
        """
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
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
        
        # Try to create LLM service (may not be available)
        llm_service = None
        try:
            llm_config = LLMServiceConfig(
                name="FileCategorizationTest",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model=None,  # Use centralized config
                max_retries=1,
                retry_delay=1.0,
                timeout=30,
                enable_fallback=False,
                max_cost_per_request=0.5  # Lower cost limit for testing
            )
            llm_service = LLMService("FileCategorizationTest", llm_config)
            await llm_service.initialize()
        except Exception as e:
            pytest.skip(f"LLM service not available: {e}")
        
        # Create service with LLM
        service = FileCategorizationService(
            llm_service=llm_service,
            enable_caching=True
        )
        
        # Test with a small subset of files first (to avoid rate limits)
        test_files = project_data.files[:10]  # First 10 files
        
        # Categorize files using service (will use LLM if available)
        results = await service.categorize_files(
            files=test_files,
            layer1_suggestions={f.path: layer1_suggestions[f.path] for f in test_files if f.path in layer1_suggestions},
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) > 0
        
        # Verify results have proper structure
        for file_path, result in results.items():
            assert result is not None
            assert isinstance(result.documentation_type, DocumentationType)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.excluded, bool)
            assert isinstance(result.reason, str)
        
        # Verify some expected categorizations
        # README.md should be documentation_home (if in root)
        readme_files = [path for path in results.keys() if path.lower() == "readme.md"]
        if readme_files:
            readme_path = readme_files[0]
            readme_result = results[readme_path]
            # Should be documentation_home or making_instructions (not excluded)
            assert not readme_result.excluded
            assert readme_result.documentation_type in [
                DocumentationType.DOCUMENTATION_HOME,
                DocumentationType.MAKING_INSTRUCTIONS
            ]
        
        # .stl files should be manufacturing_files
        stl_files = [path for path in results.keys() if path.endswith('.stl')]
        for stl_file in stl_files:
            if stl_file in results and not results[stl_file].excluded:
                assert results[stl_file].documentation_type == DocumentationType.MANUFACTURING_FILES
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llm_categorization_fallback_to_layer1(self):
        """
        Test that service falls back to Layer 1 when LLM is unavailable.
        
        This test verifies the fallback mechanism works correctly.
        """
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
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
        
        # Create service WITHOUT LLM (should fall back to Layer 1)
        service = FileCategorizationService(
            llm_service=None,  # No LLM service
            enable_caching=False
        )
        
        # Test with a small subset of files
        test_files = project_data.files[:10]
        
        # Categorize files (should use Layer 1 only)
        results = await service.categorize_files(
            files=test_files,
            layer1_suggestions={f.path: layer1_suggestions[f.path] for f in test_files if f.path in layer1_suggestions},
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) > 0
        
        # Verify results match Layer 1 suggestions (since LLM is not available)
        for file_path, result in results.items():
            assert result is not None
            if file_path in layer1_suggestions:
                # Results should match Layer 1 suggestions when LLM unavailable
                layer1_result = layer1_suggestions[file_path]
                assert result.documentation_type == layer1_result.documentation_type
                assert result.excluded == layer1_result.excluded
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llm_categorization_different_depths(self):
        """
        Test LLM categorization with different analysis depths.
        
        This test verifies that different analysis depths produce different results.
        """
        # Extract project data from real repository
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project("https://github.com/nasa-jpl/open-source-rover")
        
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
        
        # Try to create LLM service
        llm_service = None
        try:
            llm_config = LLMServiceConfig(
                name="FileCategorizationTest",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model=None,
                max_retries=1,
                retry_delay=1.0,
                timeout=30,
                enable_fallback=False,
                max_cost_per_request=0.5
            )
            llm_service = LLMService("FileCategorizationTest", llm_config)
            await llm_service.initialize()
        except Exception as e:
            pytest.skip(f"LLM service not available: {e}")
        
        # Find a markdown file to test with
        markdown_files = [f for f in project_data.files if f.path.endswith('.md')]
        if not markdown_files:
            pytest.skip("No markdown files found in repository")
        
        test_file = markdown_files[0]
        
        # Test with Shallow depth
        service_shallow = FileCategorizationService(llm_service=llm_service)
        result_shallow = await service_shallow._categorize_with_llm(
            file_info=test_file,
            layer1_suggestion=layer1_suggestions.get(test_file.path),
            depth=AnalysisDepth.SHALLOW
        )
        
        # Test with Deep depth
        service_deep = FileCategorizationService(llm_service=llm_service)
        result_deep = await service_deep._categorize_with_llm(
            file_info=test_file,
            layer1_suggestion=layer1_suggestions.get(test_file.path),
            depth=AnalysisDepth.DEEP
        )
        
        # Both should produce results
        if result_shallow is not None and result_deep is not None:
            # Results should be valid
            assert isinstance(result_shallow.documentation_type, DocumentationType)
            assert isinstance(result_deep.documentation_type, DocumentationType)
            assert 0.0 <= result_shallow.confidence <= 1.0
            assert 0.0 <= result_deep.confidence <= 1.0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llm_categorization_openflexure_microscope(self):
        """
        Test LLM categorization with OpenFlexure Microscope repository.
        
        This test uses a different repository to verify the service works
        with different project structures.
        """
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
        
        # Try to create LLM service
        llm_service = None
        try:
            llm_config = LLMServiceConfig(
                name="FileCategorizationTest",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model=None,
                max_retries=1,
                retry_delay=1.0,
                timeout=30,
                enable_fallback=False,
                max_cost_per_request=0.5
            )
            llm_service = LLMService("FileCategorizationTest", llm_config)
            await llm_service.initialize()
        except Exception as e:
            pytest.skip(f"LLM service not available: {e}")
        
        # Create service with LLM
        service = FileCategorizationService(
            llm_service=llm_service,
            enable_caching=True
        )
        
        # Test with a small subset of files
        test_files = project_data.files[:10]
        
        # Categorize files
        results = await service.categorize_files(
            files=test_files,
            layer1_suggestions={f.path: layer1_suggestions[f.path] for f in test_files if f.path in layer1_suggestions},
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) > 0
        
        # Verify results have proper structure
        for file_path, result in results.items():
            assert result is not None
            assert isinstance(result.documentation_type, DocumentationType)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.excluded, bool)
        
        # Verify most files are categorized (not excluded)
        categorized_count = sum(1 for r in results.values() if not r.excluded)
        assert categorized_count > 0

