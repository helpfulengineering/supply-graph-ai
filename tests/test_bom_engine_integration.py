"""
Tests for BOM integration in the generation engine
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo, LayerConfig, GenerationLayer
from src.core.generation.bom_models import BOMCollector, BOMProcessor, BOMBuilder
from src.core.models.bom import BillOfMaterials, Component


class TestBOMEngineIntegration:
    """Test BOM integration in the generation engine"""
    
    @pytest.fixture
    def mock_project_data(self):
        """Mock project data for testing"""
        return ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/project",
            metadata={"name": "Test Project", "description": "A test project"},
            files=[
                FileInfo(
                    path="README.md",
                    size=1000,
                    content="""
# Test Project

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
                    """,
                    file_type="markdown"
                )
            ],
            documentation=[
                DocumentInfo(
                    title="README",
                    path="README.md",
                    content="""
# Test Project

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
                    """,
                    doc_type="readme"
                )
            ],
            raw_content={
                "README.md": """
# Test Project

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
                """
            }
        )
    
    @pytest.fixture
    def bom_enabled_config(self):
        """Configuration with BOM normalization enabled"""
        config = LayerConfig()
        config.use_bom_normalization = True
        return config
    
    @pytest.mark.asyncio
    async def test_generation_engine_with_bom_normalization(self, mock_project_data, bom_enabled_config):
        """Test generation engine with BOM normalization enabled"""
        engine = GenerationEngine(config=bom_enabled_config)
        
        # Generate manifest with BOM normalization
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Verify BOM was generated
        assert "bom" in result.generated_fields
        bom_field = result.generated_fields["bom"]
        
        # Verify BOM field structure
        assert bom_field.value is not None
        assert isinstance(bom_field.value, dict)
        assert "id" in bom_field.value
        assert "name" in bom_field.value
        assert "components" in bom_field.value
        assert "metadata" in bom_field.value
        
        # Verify BOM components
        bom_data = bom_field.value
        assert len(bom_data["components"]) >= 3  # Should extract the 3 components from README
        
        # Verify component structure
        for component in bom_data["components"]:
            assert "id" in component
            assert "name" in component
            assert "quantity" in component
            assert "unit" in component
            assert "metadata" in component
        
        # Verify BOM metadata
        assert "generated_at" in bom_data["metadata"]
        assert "generation_method" in bom_data["metadata"]
        assert bom_data["metadata"]["generation_method"] == "bom_normalization"
        
        print(f"✅ BOM generated with {len(bom_data['components'])} components")
        for component in bom_data["components"]:
            print(f"  - {component['quantity']} {component['name']} ({component['unit']})")
    
    @pytest.mark.asyncio
    async def test_generation_engine_without_bom_normalization(self, mock_project_data):
        """Test generation engine with BOM normalization disabled"""
        config = LayerConfig()
        config.use_bom_normalization = False
        engine = GenerationEngine(config=config)
        
        # Generate manifest without BOM normalization
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Verify BOM was not generated
        assert "bom" not in result.generated_fields
        
        print("✅ BOM normalization correctly disabled")
    
    @pytest.mark.asyncio
    async def test_bom_generation_method(self, mock_project_data, bom_enabled_config):
        """Test the _generate_normalized_bom method"""
        engine = GenerationEngine(config=bom_enabled_config)
        
        # Test the BOM generation method directly
        bom = await engine._generate_normalized_bom(mock_project_data)
        
        # Verify BOM object
        assert isinstance(bom, BillOfMaterials)
        assert bom.name == "Test Project BOM"
        assert len(bom.components) >= 3
        
        # Verify components
        component_names = [comp.name for comp in bom.components]
        assert "stethoscope head" in component_names
        assert "ear tubes" in component_names
        assert "Y-piece" in component_names
        
        # Verify component metadata
        for component in bom.components:
            assert component.metadata["source"] == "readme_materials"
            assert component.metadata["confidence"] > 0.0
            assert "file_reference" in component.metadata
        
        print(f"✅ BOM generation method works: {len(bom.components)} components")
    
    @pytest.mark.asyncio
    async def test_bom_field_generation_structure(self, mock_project_data, bom_enabled_config):
        """Test the structure of the BOM field generation"""
        engine = GenerationEngine(config=bom_enabled_config)
        
        result = await engine.generate_manifest_async(mock_project_data)
        bom_field = result.generated_fields["bom"]
        
        # Verify FieldGeneration structure
        assert bom_field.confidence > 0.0
        assert bom_field.source_layer == GenerationLayer.BOM_NORMALIZATION
        assert bom_field.generation_method == "bom_normalization"
        assert "Extracted from" in bom_field.raw_source
        
        # Verify confidence scoring
        assert 0.0 <= bom_field.confidence <= 1.0
        
        print(f"✅ BOM field generation structure correct:")
        print(f"  Confidence: {bom_field.confidence:.2f}")
        print(f"  Source layer: {bom_field.source_layer}")
        print(f"  Generation method: {bom_field.generation_method}")
        print(f"  Raw source: {bom_field.raw_source}")
    
    @pytest.mark.asyncio
    async def test_bom_integration_with_existing_layers(self, mock_project_data, bom_enabled_config):
        """Test BOM integration works alongside existing generation layers"""
        engine = GenerationEngine(config=bom_enabled_config)
        
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Verify both BOM and other fields are generated
        assert "bom" in result.generated_fields
        assert "title" in result.generated_fields  # From direct layer
        assert "description" in result.generated_fields  # From direct layer
        
        # Verify quality report includes BOM
        assert result.quality_report is not None
        assert len(result.generated_fields) > 3  # Should have BOM + other fields
        
        print(f"✅ BOM integration with existing layers:")
        print(f"  Total fields generated: {len(result.generated_fields)}")
        print(f"  Fields: {list(result.generated_fields.keys())}")
    
    @pytest.mark.asyncio
    async def test_bom_error_handling(self, bom_enabled_config):
        """Test BOM generation error handling"""
        engine = GenerationEngine(config=bom_enabled_config)
        
        # Create project data with no BOM sources
        empty_project = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/empty",
            metadata={"name": "Empty Project"},
            files=[],
            documentation=[],
            raw_content={}
        )
        
        # Should not crash, should generate empty BOM
        result = await engine.generate_manifest_async(empty_project)
        
        # BOM field should still be present but with empty components
        assert "bom" in result.generated_fields
        bom_data = result.generated_fields["bom"].value
        assert len(bom_data["components"]) == 0
        assert bom_data["metadata"]["final_count"] == 0
        
        print("✅ BOM error handling works: empty project handled gracefully")
    
    def test_bom_config_validation(self):
        """Test BOM configuration validation"""
        # Test valid config
        config = LayerConfig()
        config.use_bom_normalization = True
        engine = GenerationEngine(config=config)
        assert engine.config.use_bom_normalization is True
        
        # Test default config
        engine_default = GenerationEngine()
        # Should have use_bom_normalization attribute (defaults to False)
        assert hasattr(engine_default.config, 'use_bom_normalization')
        
        print("✅ BOM configuration validation works")
