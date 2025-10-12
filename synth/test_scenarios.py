#!/usr/bin/env python3
"""
Test Scenarios Generator for OME Testing Framework

This module generates paired OKH/OKW data specifically designed to test
different matching scenarios in the Open Matching Engine.

Usage:
    python test_scenarios.py --scenario exact_match --count 10 --output-dir ./test_data
    python test_scenarios.py --scenario all --count 50 --output-dir ./test_data
"""

import argparse
import json
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4

# Add the src directory to the path so we can import the models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models.okh import OKHManifest, License, Person, Organization, DocumentRef, MaterialSpec
from core.models.okw import ManufacturingFacility, Equipment, Location, Address, Agent, Contact
from generate_synthetic_data import OKHGenerator, OKWGenerator

class TestScenarioGenerator:
    """Generator for specific test scenarios"""
    
    def __init__(self):
        self.okh_generator = OKHGenerator("complex")
        self.okw_generator = OKWGenerator("complex")
        
    def generate_exact_match_scenario(self, count: int = 10) -> List[Dict]:
        """Generate OKH/OKW pairs that should have perfect matches"""
        scenarios = []
        
        # Define exact match templates
        exact_match_templates = [
            {
                "okh": {
                    "title": "Precision CNC Machined Bracket",
                    "manufacturing_processes": ["CNC Machining"],
                    "materials": ["Aluminum 6061"],
                    "tools": ["CNC mill", "Cutting tools", "CMM"],
                    "standards": ["ISO 2768", "ASME Y14.5"]
                },
                "okw": {
                    "name": "Precision CNC Machine Shop",
                    "equipment_types": ["CNC mill"],
                    "materials": ["Aluminum", "Steel", "Plastic"],
                    "certifications": ["ISO 9001:2015", "AS9100"],
                    "capabilities": {
                        "tolerance": "±0.01mm",
                        "surface_finish": "Ra 0.8μm"
                    }
                }
            },
            {
                "okh": {
                    "title": "3D Printed Prototype Housing",
                    "manufacturing_processes": ["3D Printing"],
                    "materials": ["PLA", "PETG"],
                    "tools": ["3D printer", "Filament", "Calipers"],
                    "standards": ["ISO 9001"]
                },
                "okw": {
                    "name": "Rapid Prototyping Lab",
                    "equipment_types": ["3D printer"],
                    "materials": ["PLA", "PETG", "ABS", "TPU"],
                    "certifications": ["Research Grade"],
                    "capabilities": {
                        "layer_height": "0.1-0.3mm",
                        "build_volume": "300x300x400mm"
                    }
                }
            },
            {
                "okh": {
                    "title": "Laser Cut Acrylic Display Case",
                    "manufacturing_processes": ["Laser Cutting"],
                    "materials": ["Acrylic"],
                    "tools": ["Laser cutter", "Air assist", "Calipers"],
                    "standards": ["CE"]
                },
                "okw": {
                    "name": "Laser Cutting Workshop",
                    "equipment_types": ["Laser cutter"],
                    "materials": ["Acrylic", "Wood", "Fabric"],
                    "certifications": ["Basic Safety"],
                    "capabilities": {
                        "cutting_thickness": "0.1-25mm",
                        "laser_power": "60W"
                    }
                }
            }
        ]
        
        for i in range(count):
            template = random.choice(exact_match_templates)
            
            # Generate OKH manifest
            okh_manifest = self._generate_custom_okh(template["okh"])
            
            # Generate matching OKW facility
            okw_facility = self._generate_custom_okw(template["okw"])
            
            scenarios.append({
                "scenario_id": f"exact_match_{i+1:03d}",
                "scenario_type": "exact_match",
                "expected_outcome": "match",
                "expected_confidence": 0.9,
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility,
                "description": f"Perfect match between {template['okh']['title']} and {template['okw']['name']}"
            })
        
        return scenarios
    
    def generate_partial_match_scenario(self, count: int = 10) -> List[Dict]:
        """Generate OKH/OKW pairs with some matching and some non-matching requirements"""
        scenarios = []
        
        partial_match_templates = [
            {
                "okh": {
                    "title": "Multi-Process Electronic Enclosure",
                    "manufacturing_processes": ["CNC Machining", "3D Printing", "PCB Assembly"],
                    "materials": ["Aluminum", "PLA", "FR4"],
                    "tools": ["CNC mill", "3D printer", "Soldering station"],
                    "standards": ["ISO 9001", "IPC-A-610"]
                },
                "okw": {
                    "name": "CNC Machine Shop",
                    "equipment_types": ["CNC mill"],  # Only has CNC, missing 3D printing and PCB
                    "materials": ["Aluminum", "Steel"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.01mm"
                    }
                },
                "expected_matches": 1,  # Only CNC matches
                "expected_misses": 2   # 3D printing and PCB don't match
            },
            {
                "okh": {
                    "title": "High-Precision Mechanical Assembly",
                    "manufacturing_processes": ["CNC Machining", "Surface Grinding"],
                    "materials": ["Stainless Steel"],
                    "tools": ["CNC mill", "Surface grinder", "CMM"],
                    "standards": ["ISO 2768", "ASME Y14.5"]
                },
                "okw": {
                    "name": "General Machine Shop",
                    "equipment_types": ["CNC mill", "CNC router"],  # Has CNC but not surface grinding
                    "materials": ["Aluminum", "Steel", "Plastic"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.05mm"  # Lower precision than required
                    }
                },
                "expected_matches": 1,  # CNC matches but with lower precision
                "expected_misses": 1   # Surface grinding not available
            }
        ]
        
        for i in range(count):
            template = random.choice(partial_match_templates)
            
            # Generate OKH manifest
            okh_manifest = self._generate_custom_okh(template["okh"])
            
            # Generate OKW facility
            okw_facility = self._generate_custom_okw(template["okw"])
            
            scenarios.append({
                "scenario_id": f"partial_match_{i+1:03d}",
                "scenario_type": "partial_match",
                "expected_outcome": "partial_match",
                "expected_confidence": 0.6,
                "expected_matches": template.get("expected_matches", 1),
                "expected_misses": template.get("expected_misses", 1),
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility,
                "description": f"Partial match: {template['okh']['title']} vs {template['okw']['name']}"
            })
        
        return scenarios
    
    def generate_near_miss_scenario(self, count: int = 10) -> List[Dict]:
        """Generate OKH/OKW pairs with close but not exact matches (typos, synonyms)"""
        scenarios = []
        
        near_miss_templates = [
            {
                "okh": {
                    "title": "CNC Machined Component",
                    "manufacturing_processes": ["CNC Machining"],  # Exact
                    "materials": ["Aluminum 6061"],
                    "tools": ["CNC mill", "Cutting tools"],
                    "standards": ["ISO 2768"]
                },
                "okw": {
                    "name": "CNC Machine Shop",
                    "equipment_types": ["CNC mill"],
                    "materials": ["Aluminum", "Steel"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.01mm"
                    }
                },
                "variations": [
                    {"okh_process": "CNC Machinng", "description": "Typo in process name"},
                    {"okh_process": "cnc machining", "description": "Case difference"},
                    {"okh_process": "CNC  Machining", "description": "Extra whitespace"},
                    {"okh_material": "Aluminium 6061", "description": "British spelling"},
                    {"okh_tool": "CNC Mill", "description": "Case difference in tool name"}
                ]
            },
            {
                "okh": {
                    "title": "3D Printed Part",
                    "manufacturing_processes": ["3D Printing"],
                    "materials": ["PLA"],
                    "tools": ["3D printer", "Filament"],
                    "standards": ["ISO 9001"]
                },
                "okw": {
                    "name": "3D Printing Lab",
                    "equipment_types": ["3D printer"],
                    "materials": ["PLA", "PETG", "ABS"],
                    "certifications": ["Research Grade"],
                    "capabilities": {
                        "layer_height": "0.1-0.3mm"
                    }
                },
                "variations": [
                    {"okh_process": "3D printing", "description": "Case difference"},
                    {"okh_process": "3DP", "description": "Abbreviation"},
                    {"okh_process": "Additive Manufacturing", "description": "Synonym"},
                    {"okh_material": "PLA+", "description": "Material variant"},
                    {"okh_tool": "3d printer", "description": "Case difference"}
                ]
            }
        ]
        
        for i in range(count):
            template = random.choice(near_miss_templates)
            variation = random.choice(template["variations"])
            
            # Apply variation to OKH template
            okh_template = template["okh"].copy()
            if "okh_process" in variation:
                okh_template["manufacturing_processes"] = [variation["okh_process"]]
            if "okh_material" in variation:
                okh_template["materials"] = [variation["okh_material"]]
            if "okh_tool" in variation:
                okh_template["tools"] = [variation["okh_tool"]]
            
            # Generate OKH manifest
            okh_manifest = self._generate_custom_okh(okh_template)
            
            # Generate OKW facility
            okw_facility = self._generate_custom_okw(template["okw"])
            
            scenarios.append({
                "scenario_id": f"near_miss_{i+1:03d}",
                "scenario_type": "near_miss",
                "expected_outcome": "match",  # Should still match due to heuristic rules
                "expected_confidence": 0.8,
                "variation_applied": variation,
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility,
                "description": f"Near miss: {variation['description']}"
            })
        
        return scenarios
    
    def generate_no_match_scenario(self, count: int = 10) -> List[Dict]:
        """Generate OKH/OKW pairs that should not match"""
        scenarios = []
        
        no_match_templates = [
            {
                "okh": {
                    "title": "Advanced Composite Manufacturing",
                    "manufacturing_processes": ["Composite Layup", "Autoclave Curing"],
                    "materials": ["Carbon Fiber", "Epoxy Resin"],
                    "tools": ["Autoclave", "Composite cutter", "Vacuum bagging"],
                    "standards": ["AS9100", "NADCAP"]
                },
                "okw": {
                    "name": "Basic Makerspace",
                    "equipment_types": ["3D printer", "Laser cutter"],
                    "materials": ["PLA", "Acrylic", "Wood"],
                    "certifications": ["Basic Safety"],
                    "capabilities": {
                        "layer_height": "0.2mm",
                        "laser_power": "40W"
                    }
                },
                "reason": "Completely different manufacturing processes and materials"
            },
            {
                "okh": {
                    "title": "Medical Device Manufacturing",
                    "manufacturing_processes": ["Precision Machining", "Clean Room Assembly"],
                    "materials": ["Titanium", "Medical Grade Plastic"],
                    "tools": ["Precision CNC", "Clean room equipment", "Sterilization"],
                    "standards": ["ISO 13485", "FDA 21 CFR Part 820"]
                },
                "okw": {
                    "name": "Woodworking Shop",
                    "equipment_types": ["CNC router", "Table saw"],
                    "materials": ["Wood", "Plywood", "MDF"],
                    "certifications": ["Basic Safety"],
                    "capabilities": {
                        "tolerance": "±1mm",
                        "working_surface": "1200x800mm"
                    }
                },
                "reason": "Medical device requirements vs woodworking capabilities"
            },
            {
                "okh": {
                    "title": "High-Volume Electronics Assembly",
                    "manufacturing_processes": ["SMT Assembly", "Wave Soldering", "ICT Testing"],
                    "materials": ["FR4", "Electronic Components", "Solder Paste"],
                    "tools": ["Pick and place", "Reflow oven", "ICT tester"],
                    "standards": ["IPC-A-610", "IPC-J-STD-001"]
                },
                "okw": {
                    "name": "Metal Fabrication Shop",
                    "equipment_types": ["CNC mill", "Welder", "Sheet metal brake"],
                    "materials": ["Steel", "Aluminum", "Stainless Steel"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.1mm",
                        "thickness": "0.5-25mm"
                    }
                },
                "reason": "Electronics assembly vs metal fabrication"
            }
        ]
        
        for i in range(count):
            template = random.choice(no_match_templates)
            
            # Generate OKH manifest
            okh_manifest = self._generate_custom_okh(template["okh"])
            
            # Generate OKW facility
            okw_facility = self._generate_custom_okw(template["okw"])
            
            scenarios.append({
                "scenario_id": f"no_match_{i+1:03d}",
                "scenario_type": "no_match",
                "expected_outcome": "no_match",
                "expected_confidence": 0.0,
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility,
                "description": f"No match: {template['reason']}"
            })
        
        return scenarios
    
    def generate_edge_case_scenario(self, count: int = 10) -> List[Dict]:
        """Generate edge cases and boundary conditions"""
        scenarios = []
        
        edge_case_templates = [
            {
                "name": "empty_manufacturing_processes",
                "okh": {
                    "title": "Design Only Project",
                    "manufacturing_processes": [],  # Empty processes
                    "materials": ["PLA"],
                    "tools": [],
                    "standards": []
                },
                "okw": {
                    "name": "Full Service Shop",
                    "equipment_types": ["3D printer", "CNC mill", "Laser cutter"],
                    "materials": ["PLA", "Aluminum", "Acrylic"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {}
                },
                "description": "OKH with no manufacturing processes specified"
            },
            {
                "name": "empty_okw_capabilities",
                "okh": {
                    "title": "Standard Part",
                    "manufacturing_processes": ["CNC Machining"],
                    "materials": ["Aluminum"],
                    "tools": ["CNC mill"],
                    "standards": ["ISO 2768"]
                },
                "okw": {
                    "name": "New Facility",
                    "equipment_types": [],  # No equipment
                    "materials": [],
                    "certifications": [],
                    "capabilities": {}
                },
                "description": "OKW facility with no capabilities"
            },
            {
                "name": "extreme_precision_requirements",
                "okh": {
                    "title": "Ultra-Precision Component",
                    "manufacturing_processes": ["Ultra-Precision Machining"],
                    "materials": ["Silicon", "Quartz"],
                    "tools": ["Ultra-precision CNC", "Laser interferometer"],
                    "standards": ["ISO 1", "ASME B89"]
                },
                "okw": {
                    "name": "Standard Machine Shop",
                    "equipment_types": ["CNC mill"],
                    "materials": ["Aluminum", "Steel"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.1mm"  # Much lower precision than required
                    }
                },
                "description": "Extreme precision requirements vs standard capabilities"
            },
            {
                "name": "massive_scale_requirements",
                "okh": {
                    "title": "Mass Production Component",
                    "manufacturing_processes": ["High-Volume CNC", "Automated Assembly"],
                    "materials": ["Aluminum"],
                    "tools": ["High-speed CNC", "Robotic assembly"],
                    "standards": ["ISO 9001", "IATF 16949"]
                },
                "okw": {
                    "name": "Prototype Shop",
                    "equipment_types": ["CNC mill"],
                    "materials": ["Aluminum"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "batch_size": "1-10 units",
                        "tolerance": "±0.01mm"
                    }
                },
                "description": "Mass production requirements vs prototype capabilities"
            },
            {
                "name": "unusual_material_requirements",
                "okh": {
                    "title": "Exotic Material Part",
                    "manufacturing_processes": ["CNC Machining"],
                    "materials": ["Inconel 718", "Titanium 6Al-4V"],
                    "tools": ["High-performance CNC", "Specialized cutting tools"],
                    "standards": ["AS9100", "NADCAP"]
                },
                "okw": {
                    "name": "General Machine Shop",
                    "equipment_types": ["CNC mill"],
                    "materials": ["Aluminum", "Steel", "Plastic"],
                    "certifications": ["ISO 9001:2015"],
                    "capabilities": {
                        "tolerance": "±0.05mm"
                    }
                },
                "description": "Exotic materials vs standard material capabilities"
            }
        ]
        
        for i in range(count):
            template = random.choice(edge_case_templates)
            
            # Generate OKH manifest
            okh_manifest = self._generate_custom_okh(template["okh"])
            
            # Generate OKW facility
            okw_facility = self._generate_custom_okw(template["okw"])
            
            scenarios.append({
                "scenario_id": f"edge_case_{i+1:03d}",
                "scenario_type": "edge_case",
                "edge_case_type": template["name"],
                "expected_outcome": "unknown",  # Edge cases may have unpredictable outcomes
                "expected_confidence": 0.0,
                "okh_manifest": okh_manifest,
                "okw_facility": okw_facility,
                "description": template["description"]
            })
        
        return scenarios
    
    def _generate_custom_okh(self, template: Dict) -> OKHManifest:
        """Generate a custom OKH manifest from template"""
        # Start with a base manifest
        base_manifest = self.okh_generator.generate_okh_manifest()
        
        # Override with template values
        if "title" in template:
            base_manifest.title = template["title"]
        
        if "manufacturing_processes" in template:
            base_manifest.manufacturing_processes = template["manufacturing_processes"]
        
        if "materials" in template:
            base_manifest.materials = []
            for material_name in template["materials"]:
                material = MaterialSpec(
                    material_id=material_name.replace(" ", "_").upper(),
                    name=material_name,
                    quantity=random.uniform(10, 100),
                    unit="kg" if "Aluminum" in material_name or "Steel" in material_name else "g"
                )
                base_manifest.materials.append(material)
        
        if "tools" in template:
            base_manifest.tool_list = template["tools"]
        
        if "standards" in template:
            base_manifest.standards_used = []
            for std_name in template["standards"]:
                from core.models.okh import Standard
                standard = Standard(
                    standard_title=std_name,
                    publisher="ISO" if "ISO" in std_name else "Other",
                    reference=std_name
                )
                base_manifest.standards_used.append(standard)
        
        return base_manifest
    
    def _generate_custom_okw(self, template: Dict) -> ManufacturingFacility:
        """Generate a custom OKW facility from template"""
        # Start with a base facility
        base_facility = self.okw_generator.generate_manufacturing_facility()
        
        # Override with template values
        if "name" in template:
            base_facility.name = template["name"]
        
        if "equipment_types" in template:
            base_facility.equipment = []
            for eq_type in template["equipment_types"]:
                equipment = self.okw_generator.generate_equipment(eq_type)
                base_facility.equipment.append(equipment)
        
        if "materials" in template:
            base_facility.typical_materials = []
            for material_name in template["materials"]:
                from core.models.okw import Material
                material = Material(
                    material_type=f"https://en.wikipedia.org/wiki/{material_name.replace(' ', '_')}",
                    manufacturer=random.choice(["Generic", "Brand A", "Brand B"]),
                    brand=random.choice(["Standard", "Professional"])
                )
                base_facility.typical_materials.append(material)
        
        if "certifications" in template:
            base_facility.certifications = template["certifications"]
        
        if "capabilities" in template:
            # Add capabilities to equipment
            for equipment in base_facility.equipment:
                equipment.additional_properties["detailed_capabilities"] = template["capabilities"]
        
        return base_facility
    
    def generate_all_scenarios(self, count_per_type: int = 10) -> List[Dict]:
        """Generate all types of test scenarios"""
        all_scenarios = []
        
        print("Generating exact match scenarios...")
        all_scenarios.extend(self.generate_exact_match_scenario(count_per_type))
        
        print("Generating partial match scenarios...")
        all_scenarios.extend(self.generate_partial_match_scenario(count_per_type))
        
        print("Generating near miss scenarios...")
        all_scenarios.extend(self.generate_near_miss_scenario(count_per_type))
        
        print("Generating no match scenarios...")
        all_scenarios.extend(self.generate_no_match_scenario(count_per_type))
        
        print("Generating edge case scenarios...")
        all_scenarios.extend(self.generate_edge_case_scenario(count_per_type))
        
        return all_scenarios

def save_scenario(scenario: Dict, output_dir: str) -> Tuple[str, str]:
    """Save a test scenario to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    scenario_id = scenario["scenario_id"]
    
    # Save OKH manifest
    okh_file = os.path.join(output_dir, f"{scenario_id}_okh.json")
    with open(okh_file, 'w', encoding='utf-8') as f:
        json.dump(scenario["okh_manifest"].to_dict(), f, indent=2, ensure_ascii=False, default=str)
    
    # Save OKW facility
    okw_file = os.path.join(output_dir, f"{scenario_id}_okw.json")
    with open(okw_file, 'w', encoding='utf-8') as f:
        json.dump(scenario["okw_facility"].to_dict(), f, indent=2, ensure_ascii=False, default=str)
    
    # Save scenario metadata
    metadata_file = os.path.join(output_dir, f"{scenario_id}_metadata.json")
    metadata = {
        "scenario_id": scenario["scenario_id"],
        "scenario_type": scenario["scenario_type"],
        "expected_outcome": scenario["expected_outcome"],
        "expected_confidence": scenario.get("expected_confidence", 0.0),
        "description": scenario["description"],
        "okh_file": f"{scenario_id}_okh.json",
        "okw_file": f"{scenario_id}_okw.json",
        "generated_at": datetime.now().isoformat()
    }
    
    # Add type-specific metadata
    if scenario["scenario_type"] == "partial_match":
        metadata["expected_matches"] = scenario.get("expected_matches", 1)
        metadata["expected_misses"] = scenario.get("expected_misses", 1)
    elif scenario["scenario_type"] == "near_miss":
        metadata["variation_applied"] = scenario.get("variation_applied", {})
    elif scenario["scenario_type"] == "edge_case":
        metadata["edge_case_type"] = scenario.get("edge_case_type", "")
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return okh_file, okw_file

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate test scenarios for OME testing")
    parser.add_argument("--scenario", choices=["exact_match", "partial_match", "near_miss", "no_match", "edge_case", "all"], 
                       required=True, help="Type of scenario to generate")
    parser.add_argument("--count", type=int, default=10, help="Number of scenarios to generate per type")
    parser.add_argument("--output-dir", default="./test_scenarios", help="Output directory for generated scenarios")
    
    args = parser.parse_args()
    
    print(f"Generating {args.count} {args.scenario} scenarios...")
    
    generator = TestScenarioGenerator()
    
    # Generate scenarios based on type
    if args.scenario == "all":
        scenarios = generator.generate_all_scenarios(args.count)
    elif args.scenario == "exact_match":
        scenarios = generator.generate_exact_match_scenario(args.count)
    elif args.scenario == "partial_match":
        scenarios = generator.generate_partial_match_scenario(args.count)
    elif args.scenario == "near_miss":
        scenarios = generator.generate_near_miss_scenario(args.count)
    elif args.scenario == "no_match":
        scenarios = generator.generate_no_match_scenario(args.count)
    elif args.scenario == "edge_case":
        scenarios = generator.generate_edge_case_scenario(args.count)
    
    # Save scenarios
    saved_count = 0
    for scenario in scenarios:
        try:
            okh_file, okw_file = save_scenario(scenario, args.output_dir)
            print(f"Saved: {scenario['scenario_id']} -> {okh_file}, {okw_file}")
            saved_count += 1
        except Exception as e:
            print(f"Error saving scenario {scenario['scenario_id']}: {e}")
    
    print(f"\nGeneration complete!")
    print(f"Successfully generated: {saved_count} scenarios")
    print(f"Output directory: {args.output_dir}")
    
    # Generate summary
    summary = {
        "total_scenarios": len(scenarios),
        "saved_scenarios": saved_count,
        "scenario_types": list(set(s["scenario_type"] for s in scenarios)),
        "generated_at": datetime.now().isoformat(),
        "output_directory": args.output_dir
    }
    
    summary_file = os.path.join(args.output_dir, "scenario_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
