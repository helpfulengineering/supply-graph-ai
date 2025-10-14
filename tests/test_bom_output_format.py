"""
Test BOM output format integration with OKH manifest and built directory structure
"""
import pytest
import json
import asyncio
from pathlib import Path
from src.core.generation.platforms.github import GitHubExtractor
from src.core.generation.bom_models import BOMCollector, BOMProcessor, BOMBuilder
from src.core.models.bom import BillOfMaterials, Component


class TestBOMOutputFormat:
    """Test BOM output format for OKH manifest integration"""
    
    @pytest.mark.asyncio
    async def test_bom_okh_manifest_integration(self):
        """Test how BOM should integrate with OKH manifest structure"""
        # Extract and process BOM data
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project('https://github.com/rwb27/openflexure_microscope')
        
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)
        
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)
        
        builder = BOMBuilder()
        bom = builder.build_bom(components, 'OpenFlexure Microscope BOM')
        
        # Test OKH manifest integration formats
        print("🔍 BOM Integration Analysis:")
        
        # Format 1: Replace the current 'bom' field (URL) with structured BOM
        okh_manifest_bom_field = {
            "bom": bom.to_dict()  # Replace URL with structured BOM
        }
        
        # Format 2: Add BOM as a separate field while keeping materials
        okh_manifest_with_both = {
            "materials": [
                {
                    "material_id": "PLA",
                    "name": "Polylactic Acid", 
                    "quantity": 500,
                    "unit": "g",
                    "notes": "Primary material for 3D printing"
                }
            ],
            "bom": bom.to_dict()  # Structured BOM
        }
        
        # Format 3: Normalized approach - only structured BOM
        okh_manifest_normalized = {
            "bom": bom.to_dict()  # Single source of truth
        }
        
        print("📋 Format 1 - Replace BOM URL with structured BOM:")
        print(f"  BOM field type: {type(okh_manifest_bom_field['bom'])}")
        print(f"  Components count: {len(okh_manifest_bom_field['bom']['components'])}")
        
        print("\n📋 Format 2 - Keep both materials and structured BOM:")
        print(f"  Materials count: {len(okh_manifest_with_both['materials'])}")
        print(f"  BOM components count: {len(okh_manifest_with_both['bom']['components'])}")
        
        print("\n📋 Format 3 - Normalized (recommended):")
        print(f"  BOM components count: {len(okh_manifest_normalized['bom']['components'])}")
        
        # Validate BOM structure
        assert isinstance(bom, BillOfMaterials)
        assert len(bom.components) > 0
        assert all(isinstance(comp, Component) for comp in bom.components)
        
        return {
            "bom_object": bom,
            "okh_formats": {
                "replace_url": okh_manifest_bom_field,
                "keep_both": okh_manifest_with_both, 
                "normalized": okh_manifest_normalized
            }
        }
    
    def test_bom_built_directory_structure(self):
        """Test BOM output for built directory structure"""
        # Simulate a BOM for built directory
        bom_data = {
            "id": "test-bom-123",
            "name": "Test Project BOM",
            "components": [
                {
                    "id": "comp1",
                    "name": "M3x25mm hexagon head screws",
                    "quantity": 3.0,
                    "unit": "pcs",
                    "requirements": {},
                    "metadata": {
                        "source": "bom_file",
                        "file_path": "docs/0_bill_of_materials.md",
                        "confidence": 0.9,
                        "file_reference": "./parts/fixings/m3x25mm_hexagonhead_screw.md"
                    }
                }
            ],
            "metadata": {
                "generated_at": "2025-10-14T12:43:14.265685Z",
                "source_count": 1,
                "final_count": 1,
                "generation_method": "bom_normalization"
            }
        }
        
        # Test built directory structure options
        built_directory_options = {
            "option_1": {
                "description": "BOM as separate file in built directory",
                "structure": {
                    "built/": {
                        "manifest.okh.json": "OKH manifest with BOM reference",
                        "bom.json": "Structured BOM file",
                        "bom.md": "Human-readable BOM"
                    }
                }
            },
            "option_2": {
                "description": "BOM embedded in manifest",
                "structure": {
                    "built/": {
                        "manifest.okh.json": "OKH manifest with embedded BOM"
                    }
                }
            },
            "option_3": {
                "description": "Multiple BOM formats",
                "structure": {
                    "built/": {
                        "manifest.okh.json": "OKH manifest",
                        "bom/": {
                            "bom.json": "Structured BOM",
                            "bom.md": "Human-readable BOM", 
                            "bom.csv": "CSV export",
                            "components/": "Individual component files"
                        }
                    }
                }
            }
        }
        
        print("📁 Built Directory Structure Options:")
        for option, details in built_directory_options.items():
            print(f"\n{option}: {details['description']}")
            print(f"  Structure: {details['structure']}")
        
        # Test JSON serialization for built directory
        bom_json = json.dumps(bom_data, indent=2)
        print(f"\n📄 BOM JSON for built directory ({len(bom_json)} chars):")
        print(bom_json[:200] + "...")
        
        return {
            "bom_data": bom_data,
            "built_options": built_directory_options,
            "json_output": bom_json
        }
    
    def test_bom_component_metadata_analysis(self):
        """Analyze component metadata for built directory integration"""
        # Create test component with rich metadata
        component = Component(
            id="test-component-123",
            name="M3x25mm hexagon head screws",
            quantity=3.0,
            unit="pcs",
            metadata={
                "source": "bom_file",
                "file_path": "docs/0_bill_of_materials.md",
                "confidence": 0.9,
                "file_reference": "./parts/fixings/m3x25mm_hexagonhead_screw.md",
                "category": "hardware",
                "subcategory": "fasteners",
                "material": "stainless_steel",
                "supplier_info": {
                    "common_suppliers": ["McMaster-Carr", "Fastenal"],
                    "part_numbers": ["91290A115", "M3-0.5x25"]
                }
            }
        )
        
        # Analyze metadata structure
        metadata_analysis = {
            "core_fields": ["source", "file_path", "confidence", "file_reference"],
            "extended_fields": ["category", "subcategory", "material", "supplier_info"],
            "built_directory_usage": {
                "file_reference": "Link to detailed part documentation",
                "confidence": "Quality indicator for generated data",
                "source": "Traceability for data origin",
                "category": "Component classification for organization"
            }
        }
        
        print("🔍 Component Metadata Analysis:")
        print(f"  Core fields: {metadata_analysis['core_fields']}")
        print(f"  Extended fields: {metadata_analysis['extended_fields']}")
        print(f"  Built directory usage: {metadata_analysis['built_directory_usage']}")
        
        # Test component serialization
        component_dict = component.to_dict()
        print(f"\n📄 Component JSON ({len(json.dumps(component_dict))} chars):")
        print(json.dumps(component_dict, indent=2)[:300] + "...")
        
        return {
            "component": component,
            "metadata_analysis": metadata_analysis,
            "component_dict": component_dict
        }
    
    def test_bom_export_formats(self):
        """Test different BOM export formats for built directory"""
        # Create test BOM
        bom = BillOfMaterials(
            name="Test Project BOM",
            components=[
                Component(
                    id="comp1",
                    name="M3x25mm hexagon head screws",
                    quantity=3.0,
                    unit="pcs",
                    metadata={"source": "bom_file", "confidence": 0.9}
                ),
                Component(
                    id="comp2", 
                    name="PLA filament",
                    quantity=500.0,
                    unit="g",
                    metadata={"source": "readme", "confidence": 0.8}
                )
            ]
        )
        
        # Test different export formats
        export_formats = {
            "json": {
                "format": "JSON",
                "content": json.dumps(bom.to_dict(), indent=2),
                "use_case": "Machine-readable, full metadata"
            },
            "csv": {
                "format": "CSV", 
                "content": self._bom_to_csv(bom),
                "use_case": "Spreadsheet import, simple view"
            },
            "markdown": {
                "format": "Markdown",
                "content": self._bom_to_markdown(bom),
                "use_case": "Human-readable documentation"
            },
            "summary": {
                "format": "Summary",
                "content": self._bom_to_summary(bom),
                "use_case": "Quick overview"
            }
        }
        
        print("📤 BOM Export Formats:")
        for format_name, format_data in export_formats.items():
            print(f"\n{format_name.upper()}:")
            print(f"  Use case: {format_data['use_case']}")
            print(f"  Content preview: {format_data['content'][:100]}...")
        
        return {
            "bom": bom,
            "export_formats": export_formats
        }
    
    def _bom_to_csv(self, bom: BillOfMaterials) -> str:
        """Convert BOM to CSV format"""
        lines = ["ID,Name,Quantity,Unit,Source,Confidence"]
        for comp in bom.components:
            lines.append(f"{comp.id},{comp.name},{comp.quantity},{comp.unit},{comp.metadata.get('source', '')},{comp.metadata.get('confidence', '')}")
        return "\n".join(lines)
    
    def _bom_to_markdown(self, bom: BillOfMaterials) -> str:
        """Convert BOM to Markdown format"""
        lines = [f"# {bom.name}", "", "| ID | Name | Quantity | Unit | Source |", "|----|------|----------|------|--------|"]
        for comp in bom.components:
            lines.append(f"| {comp.id} | {comp.name} | {comp.quantity} | {comp.unit} | {comp.metadata.get('source', '')} |")
        return "\n".join(lines)
    
    def _bom_to_summary(self, bom: BillOfMaterials) -> str:
        """Convert BOM to summary format"""
        total_components = len(bom.components)
        total_quantity = sum(comp.quantity for comp in bom.components)
        sources = set(comp.metadata.get('source', '') for comp in bom.components)
        
        return f"BOM Summary: {total_components} components, {total_quantity} total quantity, sources: {', '.join(sources)}"
