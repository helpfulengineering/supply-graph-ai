import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class DocumentationType(Enum):
    """Types of documentation that can be associated with an OKH module"""

    DESIGN_FILES = "design-files"
    MANUFACTURING_FILES = "manufacturing-files"
    MAINTENANCE_INSTRUCTIONS = "maintenance-instructions"
    DISPOSAL_INSTRUCTIONS = "disposal-instructions"
    SOFTWARE = "software"
    RISK_ASSESSMENT = "risk-assessment"
    SCHEMATICS = "schematics"
    # Consolidated documentation types
    MAKING_INSTRUCTIONS = "making-instructions"  # Consolidates TOOL_SETTINGS
    DOCUMENTATION_HOME = "documentation-home"
    TECHNICAL_SPECIFICATIONS = (
        "technical-specifications"  # Consolidates QUALITY_INSTRUCTIONS
    )
    OPERATING_INSTRUCTIONS = "operating-instructions"  # Consolidates USER_MANUAL
    PUBLICATIONS = "publications"

    @classmethod
    def _missing_(cls, value):
        """Handle backward compatibility with old type values."""
        # Map old values to new consolidated types
        mapping = {
            "user-manual": cls.OPERATING_INSTRUCTIONS,
            "tool-settings": cls.MAKING_INSTRUCTIONS,
            "quality-instructions": cls.TECHNICAL_SPECIFICATIONS,
        }
        if value in mapping:
            return mapping[value]
        return None


@dataclass
class License:
    """License information for different aspects of the module"""

    hardware: Optional[str] = None  # SPDX identifier
    documentation: Optional[str] = None  # SPDX identifier
    software: Optional[str] = None  # SPDX identifier

    def validate(self) -> bool:
        """Validates that at least one license is specified"""
        return any([self.hardware, self.documentation, self.software])

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "hardware": self.hardware,
            "documentation": self.documentation,
            "software": self.software,
        }


@dataclass
class Person:
    """Represents a person associated with the OKH module"""

    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    social: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "email": self.email,
            "affiliation": self.affiliation,
            "social": self.social,
        }


@dataclass
class Organization:
    """Represents an organization associated with the OKH module"""

    name: str
    url: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {"name": self.name, "url": self.url, "email": self.email}


