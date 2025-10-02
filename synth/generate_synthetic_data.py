#!/usr/bin/env python3
"""
Synthetic Data Generator for OKH and OKW Models

This script generates realistic synthetic data for testing the matching engine.
It can create both OKH manifests and OKW facilities with configurable complexity levels.

Usage:
    python generate_synthetic_data.py --type okh --count 10 --complexity complex --output-dir ./data
    python generate_synthetic_data.py --type okw --count 20 --complexity mixed --output-dir ./facilities
"""

import argparse
import json
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import uuid4

from faker import Faker

# Add the src directory to the path so we can import the models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models.okh import (
    OKHManifest, License, Person, Organization, DocumentRef, MaterialSpec,
    ProcessRequirement, ManufacturingSpec, Standard, Software, PartSpec,
    DocumentationType
)
from core.models.okw import (
    ManufacturingFacility, Equipment, Location, Address, What3Words, Agent,
    Contact, SocialMedia, CircularEconomy, HumanCapacity, InnovationSpace,
    Material, RecordData, FacilityStatus, AccessType, BatchSize
)

fake = Faker()

class SyntheticDataGenerator:
    """Base class for generating synthetic data"""
    
    def __init__(self, complexity: str = "mixed"):
        self.complexity = complexity
        self.faker = Faker()
        
    def should_include_field(self, field_type: str = "optional") -> bool:
        """Determine if a field should be included based on complexity level"""
        if self.complexity == "minimal":
            return field_type == "required"
        elif self.complexity == "complex":
            return True
        else:  # mixed
            return random.choice([True, False])

