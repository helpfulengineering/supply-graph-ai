#!/usr/bin/env python3
"""
Diagnostic script to check if component manifests are being created correctly.
Run this locally to verify TSDC codes are being converted to URIs.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models.okh import OKHManifest
from src.core.services.matching_service import MatchingService
from src.core.services.bom_resolution_service import BOMResolutionService


async def diagnose():
    """Diagnose component manifest creation"""
    print("=" * 80)
    print("Component Manifest Creation Diagnostic")
    print("=" * 80)
    
    # Load the workflow OKH file
    okh_file = Path("workflow-data/workflow2/okh/iot-sensor-node-3.7.9-okh.json")
    
    if not okh_file.exists():
        print(f"ERROR: Workflow data file not found: {okh_file}")
        return
    
    with open(okh_file, "r") as f:
        okh_data = json.load(f)
    
    manifest = OKHManifest.from_dict(okh_data)
    
    print(f"\nBase Manifest: {manifest.title}")
    print(f"Base manifest processes: {manifest.manufacturing_processes}")
    print()
    
    # Resolve BOM
    bom_service = BOMResolutionService()
    bom = await bom_service.resolve_bom(manifest)
    
    print(f"BOM Components: {len(bom.components)}")
    print()
    
    # Create matching service
    matching_service = await MatchingService.get_instance()
    
    # Check each component
    for component in bom.components:
        print(f"Component: {component.name}")
        print(f"  ID: {component.id}")
        print(f"  TSDC codes: {component.metadata.get('tsdc', []) if component.metadata else []}")
        print(f"  Requirements: {component.requirements}")
        
        # Create component manifest
        component_manifest = matching_service._create_component_manifest(manifest, component)
        processes = component_manifest.manufacturing_processes or []
        
        print(f"  Component manifest processes: {processes}")
        
        # Check if processes are URIs
        uri_processes = [p for p in processes if isinstance(p, str) and (p.startswith("http://") or p.startswith("https://"))]
        non_uri_processes = [p for p in processes if not (isinstance(p, str) and (p.startswith("http://") or p.startswith("https://")))]
        
        print(f"  URI processes: {len(uri_processes)}")
        if uri_processes:
            for uri in uri_processes:
                print(f"    - {uri}")
        
        if non_uri_processes:
            print(f"  ⚠️  NON-URI PROCESSES FOUND: {non_uri_processes}")
        else:
            print(f"  ✅ All processes are URIs")
        
        print()
    
    print("=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