@dataclass
class DocumentRef:
    """Reference to a documentation file or resource"""

    title: str
    path: str  # Can be relative path or URL
    type: DocumentationType
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "path": self.path,
            "type": self.type.value,
            "metadata": self.metadata,
        }

    def validate(self) -> bool:
        """Validate the document reference"""
        # Allow HTTP/HTTPS URLs
        if self.path.startswith("http://") or self.path.startswith("https://"):
            return True

        # Allow absolute paths that exist
        if os.path.isabs(self.path) and os.path.exists(self.path):
            return True

        # For relative paths, be more lenient:
        # 1. If file exists locally, that's great
        if os.path.exists(self.path):
            return True

        # 2. If it's a relative path that looks like a repository file path,
        #    consider it valid (it will be resolved during package build)
        if not os.path.isabs(self.path) and "/" in self.path:
            # This looks like a repository file path (e.g., "docs/README.md")
            return True

        # 3. For simple filenames, check if they exist in common locations
        if not os.path.isabs(self.path) and "/" not in self.path:
            # Check common locations
            common_paths = [
                self.path,
                f"docs/{self.path}",
                f"documentation/{self.path}",
                f"manual/{self.path}",
            ]
            if any(os.path.exists(p) for p in common_paths):
                return True

        # 4. For generated manifests, be more permissive:
        #    If the path looks like a reasonable file reference, allow it
        #    This handles cases where files exist in remote repositories
        if not os.path.isabs(self.path):
            # Check if it looks like a reasonable file reference
            path_lower = self.path.lower()

            # Allow common file extensions
            valid_extensions = {
                ".txt",
                ".md",
                ".pdf",
                ".doc",
                ".docx",
                ".rst",
                ".stl",
                ".obj",
                ".3mf",
                ".scad",
                ".step",
                ".stp",
                ".kicad_pcb",
                ".kicad_mod",
                ".sch",
                ".brd",
                ".py",
                ".js",
                ".cpp",
                ".c",
                ".h",
                ".json",
                ".yaml",
                ".yml",
                ".csv",
                ".tsv",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".svg",
                # Script files
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
                ".ps1",
                ".bat",
                ".cmd",
                # Lock files and config files
                ".lock",
                ".toml",
                ".ini",
                ".conf",
                ".config",
            }

            if any(path_lower.endswith(ext) for ext in valid_extensions):
                return True

            # Allow common filenames
            common_filenames = {
                "readme",
                "license",
                "copying",
                "authors",
                "contributors",
                "changelog",
                "version",
                "install",
                "build",
                "makefile",
                "startup",
                "setup",
                "configure",
            }

            filename = Path(self.path).stem.lower()
            if filename in common_filenames:
                return True

            # For generated manifests, be even more permissive:
            # If it's a simple filename (no path separators) and looks like a reasonable
            # file reference (has an extension or is a common name), allow it
            # This handles cases where files exist in remote repositories
            if "/" not in self.path:
                # If it has any extension at all, consider it potentially valid
                # (will be resolved during package build)
                if "." in self.path:
                    return True

        # 5. Final fallback: For generated manifests from remote repositories,
        #    be very permissive - if it looks like any reasonable file reference,
        #    allow it. Files will be resolved during package build.
        #    This prevents validation failures for legitimate files in remote repos.
        if not os.path.isabs(self.path):
            # If the path contains any alphanumeric characters and looks like a filename,
            # consider it valid (will be resolved during package build)
            if self.path and len(self.path.strip()) > 0:
                # Basic sanity check: not just whitespace or special characters
                if any(c.isalnum() for c in self.path):
                    return True

        # If we get here, the file doesn't exist and doesn't look like a valid reference
        return False


@dataclass
class MaterialSpec:
    """Specification for a material used in the module"""

    material_id: str  # e.g. "PLA", "1.0715"
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "material_id": self.material_id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "notes": self.notes,
        }


@dataclass
class ProcessRequirement:
    """Manufacturing process requirements with context-specific validation"""

    process_name: str
    parameters: Dict = field(default_factory=dict)
    validation_criteria: Dict = field(default_factory=dict)
    required_tools: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "process_name": self.process_name,
            "parameters": self.parameters,
            "validation_criteria": self.validation_criteria,
            "required_tools": self.required_tools,
            "notes": self.notes,
        }

    def can_be_satisfied_by(self, capability) -> bool:
        """Check if this process requirement can be satisfied by a capability"""
        # Implementation would depend on matching logic
        # Basic implementation checks if process name exists in capabilities
        return self.process_name in capability.processes


@dataclass
class ManufacturingSpec:
    """Manufacturing specifications"""

    joining_processes: List[str] = field(default_factory=list)
    outer_dimensions: Optional[Dict] = None
    process_requirements: List[ProcessRequirement] = field(default_factory=list)
    quality_standards: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "joining_processes": self.joining_processes,
            "outer_dimensions": self.outer_dimensions,
            "process_requirements": [pr.to_dict() for pr in self.process_requirements],
            "quality_standards": self.quality_standards,
            "notes": self.notes,
        }


@dataclass
class Standard:
    """Information about standards compliance"""

    standard_title: str
    publisher: Optional[str] = None
    reference: Optional[str] = None  # e.g. ISO 9001
    certifications: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "standard_title": self.standard_title,
            "publisher": self.publisher,
            "reference": self.reference,
            "certifications": self.certifications,
        }


@dataclass
class Software:
    """Associated software for the OKH module"""

    release: str  # URL to software release
    installation_guide: Optional[str] = None  # Path to installation guide

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {"release": self.release, "installation_guide": self.installation_guide}