class OKHGenerator(SyntheticDataGenerator):
    """Generator for OKH manifests"""
    
    def __init__(self, complexity: str = "mixed"):
        super().__init__(complexity)
        
        # Realistic hardware project templates
        self.hardware_templates = [
            {
                "title": "Arduino-based IoT Sensor Node",
                "function": "Environmental monitoring device with temperature, humidity, and air quality sensors",
                "manufacturing_processes": ["PCB", "3DP", "Assembly"],
                "materials": ["PLA", "FR4", "Copper", "Electronic components"],
                "tsdc": ["PCB", "3DP"],
                "tools": ["Soldering iron", "3D printer", "Multimeter", "Oscilloscope"]
            },
            {
                "title": "CNC Machined Aluminum Bracket",
                "function": "Precision mounting bracket for industrial equipment",
                "manufacturing_processes": ["CNC", "Deburring", "Anodizing"],
                "materials": ["Aluminum 6061", "Cutting fluid", "Anodizing solution"],
                "tsdc": ["CNC"],
                "tools": ["CNC mill", "Deburring tools", "Anodizing tank", "Calipers"]
            },
            {
                "title": "Laser Cut Acrylic Display Case",
                "function": "Protective display case for electronic components",
                "manufacturing_processes": ["LASER", "Assembly"],
                "materials": ["Acrylic sheet", "Adhesive", "Hinges"],
                "tsdc": ["LASER"],
                "tools": ["Laser cutter", "Acrylic cement", "Clamps"]
            },
            {
                "title": "3D Printed Prosthetic Hand",
                "function": "Functional prosthetic hand for upper limb amputees",
                "manufacturing_processes": ["3DP", "Post-processing", "Assembly"],
                "materials": ["PETG", "TPU", "Nylon", "Screws", "Cables"],
                "tsdc": ["3DP"],
                "tools": ["3D printer", "Heat gun", "Drill", "Screwdriver"]
            },
            {
                "title": "Sheet Metal Enclosure",
                "function": "Weatherproof enclosure for outdoor electronics",
                "manufacturing_processes": ["SHEET", "Welding", "Painting"],
                "materials": ["Steel sheet", "Welding wire", "Primer", "Paint"],
                "tsdc": ["SHEET"],
                "tools": ["Sheet metal brake", "Welder", "Drill press", "Paint gun"]
            }
        ]
        
        # Common licenses
        self.licenses = [
            {"hardware": "CERN-OHL-S-2.0", "documentation": "CC-BY-4.0", "software": "GPL-3.0-or-later"},
            {"hardware": "CERN-OHL-W-2.0", "documentation": "CC-BY-SA-4.0", "software": "MIT"},
            {"hardware": "TAPR-OHL-1.0", "documentation": "CC-BY-4.0", "software": "Apache-2.0"},
            {"hardware": "Solderpad-Hardware-0.51", "documentation": "CC-BY-4.0", "software": "BSD-3-Clause"},
            {"hardware": "CERN-OHL-P-2.0", "documentation": "CC-BY-4.0", "software": "LGPL-3.0-or-later"}
        ]
        
        # Common materials
        self.materials = [
            {"id": "PLA", "name": "Polylactic Acid", "unit": "g"},
            {"id": "PETG", "name": "Polyethylene Terephthalate Glycol", "unit": "g"},
            {"id": "ABS", "name": "Acrylonitrile Butadiene Styrene", "unit": "g"},
            {"id": "TPU", "name": "Thermoplastic Polyurethane", "unit": "g"},
            {"id": "Al6061", "name": "Aluminum 6061-T6", "unit": "kg"},
            {"id": "Steel", "name": "Mild Steel", "unit": "kg"},
            {"id": "FR4", "name": "FR4 PCB Material", "unit": "m²"},
            {"id": "Acrylic", "name": "Acrylic Sheet", "unit": "m²"},
            {"id": "Wood", "name": "Hardwood", "unit": "m³"}
        ]

    def generate_license(self) -> License:
        """Generate a realistic license"""
        license_data = random.choice(self.licenses)
        return License(
            hardware=license_data["hardware"],
            documentation=license_data["documentation"],
            software=license_data["software"]
        )

    def generate_person(self) -> Person:
        """Generate a realistic person"""
        return Person(
            name=self.faker.name(),
            email=self.faker.email() if self.should_include_field() else None,
            affiliation=self.faker.company() if self.should_include_field() else None,
            social=[{"platform": "github", "handle": self.faker.user_name()}] if self.should_include_field() else []
        )

    def generate_organization(self) -> Organization:
        """Generate a realistic organization"""
        return Organization(
            name=self.faker.company(),
            url=f"https://{self.faker.domain_name()}" if self.should_include_field() else None,
            email=f"contact@{self.faker.domain_name()}" if self.should_include_field() else None
        )

    def generate_document_ref(self, doc_type: DocumentationType, title: str) -> DocumentRef:
        """Generate a realistic document reference"""
        extensions = {
            DocumentationType.DESIGN_FILES: [".stl", ".step", ".iges", ".dxf", ".f3d"],
            DocumentationType.MANUFACTURING_FILES: [".pdf", ".docx", ".md"],
            DocumentationType.USER_MANUAL: [".pdf", ".html", ".md"],
            DocumentationType.SOFTWARE: [".zip", ".tar.gz", ".git"]
        }
        
        ext = random.choice(extensions.get(doc_type, [".pdf"]))
        # Use URL paths for synthetic data to avoid validation issues
        path = f"https://github.com/{self.faker.user_name()}/project/raw/main/docs/{title.lower().replace(' ', '_')}{ext}"
        
        return DocumentRef(
            title=title,
            path=path,
            type=doc_type,
            metadata={"version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}"} if self.should_include_field() else {}
        )

    def generate_material_spec(self) -> MaterialSpec:
        """Generate a realistic material specification"""
        material = random.choice(self.materials)
        return MaterialSpec(
            material_id=material["id"],
            name=material["name"],
            quantity=round(random.uniform(10, 1000), 2) if self.should_include_field() else None,
            unit=material["unit"],
            notes=f"Grade: {random.choice(['A', 'B', 'C'])}" if self.should_include_field() else None
        )

    def generate_process_requirement(self, process_name: str) -> ProcessRequirement:
        """Generate a realistic process requirement"""
        parameters = {}
        validation_criteria = {}
        required_tools = []
        
        if process_name == "3DP":
            parameters = {
                "layer_height": f"{random.choice([0.1, 0.2, 0.3])}mm",
                "infill": f"{random.choice([10, 20, 30, 50])}%",
                "temperature": f"{random.randint(200, 250)}°C"
            }
            validation_criteria = {
                "dimensional_accuracy": "±0.1mm",
                "surface_finish": "Ra 3.2μm"
            }
            required_tools = ["3D printer", "Filament", "Calipers"]
            
        elif process_name == "CNC":
            parameters = {
                "tolerance": f"±{random.choice([0.01, 0.02, 0.05])}mm",
                "surface_finish": f"Ra {random.choice([1.6, 3.2, 6.3])}μm",
                "cutting_speed": f"{random.randint(100, 500)} m/min"
            }
            validation_criteria = {
                "dimensional_accuracy": "±0.01mm",
                "surface_roughness": "Ra 1.6μm max"
            }
            required_tools = ["CNC mill", "Cutting tools", "CMM"]
            
        elif process_name == "PCB":
            parameters = {
                "board_thickness": f"{random.choice([0.8, 1.0, 1.6, 2.0])}mm",
                "copper_thickness": "35μm",
                "layers": random.choice([1, 2, 4, 6])
            }
            validation_criteria = {
                "trace_width": "≥0.1mm",
                "via_diameter": "≥0.2mm"
            }
            required_tools = ["PCB mill", "Soldering station", "Multimeter"]
            
        elif process_name == "LASER":
            parameters = {
                "power": f"{random.randint(20, 100)}W",
                "speed": f"{random.randint(100, 1000)} mm/min",
                "passes": random.randint(1, 3)
            }
            validation_criteria = {
                "cut_quality": "Clean edges, no burrs",
                "dimensional_accuracy": "±0.05mm"
            }
            required_tools = ["Laser cutter", "Air assist", "Calipers"]
            
        return ProcessRequirement(
            process_name=process_name,
            parameters=parameters,
            validation_criteria=validation_criteria,
            required_tools=required_tools,
            notes=f"Process notes: {self.faker.sentence()}" if self.should_include_field() else ""
        )

    def generate_part_spec(self, template: Dict) -> PartSpec:
        """Generate a realistic part specification"""
        part_names = ["Main Body", "Cover", "Bracket", "Housing", "Mount", "Base", "Frame"]
        part_name = random.choice(part_names)
        
        # Select TSDC based on template
        tsdc = random.choice(template["tsdc"]) if template["tsdc"] else random.choice(["3DP", "CNC", "PCB"])
        
        # Generate manufacturing parameters based on TSDC
        manufacturing_params = {}
        if tsdc == "3DP":
            manufacturing_params = {
                "layer_height": f"{random.choice([0.1, 0.2, 0.3])}mm",
                "infill": f"{random.choice([10, 20, 30])}%",
                "support": random.choice(["required", "not_required"])
            }
        elif tsdc == "CNC":
            manufacturing_params = {
                "tolerance": f"±{random.choice([0.01, 0.02])}mm",
                "surface_finish": f"Ra {random.choice([1.6, 3.2])}μm"
            }
        elif tsdc == "PCB":
            manufacturing_params = {
                "board_thickness": f"{random.choice([0.8, 1.6])}mm",
                "copper_thickness": "35μm"
            }
        
        return PartSpec(
            name=part_name,
            source=[f"https://github.com/{self.faker.user_name()}/project/raw/main/models/{part_name.lower().replace(' ', '_')}.stl"] if self.should_include_field() else [],
            export=[f"https://github.com/{self.faker.user_name()}/project/raw/main/exports/{part_name.lower().replace(' ', '_')}.step"] if self.should_include_field() else [],
            auxiliary=[f"https://github.com/{self.faker.user_name()}/project/raw/main/docs/{part_name.lower().replace(' ', '_')}_notes.md"] if self.should_include_field() else [],
            image=f"https://github.com/{self.faker.user_name()}/project/raw/main/images/{part_name.lower().replace(' ', '_')}.jpg" if self.should_include_field() else None,
            tsdc=[tsdc],
            material=random.choice(template["materials"]) if template["materials"] else "PLA",
            outer_dimensions={
                "length": random.randint(10, 200),
                "width": random.randint(10, 200),
                "height": random.randint(5, 100)
            } if self.should_include_field() else None,
            mass=round(random.uniform(1, 1000), 2) if self.should_include_field() else None,
            manufacturing_params=manufacturing_params
        )

    def generate_okh_manifest(self) -> OKHManifest:
        """Generate a complete OKH manifest"""
        template = random.choice(self.hardware_templates)
        
        # Generate basic manifest
        manifest = OKHManifest(
            title=template["title"],
            repo=f"https://github.com/{self.faker.user_name()}/{template['title'].lower().replace(' ', '-')}",
            version=f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            license=self.generate_license(),
            licensor=self.generate_person(),
            documentation_language=random.choice(["en", "es", "fr", "de", "it"]),
            function=template["function"]
        )
        
        # Add optional fields based on complexity
        if self.should_include_field():
            manifest.description = f"A {template['title'].lower()} designed for {self.faker.sentence()}"
            
        if self.should_include_field():
            manifest.intended_use = self.faker.sentence()
            
        if self.should_include_field():
            manifest.keywords = [self.faker.word() for _ in range(random.randint(3, 8))]
            
        if self.should_include_field():
            manifest.contact = self.generate_person()
            
        if self.should_include_field():
            manifest.contributors = [self.generate_person() for _ in range(random.randint(1, 3))]
            
        if self.should_include_field():
            manifest.organization = self.generate_organization()
            
        if self.should_include_field():
            manifest.development_stage = random.choice(["prototype", "beta", "production", "deprecated"])
            
        if self.should_include_field():
            manifest.technology_readiness_level = f"TRL-{random.randint(1, 9)}"
            
        # Add documentation references
        if self.should_include_field():
            manifest.design_files = [
                self.generate_document_ref(DocumentationType.DESIGN_FILES, "3D Model"),
                self.generate_document_ref(DocumentationType.DESIGN_FILES, "Technical Drawings")
            ]
            
        if self.should_include_field():
            manifest.manufacturing_files = [
                self.generate_document_ref(DocumentationType.MANUFACTURING_FILES, "Assembly Guide"),
                self.generate_document_ref(DocumentationType.MANUFACTURING_FILES, "Bill of Materials")
            ]
            
        if self.should_include_field():
            manifest.making_instructions = [
                self.generate_document_ref(DocumentationType.USER_MANUAL, "User Manual"),
                self.generate_document_ref(DocumentationType.MAINTENANCE_INSTRUCTIONS, "Maintenance Guide")
            ]
            
        # Add manufacturing processes
        manifest.manufacturing_processes = template["manufacturing_processes"]
        
        # Add materials
        for _ in range(random.randint(1, 4)):
            manifest.materials.append(self.generate_material_spec())
            
        # Add manufacturing specifications
        if self.should_include_field():
            process_requirements = []
            for process in template["manufacturing_processes"]:
                if process in ["3DP", "CNC", "PCB", "LASER"]:
                    process_requirements.append(self.generate_process_requirement(process))
                    
            manifest.manufacturing_specs = ManufacturingSpec(
                joining_processes=random.choice([["Screws"], ["Adhesive"], ["Welding"], ["Press-fit"]]),
                outer_dimensions={
                    "length": random.randint(50, 500),
                    "width": random.randint(50, 500),
                    "height": random.randint(20, 200)
                } if self.should_include_field() else None,
                process_requirements=process_requirements,
                quality_standards=[random.choice(["ISO 9001", "CE", "FCC", "RoHS"])] if self.should_include_field() else [],
                notes=f"Manufacturing notes: {self.faker.sentence()}" if self.should_include_field() else ""
            )
            
        # Add parts
        for _ in range(random.randint(1, 5)):
            manifest.parts.append(self.generate_part_spec(template))
            
        # Add TSDC codes
        manifest.tsdc = list(set([part.tsdc[0] for part in manifest.parts if part.tsdc]))
        
        return manifest

