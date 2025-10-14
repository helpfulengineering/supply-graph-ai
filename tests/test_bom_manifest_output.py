"""
Tests for BOM integration in OKH manifest output format
"""
import pytest
import asyncio
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo, LayerConfig, ManifestGeneration
from src.core.models.bom import BillOfMaterials, Component


class TestBOMManifestOutput:
    """Test BOM integration in OKH manifest output format"""
    
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
    async def test_okh_manifest_with_structured_bom(self, mock_project_data, bom_enabled_config):
        """Test OKH manifest output includes structured BOM"""
        engine = GenerationEngine(config=bom_enabled_config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        
        # Verify BOM field exists and is structured
        assert "bom" in okh_manifest
        bom_data = okh_manifest["bom"]
        
        # Verify BOM structure
        assert isinstance(bom_data, dict)
        assert "id" in bom_data
        assert "name" in bom_data
        assert "components" in bom_data
        assert "metadata" in bom_data
        
        # Verify BOM components
        assert len(bom_data["components"]) >= 3
        for component in bom_data["components"]:
            assert "id" in component
            assert "name" in component
            assert "quantity" in component
            assert "unit" in component
            assert "metadata" in component
        
        print(f"✅ OKH manifest with structured BOM:")
        print(f"  BOM ID: {bom_data['id']}")
        print(f"  BOM Name: {bom_data['name']}")
        print(f"  Components: {len(bom_data['components'])}")
        for component in bom_data["components"]:
            print(f"    - {component['quantity']} {component['name']} ({component['unit']})")
    
    @pytest.mark.asyncio
    async def test_okh_manifest_bom_vs_materials_comparison(self, mock_project_data, bom_enabled_config):
        """Test comparison between BOM and materials fields in OKH manifest"""
        engine = GenerationEngine(config=bom_enabled_config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        
        # Both BOM and materials should be present (for backward compatibility)
        assert "bom" in okh_manifest
        assert "materials" in okh_manifest
        
        # Compare data richness
        bom_data = okh_manifest["bom"]
        materials_data = okh_manifest["materials"]
        
        # BOM should have structured data (dict with components)
        assert isinstance(bom_data, dict)
        assert "components" in bom_data
        assert len(bom_data["components"]) > 0
        
        # Materials should be present (can be string or list for backward compatibility)
        assert materials_data is not None
        
        # BOM should have structured metadata
        assert "metadata" in bom_data
        assert "generated_at" in bom_data["metadata"]
        assert "generation_method" in bom_data["metadata"]
        
        # Materials should be simpler (backward compatibility)
        # Materials can be a string (raw text) or list (structured)
        if isinstance(materials_data, list):
            for material in materials_data:
                assert "name" in material
                assert "quantity" in material
                assert "unit" in material
        elif isinstance(materials_data, str):
            # Raw text materials - should contain the materials content
            assert len(materials_data) > 0
        
        print(f"✅ BOM vs Materials comparison:")
        print(f"  BOM components: {len(bom_data['components'])}")
        print(f"  Materials type: {type(materials_data)}")
        if isinstance(materials_data, list):
            print(f"  Materials entries: {len(materials_data)}")
        else:
            print(f"  Materials length: {len(materials_data)}")
        print(f"  BOM has metadata: {'metadata' in bom_data}")
        print(f"  BOM generation method: {bom_data['metadata'].get('generation_method', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_okh_manifest_without_bom_normalization(self, mock_project_data):
        """Test OKH manifest without BOM normalization (fallback behavior)"""
        config = LayerConfig()
        config.use_bom_normalization = False
        engine = GenerationEngine(config=config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        
        # BOM field should not be present or should be empty/URL
        if "bom" in okh_manifest:
            # If present, should be a simple string (URL) or empty
            bom_value = okh_manifest["bom"]
            assert isinstance(bom_value, str) or bom_value == ""
        
        # Materials should still be present
        assert "materials" in okh_manifest
        
        print("✅ OKH manifest without BOM normalization:")
        print(f"  BOM field: {okh_manifest.get('bom', 'Not present')}")
        print(f"  Materials present: {'materials' in okh_manifest}")
    
    @pytest.mark.asyncio
    async def test_okh_manifest_bom_metadata_structure(self, mock_project_data, bom_enabled_config):
        """Test BOM metadata structure in OKH manifest"""
        engine = GenerationEngine(config=bom_enabled_config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        bom_data = okh_manifest["bom"]
        
        # Verify BOM metadata structure
        metadata = bom_data["metadata"]
        assert "generated_at" in metadata
        assert "generation_method" in metadata
        assert "source_count" in metadata
        assert "final_count" in metadata
        
        # Verify metadata values
        assert metadata["generation_method"] == "bom_normalization"
        assert metadata["source_count"] >= 0
        assert metadata["final_count"] >= 0
        assert metadata["final_count"] <= metadata["source_count"]
        
        print(f"✅ BOM metadata structure:")
        print(f"  Generated at: {metadata['generated_at']}")
        print(f"  Generation method: {metadata['generation_method']}")
        print(f"  Source count: {metadata['source_count']}")
        print(f"  Final count: {metadata['final_count']}")
    
    @pytest.mark.asyncio
    async def test_okh_manifest_component_metadata(self, mock_project_data, bom_enabled_config):
        """Test component metadata structure in OKH manifest"""
        engine = GenerationEngine(config=bom_enabled_config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        bom_data = okh_manifest["bom"]
        
        # Verify component metadata
        for component in bom_data["components"]:
            metadata = component["metadata"]
            assert "source" in metadata
            assert "confidence" in metadata
            assert "file_path" in metadata
            
            # Verify metadata values
            assert metadata["source"] in ["readme_materials", "bom_file", "documentation_materials"]
            assert 0.0 <= metadata["confidence"] <= 1.0
            assert metadata["file_path"] is not None
            
            # Check for file reference if present
            if "file_reference" in metadata:
                assert metadata["file_reference"] is not None
        
        print(f"✅ Component metadata structure:")
        for i, component in enumerate(bom_data["components"][:2]):  # Show first 2
            metadata = component["metadata"]
            print(f"  Component {i+1}: {component['name']}")
            print(f"    Source: {metadata['source']}")
            print(f"    Confidence: {metadata['confidence']:.2f}")
            print(f"    File path: {metadata['file_path']}")
            if "file_reference" in metadata:
                print(f"    File reference: {metadata['file_reference']}")
    
    def test_okh_manifest_json_serialization(self, mock_project_data, bom_enabled_config):
        """Test OKH manifest JSON serialization with BOM"""
        import json
        
        async def run_test():
            engine = GenerationEngine(config=bom_enabled_config)
            result = await engine.generate_manifest_async(mock_project_data)
            okh_manifest = result.to_okh_manifest()
            
            # Test JSON serialization
            json_str = json.dumps(okh_manifest, indent=2)
            assert len(json_str) > 0
            
            # Test JSON deserialization
            parsed_manifest = json.loads(json_str)
            assert "bom" in parsed_manifest
            assert isinstance(parsed_manifest["bom"], dict)
            
            return json_str, parsed_manifest
        
        # Run async test
        json_str, parsed_manifest = asyncio.run(run_test())
        
        print(f"✅ JSON serialization test:")
        print(f"  JSON length: {len(json_str)} characters")
        print(f"  BOM present in parsed: {'bom' in parsed_manifest}")
        print(f"  BOM components in parsed: {len(parsed_manifest['bom']['components'])}")
    
    @pytest.mark.asyncio
    async def test_okh_manifest_backward_compatibility(self, mock_project_data, bom_enabled_config):
        """Test OKH manifest backward compatibility"""
        engine = GenerationEngine(config=bom_enabled_config)
        result = await engine.generate_manifest_async(mock_project_data)
        
        # Convert to OKH manifest format
        okh_manifest = result.to_okh_manifest()
        
        # Verify all expected OKH fields are present
        expected_fields = [
            "okhv", "id", "title", "repo", "version", "license",
            "documentation_language", "function", "description",
            "intended_use", "contact", "organization", "development_stage",
            "manufacturing_files", "design_files", "making_instructions",
            "operating_instructions", "tool_list", "manufacturing_processes",
            "materials", "bom"
        ]
        
        for field in expected_fields:
            assert field in okh_manifest, f"Missing field: {field}"
        
        # Verify BOM is structured (not just a URL)
        assert isinstance(okh_manifest["bom"], dict)
        assert "components" in okh_manifest["bom"]
        
        print(f"✅ Backward compatibility test:")
        print(f"  All expected fields present: {len(expected_fields)}")
        print(f"  BOM is structured: {isinstance(okh_manifest['bom'], dict)}")
        print(f"  BOM has components: {'components' in okh_manifest['bom']}")