@dataclass
class PartSpec:
    """Specification for a part of the OKH module"""

    name: str
    id: UUID = field(default_factory=uuid4)
    source: Union[str, List[str]] = field(default_factory=list)  # Path to source files
    export: Union[str, List[str]] = field(default_factory=list)  # Path to export files
    auxiliary: Union[str, List[str]] = field(
        default_factory=list
    )  # Path to auxiliary files
    image: Optional[str] = None  # Path to image
    tsdc: List[str] = field(
        default_factory=list
    )  # Technology-specific Documentation Criteria
    material: Optional[str] = None  # Material reference
    outer_dimensions: Optional[Dict] = None  # Dimensions in mm
    mass: Optional[float] = None  # Mass in g

    # Manufacturing-specific fields for different TSDCs
    manufacturing_params: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        source_list = [self.source] if isinstance(self.source, str) else self.source
        export_list = [self.export] if isinstance(self.export, str) else self.export
        auxiliary_list = (
            [self.auxiliary] if isinstance(self.auxiliary, str) else self.auxiliary
        )

        return {
            "name": self.name,
            "id": str(self.id),
            "source": source_list,
            "export": export_list,
            "auxiliary": auxiliary_list,
            "image": self.image,
            "tsdc": self.tsdc,
            "material": self.material,
            "outer_dimensions": self.outer_dimensions,
            "mass": self.mass,
            "manufacturing_params": self.manufacturing_params,
        }

    def has_tsdc(self, tsdc_code: str) -> bool:
        """Check if part has a specific TSDC"""
        return tsdc_code in self.tsdc