class OKWGenerator(SyntheticDataGenerator):
    """Generator for OKW manufacturing facilities"""
    
    def __init__(self, complexity: str = "mixed"):
        super().__init__(complexity)
        
        # Realistic facility templates
        self.facility_templates = [
            {
                "name": "Community Makerspace",
                "description": "Public makerspace with basic fabrication equipment",
                "access_type": AccessType.MEMBERSHIP,
                "equipment_types": ["3D printer", "Laser cutter", "CNC router"],
                "batch_size": BatchSize.SMALL,
                "certifications": ["Basic Safety"]
            },
            {
                "name": "Professional Machine Shop",
                "description": "Commercial machining facility with precision equipment",
                "access_type": AccessType.RESTRICTED,
                "equipment_types": ["CNC mill", "CNC lathe", "Surface grinder"],
                "batch_size": BatchSize.MEDIUM,
                "certifications": ["ISO 9001", "AS9100"]
            },
            {
                "name": "Rapid Prototyping Lab",
                "description": "University research facility for rapid prototyping",
                "access_type": AccessType.RESTRICTED_PUBLIC,
                "equipment_types": ["3D printer", "SLA printer", "CNC mill"],
                "batch_size": BatchSize.SMALL,
                "certifications": ["Research Grade"]
            },
            {
                "name": "Industrial Manufacturing Plant",
                "description": "Large-scale manufacturing facility",
                "access_type": AccessType.RESTRICTED,
                "equipment_types": ["CNC mill", "CNC lathe", "Sheet metal brake", "Welder"],
                "batch_size": BatchSize.LARGE,
                "certifications": ["ISO 9001", "ISO 14001", "OHSAS 18001"]
            },
            {
                "name": "Electronics Assembly House",
                "description": "Specialized in PCB assembly and electronics manufacturing",
                "access_type": AccessType.RESTRICTED,
                "equipment_types": ["Pick and place", "Reflow oven", "AOI", "ICT"],
                "batch_size": BatchSize.MEDIUM,
                "certifications": ["IPC-A-610", "ISO 9001"]
            }
        ]
        
        # Equipment specifications
        self.equipment_specs = {
            "3D printer": {
                "makes": ["Prusa", "Ultimaker", "Creality", "Formlabs"],
                "models": ["i3 MK3S+", "S5", "Ender 3", "Form 3"],
                "process": "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
                "materials": ["PLA", "PETG", "ABS", "TPU"],
                "properties": {"build_volume": [200, 300, 400], "nozzle_size": [0.4, 0.6, 0.8]}
            },
            "CNC mill": {
                "makes": ["Haas", "Mazak", "DMG Mori", "Tormach"],
                "models": ["VF-2", "VTC-20", "DMU 50", "PCNC 440"],
                "process": "https://en.wikipedia.org/wiki/Machining",
                "materials": ["Aluminum", "Steel", "Plastic", "Wood"],
                "properties": {"working_surface": [400, 600, 800], "axes": [3, 4, 5]}
            },
            "Laser cutter": {
                "makes": ["Epilog", "Trotec", "Universal", "Boss"],
                "models": ["Fusion Pro", "Speedy 300", "VLS 3.50", "LS-1630"],
                "process": "https://en.wikipedia.org/wiki/Laser_cutting",
                "materials": ["Acrylic", "Wood", "Fabric", "Leather"],
                "properties": {"laser_power": [30, 60, 100], "working_surface": [300, 600, 900]}
            },
            "CNC router": {
                "makes": ["ShopBot", "Axiom", "Shapeoko", "Onefinity"],
                "models": ["Desktop", "Pro", "XXL", "Woodworker"],
                "process": "https://en.wikipedia.org/wiki/CNC_router",
                "materials": ["Wood", "Plastic", "Aluminum", "Foam"],
                "properties": {"working_surface": [300, 600, 1200], "axes": [3, 4]}
            }
        }

    def generate_address(self) -> Address:
        """Generate a realistic address"""
        return Address(
            number=str(random.randint(1, 9999)),
            street=self.faker.street_name(),
            city=self.faker.city(),
            region=self.faker.state(),
            country=self.faker.country(),
            postcode=self.faker.postcode()
        )

    def generate_location(self) -> Location:
        """Generate a realistic location"""
        address = self.generate_address()
        
        # Generate GPS coordinates (roughly in North America/Europe)
        lat = round(random.uniform(25.0, 70.0), 6)
        lon = round(random.uniform(-125.0, 40.0), 6)
        
        return Location(
            address=address,
            gps_coordinates=f"{lat}, {lon}",
            directions=f"Located {random.choice(['near', 'behind', 'across from'])} {self.faker.company()}" if self.should_include_field() else None,
            city=address.city,
            country=address.country
        )

    def generate_contact(self) -> Contact:
        """Generate realistic contact information"""
        return Contact(
            landline=f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}" if self.should_include_field() else None,
            mobile=f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}" if self.should_include_field() else None,
            email=f"info@{self.faker.domain_name()}" if self.should_include_field() else None,
            whatsapp=f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}" if self.should_include_field() else None
        )

    def generate_social_media(self) -> SocialMedia:
        """Generate realistic social media information"""
        if not self.should_include_field():
            return SocialMedia()
            
        return SocialMedia(
            facebook=f"https://facebook.com/{self.faker.user_name()}" if random.choice([True, False]) else None,
            twitter=f"@{self.faker.user_name()}" if random.choice([True, False]) else None,
            instagram=f"@{self.faker.user_name()}" if random.choice([True, False]) else None,
            other_urls=[f"https://{self.faker.domain_name()}" for _ in range(random.randint(0, 2))]
        )

    def generate_agent(self) -> Agent:
        """Generate a realistic agent (person or organization)"""
        return Agent(
            name=self.faker.company(),
            location=self.generate_location() if self.should_include_field() else None,
            contact_person=self.faker.name() if self.should_include_field() else None,
            bio=f"Established in {random.randint(1990, 2020)}, we specialize in {self.faker.catch_phrase()}" if self.should_include_field() else None,
            website=f"https://{self.faker.domain_name()}" if self.should_include_field() else None,
            languages=random.sample(["en", "es", "fr", "de"], random.randint(1, 3)) if self.should_include_field() else [],
            mailing_list=f"{self.faker.user_name()}@lists.{self.faker.domain_name()}" if self.should_include_field() else None,
            images=[f"images/{self.faker.word()}.jpg" for _ in range(random.randint(0, 3))] if self.should_include_field() else [],
            contact=self.generate_contact(),
            social_media=self.generate_social_media()
        )

    def generate_material(self, material_type: str) -> Material:
        """Generate a realistic material"""
        return Material(
            material_type=f"https://en.wikipedia.org/wiki/{material_type.replace(' ', '_')}",
            manufacturer=random.choice(["Generic", "Brand A", "Brand B", "Premium"]) if self.should_include_field() else None,
            brand=random.choice(["Standard", "Professional", "Industrial"]) if self.should_include_field() else None,
            supplier_location=self.generate_location() if self.should_include_field() else None
        )

    def generate_equipment(self, equipment_type: str) -> Equipment:
        """Generate realistic equipment"""
        if equipment_type not in self.equipment_specs:
            # Generic equipment
            return Equipment(
                equipment_type=f"https://en.wikipedia.org/wiki/{equipment_type.replace(' ', '_')}",
                manufacturing_process=f"https://en.wikipedia.org/wiki/{equipment_type.replace(' ', '_')}",
                make=random.choice(["Generic", "Brand A", "Brand B"]),
                model=f"Model {random.randint(100, 999)}",
                condition=random.choice(["Excellent", "Good", "Fair"]),
                computer_controlled=random.choice([True, False])
            )
        
        spec = self.equipment_specs[equipment_type]
        make = random.choice(spec["makes"])
        model = random.choice(spec["models"])
        
        # Generate equipment-specific properties
        properties = {}
        for prop, values in spec["properties"].items():
            if prop == "build_volume":
                size = random.choice(values)
                properties["build_volume"] = size * size * size  # cubic mm
            elif prop == "working_surface":
                properties["working_surface"] = random.choice(values)
            elif prop == "laser_power":
                properties["laser_power"] = random.choice(values)
            elif prop == "axes":
                properties["axes"] = random.choice(values)
            elif prop == "nozzle_size":
                properties["nozzle_size"] = random.choice(values)
        
        return Equipment(
            equipment_type=f"https://en.wikipedia.org/wiki/{equipment_type.replace(' ', '_')}",
            manufacturing_process=spec["process"],
            make=make,
            model=model,
            serial_number=f"SN{random.randint(100000, 999999)}" if self.should_include_field() else None,
            condition=random.choice(["Excellent", "Good", "Fair", "Needs Maintenance"]),
            notes=f"Equipment notes: {self.faker.sentence()}" if self.should_include_field() else None,
            quantity=random.randint(1, 5) if self.should_include_field() else None,
            throughput=f"{random.randint(1, 100)} parts/hour" if self.should_include_field() else None,
            power_rating=random.randint(1000, 10000) if self.should_include_field() else None,
            materials_worked=[self.generate_material(mat) for mat in spec["materials"]],
            maintenance_schedule=f"Every {random.randint(1, 12)} months" if self.should_include_field() else None,
            usage_levels=random.choice(["Low", "Medium", "High"]) if self.should_include_field() else None,
            tolerance_class=random.choice(["ISO 2768-f", "ISO 2768-m", "ISO 2768-c"]) if self.should_include_field() else None,
            computer_controlled=True,
            extraction_system=random.choice([True, False]) if self.should_include_field() else False,
            uninterrupted_power_supply=random.choice([True, False]) if self.should_include_field() else False,
            **properties
        )

    def generate_manufacturing_facility(self) -> ManufacturingFacility:
        """Generate a complete manufacturing facility"""
        template = random.choice(self.facility_templates)
        
        # Generate basic facility
        facility = ManufacturingFacility(
            name=template["name"],
            location=self.generate_location(),
            facility_status=random.choice([FacilityStatus.ACTIVE, FacilityStatus.ACTIVE, FacilityStatus.ACTIVE, FacilityStatus.PLANNED]),  # Mostly active
            access_type=template["access_type"],
            description=template["description"]
        )
        
        # Add optional fields based on complexity
        if self.should_include_field():
            facility.owner = self.generate_agent()
            
        if self.should_include_field():
            facility.contact = self.generate_agent()
            
        if self.should_include_field():
            facility.opening_hours = f"Mon-Fri: {random.randint(6, 9)}:00-{random.randint(17, 22)}:00"
            
        if self.should_include_field():
            facility.date_founded = date(random.randint(1990, 2020), random.randint(1, 12), random.randint(1, 28))
            
        if self.should_include_field():
            facility.wheelchair_accessibility = random.choice(["Fully accessible", "Partially accessible", "Not accessible"])
            
        # Add equipment
        for equipment_type in template["equipment_types"]:
            facility.equipment.append(self.generate_equipment(equipment_type))
            
        # Add manufacturing processes
        facility.manufacturing_processes = [
            f"https://en.wikipedia.org/wiki/{process.replace(' ', '_')}" 
            for process in template["equipment_types"]
        ]
        
        # Add batch size
        facility.typical_batch_size = template["batch_size"]
        
        # Add facility properties
        if self.should_include_field():
            facility.floor_size = random.randint(100, 5000)  # square meters
            
        if self.should_include_field():
            facility.storage_capacity = f"{random.randint(10, 1000)} cubic meters"
            
        if self.should_include_field():
            facility.certifications = template["certifications"]
            
        # Add boolean properties
        facility.backup_generator = random.choice([True, False]) if self.should_include_field() else False
        facility.uninterrupted_power_supply = random.choice([True, False]) if self.should_include_field() else False
        facility.road_access = random.choice([True, False]) if self.should_include_field() else True
        facility.loading_dock = random.choice([True, False]) if self.should_include_field() else False
        
        if self.should_include_field():
            facility.maintenance_schedule = f"Every {random.randint(1, 6)} months"
            
        if self.should_include_field():
            facility.typical_products = [self.faker.catch_phrase() for _ in range(random.randint(1, 5))]
            
        # Add sub-property collections
        if self.should_include_field():
            facility.circular_economy = CircularEconomy(
                applies_principles=random.choice([True, False]),
                description=f"Circular economy practices: {self.faker.sentence()}" if random.choice([True, False]) else None,
                by_products=[self.faker.word() for _ in range(random.randint(0, 3))]
            )
            
        if self.should_include_field():
            facility.human_capacity = HumanCapacity(
                headcount=random.randint(1, 50)
            )
            
        if self.should_include_field():
            facility.innovation_space = InnovationSpace(
                staff=random.randint(0, 10),
                learning_resources=[self.faker.catch_phrase() for _ in range(random.randint(0, 5))],
                services=[self.faker.catch_phrase() for _ in range(random.randint(0, 5))],
                footfall=random.randint(0, 100),
                residencies=random.choice([True, False])
            )
            
        # Add record data
        if self.should_include_field():
            facility.record_data = RecordData(
                date_created=datetime.now(),
                created_by=self.generate_agent(),
                data_collection_method=random.choice(["Survey", "Interview", "Website", "Direct observation"])
            )
            
        return facility

