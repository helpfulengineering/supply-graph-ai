"""
Service for generating OKH-compliant project scaffolds.

This module provides an opinionated scaffolding system for new open hardware
projects that conform to the Open Know How (OKH) data model. It is tightly
coupled to the OKHManifest dataclass so that generated output maps directly
to fields consumed by the rest of the OME system.

Multi-pass implementation strategy:
1) Define public API, core types, and method stubs
2) Implement JSON blueprint generation (no filesystem/zip writes yet)
3) Add filesystem and ZIP writers
4) Integrate MkDocs-aware docs structure and stub templates (by level)
5) Finalize error handling and typing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pathlib import Path

# NOTE: Keep imports local where feasible to avoid circular deps during import
# from src.core.models.okh import OKHManifest  # Imported lazily in methods


OutputFormat = Literal["json", "zip", "filesystem"]
TemplateLevel = Literal["minimal", "standard", "detailed"]


@dataclass
class ScaffoldOptions:
    """Options controlling scaffold generation.

    Attributes:
        project_name: Human-friendly project name; used for directory name.
        version: Initial project version string (semantic recommended).
        organization: Optional organization name for future packaging alignment.
        template_level: Amount of guidance placed in stub docs.
        output_format: One of json, zip, filesystem.
        output_path: Required for filesystem writes; ignored for others.
        include_examples: Whether to include sample files/content.
        okh_version: OKH schema version tag written into manifest stub.
    """
    project_name: str
    version: str = "0.1.0"
    organization: Optional[str] = None
    template_level: TemplateLevel = "standard"
    output_format: OutputFormat = "json"
    output_path: Optional[str] = None
    include_examples: bool = True
    okh_version: str = "OKH-LOSHv1.0"


@dataclass
class ScaffoldResult:
    """Result of scaffold generation.

    Attributes:
        project_name: Echo of input for convenience.
        structure: Directory/file tree as a nested dictionary blueprint.
        manifest_template: Dict ready to be consumed by OKHManifest.from_dict.
        filesystem_path: If output_format == filesystem, absolute path used.
        download_url: If output_format == zip, storage URL (future integration).
        warnings: Non-fatal issues encountered during generation.
    """
    project_name: str
    structure: Dict[str, Any]
    manifest_template: Dict[str, Any]
    filesystem_path: Optional[str] = None
    download_url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ScaffoldService:
    """Service responsible for generating OKH project scaffolds.

    Public entrypoint:
        - generate_scaffold(options) -> ScaffoldResult

    Internal responsibilities:
        - Build normalized directory blueprint including MkDocs layout
        - Produce documentation stubs at requested template level
        - Create an OKH-aligned manifest stub using OKHManifest fields
        - Materialize output in JSON, filesystem, or ZIP form
    """

    # -------- Public API --------
    async def generate_scaffold(self, options: ScaffoldOptions) -> ScaffoldResult:
        """Generate a new OKH project scaffold per provided options.

        High-level flow (implemented in subsequent passes):
            1) Validate options (names, paths, enums)
            2) Build directory blueprint (MkDocs-aware structure)
            3) Generate manifest template (from OKHManifest dataclass)
            4) Attach documentation stubs based on template_level
            5) Materialize output according to output_format
            6) Return ScaffoldResult with relevant metadata
        """
        # 1) Validate options
        self._validate_options(options)

        # 2) Build blueprint
        project_root = self._normalize_project_root_name(options.project_name)
        structure = self._create_directory_blueprint(project_root, options)

        # 3) Manifest template (initial: minimal viable structure; fill later)
        manifest_template = self._create_manifest_template(options)

        # 4) Inject stub content per template level (initial placeholders)
        self._inject_stub_documents(structure, options)

        # 5) Materialize per output format
        filesystem_path, download_url = None, None
        if options.output_format == "filesystem":
            filesystem_path = self._write_filesystem(
                structure=structure,
                options=options,
                manifest_template=manifest_template,
            )
        elif options.output_format == "zip":
            download_url = await self._create_and_store_zip(
                structure=structure,
                options=options,
                manifest_template=manifest_template,
            )
        else:
            # json: Nothing to materialize; client receives blueprint
            pass

        return ScaffoldResult(
            project_name=options.project_name,
            structure=structure,
            manifest_template=manifest_template,
            filesystem_path=filesystem_path,
            download_url=download_url,
        )

    # -------- Validation --------
    def _validate_options(self, options: ScaffoldOptions) -> None:
        """Validate input options and raise ValueError for invalid inputs."""
        if options.template_level not in ("minimal", "standard", "detailed"):
            raise ValueError("template_level must be one of: minimal, standard, detailed")

        if options.output_format not in ("json", "zip", "filesystem"):
            raise ValueError("output_format must be one of: json, zip, filesystem")

        if options.output_format == "filesystem" and not options.output_path:
            raise ValueError("output_path is required when output_format is 'filesystem'")

        if not options.project_name or options.project_name.strip() == "":
            raise ValueError("project_name is required")

    # -------- Blueprint Creation --------
    def _normalize_project_root_name(self, project_name: str) -> str:
        """Create a filesystem-friendly project root directory name."""
        safe = project_name.strip().lower()
        safe = "-".join(part for part in safe.replace("_", "-").split())
        return safe

    def _create_directory_blueprint(self, project_root: str, options: ScaffoldOptions) -> Dict[str, Any]:
        """Return a nested dict representing the project directory structure.

        The blueprint format uses dictionaries for directories and string values
        for file contents. For files whose contents are generated later, use
        placeholders None or empty strings which will be populated by
        _inject_stub_documents.
        """
        # MkDocs-aware structure with dedicated bom/ directory
        # See plan for full tree; placeholders below will be filled later.
        return {
            project_root: {
                "okh-manifest.json": "{}",  # will be replaced with manifest_template when materializing
                "README.md": "",            # root entrypoint
                "LICENSE": "",              # license stub
                "CONTRIBUTING.md": "",      # contributing guide
                "mkdocs.yml": "",           # mkdocs config
                "design-files": {
                    "index.md": "",
                },
                "manufacturing-files": {
                    "index.md": "",
                },
                "bom": {
                    "index.md": "",
                    "bom.csv": "",
                    "bom.md": "",
                },
                "making-instructions": {
                    "index.md": "",
                    "assembly-guide.md": "",
                },
                "operating-instructions": {
                    "index.md": "",
                },
                "quality-instructions": {
                    "index.md": "",
                },
                "risk-assessment": {
                    "index.md": "",
                },
                "software": {
                    "index.md": "",
                },
                "tool-settings": {
                    "index.md": "",
                },
                "schematics": {
                    "index.md": "",
                },
                "parts": {
                    "index.md": "",
                },
                "docs": {
                    "index.md": "",
                    "getting-started.md": "",
                    "development.md": "",
                    "manufacturing.md": "",
                    "assembly.md": "",
                    "maintenance.md": "",
                },
            }
        }

    # -------- Manifest Template --------
    def _create_manifest_template(self, options: ScaffoldOptions) -> Dict[str, Any]:
        """Create a OKH manifest template by introspecting OKHManifest dataclass.

        Uses dataclass introspection to generate templates with proper field types,
        required/optional indicators, and helpful placeholders based on template_level.
        """
        from src.core.models.okh import OKHManifest
        import dataclasses

        # Get field information from OKHManifest dataclass
        fields = dataclasses.fields(OKHManifest)
        field_info = {f.name: f for f in fields}

        # Build template based on template level
        template = {}
        
        # Required fields (always present)
        required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
        for field_name in required_fields:
            if field_name in field_info:
                template[field_name] = self._generate_field_template(field_name, field_info[field_name], options, required=True)

        # Optional fields (based on template level)
        optional_fields = [
            "description", "intended_use", "keywords", "project_link", "health_safety_notice",
            "contact", "contributors", "organization", "image", "version_date", "readme",
            "contribution_guide", "development_stage", "attestation", "technology_readiness_level",
            "documentation_readiness_level", "manufacturing_files", "documentation_home",
            "archive_download", "design_files", "making_instructions", "operating_instructions",
            "tool_list", "manufacturing_processes", "materials", "manufacturing_specs",
            "bom", "standards_used", "cpc_patent_class", "tsdc", "parts", "derivative_of",
            "variant_of", "sub_parts", "software", "metadata"
        ]

        # Include optional fields based on template level
        if options.template_level in ("standard", "detailed"):
            for field_name in optional_fields:
                if field_name in field_info:
                    template[field_name] = self._generate_field_template(field_name, field_info[field_name], options, required=False)

        # Set OKH version
        template["okhv"] = options.okh_version

        return template

    def _generate_field_template(self, field_name: str, field_info, options: ScaffoldOptions, required: bool) -> Any:
        """Generate template value for a specific field based on its type and template level."""
        field_type = field_info.type
        
        # Handle special cases first
        if field_name == "title":
            return options.project_name
        elif field_name == "version":
            return options.version
        elif field_name == "documentation_language":
            return "en"
        elif field_name == "license":
            return {
                "hardware": self._get_placeholder("SPDX license ID", required, options),
                "documentation": self._get_placeholder("SPDX license ID", required, options),
                "software": self._get_placeholder("SPDX license ID", False, options)
            }
        elif field_name == "licensor":
            return self._get_placeholder("Name or Person object", required, options)
        elif field_name == "function":
            return self._get_placeholder("Brief functional description", required, options)

        # Handle collection types
        if hasattr(field_type, "__origin__"):
            origin = field_type.__origin__
            if origin is list:
                return []
            elif origin is dict:
                return {}

        # Handle Union types (Optional fields)
        if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
            # For Optional fields, use the non-None type
            args = field_type.__args__
            non_none_types = [t for t in args if t is not type(None)]
            if non_none_types:
                return self._get_placeholder(f"Value of type {non_none_types[0].__name__}", required, options)

        # Handle basic types
        if field_type == str:
            return self._get_placeholder("String value", required, options)
        elif field_type == int:
            return self._get_placeholder("Integer value", required, options)
        elif field_type == float:
            return self._get_placeholder("Float value", required, options)
        elif field_type == bool:
            return False

        # Default fallback
        return self._get_placeholder(f"Value of type {field_type}", required, options)

    def _get_placeholder(self, description: str, required: bool, options: ScaffoldOptions) -> str:
        """Generate appropriate placeholder text based on template level."""
        if options.template_level == "minimal":
            return f"[{description}]"
        elif options.template_level == "standard":
            req_text = "REQUIRED" if required else "OPTIONAL"
            return f"[{req_text}: {description}]"
        else:  # detailed
            req_text = "REQUIRED" if required else "OPTIONAL"
            return f"[{req_text}: {description}]"

    # -------- Stub Documents Injection --------
    def _inject_stub_documents(self, structure: Dict[str, Any], options: ScaffoldOptions) -> None:
        """Populate blueprint with content stubs based on template_level.

        Walk the nested dict and fill known files with templated content. This
        phase uses lightweight templates; later passes may switch to Jinja2.
        """
        root_name = next(iter(structure.keys()))
        root = structure[root_name]

        # Root files
        root["README.md"] = self._template_readme(options)
        root["LICENSE"] = self._template_license(options)
        root["CONTRIBUTING.md"] = self._template_contributing(options)
        root["mkdocs.yml"] = self._template_mkdocs_yaml(root_name)

        # Directory index stubs
        def setf(path_parts: Tuple[str, ...], filename: str, content: str) -> None:
            node = root
            for part in path_parts:
                node = node[part]
            node[filename] = content

        setf(("design-files",), "index.md", self._template_index("Design Files", options))
        setf(("manufacturing-files",), "index.md", self._template_index("Manufacturing Files", options))
        setf(("bom",), "index.md", self._template_bom_index(options))
        setf(("bom",), "bom.csv", self._template_bom_csv(options))
        setf(("bom",), "bom.md", self._template_bom_md(options))
        setf(("making-instructions",), "index.md", self._template_index("Making Instructions", options))
        setf(("making-instructions",), "assembly-guide.md", self._template_assembly_guide(options))
        setf(("operating-instructions",), "index.md", self._template_index("Operating Instructions", options))
        setf(("quality-instructions",), "index.md", self._template_index("Quality Instructions", options))
        setf(("risk-assessment",), "index.md", self._template_index("Risk Assessment", options))
        setf(("software",), "index.md", self._template_index("Software", options))
        setf(("tool-settings",), "index.md", self._template_index("Tool Settings", options))
        setf(("schematics",), "index.md", self._template_index("Schematics", options))
        setf(("parts",), "index.md", self._template_index("Parts", options))

        # Docs section
        setf(("docs",), "index.md", self._template_docs_home(options))
        setf(("docs",), "getting-started.md", self._template_getting_started(options))
        setf(("docs",), "development.md", self._template_development(options))
        setf(("docs",), "manufacturing.md", self._template_index("Manufacturing", options))
        setf(("docs",), "assembly.md", self._template_index("Assembly", options))
        setf(("docs",), "maintenance.md", self._template_index("Maintenance", options))

    # -------- Templates (first pass, lightweight) --------
    def _template_readme(self, options: ScaffoldOptions) -> str:
        """Generate README template based on template level."""
        if options.template_level == "minimal":
            return f"# {options.project_name}\n\n[Project description]\n"
        elif options.template_level == "standard":
            return (
                f"# {options.project_name}\n\n"
                "Welcome! This project follows the Open Know How (OKH) structure and is\n"
                "scaffolded for compatibility with the Open Matching Engine (OME).\n\n"
                "## Quick Start\n\n"
                "1. Edit `okh-manifest.json` to define your project\n"
                "2. Explore documentation in `docs/` (MkDocs)\n"
                "3. Build docs locally: `mkdocs serve`\n\n"
                "## Project Structure\n\n"
                "- `design-files/` - CAD models and technical drawings\n"
                "- `manufacturing-files/` - Assembly guides and compliance docs\n"
                "- `bom/` - Bill of Materials (CSV and Markdown)\n"
                "- `making-instructions/` - Step-by-step build instructions\n"
                "- `docs/` - Comprehensive documentation (MkDocs)\n"
            )
        else:  # detailed
            return (
                f"# {options.project_name}\n\n"
                "Welcome! This project follows the Open Know How (OKH) structure and is\n"
                "scaffolded for compatibility with the Open Matching Engine (OME).\n\n"
                "## Overview\n\n"
                "This is an open hardware project that follows the OKH specification for\n"
                "maximum interoperability and discoverability in the open-source hardware\n"
                "ecosystem.\n\n"
                "## Quick Start\n\n"
                "1. **Edit the manifest**: Start with `okh-manifest.json` to define your project\n"
                "2. **Explore documentation**: Check out the `docs/` directory (MkDocs)\n"
                "3. **Build docs locally**: Run `mkdocs serve` to preview documentation\n"
                "4. **Add your content**: Populate the various directories with your files\n\n"
                "## Project Structure\n\n"
                "This project follows the OKH package structure:\n\n"
                "- `design-files/` - CAD models, technical drawings, and design documentation\n"
                "- `manufacturing-files/` - Assembly guides, compliance documentation\n"
                "- `bom/` - Bill of Materials in both CSV and Markdown formats\n"
                "- `making-instructions/` - Step-by-step build and assembly instructions\n"
                "- `operating-instructions/` - User manuals and maintenance guides\n"
                "- `quality-instructions/` - QC checklists and testing protocols\n"
                "- `risk-assessment/` - Safety and risk documentation\n"
                "- `software/` - Firmware, control software, and related code\n"
                "- `tool-settings/` - Machine configurations and tool parameters\n"
                "- `schematics/` - Electrical schematics and circuit diagrams\n"
                "- `parts/` - Part-specific files organized by component\n"
                "- `docs/` - Comprehensive documentation using MkDocs\n\n"
                "## Development\n\n"
                "This project is designed to work seamlessly with the Open Matching Engine.\n"
                "The OKH manifest (`okh-manifest.json`) contains all metadata needed for\n"
                "discovery, matching, and manufacturing coordination.\n\n"
                "## Contributing\n\n"
                "Please see `CONTRIBUTING.md` for guidelines on contributing to this project.\n"
            )

    def _template_license(self, options: ScaffoldOptions) -> str:
        return (
            "SPDX-License-Identifier: [CHOOSE-A-LICENSE]\n\n"
            "Replace this file with your chosen license text (e.g., CERN-OHL-S-2.0,\n"
            "CC-BY-4.0, GPL-3.0-or-later)."
        )

    def _template_contributing(self, options: ScaffoldOptions) -> str:
        return (
            "# Contributing\n\n"
            "Thank you for your interest in contributing! Please open issues and pull\n"
            "requests. Follow the OKH structure and keep documentation up to date."
        )

    def _template_mkdocs_yaml(self, project_root: str) -> str:
        return (
            "site_name: " + project_root + "\n"
            "nav:\n"
            "  - Home: docs/index.md\n"
            "  - Getting Started: docs/getting-started.md\n"
            "  - Development: docs/development.md\n"
            "  - Manufacturing: docs/manufacturing.md\n"
            "  - Assembly: docs/assembly.md\n"
            "  - Maintenance: docs/maintenance.md\n"
        )

    def _template_index(self, title: str, options: ScaffoldOptions) -> str:
        """Generate index template based on template level."""
        if options.template_level == "minimal":
            return f"# {title}\n\n[Add {title.lower()} documentation]"
        elif options.template_level == "standard":
            return (
                f"# {title}\n\n"
                f"Documentation for {title.lower()}.\n\n"
                f"## Purpose\n\n"
                f"This directory contains {title.lower()} for the project.\n\n"
                f"## Contents\n\n"
                f"- Add relevant files to this directory\n"
                f"- Update this index.md with descriptions\n"
                f"- Link to external resources as needed\n"
            )
        else:  # detailed
            return (
                f"# {title}\n\n"
                f"Comprehensive documentation for {title.lower()}.\n\n"
                f"## Purpose\n\n"
                f"This directory contains all {title.lower()} related to the project.\n"
                f"Follow OKH best practices for organization and documentation.\n\n"
                f"## Organization\n\n"
                f"- Use descriptive filenames\n"
                f"- Include metadata in file headers\n"
                f"- Cross-reference related documentation\n"
                f"- Maintain version control for all files\n\n"
                f"## Best Practices\n\n"
                f"- Keep files focused and well-organized\n"
                f"- Include images and diagrams where helpful\n"
                f"- Use standard formats when possible\n"
                f"- Document assumptions and limitations\n\n"
                f"## Contents\n\n"
                f"Add your {title.lower()} files here and update this index accordingly.\n"
            )

    def _template_bom_index(self, options: ScaffoldOptions) -> str:
        """Generate BOM index template based on template level."""
        if options.template_level == "minimal":
            return "# Bill of Materials (BOM)\n\n[Add BOM documentation]"
        elif options.template_level == "standard":
            return (
                "# Bill of Materials (BOM)\n\n"
                "This directory contains the Bill of Materials for the project.\n\n"
                "## Files\n\n"
                "- `bom.csv` - Structured tabular data\n"
                "- `bom.md` - Human-readable list\n\n"
                "## Usage\n\n"
                "The generation services can ingest or produce BOM content compatible\n"
                "with this directory structure.\n"
            )
        else:  # detailed
            return (
                "# Bill of Materials (BOM)\n\n"
                "This directory contains the complete Bill of Materials for the project,\n"
                "organized for maximum compatibility with the Open Matching Engine.\n\n"
                "## File Formats\n\n"
                "### CSV Format (`bom.csv`)\n"
                "- Structured tabular data for programmatic processing\n"
                "- Columns: item, quantity, unit, notes\n"
                "- Compatible with spreadsheet applications\n"
                "- Machine-readable for automation\n\n"
                "### Markdown Format (`bom.md`)\n"
                "- Human-readable list format\n"
                "- Includes descriptions and context\n"
                "- Easy to read and edit manually\n"
                "- Good for documentation and review\n\n"
                "## Integration\n\n"
                "The generation services can:\n"
                "- Ingest BOM content from this directory\n"
                "- Produce BOM content compatible with this structure\n"
                "- Validate BOM completeness and accuracy\n"
                "- Generate manufacturing requirements\n\n"
                "## Best Practices\n\n"
                "- Keep both formats synchronized\n"
                "- Include part numbers and specifications\n"
                "- Document alternatives and substitutions\n"
                "- Update when design changes\n"
            )

    def _template_bom_csv(self, options: ScaffoldOptions) -> str:
        """Generate BOM CSV template based on template level."""
        if options.template_level == "minimal":
            return "item,quantity,unit,notes\n[Part Name],[Quantity],[Unit],[Notes]"
        elif options.template_level == "standard":
            return (
                "item,quantity,unit,notes\n"
                "Example Part,1,pcs,Example entry\n"
                "PLA Filament,250,g,3D printing material\n"
                "Arduino Uno,1,pcs,Microcontroller board"
            )
        else:  # detailed
            return (
                "item,quantity,unit,notes,supplier,part_number,cost\n"
                "Example Part,1,pcs,Example entry,Supplier Name,PART-001,$5.00\n"
                "PLA Filament,250,g,3D printing material,Local Supplier,PLA-250,$15.00\n"
                "Arduino Uno,1,pcs,Microcontroller board,Arduino,ARDUINO-UNO,$25.00\n"
                "Resistor 10kΩ,5,pcs,10k ohm resistor,Electronics Store,RES-10K,$0.10"
            )

    def _template_bom_md(self, options: ScaffoldOptions) -> str:
        """Generate BOM Markdown template based on template level."""
        if options.template_level == "minimal":
            return "# BOM (Markdown)\n\n- [Part Name] — [Quantity] [Unit] — [Notes]"
        elif options.template_level == "standard":
            return (
                "# BOM (Markdown)\n\n"
                "## Components\n\n"
                "- Example Part — 1 pcs — Example entry\n"
                "- PLA Filament — 250 g — 3D printing material\n"
                "- Arduino Uno — 1 pcs — Microcontroller board\n\n"
                "## Notes\n\n"
                "Add any special requirements or notes here."
            )
        else:  # detailed
            return (
                "# BOM (Markdown)\n\n"
                "## Components\n\n"
                "### Electronics\n"
                "- Arduino Uno — 1 pcs — Microcontroller board\n"
                "  - Supplier: Arduino\n"
                "  - Part Number: ARDUINO-UNO\n"
                "  - Cost: $25.00\n\n"
                "- Resistor 10kΩ — 5 pcs — 10k ohm resistor\n"
                "  - Supplier: Electronics Store\n"
                "  - Part Number: RES-10K\n"
                "  - Cost: $0.10 each\n\n"
                "### Materials\n"
                "- PLA Filament — 250 g — 3D printing material\n"
                "  - Supplier: Local Supplier\n"
                "  - Part Number: PLA-250\n"
                "  - Cost: $15.00\n\n"
                "### Mechanical Parts\n"
                "- Example Part — 1 pcs — Example entry\n"
                "  - Supplier: Supplier Name\n"
                "  - Part Number: PART-001\n"
                "  - Cost: $5.00\n\n"
                "## Total Estimated Cost\n\n"
                "Approximately $45.50 per unit\n\n"
                "## Notes\n\n"
                "- Prices are estimates and may vary by supplier\n"
                "- Some components may have alternatives\n"
                "- Check availability before ordering\n"
            )

    def _template_assembly_guide(self, options: ScaffoldOptions) -> str:
        return (
            "# Assembly Guide\n\n"
            "Provide step-by-step assembly instructions with images as needed."
        )

    def _template_docs_home(self, options: ScaffoldOptions) -> str:
        return (
            "# Documentation\n\n"
            "Welcome to the project documentation. Use the navigation to explore."
        )

    def _template_getting_started(self, options: ScaffoldOptions) -> str:
        return (
            "# Getting Started\n\n"
            "1. Install MkDocs: `pip install mkdocs`\n"
            "2. Serve docs locally: `mkdocs serve`\n"
            "3. Edit `okh-manifest.json` to define your project per OKH."
        )

    def _template_development(self, options: ScaffoldOptions) -> str:
        return (
            "# Development Guide\n\n"
            "Describe development workflows, testing, and contribution practices."
        )

    # -------- Materializers (stubs; implemented in later passes) --------
    def _write_filesystem(self, structure: Dict[str, Any], options: ScaffoldOptions, manifest_template: Dict[str, Any]) -> str:
        """Write the blueprint to the filesystem and return the absolute path.

        Rules:
        - Create the target root directory inside options.output_path
        - Recursively create directories and files from the blueprint
        - Write `okh-manifest.json` using the provided manifest_template
        """
        import json
        base = Path(options.output_path).expanduser().resolve()
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)

        # The blueprint has a single top-level project directory
        if len(structure.keys()) != 1:
            raise ValueError("Invalid structure: expected a single project root")

        project_root_name = next(iter(structure.keys()))
        project_root_node = structure[project_root_name]
        project_root_path = base / project_root_name
        project_root_path.mkdir(parents=True, exist_ok=True)

        def write_node(node: Any, current_path: Path) -> None:
            if isinstance(node, dict):
                # Directory: entries can be subdirectories or files (str content)
                for name, child in node.items():
                    target = current_path / name
                    if isinstance(child, dict):
                        target.mkdir(parents=True, exist_ok=True)
                        write_node(child, target)
                    else:
                        content: str = child if isinstance(child, str) else ""
                        # Special handling for manifest file
                        if name == "okh-manifest.json":
                            content = json.dumps(manifest_template, indent=2) + "\n"
                        target.write_text(content, encoding="utf-8")
            else:
                # Leaf nodes should be strings; safeguard
                current_path.write_text(str(node), encoding="utf-8")

        write_node(project_root_node, project_root_path)

        return str(project_root_path)

    async def _create_and_store_zip(self, structure: Dict[str, Any], options: ScaffoldOptions, manifest_template: Dict[str, Any]) -> str:
        """Create a ZIP archive for the scaffold and return a file URL.

        Behavior:
        - Builds an in-memory ZIP from the directory blueprint
        - Writes `okh-manifest.json` using the `manifest_template`
        - Saves the ZIP file to `options.output_path` if provided, otherwise a temp directory
        - Returns a file URL (file://...) to the ZIP on local disk
        """
        import io
        import json
        import time
        import tempfile
        from zipfile import ZipFile, ZIP_DEFLATED

        # Determine root name
        if len(structure.keys()) != 1:
            raise ValueError("Invalid structure: expected a single project root")

        project_root_name = next(iter(structure.keys()))
        project_root_node = structure[project_root_name]

        # Build in-memory zip
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
            def add_node(node: Any, prefix: str) -> None:
                if isinstance(node, dict):
                    for name, child in node.items():
                        child_path = f"{prefix}{name}"
                        if isinstance(child, dict):
                            # Ensure directory entry exists (optional in ZIP)
                            dir_entry = child_path if child_path.endswith("/") else child_path + "/"
                            zf.writestr(dir_entry, "")
                            add_node(child, dir_entry)
                        else:
                            content: str = child if isinstance(child, str) else ""
                            # Special-case manifest
                            if name == "okh-manifest.json":
                                content = json.dumps(manifest_template, indent=2) + "\n"
                            zf.writestr(child_path, content)
                else:
                    # Leaf not expected here, but handle defensively
                    zf.writestr(prefix, str(node))

            add_node(project_root_node, f"{project_root_name}/")

        # Persist to disk
        base_dir = Path(options.output_path).expanduser().resolve() if options.output_path else Path(tempfile.gettempdir()) / "ome-scaffolds"
        base_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        version_tag = options.version.replace("/", "-") if options.version else "0.1.0"
        zip_name = f"{project_root_name}-{version_tag}-{timestamp}.zip"
        zip_path = base_dir / zip_name

        with open(zip_path, "wb") as f:
            f.write(buffer.getvalue())

        return zip_path.as_uri()


