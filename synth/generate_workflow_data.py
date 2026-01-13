#!/usr/bin/env python3
"""
Generate Workflow-Specific Demo Data

This script generates OKH and OKW files specifically designed for the two demo workflows:
1. Simple Matching: 1 OKH + 5 OKW facilities (3-8 matches)
2. Depth Matching: 1 nested OKH + 3 OKW facilities (multi-facility solution)

Usage:
    python generate_workflow_data.py --output-dir ./workflow-data --country US
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

# Add project root and src directory to the path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import from synth directory (same directory as this script)
from synth.generate_synthetic_data import OKHGenerator, OKWGenerator

# Import models from src/core/models
from core.models.okh import (
    OKHManifest, PartSpec, MaterialSpec, ProcessRequirement, ManufacturingSpec
)
from core.models.okw import ManufacturingFacility


def generate_workflow1_okh(okh_gen: OKHGenerator) -> OKHManifest:
    """
    Generate OKH for Workflow 1: Simple Matching
    - Simple design (no nesting)
    - Clear process requirements: 3DP, Post-processing, Assembly
    - Should match 3-8 facilities
    """
    manifest = okh_gen.generate_okh_manifest()
    
    # Override with specific design for workflow 1
    manifest.title = "3D Printed Prosthetic Hand"
    manifest.function = "Functional prosthetic hand for upper limb amputees, designed for 3D printing and assembly"
    manifest.manufacturing_processes = ["3DP", "Post-processing", "Assembly"]
    
    # Clear any nested parts/sub_parts to keep it simple
    manifest.parts = []
    manifest.sub_parts = []
    
    # Add simple top-level parts (no nesting)
    manifest.parts = [
        PartSpec(
            name="Hand Frame",
            tsdc=["3DP"],
            material="PLA"
        ),
        PartSpec(
            name="Finger Joints",
            tsdc=["3DP"],
            material="TPU"
        ),
        PartSpec(
            name="Assembly Components",
            tsdc=["Assembly"],
            material=None
        )
    ]
    
    # Set materials
    manifest.materials = [
        MaterialSpec(
            material_id="PLA",
            name="Polylactic Acid",
            quantity=500.0,
            unit="g",
            notes="Grade: A"
        ),
        MaterialSpec(
            material_id="TPU",
            name="Thermoplastic Polyurethane",
            quantity=100.0,
            unit="g",
            notes="Grade: B"
        )
    ]
    
    # Set manufacturing specs
    manifest.manufacturing_specs = ManufacturingSpec(
        process_requirements=[
            ProcessRequirement(
                process_name="3DP",
                parameters={
                    "layer_height": "0.2mm",
                    "infill": "20%",
                    "temperature": "210°C"
                }
            ),
            ProcessRequirement(
                process_name="Post-processing",
                parameters={
                    "support_removal": "required",
                    "sanding": "optional"
                }
            ),
            ProcessRequirement(
                process_name="Assembly",
                parameters={
                    "tools": ["screwdriver", "pliers"]
                }
            )
        ],
        outer_dimensions={
            "length": 200,
            "width": 100,
            "height": 50
        }
    )
    
    return manifest


def generate_workflow1_okw_facilities(okw_gen: OKWGenerator, count: int = 5) -> List[ManufacturingFacility]:
    """
    Generate OKW facilities for Workflow 1: Simple Matching
    - 5 facilities total:
      - 2x 3D Printing facilities (match 3DP requirement)
      - 2x Assembly facilities (match Assembly requirement)
      - 1x Post-processing facility (match Post-processing requirement)
    """
    facilities = []
    
    # Generate 2x 3D Printing facilities (using "3DP" specialization)
    for i in range(2):
        facility = okw_gen.generate_specialized_facility(
            specialization="3DP",
            facility_index=i+1
        )
        facilities.append(facility)
    
    # Generate 2x Assembly facilities (using "Assembly" specialization)
    for i in range(2):
        facility = okw_gen.generate_specialized_facility(
            specialization="Assembly",
            facility_index=i+1
        )
        facilities.append(facility)
    
    # Generate 1x Post-processing facility
    # Note: Post-processing might not be a direct specialization, so we'll use a general facility
    # and customize it, or use "3DP" and modify it
    facility = okw_gen.generate_specialized_facility(
        specialization="3DP",
        facility_index=3
    )
    # Customize for post-processing
    facility.name = "Post-Processing Facility 1"
    facility.description = "Specialized in post-processing and finishing of 3D printed parts"
    # Modify manufacturing processes to emphasize post-processing
    facility.manufacturing_processes = [
        "https://en.wikipedia.org/wiki/Post-processing",
        "https://en.wikipedia.org/wiki/Finishing"
    ]
    facilities.append(facility)
    
    return facilities


def generate_workflow2_okh(okh_gen: OKHGenerator) -> OKHManifest:
    """
    Generate OKH for Workflow 2: Depth Matching (Nested)
    - Nested design with 3 top-level components
    - Each component requires different processes:
      - Component 1: PCB (requires PCB fabrication)
      - Component 2: Enclosure (requires 3D printing)
      - Component 3: Final Assembly (requires assembly)
    - No single facility can make the entire design
    """
    # Use the nested generation method
    manifest = okh_gen.generate_okh_manifest_with_nesting(max_depth=2)
    
    # Override with specific design for workflow 2
    manifest.title = "IoT Sensor Node"
    manifest.function = "Complete IoT sensor node with PCB, 3D printed enclosure, and final assembly"
    manifest.manufacturing_processes = ["PCB", "3DP", "Assembly"]
    
    # Clear existing parts and create specific nested structure
    manifest.parts = []
    manifest.sub_parts = []
    
    # Component 1: PCB (top-level part)
    manifest.parts.append(
        PartSpec(
            name="Sensor PCB",
            tsdc=["PCB"],
            material="FR4"
        )
    )
    
    # Component 2: Enclosure (top-level part)
    manifest.parts.append(
        PartSpec(
            name="3D Printed Enclosure",
            tsdc=["3DP"],
            material="PLA"
        )
    )
    
    # Component 3: Final Assembly (top-level part)
    manifest.parts.append(
        PartSpec(
            name="Final Assembly",
            tsdc=["Assembly"],
            material=None
        )
    )
    
    # Add sub_parts to show nesting (PCB has components, Enclosure has parts)
    manifest.sub_parts = [
        {
            "name": "Microcontroller",
            "component_id": "MCU-001",
            "quantity": 1,
            "unit": "pcs",
            "tsdc": ["PCB"],
            "material": "Silicon",
            "depends_on": []
        },
        {
            "name": "Sensor Module",
            "component_id": "SENSOR-001",
            "quantity": 1,
            "unit": "pcs",
            "tsdc": ["PCB"],
            "material": "FR4",
            "depends_on": []
        },
        {
            "name": "Enclosure Base",
            "component_id": "ENC-BASE",
            "quantity": 1,
            "unit": "pcs",
            "tsdc": ["3DP"],
            "material": "PLA",
            "depends_on": []
        },
        {
            "name": "Enclosure Lid",
            "component_id": "ENC-LID",
            "quantity": 1,
            "unit": "pcs",
            "tsdc": ["3DP"],
            "material": "PLA",
            "depends_on": ["Enclosure Base"]
        }
    ]
    
    # Set materials
    manifest.materials = [
        MaterialSpec(
            material_id="FR4",
            name="FR4 PCB Material",
            quantity=50.0,
            unit="g",
            notes="Standard PCB substrate"
        ),
        MaterialSpec(
            material_id="PLA",
            name="Polylactic Acid",
            quantity=200.0,
            unit="g",
            notes="Grade: A"
        ),
        MaterialSpec(
            material_id="Copper",
            name="Copper Traces",
            quantity=10.0,
            unit="g",
            notes="PCB traces"
        )
    ]
    
    # Set manufacturing specs
    manifest.manufacturing_specs = ManufacturingSpec(
        process_requirements=[
            ProcessRequirement(
                process_name="PCB",
                parameters={
                    "layers": "2",
                    "trace_width": "0.1mm",
                    "via_diameter": "0.2mm"
                }
            ),
            ProcessRequirement(
                process_name="3DP",
                parameters={
                    "layer_height": "0.2mm",
                    "infill": "30%",
                    "temperature": "210°C"
                }
            ),
            ProcessRequirement(
                process_name="Assembly",
                parameters={
                    "tools": ["soldering iron", "screwdriver"],
                    "sequence": ["PCB first", "then enclosure", "final assembly"]
                }
            )
        ],
        outer_dimensions={
            "length": 80,
            "width": 60,
            "height": 25
        }
    )
    
    return manifest


def generate_workflow2_okw_facilities(okw_gen: OKWGenerator) -> List[ManufacturingFacility]:
    """
    Generate OKW facilities for Workflow 2: Depth Matching
    - 3 facilities, each specialized:
      - 1x PCB Fabrication Facility (matches PCB component)
      - 1x 3D Printing Facility (matches Enclosure component)
      - 1x Assembly Facility (matches Final Assembly component)
    """
    facilities = []
    
    # PCB Fabrication Facility (using "PCB" specialization)
    pcb_facility = okw_gen.generate_specialized_facility(
        specialization="PCB",
        facility_index=1
    )
    facilities.append(pcb_facility)
    
    # 3D Printing Facility (using "3DP" specialization)
    printing_facility = okw_gen.generate_specialized_facility(
        specialization="3DP",
        facility_index=1
    )
    facilities.append(printing_facility)
    
    # Assembly Facility (using "Assembly" specialization)
    assembly_facility = okw_gen.generate_specialized_facility(
        specialization="Assembly",
        facility_index=1
    )
    facilities.append(assembly_facility)
    
    return facilities


def save_okh_manifest(manifest: OKHManifest, output_path: Path):
    """Save OKH manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use the built-in to_dict() method
    manifest_dict = manifest.to_dict()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_dict, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Saved OKH: {output_path}")


