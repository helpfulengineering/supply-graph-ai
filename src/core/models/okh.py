from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from datetime import date
from enum import Enum
from uuid import UUID


class DocumentationType(Enum):
    """Types of documentation that can be associated with an OKH module"""
    DESIGN_FILES = "design-files"
    MANUFACTURING_FILES = "manufacturing-files" 
    USER_MANUAL = "user-manual"
    MAINTENANCE_INSTRUCTIONS = "maintenance-instructions"
    DISPOSAL_INSTRUCTIONS = "disposal-instructions"
    SOFTWARE = "software"
    QUALITY_INSTRUCTIONS = "quality-instructions"
    RISK_ASSESSMENT = "risk-assessment"
    TOOL_SETTINGS = "tool-settings"
    SCHEMATICS = "schematics"


@dataclass
class DocumentRef:
    """Reference to a documentation file or resource"""
    title: str
    path: str  # Can be relative path or URL
    type: DocumentationType
    metadata: Dict = field(default_factory=dict)


@dataclass
class Person:
    """Represents a person associated with the OKH module"""
    name: Optional[str] = None
    email: Optional[str] = None
    affiliation: Optional[str] = None
    social: List[Dict[str, str]] = field(default_factory=list)


@dataclass 
class License:
    """License information for different aspects of the module"""
    hardware: Optional[str] = None  # SPDX identifier
    documentation: Optional[str] = None  # SPDX identifier
    software: Optional[str] = None  # SPDX identifier


@dataclass
class Standard:
    """Information about standards compliance"""
    standard_title: str
    publisher: Optional[str] = None
    reference: Optional[str] = None  # e.g. ISO 9001
    certifications: List[Dict] = field(default_factory=list)


@dataclass
class MaterialSpec:
    """Specification for a material used in the module"""
    material_id: str  # e.g. "PLA", "1.0715"
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ProcessRequirement:
    """Manufacturing process requirements"""
    process_name: str
    parameters: Dict = field(default_factory=dict)
    validation_criteria: Dict = field(default_factory=dict)
    required_tools: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ManufacturingSpec:
    """Manufacturing specifications"""
    joining_processes: List[str] = field(default_factory=list)
    outer_dimensions: Optional[Dict] = None
    process_requirements: List[ProcessRequirement] = field(default_factory=list)
    quality_standards: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class OKHManifest:
    """Primary OKH manifest structure"""
    # Required fields
    title: str
    repo: str  # URL to repository
    version: str
    license: License
    licensor: str
    documentation_language: str
    function: str
    
    # Optional but recommended fields
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Person] = None
    contributors: List[Person] = field(default_factory=list)
    image: Optional[str] = None
    version_date: Optional[date] = None
    
    # Development and documentation status
    development_stage: Optional[str] = None  # e.g. "prototype", "production"
    attestation: Optional[str] = None  # URL to certification/attestation
    technology_readiness_level: Optional[str] = None
    documentation_readiness_level: Optional[str] = None
    
    # Technical documentation references
    manufacturing_files: List[DocumentRef] = field(default_factory=list)
    documentation_home: Optional[str] = None
    archive_download: Optional[str] = None
    design_files: List[DocumentRef] = field(default_factory=list)
    making_instructions: List[DocumentRef] = field(default_factory=list)
    operating_instructions: List[DocumentRef] = field(default_factory=list)
    tool_list: List[str] = field(default_factory=list)
    
    # Manufacturing specifications
    manufacturing_processes: List[str] = field(default_factory=list)
    materials: List[MaterialSpec] = field(default_factory=list)
    manufacturing_specs: Optional[ManufacturingSpec] = None
    
    # Standards and classification
    standards_used: List[Standard] = field(default_factory=list)
    cpc_patent_class: Optional[str] = None  # e.g. "D03D 35/00"
    tsdc: List[str] = field(default_factory=list)  # Technology-specific Documentation Criteria
    
    # Relationship to other projects
    derivative_of: Optional[Dict] = None
    variant_of: Optional[Dict] = None
    sub_parts: List[Dict] = field(default_factory=list)
    
    # Metadata
    metadata: Dict = field(default_factory=dict)
    
    def validate(self) -> bool:
        """
        Validate that all required fields are present and properly formatted.
        Returns True if valid, raises ValidationError if invalid.
        """
        required_fields = [
            self.title,
            self.repo,
            self.version,
            self.license,
            self.licensor,
            self.documentation_language,
            self.function
        ]
        
        if not all(required_fields):
            missing = [
                field for field, value in zip(
                    ["title", "repo", "version", "license", "licensor", 
                     "documentation_language", "function"],
                    required_fields
                ) if not value
            ]
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
        # Additional validation could be added here
        return True
    
    def to_dict(self) -> Dict:
        """Convert the manifest to a dictionary format"""
        # Implementation would go here
        pass
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OKHManifest':
        """Create an OKHManifest instance from a dictionary"""
        # Implementation would go here
        pass
    
    @classmethod
    def from_toml(cls, filepath: str) -> 'OKHManifest':
        """Load an OKHManifest from a TOML file"""
        # Implementation would go here
        pass
    
    def to_toml(self, filepath: str) -> None:
        """Save the manifest to a TOML file"""
        # Implementation would go here
        pass



# Example usage:
# if __name__ == "__main__":
#     # Create a basic manifest
#     license = License(
#         hardware="CERN-OHL-S-2.0",
#         documentation="CC-BY-4.0",
#         software="GPL-3.0-or-later"
#     )
    
#     manifest = OKHManifest(
#         title="Example Hardware Project",
#         repo="https://github.com/example/project",
#         version="1.0.0",
#         license=license,
#         licensor="John Doe",
#         documentation_language="en",
#         function="This project demonstrates the OKH manifest structure"
#     )
    
#     # Validate the manifest
#     try:
#         manifest.validate()
#         print("Manifest is valid!")
#     except ValueError as e:
#         print(f"Manifest validation failed: {e}")