def validate_record(record: Union[OKHManifest, ManufacturingFacility]) -> bool:
    """Validate a generated record"""
    try:
        if isinstance(record, OKHManifest):
            record.validate()
        # OKW facilities don't have a validate method, but we can check basic requirements
        elif isinstance(record, ManufacturingFacility):
            if not record.name or not record.location or not record.facility_status:
                return False
        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def save_record(record: Union[OKHManifest, ManufacturingFacility], output_dir: str, index: int) -> str:
    """Save a record to a JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    record_type = "okh" if isinstance(record, OKHManifest) else "okw"
    filename = f"{record_type}_manifest_{index:03d}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(record.to_dict(), f, indent=2, ensure_ascii=False, default=str)
    
    return filepath

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate synthetic OKH and OKW data")
    parser.add_argument("--type", choices=["okh", "okw"], required=True, help="Type of data to generate")
    parser.add_argument("--count", type=int, default=10, help="Number of records to generate")
    parser.add_argument("--complexity", choices=["minimal", "complex", "mixed"], default="mixed", help="Complexity level of generated data")
    parser.add_argument("--output-dir", default="./synthetic_data", help="Output directory for generated files")
    parser.add_argument("--validate", action="store_true", help="Validate generated records")
    
    args = parser.parse_args()
    
    print(f"Generating {args.count} {args.type.upper()} records with {args.complexity} complexity...")
    
    # Initialize generator
    if args.type == "okh":
        generator = OKHGenerator(args.complexity)
    else:
        generator = OKWGenerator(args.complexity)
    
    generated_count = 0
    failed_count = 0
    
    for i in range(args.count):
        try:
            # Generate record
            if args.type == "okh":
                record = generator.generate_okh_manifest()
            else:
                record = generator.generate_manufacturing_facility()
            
            # Validate if requested
            if args.validate and not validate_record(record):
                print(f"Warning: Record {i+1} failed validation, skipping...")
                failed_count += 1
                continue
            
            # Save record
            filepath = save_record(record, args.output_dir, i + 1)
            print(f"Generated: {filepath}")
            generated_count += 1
            
        except Exception as e:
            print(f"Error generating record {i+1}: {e}")
            failed_count += 1
    
    print(f"\nGeneration complete!")
    print(f"Successfully generated: {generated_count} records")
    print(f"Failed: {failed_count} records")
    print(f"Output directory: {args.output_dir}")

if __name__ == "__main__":
    main()
