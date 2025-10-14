"""
Test BOM normalization against the OpenFlexure Microscope project
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
from src.core.generation.bom_models import BOMCollector, BOMProcessor, BOMBuilder
from src.core.generation.platforms.github import GitHubExtractor


class TestOpenFlexureBOMComparison:
    """Test BOM normalization against real OpenFlexure Microscope data"""
    
    @pytest.fixture
    def openflexure_url(self):
        """OpenFlexure Microscope GitHub URL"""
        return "https://github.com/rwb27/openflexure_microscope"
    
    @pytest.fixture
    def expected_bom_components(self):
        """Expected BOM components from the existing manifest"""
        return [
            {"name": "PLA", "quantity": 500, "unit": "g"},
            {"name": "Actuator Assembly Tools", "material": "PLA"},
            {"name": "Actuator Column", "material": "PLA"},
            # Add more expected components based on the manifest
        ]
    
    @pytest.mark.asyncio
    async def test_openflexure_bom_extraction(self, openflexure_url):
        """Test BOM extraction from OpenFlexure Microscope repository"""
        # Extract project data from GitHub
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project(openflexure_url)
        
        # Verify we got real data
        assert project_data.platform == PlatformType.GITHUB
        assert project_data.url == openflexure_url
        assert len(project_data.files) > 0
        assert len(project_data.documentation) > 0
        
        print(f"✅ Extracted {len(project_data.files)} files and {len(project_data.documentation)} documents")
        
        # Step 1: Collect BOM data
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)
        
        print(f"📊 Found {len(sources)} BOM sources:")
        for source in sources:
            print(f"  - {source.source_type.value}: {source.file_path} (confidence: {source.confidence:.2f})")
            print(f"    Content preview: {source.raw_content[:100]}...")
        
        # Should find BOM sources
        assert len(sources) > 0
        
        # Step 2: Process BOM data
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)
        
        print(f"🔧 Processed {len(components)} components:")
        for component in components:
            print(f"  - {component.quantity} {component.name} ({component.unit})")
            if "file_reference" in component.metadata:
                print(f"    File: {component.metadata['file_reference']}")
        
        # Should extract components
        assert len(components) > 0
        
        # Step 3: Build final BOM
        builder = BOMBuilder()
        bom = builder.build_bom(components, "OpenFlexure Microscope BOM")
        
        print(f"📋 Final BOM: {len(bom.components)} components")
        print(f"📊 BOM metadata: {bom.metadata}")
        
        # Verify BOM structure
        from src.core.models.bom import BillOfMaterials
        assert isinstance(bom, BillOfMaterials)
        assert bom.name == "OpenFlexure Microscope BOM"
        assert len(bom.components) > 0
        
        return bom
    
    def test_bom_comparison_with_existing_manifest(self):
        """Compare our BOM extraction with the existing manifest"""
        # Load the existing manifest
        import json
        with open("test-data/openflexure-microscope.okh.json", "r") as f:
            existing_manifest = json.load(f)
        
        # Extract expected components from existing manifest
        expected_materials = existing_manifest.get("materials", [])
        expected_parts = existing_manifest.get("parts", [])
        
        print("📋 Existing manifest analysis:")
        print(f"  Materials: {len(expected_materials)} items")
        for material in expected_materials:
            print(f"    - {material.get('quantity', 'N/A')} {material.get('name', 'Unknown')} ({material.get('unit', 'N/A')})")
        
        print(f"  Parts: {len(expected_parts)} items")
        for part in expected_parts:
            print(f"    - {part.get('name', 'Unknown')} ({part.get('material', 'Unknown material')})")
        
        # This test will be expanded once we have the actual BOM extraction results
        assert len(expected_materials) > 0
        assert len(expected_parts) > 0
    
    @pytest.mark.asyncio
    async def test_bom_quality_assessment(self, openflexure_url):
        """Assess the quality of BOM extraction"""
        # Extract and process BOM data
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project(openflexure_url)
        
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)
        
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)
        
        builder = BOMBuilder()
        bom = builder.build_bom(components, "OpenFlexure Microscope BOM")
        
        # Quality assessment
        quality_metrics = {
            "total_sources": len(sources),
            "total_components": len(bom.components),
            "avg_confidence": sum(c.metadata.get("confidence", 0) for c in bom.components) / len(bom.components) if bom.components else 0,
            "sources_with_high_confidence": len([s for s in sources if s.confidence > 0.8]),
            "components_with_file_refs": len([c for c in bom.components if "file_reference" in c.metadata])
        }
        
        print("📊 BOM Quality Assessment:")
        for metric, value in quality_metrics.items():
            print(f"  {metric}: {value}")
        
        # Quality thresholds
        assert quality_metrics["total_sources"] > 0, "Should find at least one BOM source"
        assert quality_metrics["total_components"] > 0, "Should extract at least one component"
        assert quality_metrics["avg_confidence"] > 0.5, "Average confidence should be reasonable"
        
        return quality_metrics
    
    def test_bom_normalization_benefits(self):
        """Demonstrate the benefits of BOM normalization"""
        # Load existing manifest
        import json
        with open("test-data/openflexure-microscope.okh.json", "r") as f:
            existing_manifest = json.load(f)
        
        # Analyze current structure
        current_structure = {
            "materials_field": existing_manifest.get("materials", []),
            "bom_field": existing_manifest.get("bom", ""),
            "parts_field": existing_manifest.get("parts", [])
        }
        
        print("🔍 Current manifest structure analysis:")
        print(f"  Materials field: {len(current_structure['materials_field'])} items")
        print(f"  BOM field: {'URL' if current_structure['bom_field'] else 'Empty'}")
        print(f"  Parts field: {len(current_structure['parts_field'])} items")
        
        # Identify redundancy and issues
        issues = []
        
        # Check for redundancy between materials and parts
        materials_names = [m.get("name", "").lower() for m in current_structure["materials_field"]]
        parts_materials = [p.get("material", "").lower() for p in current_structure["parts_field"]]
        
        if any(mat in parts_materials for mat in materials_names):
            issues.append("Redundancy between materials and parts fields")
        
        if not current_structure["bom_field"]:
            issues.append("BOM field is empty (should contain structured data)")
        
        if len(current_structure["materials_field"]) == 0:
            issues.append("Materials field is empty")
        
        print("⚠️  Issues identified:")
        for issue in issues:
            print(f"  - {issue}")
        
        print("✅ Benefits of BOM normalization:")
        print("  - Single source of truth for all materials/components")
        print("  - Structured data with quantities, units, and metadata")
        print("  - Automatic deduplication from multiple sources")
        print("  - Confidence scoring for data quality")
        print("  - File references and traceability")
        
        return {
            "current_structure": current_structure,
            "issues": issues,
            "benefits": [
                "Single source of truth",
                "Structured data",
                "Automatic deduplication", 
                "Confidence scoring",
                "File references and traceability"
            ]
        }