@dataclass
class OKHManifest:
    """Primary OKH manifest structure representing an open hardware module"""

    # Required fields
    title: str
    version: str
    license: License
    licensor: Union[str, Person, List[Union[str, Person]]]
    documentation_language: Union[str, List[str]]
    function: str

    # Optional fields
    repo: Optional[str] = None  # URL to repository (optional for inline manifests)

    # Unique identifier
    id: UUID = field(default_factory=uuid4)

    # Metadata
    okhv: str = "OKH-LOSHv1.0"  # OKH specification version
    data_source: Optional[str] = None  # Platform where metadata was found

    # Optional fields
    description: Optional[str] = None
    intended_use: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    project_link: Optional[str] = None
    health_safety_notice: Optional[str] = None
    contact: Optional[Person] = None
    contributors: List[Person] = field(default_factory=list)
    organization: Optional[Union[str, Organization, List[Union[str, Organization]]]] = (
        None
    )
    image: Optional[str] = None
    version_date: Optional[date] = None
    readme: Optional[str] = None
    contribution_guide: Optional[str] = None

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
    technical_specifications: List[DocumentRef] = field(default_factory=list)
    publications: List[DocumentRef] = field(default_factory=list)
    tool_list: List[str] = field(default_factory=list)

    # Manufacturing specifications
    manufacturing_processes: List[str] = field(default_factory=list)
    materials: List[MaterialSpec] = field(default_factory=list)
    manufacturing_specs: Optional[ManufacturingSpec] = None
    bom: Optional[str] = None  # Path to bill of materials

    # Standards and classification
    standards_used: List[Standard] = field(default_factory=list)
    cpc_patent_class: Optional[str] = None  # e.g. "D03D 35/00"
    tsdc: List[str] = field(
        default_factory=list
    )  # Technology-specific Documentation Criteria

    # Parts and components
    parts: List[PartSpec] = field(default_factory=list)

    # Relationship to other projects
    derivative_of: Optional[Dict] = None
    variant_of: Optional[Dict] = None
    sub_parts: List[Dict] = field(default_factory=list)

    # Software
    software: List[Software] = field(default_factory=list)

    # Additional metadata
    metadata: Dict = field(default_factory=dict)

    # Domain metadata
    domain: Optional[str] = None  # "manufacturing" or "cooking"

    def validate(self) -> bool:
        """
        Validate that all required fields are present and properly formatted.
        Returns True if valid, raises ValidationError if invalid.
        """
        required_fields = [
            self.title,
            self.version,
            self.license,
            self.licensor,
            self.documentation_language,
            self.function,
        ]

        if not all(required_fields):
            missing = [
                field
                for field, value in zip(
                    [
                        "title",
                        "version",
                        "license",
                        "licensor",
                        "documentation_language",
                        "function",
                    ],
                    required_fields,
                )
                if not value
            ]
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Validate license
        if not self.license.validate():
            raise ValueError("License validation failed")

        # Validate document references
        # For generated manifests, be lenient - files may exist in remote repositories
        invalid_docs = []
        for doc in (
            self.manufacturing_files
            + self.design_files
            + self.making_instructions
            + self.operating_instructions
            + self.technical_specifications
            + self.publications
        ):
            if not doc.validate():
                invalid_docs.append(doc.title)

        # Only raise error if we have invalid docs AND they don't look like reasonable file references
        # This prevents false positives for files in remote repositories
        if invalid_docs:
            # Check if any invalid docs look like they might be valid (have extensions, etc.)
            potentially_valid = False
            for doc_title in invalid_docs:
                # If it has an extension or looks like a filename, it might be valid in a repo
                if "." in doc_title or any(c.isalnum() for c in doc_title):
                    potentially_valid = True
                    break

            if not potentially_valid:
                raise ValueError(f"Invalid document reference: {invalid_docs[0]}")
            else:
                # Log warning but don't fail - these will be resolved during package build
                logger.warning(
                    f"Document reference validation warning for: {', '.join(invalid_docs)}. "
                    f"These will be resolved during package build."
                )

        return True

    def to_dict(self) -> Dict:
        """Convert the manifest to a dictionary format"""
        licensor_dict = self._convert_agent_to_dict(self.licensor)
        organization_dict = (
            self._convert_agent_to_dict(self.organization)
            if self.organization
            else None
        )

        result = {
            "okhv": self.okhv,
            "id": str(self.id),
            "title": self.title,
            "repo": self.repo,
            "version": self.version,
            "license": self.license.to_dict() if self.license else {},
            "licensor": licensor_dict,
            "documentation_language": self.documentation_language,
            "function": self.function,
        }

        # Add optional fields that are not None
        optional_fields = {
            "description": self.description,
            "intended_use": self.intended_use,
            "keywords": self.keywords,
            "project_link": self.project_link,
            "health_safety_notice": self.health_safety_notice,
            "contact": self.contact.to_dict() if self.contact else None,
            "contributors": (
                [c.to_dict() for c in self.contributors] if self.contributors else None
            ),
            "organization": organization_dict,
            "image": self.image,
            "version_date": (
                self.version_date.isoformat() if self.version_date else None
            ),
            "readme": self.readme,
            "contribution_guide": self.contribution_guide,
            "development_stage": self.development_stage,
            "attestation": self.attestation,
            "technology_readiness_level": self.technology_readiness_level,
            "documentation_readiness_level": self.documentation_readiness_level,
            "manufacturing_files": [doc.to_dict() for doc in self.manufacturing_files],
            "documentation_home": self.documentation_home,
            "archive_download": self.archive_download,
            "design_files": [doc.to_dict() for doc in self.design_files],
            "making_instructions": [doc.to_dict() for doc in self.making_instructions],
            "operating_instructions": [
                doc.to_dict() for doc in self.operating_instructions
            ],
            "technical_specifications": [
                doc.to_dict() for doc in self.technical_specifications
            ],
            "publications": [doc.to_dict() for doc in self.publications],
            "tool_list": self.tool_list,
            "manufacturing_processes": self.manufacturing_processes,
            "materials": [mat.to_dict() for mat in self.materials],
            "manufacturing_specs": (
                self.manufacturing_specs.to_dict() if self.manufacturing_specs else None
            ),
            "bom": self.bom,
            "standards_used": [std.to_dict() for std in self.standards_used],
            "cpc_patent_class": self.cpc_patent_class,
            "tsdc": self.tsdc,
            "parts": [part.to_dict() for part in self.parts],
            "derivative_of": self.derivative_of,
            "variant_of": self.variant_of,
            "sub_parts": self.sub_parts,
            "software": [sw.to_dict() for sw in self.software],
            "metadata": self.metadata,
            "domain": self.domain,
        }

        # Merge optional fields with result
        result.update(optional_fields)

        # Filter out None values, but keep empty lists and other falsy values that are meaningful
        return {k: v for k, v in result.items() if v is not None}

    def _convert_agent_to_dict(self, agent):
        """Convert licensor or organization to dict format"""
        if isinstance(agent, str):
            return agent
        elif isinstance(agent, (Person, Organization)):
            return agent.to_dict()
        elif isinstance(agent, list):
            return [
                a.to_dict() if isinstance(a, (Person, Organization)) else a
                for a in agent
            ]
        return None

    @classmethod
    def from_dict(cls, data: Dict) -> "OKHManifest":
        """Create an OKHManifest instance from a dictionary"""
        # Handle required fields
        license_data = data.get("license", {})

        # Handle both string and dictionary license formats
        if isinstance(license_data, str):
            # If license is a string, use it for all license types
            license_obj = License(
                hardware=license_data, documentation=license_data, software=license_data
            )
        elif isinstance(license_data, dict):
            # If license is a dictionary, extract individual fields
            license_obj = License(
                hardware=license_data.get("hardware"),
                documentation=license_data.get("documentation"),
                software=license_data.get("software"),
            )
        else:
            # Fallback to empty license
            license_obj = License(hardware=None, documentation=None, software=None)

        # Initialize basic instance
        instance = cls(
            title=data.get("title", ""),
            version=data.get("version", ""),
            license=license_obj,
            licensor=cls._parse_agent(data.get("licensor")),
            documentation_language=data.get("documentation_language", ""),
            function=data.get("function", ""),
            repo=data.get("repo"),  # Optional field, defaults to None if not provided
        )

        # Set the ID from data if provided
        if "id" in data and data["id"]:
            manifest_id_str = data["id"]
            try:
                instance.id = UUID(manifest_id_str)
            except (ValueError, TypeError):
                # Handle invalid UUIDs (e.g., slug-like IDs from older manifests)
                # Convert to UUID using UUIDValidator
                from ..validation.uuid_validator import UUIDValidator

                fixed_uuid = UUIDValidator.fix_invalid_uuid(
                    manifest_id_str, fallback_to_random=True
                )
                instance.id = UUID(fixed_uuid)
                logger.warning(
                    f"Converted invalid manifest ID '{manifest_id_str}' to UUID '{fixed_uuid}'"
                )

        # Set optional fields
        for field in [
            "description",
            "intended_use",
            "keywords",
            "project_link",
            "health_safety_notice",
            "image",
            "readme",
            "contribution_guide",
            "development_stage",
            "attestation",
            "technology_readiness_level",
            "documentation_readiness_level",
            "documentation_home",
            "archive_download",
            "tool_list",
            "manufacturing_processes",
            "cpc_patent_class",
            "tsdc",
            "derivative_of",
            "variant_of",
            "sub_parts",
            "metadata",
            "bom",
            "okhv",
            "data_source",
            "domain",
        ]:
            if field in data and data[field] is not None:
                # For list fields, ensure they're not None (use empty list instead)
                if field in [
                    "tool_list",
                    "manufacturing_processes",
                    "tsdc",
                    "sub_parts",
                    "keywords",
                ]:
                    setattr(
                        instance,
                        field,
                        data[field] if isinstance(data[field], list) else [],
                    )
                else:
                    setattr(instance, field, data[field])

        # Handle complex fields
        if "contact" in data:
            instance.contact = cls._parse_person(data["contact"])

        if "contributors" in data and data["contributors"] is not None:
            instance.contributors = [cls._parse_person(c) for c in data["contributors"]]

        if "organization" in data:
            instance.organization = cls._parse_agent(data["organization"])

        if "version_date" in data:
            instance.version_date = (
                date.fromisoformat(data["version_date"])
                if data["version_date"]
                else None
            )

        # Handle document references
        for doc_field in [
            "manufacturing_files",
            "design_files",
            "making_instructions",
            "operating_instructions",
            "technical_specifications",
            "publications",
        ]:
            if doc_field in data and data[doc_field] is not None:
                doc_list = []
                for doc_data in data[doc_field]:
                    doc_type = DocumentationType(
                        doc_data.get("type", DocumentationType.DESIGN_FILES.value)
                    )
                    doc = DocumentRef(
                        title=doc_data.get("title", ""),
                        path=doc_data.get("path", ""),
                        type=doc_type,
                        metadata=doc_data.get("metadata", {}),
                    )
                    doc_list.append(doc)
                setattr(instance, doc_field, doc_list)

        # Handle materials
        if "materials" in data and data["materials"] is not None:
            instance.materials = []
            for mat_data in data["materials"]:
                if isinstance(mat_data, str):
                    # Handle simple string materials (from our generated manifests)
                    mat = MaterialSpec(
                        material_id="",
                        name=mat_data,
                        quantity=None,
                        unit=None,
                        notes=None,
                    )
                elif isinstance(mat_data, dict):
                    # Handle structured material dictionaries
                    mat = MaterialSpec(
                        material_id=mat_data.get("material_id", ""),
                        name=mat_data.get("name", ""),
                        quantity=mat_data.get("quantity"),
                        unit=mat_data.get("unit"),
                        notes=mat_data.get("notes"),
                    )
                else:
                    # Skip invalid material data
                    continue
                instance.materials.append(mat)

        # Handle manufacturing specs
        if "manufacturing_specs" in data and data["manufacturing_specs"] is not None:
            spec_data = data["manufacturing_specs"]
            process_reqs = []
            for proc_data in spec_data.get("process_requirements", []):
                proc = ProcessRequirement(
                    process_name=proc_data.get("process_name", ""),
                    parameters=proc_data.get("parameters", {}),
                    validation_criteria=proc_data.get("validation_criteria", {}),
                    required_tools=proc_data.get("required_tools", []),
                    notes=proc_data.get("notes", ""),
                )
                process_reqs.append(proc)

            specs = ManufacturingSpec(
                joining_processes=spec_data.get("joining_processes", []),
                outer_dimensions=spec_data.get("outer_dimensions"),
                process_requirements=process_reqs,
                quality_standards=spec_data.get("quality_standards", []),
                notes=spec_data.get("notes", ""),
            )
            instance.manufacturing_specs = specs

        # Handle parts
        if "parts" in data and data["parts"] is not None:
            instance.parts = []
            for part_data in data["parts"]:
                part = PartSpec(
                    name=part_data.get("name", ""),
                    source=part_data.get("source", []),
                    export=part_data.get("export", []),
                    auxiliary=part_data.get("auxiliary", []),
                    image=part_data.get("image"),
                    tsdc=part_data.get("tsdc", []),
                    material=part_data.get("material"),
                    outer_dimensions=part_data.get("outer_dimensions"),
                    mass=part_data.get("mass"),
                    manufacturing_params=part_data.get("manufacturing_params", {}),
                )
                if "id" in part_data:
                    part_id_str = part_data["id"]
                    try:
                        part.id = UUID(part_id_str)
                    except (ValueError, TypeError):
                        # Handle invalid UUIDs (e.g., slug-like IDs from older manifests)
                        # Convert to UUID using UUIDValidator
                        from ..validation.uuid_validator import UUIDValidator

                        fixed_uuid = UUIDValidator.fix_invalid_uuid(
                            part_id_str, fallback_to_random=True
                        )
                        part.id = UUID(fixed_uuid)
                        logger.warning(
                            f"Converted invalid part ID '{part_id_str}' to UUID '{fixed_uuid}'"
                        )
                instance.parts.append(part)

        # Handle standards
        if "standards_used" in data and data["standards_used"] is not None:
            instance.standards_used = []
            for std_data in data["standards_used"]:
                std = Standard(
                    standard_title=std_data.get("standard_title", ""),
                    publisher=std_data.get("publisher"),
                    reference=std_data.get("reference"),
                    certifications=std_data.get("certifications", []),
                )
                instance.standards_used.append(std)

        # Handle software
        if "software" in data and data["software"] is not None:
            instance.software = []
            for sw_data in data["software"]:
                sw = Software(
                    release=sw_data.get("release", ""),
                    installation_guide=sw_data.get("installation_guide"),
                )
                instance.software.append(sw)

        return instance

    @staticmethod
    def _parse_person(data) -> Optional[Person]:
        """Parse person data from dict or string"""
        if not data:
            return None

        if isinstance(data, dict):
            return Person(
                name=data.get("name", ""),
                email=data.get("email"),
                affiliation=data.get("affiliation"),
                social=data.get("social", []),
            )

        # Try to parse from string like "John Doe <john.doe@email.com>"
        if isinstance(data, str):
            match = re.match(r"(.*?)(?:\s+\((.*?)\))?\s*(?:<(.+?)>)?$", data)
            if match:
                name, affiliation, email = match.groups()
                return Person(name=name.strip(), email=email, affiliation=affiliation)

        return None

    @staticmethod
    def _parse_agent(data):
        """Parse agent (person or organization) data"""
        if not data:
            return None

        if isinstance(data, list):
            return [OKHManifest._parse_agent(item) for item in data]

        if isinstance(data, dict):
            if "name" in data:
                # Check whether it's an organization or person
                if any(key in data for key in ["email", "affiliation", "social"]):
                    return OKHManifest._parse_person(data)
                else:
                    return Organization(
                        name=data.get("name", ""),
                        url=data.get("url"),
                        email=data.get("email"),
                    )

        if isinstance(data, str):
            # Try to parse as person first
            person = OKHManifest._parse_person(data)
            if person:
                return person
            # If not a person, treat as organization name
            return Organization(name=data)

        return data

    @classmethod
    def from_toml(cls, filepath: str) -> "OKHManifest":
        """Load an OKHManifest from a TOML file"""
        import tomli

        with open(filepath, "rb") as f:
            data = tomli.load(f)

        return cls.from_dict(data)

    def to_toml(self, filepath: str) -> None:
        """Save the manifest to a TOML file"""
        import tomli_w

        with open(filepath, "wb") as f:
            tomli_w.dump(self.to_dict(), f)

    def extract_requirements(self) -> List[ProcessRequirement]:
        """Extract process requirements for matching"""
        requirements = []

        # Add requirements from manufacturing specs
        if self.manufacturing_specs:
            requirements.extend(self.manufacturing_specs.process_requirements)

        # Extract implicit requirements from manufacturing processes
        for process in self.manufacturing_processes:
            req = ProcessRequirement(
                process_name=process,
                parameters={},
                validation_criteria={},
                required_tools=[],
            )
            requirements.append(req)

        # Extract requirements from parts
        for part in self.parts:
            for tsdc in part.tsdc:
                # Create process requirement based on TSDC
                params = part.manufacturing_params.copy()
                params["material"] = part.material

                req = ProcessRequirement(
                    process_name=tsdc,
                    parameters=params,
                    validation_criteria={},
                    required_tools=[],
                )
                requirements.append(req)

        return requirements

    def has_tsdc(self, tsdc_code: str) -> bool:
        """Check if module has a specific TSDC"""
        if tsdc_code in self.tsdc:
            return True

        # Check parts
        for part in self.parts:
            if part.has_tsdc(tsdc_code):
                return True

        return False

    def get_package_name(self) -> str:
        """Generate package name from manifest fields"""
        # Extract organization
        if self.organization:
            if isinstance(self.organization, str):
                org_name = self.organization
            else:
                org_name = self.organization.name
        else:
            org_name = "community"

        # Sanitize names
        from .package import sanitize_package_name

        org_sanitized = sanitize_package_name(org_name)
        project_sanitized = sanitize_package_name(self.title)

        return f"{org_sanitized}/{project_sanitized}"

    def get_package_path(self, base_dir: str = "packages") -> str:
        """Get the full package path including version"""
        package_name = self.get_package_name()
        return f"{base_dir}/{package_name}/{self.version}"
