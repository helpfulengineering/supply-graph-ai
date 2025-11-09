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
from typing import Dict, List, Union

from faker import Faker

# Add the src directory to the path so we can import the models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models.okh import (
    OKHManifest, License, Person, Organization, DocumentRef, MaterialSpec,
    ProcessRequirement, ManufacturingSpec, Standard, PartSpec,
    DocumentationType
)
from core.models.okw import (
    ManufacturingFacility, Equipment, Location, Address, Agent,
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
        
        # Domain-specific keywords for different hardware types
        self.keyword_templates = {
            "iot": ["sensor", "wireless", "connectivity", "monitoring", "data", "network", "embedded", "microcontroller"],
            "cnc": ["precision", "machining", "tolerance", "surface", "finish", "dimensional", "accuracy", "metalworking"],
            "laser": ["cutting", "engraving", "precision", "vector", "raster", "material", "thickness", "speed"],
            "3d_printing": ["additive", "layer", "infill", "support", "resolution", "filament", "bed", "extrusion"],
            "electronics": ["circuit", "pcb", "component", "soldering", "assembly", "testing", "voltage", "current"],
            "mechanical": ["assembly", "fastener", "bearing", "gear", "shaft", "housing", "mount", "bracket"]
        }
        
        # Standards by domain and process
        self.standards_by_domain = {
            "general": [
                {"standard_title": "ISO 9001:2015", "publisher": "ISO", "reference": "ISO 9001:2015"},
                {"standard_title": "CE Marking", "publisher": "EU", "reference": "CE"},
                {"standard_title": "RoHS Compliance", "publisher": "EU", "reference": "RoHS 2011/65/EU"}
            ],
            "electronics": [
                {"standard_title": "IPC-A-610", "publisher": "IPC", "reference": "IPC-A-610"},
                {"standard_title": "FCC Part 15", "publisher": "FCC", "reference": "47 CFR Part 15"},
                {"standard_title": "IEC 61000", "publisher": "IEC", "reference": "IEC 61000"}
            ],
            "mechanical": [
                {"standard_title": "ISO 2768", "publisher": "ISO", "reference": "ISO 2768"},
                {"standard_title": "ASME Y14.5", "publisher": "ASME", "reference": "ASME Y14.5"},
                {"standard_title": "DIN 7168", "publisher": "DIN", "reference": "DIN 7168"}
            ],
            "safety": [
                {"standard_title": "ISO 13849", "publisher": "ISO", "reference": "ISO 13849"},
                {"standard_title": "IEC 61508", "publisher": "IEC", "reference": "IEC 61508"},
                {"standard_title": "UL 94", "publisher": "UL", "reference": "UL 94"}
            ]
        }
        
        # Tool categories and specific tools
        self.tool_categories = {
            "3DP": ["3D printer", "Filament", "Build plate", "Nozzle", "Calipers", "Deburring tool", "Heat gun"],
            "CNC": ["CNC mill", "Cutting tools", "Workholding", "CMM", "Surface plate", "Dial indicator", "Micrometer"],
            "LASER": ["Laser cutter", "Air assist", "Focus lens", "Cutting bed", "Material guides", "Exhaust system"],
            "PCB": ["PCB mill", "Soldering station", "Multimeter", "Oscilloscope", "Pick and place", "Reflow oven"],
            "SHEET": ["Sheet metal brake", "Shear", "Punch press", "Welder", "Grinder", "Drill press"],
            "Assembly": ["Screwdriver set", "Wrench set", "Pliers", "Crimping tool", "Heat shrink", "Cable ties"]
        }

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
            DocumentationType.OPERATING_INSTRUCTIONS: [".pdf", ".html", ".md"],
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

    def generate_keywords(self, template: Dict) -> List[str]:
        """Generate domain-specific keywords based on template"""
        keywords = []
        
        # Add keywords based on manufacturing processes
        for process in template["manufacturing_processes"]:
            if process in self.keyword_templates:
                keywords.extend(random.sample(self.keyword_templates[process], random.randint(2, 4)))
        
        # Add general hardware keywords
        keywords.extend(random.sample(self.keyword_templates["mechanical"], random.randint(1, 3)))
        
        # Add some random technical terms
        tech_terms = ["prototype", "open-source", "modular", "customizable", "reproducible", "documented"]
        keywords.extend(random.sample(tech_terms, random.randint(1, 2)))
        
        return list(set(keywords))  # Remove duplicates
    
    def generate_standards(self, template: Dict) -> List[Standard]:
        """Generate relevant standards based on template"""
        standards = []
        
        # Always include general standards
        general_standards = random.sample(self.standards_by_domain["general"], random.randint(1, 2))
        for std_data in general_standards:
            standards.append(Standard(
                standard_title=std_data["standard_title"],
                publisher=std_data["publisher"],
                reference=std_data["reference"],
                certifications=[{"type": "compliance", "status": "required"}] if self.should_include_field() else []
            ))
        
        # Add domain-specific standards
        if "PCB" in template["manufacturing_processes"]:
            electronics_standards = random.sample(self.standards_by_domain["electronics"], random.randint(1, 2))
            for std_data in electronics_standards:
                standards.append(Standard(
                    standard_title=std_data["standard_title"],
                    publisher=std_data["publisher"],
                    reference=std_data["reference"],
                    certifications=[{"type": "testing", "status": "passed"}] if self.should_include_field() else []
                ))
        
        if any(proc in template["manufacturing_processes"] for proc in ["CNC", "SHEET"]):
            mechanical_standards = random.sample(self.standards_by_domain["mechanical"], random.randint(1, 2))
            for std_data in mechanical_standards:
                standards.append(Standard(
                    standard_title=std_data["standard_title"],
                    publisher=std_data["publisher"],
                    reference=std_data["reference"],
                    certifications=[{"type": "certification", "status": "valid"}] if self.should_include_field() else []
                ))
        
        return standards
    
    def generate_tool_list(self, template: Dict) -> List[str]:
        """Generate tool list based on manufacturing processes"""
        tools = []
        
        # Add tools for each manufacturing process
        for process in template["manufacturing_processes"]:
            if process in self.tool_categories:
                # Select 3-5 tools from each category
                selected_tools = random.sample(self.tool_categories[process], random.randint(3, 5))
                tools.extend(selected_tools)
        
        # Add general assembly tools
        if self.should_include_field():
            assembly_tools = random.sample(self.tool_categories["Assembly"], random.randint(2, 4))
            tools.extend(assembly_tools)
        
        return list(set(tools))  # Remove duplicates
    
    def generate_making_instructions(self, template: Dict) -> List[DocumentRef]:
        """Generate detailed making instruction documents"""
        instructions = []
        
        # Assembly guide
        instructions.append(self.generate_document_ref(
            DocumentationType.MANUFACTURING_FILES,
            f"Assembly Guide for {template['title']}"
        ))
        
        # Manufacturing instructions for each process
        for process in template["manufacturing_processes"]:
            if process == "3DP":
                instructions.append(self.generate_document_ref(
                    DocumentationType.MANUFACTURING_FILES,
                    "3D Printing Setup and Parameters"
                ))
            elif process == "CNC":
                instructions.append(self.generate_document_ref(
                    DocumentationType.MANUFACTURING_FILES,
                    "CNC Machining Instructions"
                ))
            elif process == "PCB":
                instructions.append(self.generate_document_ref(
                    DocumentationType.MANUFACTURING_FILES,
                    "PCB Assembly Guide"
                ))
        
        # Quality control instructions
        if self.should_include_field():
            instructions.append(self.generate_document_ref(
                DocumentationType.TECHNICAL_SPECIFICATIONS,
                "Quality Control and Testing Procedures"
            ))
        
        # Risk assessment
        if self.should_include_field():
            instructions.append(self.generate_document_ref(
                DocumentationType.RISK_ASSESSMENT,
                "Safety and Risk Assessment"
            ))
        
        return instructions
    
    def generate_bom_reference(self, template: Dict) -> str:
        """Generate bill of materials reference"""
        return f"https://github.com/{self.faker.user_name()}/project/raw/main/docs/bom_{template['title'].lower().replace(' ', '_')}.csv"
    
    def generate_quality_instructions(self, template: Dict) -> List[DocumentRef]:
        """Generate quality control instruction documents"""
        quality_docs = []
        
        # Basic quality control
        quality_docs.append(self.generate_document_ref(
            DocumentationType.TECHNICAL_SPECIFICATIONS,
            "Quality Control Checklist"
        ))
        
        # Process-specific quality instructions
        for process in template["manufacturing_processes"]:
            if process == "CNC":
                quality_docs.append(self.generate_document_ref(
                    DocumentationType.TECHNICAL_SPECIFICATIONS,
                    "Dimensional Inspection Procedures"
                ))
            elif process == "PCB":
                quality_docs.append(self.generate_document_ref(
                    DocumentationType.TECHNICAL_SPECIFICATIONS,
                    "Electrical Testing Protocol"
                ))
        
        return quality_docs
    
    def generate_risk_assessment(self, template: Dict) -> List[DocumentRef]:
        """Generate risk assessment documents"""
        risk_docs = []
        
        # General risk assessment
        risk_docs.append(self.generate_document_ref(
            DocumentationType.RISK_ASSESSMENT,
            "General Safety and Risk Assessment"
        ))
        
        # Process-specific risk assessments
        for process in template["manufacturing_processes"]:
            if process in ["CNC", "LASER", "SHEET"]:
                risk_docs.append(self.generate_document_ref(
                    DocumentationType.RISK_ASSESSMENT,
                    f"{process} Safety Procedures"
                ))
        
        return risk_docs
    
    def generate_compliance_docs(self, template: Dict) -> List[DocumentRef]:
        """Generate regulatory compliance documents"""
        compliance_docs = []
        
        # General compliance
        compliance_docs.append(self.generate_document_ref(
            DocumentationType.MANUFACTURING_FILES,
            "Regulatory Compliance Statement"
        ))
        
        # Standards compliance
        if self.should_include_field():
            compliance_docs.append(self.generate_document_ref(
                DocumentationType.MANUFACTURING_FILES,
                "Standards Compliance Documentation"
            ))
        
        return compliance_docs

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
            
        # Enhanced keywords generation
        manifest.keywords = self.generate_keywords(template)
            
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
            
        # Enhanced tool list generation
        manifest.tool_list = self.generate_tool_list(template)
        
        # Enhanced standards generation
        manifest.standards_used = self.generate_standards(template)
        
        # Enhanced making instructions
        manifest.making_instructions = self.generate_making_instructions(template)
        
        # BOM reference
        if self.should_include_field():
            manifest.bom = self.generate_bom_reference(template)
            
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
            
        # Quality instructions and risk assessment
        if self.should_include_field():
            quality_instructions = self.generate_quality_instructions(template)
            # Add to manufacturing_files since OKH doesn't have separate quality_instructions field
            manifest.manufacturing_files.extend(quality_instructions)
            
        if self.should_include_field():
            risk_assessments = self.generate_risk_assessment(template)
            # Add to manufacturing_files since OKH doesn't have separate risk_assessment field
            manifest.manufacturing_files.extend(risk_assessments)
            
        if self.should_include_field():
            compliance_docs = self.generate_compliance_docs(template)
            manifest.manufacturing_files.extend(compliance_docs)
            
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
                "properties": {"build_volume": [200, 300, 400], "nozzle_size": [0.4, 0.6, 0.8]},
                "capabilities": {
                    "layer_height_range": "0.1-0.3mm",
                    "print_speed": "20-100mm/s",
                    "temperature_range": "200-280°C",
                    "bed_temperature": "60-100°C",
                    "supported_formats": ["STL", "OBJ", "3MF"]
                }
            },
            "CNC mill": {
                "makes": ["Haas", "Mazak", "DMG Mori", "Tormach"],
                "models": ["VF-2", "VTC-20", "DMU 50", "PCNC 440"],
                "process": "https://en.wikipedia.org/wiki/Machining",
                "materials": ["Aluminum", "Steel", "Plastic", "Wood"],
                "properties": {"working_surface": [400, 600, 800], "axes": [3, 4, 5]},
                "capabilities": {
                    "tolerance": "±0.01mm",
                    "surface_finish": "Ra 0.8-3.2μm",
                    "spindle_speed": "1000-12000 RPM",
                    "feed_rate": "100-2000 mm/min",
                    "tool_changer": "Automatic"
                }
            },
            "Laser cutter": {
                "makes": ["Epilog", "Trotec", "Universal", "Boss"],
                "models": ["Fusion Pro", "Speedy 300", "VLS 3.50", "LS-1630"],
                "process": "https://en.wikipedia.org/wiki/Laser_cutting",
                "materials": ["Acrylic", "Wood", "Fabric", "Leather"],
                "properties": {"laser_power": [30, 60, 100], "working_surface": [300, 600, 900]},
                "capabilities": {
                    "cutting_thickness": "0.1-25mm",
                    "engraving_depth": "0.1-2mm",
                    "cutting_speed": "1-1000 mm/min",
                    "resolution": "1000 DPI",
                    "supported_formats": ["DXF", "AI", "PDF"]
                }
            },
            "CNC router": {
                "makes": ["ShopBot", "Axiom", "Shapeoko", "Onefinity"],
                "models": ["Desktop", "Pro", "XXL", "Woodworker"],
                "process": "https://en.wikipedia.org/wiki/CNC_router",
                "materials": ["Wood", "Plastic", "Aluminum", "Foam"],
                "properties": {"working_surface": [300, 600, 1200], "axes": [3, 4]},
                "capabilities": {
                    "tolerance": "±0.1mm",
                    "spindle_speed": "5000-24000 RPM",
                    "feed_rate": "100-5000 mm/min",
                    "tool_diameter": "0.5-25mm",
                    "cutting_depth": "0.1-50mm"
                }
            }
        }
        
        # Certification templates by facility type
        self.certification_templates = {
            "makerspace": [
                "Basic Safety Training",
                "Equipment Operation Certification",
                "First Aid Training"
            ],
            "professional": [
                "ISO 9001:2015",
                "AS9100",
                "ISO 14001",
                "OHSAS 18001",
                "NADCAP"
            ],
            "university": [
                "Research Grade Equipment",
                "Academic Standards Compliance",
                "Safety Protocol Certification"
            ],
            "industrial": [
                "ISO 9001:2015",
                "ISO 14001",
                "ISO 45001",
                "IATF 16949",
                "AS9100"
            ],
            "electronics": [
                "IPC-A-610",
                "IPC-J-STD-001",
                "ISO 9001:2015",
                "RoHS Compliance"
            ]
        }
        
        # Capacity metrics templates
        self.capacity_metrics = {
            "throughput": {
                "3D printer": "1-10 parts/hour",
                "CNC mill": "1-50 parts/hour", 
                "Laser cutter": "10-100 parts/hour",
                "CNC router": "5-30 parts/hour"
            },
            "lead_times": {
                "prototype": "1-3 days",
                "small_batch": "1-2 weeks",
                "medium_batch": "2-4 weeks",
                "large_batch": "4-8 weeks"
            },
            "queue_status": ["Available", "Busy", "Booked", "Maintenance"]
        }
        
        # Quality systems templates
        self.quality_systems = {
            "inspection_equipment": [
                "CMM (Coordinate Measuring Machine)",
                "Surface roughness tester",
                "Digital calipers",
                "Micrometers",
                "Go/no-go gauges",
                "Optical comparator"
            ],
            "qms_standards": [
                "ISO 9001:2015",
                "AS9100",
                "IATF 16949",
                "ISO 13485"
            ],
            "measurement_capabilities": [
                "Dimensional inspection",
                "Surface finish measurement",
                "Material testing",
                "Electrical testing",
                "Functional testing"
            ]
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

    def generate_detailed_capabilities(self, equipment_type: str) -> Dict:
        """Generate detailed process capabilities for equipment"""
        if equipment_type not in self.equipment_specs:
            return {}
        
        spec = self.equipment_specs[equipment_type]
        capabilities = spec.get("capabilities", {}).copy()
        
        # Add some variability to capabilities
        if "tolerance" in capabilities:
            # Add tolerance variations - handle the tolerance string properly
            base_tolerance = capabilities["tolerance"]
            try:
                # Extract numeric value from tolerance string like "±0.01mm"
                if "±" in base_tolerance and "mm" in base_tolerance:
                    tolerance_value = float(base_tolerance.split('±')[1].replace('mm', ''))
                    variations = [
                        base_tolerance, 
                        f"±{tolerance_value * 1.5:.3f}mm", 
                        f"±{tolerance_value * 2:.3f}mm"
                    ]
                    capabilities["tolerance_range"] = random.choice(variations)
                else:
                    capabilities["tolerance_range"] = base_tolerance
            except (ValueError, IndexError):
                # If parsing fails, just use the original tolerance
                capabilities["tolerance_range"] = base_tolerance
        
        # Add material-specific capabilities
        materials = spec.get("materials", [])
        if materials:
            capabilities["supported_materials"] = random.sample(materials, random.randint(2, len(materials)))
        
        # Add process parameters
        capabilities["process_parameters"] = {
            "setup_time": f"{random.randint(15, 120)} minutes",
            "cycle_time": f"{random.randint(5, 60)} minutes",
            "changeover_time": f"{random.randint(10, 45)} minutes"
        }
        
        return capabilities
    
    def generate_certification_details(self, facility_type: str) -> List[Dict]:
        """Generate detailed certification information"""
        cert_templates = self.certification_templates.get(facility_type, self.certification_templates["professional"])
        certifications = []
        
        # Select 2-4 certifications
        selected_certs = random.sample(cert_templates, random.randint(2, min(4, len(cert_templates))))
        
        for cert in selected_certs:
            cert_detail = {
                "name": cert,
                "issuing_body": self._get_cert_issuing_body(cert),
                "issue_date": self.faker.date_between(start_date="-5y", end_date="today").isoformat(),
                "expiry_date": self.faker.date_between(start_date="today", end_date="+3y").isoformat(),
                "certification_number": f"CERT-{random.randint(100000, 999999)}",
                "scope": self._get_cert_scope(cert),
                "status": random.choice(["Active", "Active", "Active", "Pending Renewal"])
            }
            certifications.append(cert_detail)
        
        return certifications
    
    def _get_cert_issuing_body(self, cert_name: str) -> str:
        """Get issuing body for certification"""
        issuing_bodies = {
            "ISO": "International Organization for Standardization",
            "AS9100": "SAE International",
            "IPC": "IPC - Association Connecting Electronics Industries",
            "NADCAP": "PRI (Performance Review Institute)",
            "IATF": "International Automotive Task Force"
        }
        
        for key, body in issuing_bodies.items():
            if key in cert_name:
                return body
        return "Certification Body"
    
    def _get_cert_scope(self, cert_name: str) -> str:
        """Get scope for certification"""
        scopes = {
            "ISO 9001": "Quality Management System",
            "AS9100": "Aerospace Quality Management",
            "IPC-A-610": "Acceptability of Electronic Assemblies",
            "ISO 14001": "Environmental Management System",
            "IATF 16949": "Automotive Quality Management"
        }
        
        for key, scope in scopes.items():
            if key in cert_name:
                return scope
        return "General Manufacturing"
    
    def generate_capacity_metrics(self, equipment_types: List[str]) -> Dict:
        """Generate capacity metrics for facility"""
        metrics = {}
        
        # Throughput metrics
        total_throughput = []
        for eq_type in equipment_types:
            if eq_type in self.capacity_metrics["throughput"]:
                throughput = self.capacity_metrics["throughput"][eq_type]
                total_throughput.append(throughput)
        
        if total_throughput:
            metrics["throughput"] = {
                "equipment_throughput": dict(zip(equipment_types, total_throughput)),
                "facility_capacity": f"{random.randint(10, 1000)} parts/day",
                "utilization_rate": f"{random.randint(60, 95)}%"
            }
        
        # Lead times
        metrics["lead_times"] = {
            "prototype": self.capacity_metrics["lead_times"]["prototype"],
            "small_batch": self.capacity_metrics["lead_times"]["small_batch"],
            "medium_batch": self.capacity_metrics["lead_times"]["medium_batch"],
            "large_batch": self.capacity_metrics["lead_times"]["large_batch"]
        }
        
        # Queue status
        metrics["queue_status"] = {
            "current_status": random.choice(self.capacity_metrics["queue_status"]),
            "queue_length": random.randint(0, 20),
            "estimated_wait_time": f"{random.randint(1, 14)} days"
        }
        
        return metrics
    
    def generate_material_inventory(self, equipment_types: List[str]) -> List[Dict]:
        """Generate material inventory with quantities and specifications"""
        inventory = []
        
        # Get materials from equipment specs
        all_materials = set()
        for eq_type in equipment_types:
            if eq_type in self.equipment_specs:
                materials = self.equipment_specs[eq_type].get("materials", [])
                all_materials.update(materials)
        
        # Generate inventory for each material
        for material in list(all_materials)[:random.randint(3, 8)]:  # Limit to 3-8 materials
            item = {
                "material_name": material,
                "quantity_available": random.randint(10, 1000),
                "unit": random.choice(["kg", "m", "m²", "pieces", "rolls"]),
                "specifications": {
                    "grade": random.choice(["A", "B", "C", "Premium", "Standard"]),
                    "color": random.choice(["Natural", "Black", "White", "Clear", "Custom"]) if "PLA" in material or "ABS" in material else None,
                    "thickness": f"{random.uniform(0.1, 10):.1f}mm" if "sheet" in material.lower() else None
                },
                "supplier": self.faker.company(),
                "last_restocked": self.faker.date_between(start_date="-3M", end_date="today").isoformat(),
                "cost_per_unit": f"${random.uniform(1, 100):.2f}"
            }
            inventory.append(item)
        
        return inventory
    
    def generate_quality_systems(self, facility_type: str) -> Dict:
        """Generate quality systems information"""
        qs = {}
        
        # Inspection equipment
        if self.should_include_field():
            qs["inspection_equipment"] = random.sample(
                self.quality_systems["inspection_equipment"], 
                random.randint(2, 5)
            )
        
        # QMS standards
        if self.should_include_field():
            qs["qms_standards"] = random.sample(
                self.quality_systems["qms_standards"],
                random.randint(1, 3)
            )
        
        # Measurement capabilities
        if self.should_include_field():
            qs["measurement_capabilities"] = random.sample(
                self.quality_systems["measurement_capabilities"],
                random.randint(2, 4)
            )
        
        # Quality metrics
        qs["quality_metrics"] = {
            "first_pass_yield": f"{random.randint(85, 99)}%",
            "defect_rate": f"{random.uniform(0.1, 2.0):.1f}%",
            "customer_satisfaction": f"{random.randint(4, 5)}.{random.randint(0, 9)}/5.0",
            "on_time_delivery": f"{random.randint(90, 100)}%"
        }
        
        return qs
    
    def generate_process_parameters(self, equipment_types: List[str]) -> Dict:
        """Generate detailed process parameters for each equipment type"""
        parameters = {}
        
        for eq_type in equipment_types:
            if eq_type in self.equipment_specs:
                spec = self.equipment_specs[eq_type]
                capabilities = spec.get("capabilities", {})
                
                eq_params = {
                    "process_name": eq_type,
                    "capabilities": capabilities,
                    "operating_parameters": {
                        "power_consumption": f"{random.randint(1000, 10000)}W",
                        "operating_temperature": f"{random.randint(15, 35)}°C",
                        "humidity_range": f"{random.randint(30, 70)}%",
                        "noise_level": f"{random.randint(60, 85)}dB"
                    },
                    "safety_requirements": [
                        "Safety glasses required",
                        "Proper ventilation",
                        "Emergency stop accessible"
                    ],
                    "maintenance_schedule": f"Every {random.randint(1, 6)} months",
                    "calibration_required": random.choice([True, False])
                }
                
                parameters[eq_type] = eq_params
        
        return parameters
    
    def generate_tool_inventory(self, equipment_types: List[str]) -> List[Dict]:
        """Generate tool inventory with specifications"""
        tools = []
        
        # Define tool categories directly to avoid import issues
        tool_categories = {
            "3DP": ["3D printer", "Filament", "Build plate", "Nozzle", "Calipers", "Deburring tool", "Heat gun"],
            "CNC": ["CNC mill", "Cutting tools", "Workholding", "CMM", "Surface plate", "Dial indicator", "Micrometer"],
            "LASER": ["Laser cutter", "Air assist", "Focus lens", "Cutting bed", "Material guides", "Exhaust system"],
            "PCB": ["PCB mill", "Soldering station", "Multimeter", "Oscilloscope", "Pick and place", "Reflow oven"],
            "SHEET": ["Sheet metal brake", "Shear", "Punch press", "Welder", "Grinder", "Drill press"],
            "Assembly": ["Screwdriver set", "Wrench set", "Pliers", "Crimping tool", "Heat shrink", "Cable ties"]
        }
        
        for eq_type in equipment_types:
            if eq_type in tool_categories:
                tool_list = tool_categories[eq_type]
                # Select 2-4 tools per equipment type
                selected_tools = random.sample(tool_list, random.randint(2, min(4, len(tool_list))))
                
                for tool in selected_tools:
                    tool_spec = {
                        "tool_name": tool,
                        "equipment_type": eq_type,
                        "quantity": random.randint(1, 5),
                        "condition": random.choice(["Excellent", "Good", "Fair", "Needs Replacement"]),
                        "specifications": {
                            "size": f"{random.uniform(0.1, 25):.1f}mm" if "nozzle" in tool.lower() or "bit" in tool.lower() else None,
                            "material": random.choice(["Carbide", "HSS", "Ceramic", "Diamond"]) if "cutting" in tool.lower() else None,
                            "coating": random.choice(["TiN", "TiAlN", "DLC", "None"]) if "cutting" in tool.lower() else None
                        },
                        "last_maintenance": self.faker.date_between(start_date="-6M", end_date="today").isoformat(),
                        "next_maintenance": self.faker.date_between(start_date="today", end_date="+6M").isoformat(),
                        "cost": f"${random.uniform(10, 500):.2f}"
                    }
                    tools.append(tool_spec)
        
        return tools
    
    def _get_facility_type_from_template(self, template: Dict) -> str:
        """Determine facility type from template for certification purposes"""
        name = template["name"].lower()
        if "makerspace" in name or "community" in name:
            return "makerspace"
        elif "university" in name or "research" in name:
            return "university"
        elif "electronics" in name or "assembly" in name:
            return "electronics"
        elif "industrial" in name or "plant" in name:
            return "industrial"
        else:
            return "professional"

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
        
        # Enhanced capabilities and metrics
        if self.should_include_field():
            # Add detailed capabilities to equipment
            for equipment in facility.equipment:
                equipment_type = equipment.equipment_type.split('/')[-1].replace('_', ' ')
                detailed_capabilities = self.generate_detailed_capabilities(equipment_type)
                if detailed_capabilities:
                    equipment.additional_properties["detailed_capabilities"] = detailed_capabilities
        
        # Add certification details
        if self.should_include_field():
            facility_type = self._get_facility_type_from_template(template)
            cert_details = self.generate_certification_details(facility_type)
            facility.certifications = [cert["name"] for cert in cert_details]
            # Store detailed certification info in metadata
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["certification_details"] = cert_details
        
        # Add capacity metrics
        if self.should_include_field():
            capacity_metrics = self.generate_capacity_metrics(template["equipment_types"])
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["capacity_metrics"] = capacity_metrics
        
        # Add material inventory
        if self.should_include_field():
            material_inventory = self.generate_material_inventory(template["equipment_types"])
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["material_inventory"] = material_inventory
        
        # Add quality systems
        if self.should_include_field():
            facility_type = self._get_facility_type_from_template(template)
            quality_systems = self.generate_quality_systems(facility_type)
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["quality_systems"] = quality_systems
        
        # Add process parameters
        if self.should_include_field():
            process_parameters = self.generate_process_parameters(template["equipment_types"])
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["process_parameters"] = process_parameters
        
        # Add tool inventory
        if self.should_include_field():
            tool_inventory = self.generate_tool_inventory(template["equipment_types"])
            if not hasattr(facility, 'metadata'):
                facility.metadata = {}
            facility.metadata["tool_inventory"] = tool_inventory
        
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
    
    if isinstance(record, OKHManifest):
        # Use title and version for OKH files
        safe_title = "".join(c for c in record.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '-').lower()
        safe_version = record.version.replace('.', '-')
        filename = f"{safe_title}-{safe_version}-okh.json"
    else:
        # Use name for OKW files
        safe_name = "".join(c for c in record.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '-').lower()
        filename = f"{safe_name}-{index:03d}-okw.json"
    
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