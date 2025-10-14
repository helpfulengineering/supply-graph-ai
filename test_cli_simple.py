#!/usr/bin/env python3
"""
Simple test script for CLI BOM export functionality
"""
import asyncio
import tempfile
from pathlib import Path
from src.core.generation.engine import GenerationEngine
from src.core.generation.models import LayerConfig
from src.core.generation.platforms.github import GitHubExtractor
from src.core.generation.built_directory import BuiltDirectoryExporter


async def test_bom_export():
    """Test BOM export functionality directly"""
    print("🔍 Testing BOM export functionality...")
    
    try:
        # Step 1: Generate manifest with BOM
        config = LayerConfig()
        config.use_bom_normalization = True
        engine = GenerationEngine(config=config)
        
        extractor = GitHubExtractor()
        project_data = await extractor.extract_project('https://github.com/rwb27/openflexure_microscope')
        
        print(f"✅ Project data extracted: {len(project_data.files)} files")
        
        result = await engine.generate_manifest_async(project_data)
        print(f"✅ Generation result: {len(result.generated_fields)} fields")
        
        # Step 2: Convert to OKH manifest
        okh_manifest = result.to_okh_manifest()
        print(f"✅ OKH manifest created with BOM: {'bom' in okh_manifest}")
        
        # Step 3: Test BOM export
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            
            if 'bom' in okh_manifest and isinstance(okh_manifest['bom'], dict):
                from src.core.models.bom import BillOfMaterials, Component
                
                # Convert BOM dict back to BillOfMaterials object
                bom_data = okh_manifest['bom']
                components = []
                
                for comp_data in bom_data.get('components', []):
                    component = Component(
                        id=comp_data.get('id', ''),
                        name=comp_data.get('name', ''),
                        quantity=comp_data.get('quantity', 1.0),
                        unit=comp_data.get('unit', 'pcs'),
                        metadata=comp_data.get('metadata', {})
                    )
                    components.append(component)
                
                bom = BillOfMaterials(
                    name=bom_data.get('name', 'Project BOM'),
                    components=components,
                    metadata=bom_data.get('metadata', {})
                )
                
                # Export BOM
                exporter = BuiltDirectoryExporter(output_path)
                await exporter._export_bom_formats(bom)
                
                print(f"✅ BOM exported to: {output_path}")
                print(f"📁 Files created: {list(output_path.rglob('*'))}")
                
                # Verify files
                assert (output_path / "bom" / "bom.json").exists()
                assert (output_path / "bom" / "bom.md").exists()
                assert (output_path / "bom" / "bom.csv").exists()
                print("✅ All BOM files created successfully")
                
            else:
                print("❌ No BOM data found in manifest")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_bom_export())
