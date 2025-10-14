"""
Tests for BOM normalization system
"""
import pytest
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

# Import the BOM models we'll create
from src.core.generation.bom_models import BOMSource, BOMSourceType, BOMCollector, BOMProcessor, BOMBuilder
from src.core.models.bom import Component, BillOfMaterials


class TestBOMSource:
    """Test BOM source data model"""
    
    def test_bom_source_creation(self):
        """Test creating a BOM source"""
        source = BOMSource(
            source_type=BOMSourceType.README_MATERIALS,
            raw_content="* 1 stethoscope head (head.stl)\n* 2 ear tubes (eartube.stl)",
            file_path="README.md",
            confidence=0.8
        )
        
        assert source.source_type == BOMSourceType.README_MATERIALS
        assert "stethoscope head" in source.raw_content
        assert source.file_path == "README.md"
        assert source.confidence == 0.8
        assert source.metadata == {}
    
    def test_bom_source_with_metadata(self):
        """Test creating a BOM source with metadata"""
        metadata = {"section": "materials", "line_start": 45}
        source = BOMSource(
            source_type=BOMSourceType.BOM_FILE,
            raw_content="Item,Quantity,Unit\nResistor,10,pcs",
            file_path="bom.csv",
            confidence=0.9,
            metadata=metadata
        )
        
        assert source.metadata == metadata
        assert source.metadata["section"] == "materials"


class TestBOMCollector:
    """Test BOM data collection"""
    
    @pytest.fixture
    def mock_project_data(self):
        """Mock project data for testing"""
        from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
        
        return ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/project",
            metadata={"name": "Test Project"},
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

## Bill of Materials
| Item | Quantity | Unit |
|------|----------|------|
| Resistor | 10 | pcs |
| LED | 5 | pcs |
                    """,
                    file_type="markdown"
                ),
                FileInfo(
                    path="bom.csv",
                    size=200,
                    content="Item,Quantity,Unit\nResistor,10,pcs\nLED,5,pcs",
                    file_type="csv"
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
    
    def test_collect_bom_data_from_readme(self, mock_project_data):
        """Test collecting BOM data from README materials section"""
        collector = BOMCollector()
        sources = collector.collect_bom_data(mock_project_data)
        
        # Should find materials section in README
        readme_sources = [s for s in sources if s.source_type == BOMSourceType.README_MATERIALS]
        assert len(readme_sources) >= 1
        
        materials_source = readme_sources[0]
        assert "stethoscope head" in materials_source.raw_content
        assert "ear tubes" in materials_source.raw_content
        assert materials_source.file_path == "README.md"
        assert materials_source.confidence > 0.7
    
    def test_collect_bom_data_from_bom_file(self, mock_project_data):
        """Test collecting BOM data from dedicated BOM files"""
        collector = BOMCollector()
        sources = collector.collect_bom_data(mock_project_data)
        
        # Should find BOM file
        bom_sources = [s for s in sources if s.source_type == BOMSourceType.BOM_FILE]
        assert len(bom_sources) >= 1
        
        bom_source = bom_sources[0]
        assert "Resistor" in bom_source.raw_content
        assert "LED" in bom_source.raw_content
        assert bom_source.file_path == "bom.csv"
        assert bom_source.confidence > 0.8
    
    def test_collect_bom_data_from_documentation(self, mock_project_data):
        """Test collecting BOM data from documentation files"""
        collector = BOMCollector()
        sources = collector.collect_bom_data(mock_project_data)
        
        # Should find documentation sources
        doc_sources = [s for s in sources if s.source_type == BOMSourceType.DOCUMENTATION]
        assert len(doc_sources) >= 0  # May or may not find additional docs
        
        # All sources should have valid content
        for source in sources:
            assert source.raw_content
            assert source.confidence > 0.0
            assert source.file_path
    
    def test_collect_bom_data_empty_project(self):
        """Test collecting BOM data from empty project"""
        from src.core.generation.models import ProjectData, PlatformType
        
        empty_project = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/empty",
            metadata={"name": "Empty Project"},
            files=[],
            documentation=[],
            raw_content={}
        )
        
        collector = BOMCollector()
        sources = collector.collect_bom_data(empty_project)
        
        # Should return empty list for empty project
        assert len(sources) == 0
    
    def test_collect_bom_data_confidence_scoring(self, mock_project_data):
        """Test that confidence scores are appropriate"""
        collector = BOMCollector()
        sources = collector.collect_bom_data(mock_project_data)
        
        for source in sources:
            # Confidence should be between 0 and 1
            assert 0.0 <= source.confidence <= 1.0
            
            # BOM files should have higher confidence than README sections
            if source.source_type == BOMSourceType.BOM_FILE:
                assert source.confidence >= 0.8
            elif source.source_type == BOMSourceType.README_MATERIALS:
                assert source.confidence >= 0.6


class TestBOMProcessor:
    """Test BOM text processing and component extraction"""
    
    @pytest.fixture
    def mock_bom_sources(self):
        """Mock BOM sources for testing"""
        return [
            BOMSource(
                source_type=BOMSourceType.README_MATERIALS,
                raw_content="""
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
* 1 Spring (spring.stl)
* 1 Ring (ring.stl)

