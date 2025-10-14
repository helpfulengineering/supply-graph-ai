"""
Tests for BOM built directory export functionality
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from src.core.generation.built_directory import BuiltDirectoryExporter
from src.core.models.bom import BillOfMaterials, Component


class TestBOMBuiltDirectory:
    """Test BOM built directory export functionality"""
    
    @pytest.fixture
    def sample_bom(self):
        """Create a sample BOM for testing"""
        components = [
            Component(
                id="comp1",
                name="M3x25mm hexagon head screws",
                quantity=3.0,
                unit="pcs",
                metadata={
                    "source": "bom_file",
                    "file_path": "docs/0_bill_of_materials.md",
                    "confidence": 0.9,
                    "file_reference": "./parts/fixings/m3x25mm_hexagonhead_screw.md"
                }
            ),
            Component(
                id="comp2",
                name="PLA filament",
                quantity=500.0,
                unit="g",
                metadata={
                    "source": "readme_materials",
                    "file_path": "README.md",
                    "confidence": 0.8
                }
            )
        ]
        
        return BillOfMaterials(
            name="Test Project BOM",
            components=components,
            metadata={
                "generated_at": "2025-10-14T12:43:14.265685Z",
                "source_count": 2,
                "final_count": 2,
                "generation_method": "bom_normalization"
            }
        )
    
    @pytest.fixture
    def sample_manifest(self):
        """Create a sample OKH manifest for testing"""
        return {
            "okhv": "OKH-LOSHv1.0",
            "id": "test-manifest-123",
            "title": "Test Project",
            "repo": "https://github.com/test/project",
            "version": "1.0.0",
            "bom": {
                "id": "test-bom-123",
                "name": "Test Project BOM",
                "components": [
                    {
                        "id": "comp1",
                        "name": "M3x25mm hexagon head screws",
                        "quantity": 3.0,
                        "unit": "pcs"
                    }
                ]
            }
        }
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_built_directory_exporter_initialization(self, temp_output_dir):
        """Test BuiltDirectoryExporter initialization"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        
        assert exporter.output_dir == temp_output_dir
        assert exporter.bom_dir == temp_output_dir / "bom"
        assert exporter.docs_dir == temp_output_dir / "docs"
        
        print(f"✅ BuiltDirectoryExporter initialized:")
        print(f"  Output dir: {exporter.output_dir}")
        print(f"  BOM dir: {exporter.bom_dir}")
        print(f"  Docs dir: {exporter.docs_dir}")
    
    @pytest.mark.asyncio
    async def test_export_manifest_with_bom(self, sample_manifest, sample_bom, temp_output_dir):
        """Test exporting manifest with BOM to built directory"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        
        # Export manifest and BOM
        await exporter.export_manifest_with_bom(sample_manifest, sample_bom)
        
        # Verify main manifest file
        manifest_path = temp_output_dir / "manifest.okh.json"
        assert manifest_path.exists()
        
        with open(manifest_path, 'r') as f:
            exported_manifest = json.load(f)
        
        assert exported_manifest["title"] == "Test Project"
        assert exported_manifest["bom"]["name"] == "Test Project BOM"
        
        # Verify BOM directory structure
        assert exporter.bom_dir.exists()
        assert (exporter.bom_dir / "bom.json").exists()
        assert (exporter.bom_dir / "bom.md").exists()
        assert (exporter.bom_dir / "bom.csv").exists()
        assert (exporter.bom_dir / "components").exists()
        
        print(f"✅ Manifest and BOM exported successfully:")
        print(f"  Manifest file: {manifest_path}")
        print(f"  BOM directory: {exporter.bom_dir}")
        print(f"  BOM files: {list(exporter.bom_dir.glob('*'))}")
    
    @pytest.mark.asyncio
    async def test_export_bom_json_format(self, sample_bom, temp_output_dir):
        """Test BOM JSON export format"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        await exporter._export_bom_formats(sample_bom)
        
        # Verify JSON file
        bom_json_path = exporter.bom_dir / "bom.json"
        assert bom_json_path.exists()
        
        with open(bom_json_path, 'r') as f:
            bom_data = json.load(f)
        
        assert bom_data["name"] == "Test Project BOM"
        assert len(bom_data["components"]) == 2
        assert bom_data["components"][0]["name"] == "M3x25mm hexagon head screws"
        assert bom_data["components"][1]["name"] == "PLA filament"
        
        print(f"✅ BOM JSON export:")
        print(f"  File: {bom_json_path}")
        print(f"  Components: {len(bom_data['components'])}")
        print(f"  First component: {bom_data['components'][0]['name']}")
    
    @pytest.mark.asyncio
    async def test_export_bom_markdown_format(self, sample_bom, temp_output_dir):
        """Test BOM Markdown export format"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        await exporter._export_bom_formats(sample_bom)
        
        # Verify Markdown file
        bom_md_path = exporter.bom_dir / "bom.md"
        assert bom_md_path.exists()
        
        with open(bom_md_path, 'r') as f:
            bom_md_content = f.read()
        
        # Check Markdown structure
        assert "# Test Project BOM" in bom_md_content
        assert "**Generated:**" in bom_md_content
        assert "**Components:** 2" in bom_md_content
        assert "| ID | Name | Quantity | Unit | Source | Confidence |" in bom_md_content
        assert "M3x25mm hexagon head screws" in bom_md_content
        assert "PLA filament" in bom_md_content
        
        print(f"✅ BOM Markdown export:")
        print(f"  File: {bom_md_path}")
        print(f"  Content length: {len(bom_md_content)} characters")
        print(f"  Contains table: {'|' in bom_md_content}")
    
    @pytest.mark.asyncio
    async def test_export_bom_csv_format(self, sample_bom, temp_output_dir):
        """Test BOM CSV export format"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        await exporter._export_bom_formats(sample_bom)
        
        # Verify CSV file
        bom_csv_path = exporter.bom_dir / "bom.csv"
        assert bom_csv_path.exists()
        
        with open(bom_csv_path, 'r') as f:
            bom_csv_content = f.read()
        
        # Check CSV structure
        lines = bom_csv_content.strip().split('\n')
        assert len(lines) == 3  # Header + 2 components
        assert "ID,Name,Quantity,Unit,Source,Confidence,File_Reference" in lines[0]
        assert "comp1,M3x25mm hexagon head screws,3.0,pcs,bom_file,0.9" in lines[1]
        assert "comp2,PLA filament,500.0,g,readme_materials,0.8" in lines[2]
        
        print(f"✅ BOM CSV export:")
        print(f"  File: {bom_csv_path}")
        print(f"  Lines: {len(lines)}")
        print(f"  Header: {lines[0]}")
    
    @pytest.mark.asyncio
    async def test_export_individual_components(self, sample_bom, temp_output_dir):
        """Test individual component file export"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        await exporter._export_bom_formats(sample_bom)
        
        # Verify components directory
        components_dir = exporter.bom_dir / "components"
        assert components_dir.exists()
        
        # Verify individual component files
        comp1_path = components_dir / "comp1.json"
        comp2_path = components_dir / "comp2.json"
        
        assert comp1_path.exists()
        assert comp2_path.exists()
        
        # Verify component file content
        with open(comp1_path, 'r') as f:
            comp1_data = json.load(f)
        
        assert comp1_data["id"] == "comp1"
        assert comp1_data["name"] == "M3x25mm hexagon head screws"
        assert comp1_data["quantity"] == 3.0
        assert comp1_data["unit"] == "pcs"
        
        print(f"✅ Individual component export:")
        print(f"  Components dir: {components_dir}")
        print(f"  Component files: {list(components_dir.glob('*.json'))}")
        print(f"  Comp1 name: {comp1_data['name']}")
    
    def test_bom_to_markdown_conversion(self, sample_bom):
        """Test BOM to Markdown conversion"""
        exporter = BuiltDirectoryExporter(Path("/tmp"))
        markdown_content = exporter._bom_to_markdown(sample_bom)
        
        # Verify Markdown structure
        assert "# Test Project BOM" in markdown_content
        assert "**Generated:**" in markdown_content
        assert "**Components:** 2" in markdown_content
        assert "**Sources:** 2" in markdown_content
        
        # Verify table structure
        lines = markdown_content.split('\n')
        table_start = next(i for i, line in enumerate(lines) if "| ID |" in line)
        table_lines = lines[table_start:table_start + 4]  # Header + 2 components + separator
        
        assert "| ID | Name | Quantity | Unit | Source | Confidence |" in table_lines[0]
        assert "|----|------|----------|------|--------|------------|" in table_lines[1]
        assert "M3x25mm hexagon head screws" in table_lines[2]
        assert "PLA filament" in table_lines[3]
        
        print(f"✅ BOM to Markdown conversion:")
        print(f"  Content length: {len(markdown_content)} characters")
        print(f"  Table lines: {len([l for l in lines if '|' in l])}")
    
    def test_bom_to_csv_conversion(self, sample_bom):
        """Test BOM to CSV conversion"""
        exporter = BuiltDirectoryExporter(Path("/tmp"))
        csv_content = exporter._bom_to_csv(sample_bom)
        
        # Verify CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) == 3  # Header + 2 components
        
        # Verify header
        header = lines[0]
        expected_columns = ["ID", "Name", "Quantity", "Unit", "Source", "Confidence", "File_Reference"]
        for col in expected_columns:
            assert col in header
        
        # Verify data rows
        comp1_row = lines[1]
        comp2_row = lines[2]
        
        assert "comp1,M3x25mm hexagon head screws,3.0,pcs,bom_file,0.9" in comp1_row
        assert "comp2,PLA filament,500.0,g,readme_materials,0.8" in comp2_row
        
        print(f"✅ BOM to CSV conversion:")
        print(f"  Lines: {len(lines)}")
        print(f"  Header: {header}")
        print(f"  Comp1 row: {comp1_row}")
    
    @pytest.mark.asyncio
    async def test_export_error_handling(self, temp_output_dir):
        """Test export error handling"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        
        # Test with empty BOM
        empty_bom = BillOfMaterials(
            name="Empty BOM",
            components=[],
            metadata={"generated_at": "2025-10-14T12:43:14.265685Z"}
        )
        
        # Should not crash
        await exporter._export_bom_formats(empty_bom)
        
        # Verify files were created even with empty BOM
        assert (exporter.bom_dir / "bom.json").exists()
        assert (exporter.bom_dir / "bom.md").exists()
        assert (exporter.bom_dir / "bom.csv").exists()
        
        # Verify empty BOM content
        with open(exporter.bom_dir / "bom.json", 'r') as f:
            bom_data = json.load(f)
        assert len(bom_data["components"]) == 0
        
        print("✅ Export error handling: Empty BOM handled gracefully")
    
    @pytest.mark.asyncio
    async def test_directory_creation(self, temp_output_dir):
        """Test directory creation and structure"""
        exporter = BuiltDirectoryExporter(temp_output_dir)
        
        # Directories should not exist initially
        assert not exporter.bom_dir.exists()
        assert not exporter.docs_dir.exists()
        
        # Create directories
        exporter.bom_dir.mkdir(exist_ok=True)
        exporter.docs_dir.mkdir(exist_ok=True)
        
        # Verify directories exist
        assert exporter.bom_dir.exists()
        assert exporter.docs_dir.exists()
        assert exporter.bom_dir.is_dir()
        assert exporter.docs_dir.is_dir()
        
        print(f"✅ Directory creation:")
        print(f"  BOM dir created: {exporter.bom_dir.exists()}")
        print(f"  Docs dir created: {exporter.docs_dir.exists()}")