def save_okw_facility(facility: ManufacturingFacility, output_path: Path):
    """Save OKW facility to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use the built-in to_dict() method
    facility_dict = facility.to_dict()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(facility_dict, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Saved OKW: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate workflow-specific demo data")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./workflow-data",
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--country",
        type=str,
        default="US",
        help="Country for facility locations (default: US)"
    )
    parser.add_argument(
        "--workflow",
        type=str,
        choices=["1", "2", "both"],
        default="both",
        help="Which workflow(s) to generate (default: both)"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize generators
    okh_gen = OKHGenerator(complexity="complex")
    okw_gen = OKWGenerator(country=args.country, complexity="complex")
    
    print("🚀 Generating workflow-specific demo data...")
    print("")
    
    # Generate Workflow 1 data
    if args.workflow in ["1", "both"]:
        print("📦 Generating Workflow 1: Simple Matching")
        print("  - 1 OKH file (3D Printed Prosthetic Hand)")
        print("  - 5 OKW facilities (2x 3DP, 2x Assembly, 1x Post-processing)")
        print("")
        
        # Generate OKH
        okh1 = generate_workflow1_okh(okh_gen)
        okh1_path = output_dir / "workflow1" / "okh" / f"{okh1.title.lower().replace(' ', '-')}-{okh1.version}-okh.json"
        save_okh_manifest(okh1, okh1_path)
        
        # Generate OKW facilities
        okw1_facilities = generate_workflow1_okw_facilities(okw_gen, count=5)
        for i, facility in enumerate(okw1_facilities):
            facility_path = output_dir / "workflow1" / "okw" / f"{facility.name.lower().replace(' ', '-')}-{i+1:03d}-okw.json"
            save_okw_facility(facility, facility_path)
        
        print("")
        print(f"✅ Workflow 1 complete: 1 OKH + {len(okw1_facilities)} OKW files")
        print("")
    
    # Generate Workflow 2 data
    if args.workflow in ["2", "both"]:
        print("📦 Generating Workflow 2: Depth Matching (Nested)")
        print("  - 1 nested OKH file (IoT Sensor Node)")
        print("  - 3 OKW facilities (1x PCB, 1x 3D Printing, 1x Assembly)")
        print("")
        
        # Generate OKH
        okh2 = generate_workflow2_okh(okh_gen)
        okh2_path = output_dir / "workflow2" / "okh" / f"{okh2.title.lower().replace(' ', '-')}-{okh2.version}-okh.json"
        save_okh_manifest(okh2, okh2_path)
        
        # Generate OKW facilities
        okw2_facilities = generate_workflow2_okw_facilities(okw_gen)
        for i, facility in enumerate(okw2_facilities):
            facility_path = output_dir / "workflow2" / "okw" / f"{facility.name.lower().replace(' ', '-')}-{i+1:03d}-okw.json"
            save_okw_facility(facility, facility_path)
        
        print("")
        print(f"✅ Workflow 2 complete: 1 OKH + {len(okw2_facilities)} OKW files")
        print("")
    
    print("🎉 All workflow data generated successfully!")
    print(f"📁 Output directory: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