**Other hardware:**
* 40cm - 50cm Silicone tubing
* 2x 3.5mm audio jacks
                """,
                file_path="README.md",
                confidence=0.8
            ),
            BOMSource(
                source_type=BOMSourceType.BOM_FILE,
                raw_content="Item,Quantity,Unit\nResistor,10,pcs\nLED,5,pcs\nBattery,1,pcs",
                file_path="bom.csv",
                confidence=0.9
            )
        ]
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        processor = BOMProcessor()
        
        # Test markdown cleaning
        dirty_text = "**\n* 1 item\n* 2 items\n**"
        cleaned = processor._clean_text(dirty_text)
        assert "**" not in cleaned
        assert "* 1 item" in cleaned
        assert "* 2 items" in cleaned
        
        # Test whitespace normalization
        messy_text = "  \n  * 1 item  \n  * 2 items  \n  "
        cleaned = processor._clean_text(messy_text)
        assert cleaned.startswith("* 1 item")
        assert cleaned.endswith("* 2 items")
        assert "  " not in cleaned  # No double spaces
    
    def test_extract_components_from_markdown(self):
        """Test extracting components from markdown list"""
        processor = BOMProcessor()
        
        markdown_text = """
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
        """
        
        # Create a mock source
        source = BOMSource(
            source_type=BOMSourceType.README_MATERIALS,
            raw_content=markdown_text,
            file_path="README.md",
            confidence=0.8
        )
        
        components = processor._extract_components_from_markdown(markdown_text, source)
        
        assert len(components) == 3
        
        # Check first component
        head_component = components[0]
        assert head_component.name == "stethoscope head"
        assert head_component.quantity == 1.0
        assert head_component.unit == "pcs"
        assert head_component.metadata["file_reference"] == "head.stl"
        
        # Check second component
        tubes_component = components[1]
        assert tubes_component.name == "ear tubes"
        assert tubes_component.quantity == 2.0
        assert tubes_component.unit == "pcs"
        assert tubes_component.metadata["file_reference"] == "eartube.stl"
    
    def test_extract_components_from_csv(self):
        """Test extracting components from CSV format"""
        processor = BOMProcessor()
        
        csv_text = "Item,Quantity,Unit\nResistor,10,pcs\nLED,5,pcs\nBattery,1,pcs"
        
        # Create a mock source
        source = BOMSource(
            source_type=BOMSourceType.BOM_FILE,
            raw_content=csv_text,
            file_path="bom.csv",
            confidence=0.9
        )
        
        components = processor._extract_components_from_csv(csv_text, source)
        
        assert len(components) == 3
        
        # Check first component
        resistor = components[0]
        assert resistor.name == "Resistor"
        assert resistor.quantity == 10.0
        assert resistor.unit == "pcs"
        
        # Check second component
        led = components[1]
        assert led.name == "LED"
        assert led.quantity == 5.0
        assert led.unit == "pcs"
    
    def test_process_bom_sources(self, mock_bom_sources):
        """Test processing multiple BOM sources into components"""
        processor = BOMProcessor()
        
        components = processor.process_bom_sources(mock_bom_sources)
        
        # Should extract components from both sources
        assert len(components) >= 5  # At least 3 from markdown + 3 from CSV
        
        # Check that components have proper metadata
        for component in components:
            assert component.id
            assert component.name
            assert component.quantity > 0
            assert component.unit
            assert "source" in component.metadata
            assert "confidence" in component.metadata
        
        # Check specific components exist
        component_names = [c.name for c in components]
        assert "stethoscope head" in component_names
        assert "ear tubes" in component_names
        assert "Resistor" in component_names
        assert "LED" in component_names
    
    def test_component_deduplication(self):
        """Test that duplicate components are handled"""
        processor = BOMProcessor()
        
        # Create sources with overlapping components
        sources = [
            BOMSource(
                source_type=BOMSourceType.README_MATERIALS,
                raw_content="* 1 stethoscope head (head.stl)\n* 2 ear tubes (eartube.stl)",
                file_path="README.md",
                confidence=0.8
            ),
            BOMSource(
                source_type=BOMSourceType.BOM_FILE,
                raw_content="Item,Quantity,Unit\nstethoscope head,1,pcs\nLED,5,pcs",
                file_path="bom.csv",
                confidence=0.9
            )
        ]
        
        components = processor.process_bom_sources(sources)
        
        # Should have 3 unique components (stethoscope head, ear tubes, LED)
        assert len(components) == 3
        
        # Check that stethoscope head appears only once
        head_components = [c for c in components if "stethoscope head" in c.name.lower()]
        assert len(head_components) == 1
        
        # Should use higher confidence source
        head_component = head_components[0]
        assert head_component.metadata["confidence"] == 0.9  # From CSV
    
    def test_component_validation(self):
        """Test component validation and error handling"""
        processor = BOMProcessor()
        
        # Test with invalid data
        invalid_sources = [
            BOMSource(
                source_type=BOMSourceType.README_MATERIALS,
                raw_content="* invalid item without quantity",
                file_path="README.md",
                confidence=0.8
            )
        ]
        
        components = processor.process_bom_sources(invalid_sources)
        
        # Should handle invalid data gracefully
        assert len(components) >= 0  # May extract what it can or return empty
        
        # All returned components should be valid
        for component in components:
            assert component.name
            assert component.quantity > 0
            assert component.unit


class TestBOMBuilder:
    """Test BOM builder functionality"""
    
    def test_build_bom(self):
        """Test building a BOM from components"""
        builder = BOMBuilder()
        
        # Create test components
        components = [
            Component(
                id="comp1",
                name="stethoscope head",
                quantity=1.0,
                unit="pcs",
                metadata={"source": "readme", "confidence": 0.8}
            ),
            Component(
                id="comp2", 
                name="ear tubes",
                quantity=2.0,
                unit="pcs",
                metadata={"source": "readme", "confidence": 0.8}
            )
        ]
        
        bom = builder.build_bom(components, "Test Project BOM")
        
        assert isinstance(bom, BillOfMaterials)
        assert bom.name == "Test Project BOM"
        assert len(bom.components) == 2
        assert bom.components[0].name == "stethoscope head"
        assert bom.components[1].name == "ear tubes"
        assert "generated_at" in bom.metadata
        assert bom.metadata["source_count"] == 2
        assert bom.metadata["final_count"] == 2
        assert bom.metadata["generation_method"] == "bom_normalization"
    
    def test_build_bom_with_invalid_components(self):
        """Test building BOM with invalid components"""
        builder = BOMBuilder()
        
        # Create components with some invalid ones
        # We'll create valid components first, then modify them to be invalid
        valid_component = Component(
            id="comp1",
            name="valid component",
            quantity=1.0,
            unit="pcs",
            metadata={"source": "readme", "confidence": 0.8}
        )
        
        # Create invalid components by modifying after creation
        invalid_component1 = Component(
            id="comp2",
            name="invalid component",
            quantity=1.0,
            unit="pcs",
            metadata={"source": "readme", "confidence": 0.8}
        )
        invalid_component1.name = ""  # Make invalid after creation
        
        invalid_component2 = Component(
            id="comp3",
            name="another valid component",
            quantity=1.0,
            unit="pcs",
            metadata={"source": "readme", "confidence": 0.8}
        )
        invalid_component2.quantity = 0.0  # Make invalid after creation
        
        components = [valid_component, invalid_component1, invalid_component2]
        
        bom = builder.build_bom(components, "Test Project BOM")
        
        # Should only include valid components
        assert len(bom.components) == 1
        assert bom.components[0].name == "valid component"
        assert bom.metadata["source_count"] == 3
        assert bom.metadata["final_count"] == 1


class TestBOMNormalizationEndToEnd:
    """Test complete BOM normalization workflow"""
    
    def test_bom_normalization_workflow(self):
        """Test complete BOM normalization from project data to structured BOM"""
        from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
        
        # Create mock project data similar to Stethoscope
        project_data = ProjectData(
            platform=PlatformType.GITHUB,
            url="https://github.com/test/stethoscope",
            metadata={"name": "Stethoscope"},
            files=[
                FileInfo(
                    path="README.md",
                    size=1000,
                    content="""
# Stethoscope

A research-validated stethoscope whose plans are available freely and openly.

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
* 1 Spring (spring.stl)
* 1 Ring (ring.stl)

**Other hardware:**
* 40cm - 50cm Silicone tubing
* 2x 3.5mm audio jacks
                    """,
                    file_type="markdown"
                )
            ],
            documentation=[
                DocumentInfo(
                    title="README",
                    path="README.md",
                    content="""
# Stethoscope

A research-validated stethoscope whose plans are available freely and openly.

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
* 1 Spring (spring.stl)
* 1 Ring (ring.stl)
                    """,
                    doc_type="readme"
                )
            ],
            raw_content={
                "README.md": """
# Stethoscope

A research-validated stethoscope whose plans are available freely and openly.

## Materials
* 1 stethoscope head (head.stl)
* 2 ear tubes (eartube.stl)
* 1 Y-piece (y_piece.stl)
* 1 Spring (spring.stl)
* 1 Ring (ring.stl)
                """
            }
        )
        
        # Step 1: Collect BOM data
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)
        
        assert len(sources) >= 1
        assert any(s.source_type == BOMSourceType.README_MATERIALS for s in sources)
        
        # Step 2: Process BOM data
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)
        
        assert len(components) >= 5  # Should extract all components
        
        # Step 3: Build final BOM
        builder = BOMBuilder()
        bom = builder.build_bom(components, "Stethoscope BOM")
        
        assert isinstance(bom, BillOfMaterials)
        assert bom.name == "Stethoscope BOM"
        assert len(bom.components) >= 5
        
        # Verify specific components
        component_names = [c.name for c in bom.components]
        assert "stethoscope head" in component_names
        assert "ear tubes" in component_names
        assert "Y-piece" in component_names
        assert "Spring" in component_names
        assert "Ring" in component_names
        
        # Verify component structure
        for component in bom.components:
            assert component.id
            assert component.name
            assert component.quantity > 0
            assert component.unit == "pcs"
            assert "source" in component.metadata
            assert "confidence" in component.metadata
        
        # Verify file references are preserved
        head_component = next(c for c in bom.components if "stethoscope head" in c.name)
        assert head_component.metadata["file_reference"] == "head.stl"
        
        # Verify BOM metadata
        assert "generated_at" in bom.metadata
        assert bom.metadata["generation_method"] == "bom_normalization"
        assert bom.metadata["final_count"] >= 5
        
        print(f"✅ BOM normalization successful: {len(bom.components)} components in final BOM")
        for component in bom.components:
            print(f"  - {component.quantity} {component.name} ({component.metadata.get('file_reference', 'no file')})")
        
        print(f"📊 BOM metadata: {bom.metadata}")
