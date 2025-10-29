# OKH Project Scaffolding Guide

## Overview

The Open Matching Engine (OME) provides a powerful scaffolding system that generates opinionated, OKH-compliant project structures with comprehensive documentation stubs. This system helps developers quickly bootstrap new open hardware projects that work seamlessly with the OME ecosystem.

## Quick Start

### Basic Usage

Generate a new OKH project scaffold using the API:

```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "my-awesome-project",
    "template_level": "standard",
    "output_format": "json"
  }'
```

### Output Formats

The scaffolding system supports three output formats:

1. **JSON Blueprint** (default): Returns a structured JSON representation of the project
2. **ZIP Archive**: Creates a downloadable ZIP file with all project files
3. **Filesystem**: Writes directly to a specified directory path

## Project Structure

The generated project follows the OKH package conventions with MkDocs integration:

```
{project-name}/
├── okh-manifest.json          # OKH manifest template
├── README.md                  # Project overview and MkDocs entrypoint
├── LICENSE                    # License file stub
├── CONTRIBUTING.md            # Contribution guidelines stub
├── mkdocs.yml                 # MkDocs configuration
├── design-files/              # CAD models, technical drawings
│   └── index.md              # Design files documentation
├── manufacturing-files/       # Assembly guides, compliance docs
│   └── index.md              # Manufacturing documentation
├── bom/                       # Bill of Materials (dedicated directory)
│   ├── index.md              # BOM overview and instructions
│   ├── bom.csv               # BOM template in CSV format
│   └── bom.md                # BOM in markdown format
├── making-instructions/       # Step-by-step build instructions
│   ├── index.md              # Making instructions overview
│   └── assembly-guide.md     # Assembly guide template
├── operating-instructions/    # User manuals, maintenance
│   └── index.md              # Operating instructions overview
├── quality-instructions/      # QC checklists, testing protocols
│   └── index.md              # Quality documentation
├── risk-assessment/          # Safety and risk documentation
│   └── index.md              # Risk assessment documentation
├── software/                 # Firmware, control software
│   └── index.md              # Software documentation
├── tool-settings/            # Machine configurations
│   └── index.md              # Tool settings documentation
├── schematics/               # Electrical schematics
│   └── index.md              # Schematics documentation
├── parts/                    # Part-specific files
│   └── index.md              # Parts documentation
└── docs/                     # MkDocs documentation source
    ├── index.md              # Documentation home
    ├── getting-started.md    # Quick start guide
    ├── development.md        # Development guide
    ├── manufacturing.md      # Manufacturing overview
    ├── assembly.md           # Assembly overview
    └── maintenance.md        # Maintenance guide
```

## Template Levels

The scaffolding system provides three levels of documentation detail:

### Minimal
- Field names and types only
- Basic placeholders
- Suitable for experienced developers

### Standard (Default)
- Field names, types, descriptions, and placeholders
- Helpful examples and guidance
- Balanced approach for most users

### Detailed
- Full guidance with examples and best practices
- Validation hints and comprehensive documentation
- Ideal for newcomers to OKH

## API Reference

### Endpoint
```
POST /v1/api/okh/scaffold
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_name` | string | Yes | - | Human-friendly project name; used for directory name |
| `version` | string | No | "0.1.0" | Initial project version string (semantic recommended) |
| `organization` | string | No | null | Optional organization name for future packaging alignment |
| `template_level` | string | No | "standard" | Amount of guidance in stub docs ("minimal", "standard", "detailed") |
| `output_format` | string | No | "json" | Output format ("json", "zip", "filesystem") |
| `output_path` | string | No | null | Required for filesystem writes; ignored for others |
| `include_examples` | boolean | No | true | Whether to include sample files/content |
| `okh_version` | string | No | "OKH-LOSHv1.0" | OKH schema version tag written into manifest stub |

### Response Format

```json
{
  "status": "success",
  "message": "Scaffold generated successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789",
  "project_name": "my-awesome-project",
  "structure": {
    "my-awesome-project": {
      // Directory structure with file contents
    }
  },
  "manifest_template": {
    // OKH manifest template with placeholders
  },
  "download_url": "file:///tmp/scaffold_my-awesome-project.zip",
  "filesystem_path": "/path/to/output/my-awesome-project"
}
```

## Examples

### Generate JSON Blueprint

```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "arduino-sensor",
    "template_level": "detailed",
    "output_format": "json"
  }'
```

### Generate ZIP Archive

```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "microscope-stage",
    "template_level": "standard",
    "output_format": "zip"
  }'
```

### Generate Filesystem Structure

```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "prosthetic-hand",
    "template_level": "minimal",
    "output_format": "filesystem",
    "output_path": "/home/user/projects"
  }'
```

## MkDocs Integration

The generated projects include full MkDocs integration:

1. **Configuration**: `mkdocs.yml` with proper navigation structure
2. **Documentation**: Interlinked documentation in the `docs/` directory
3. **Navigation**: Automatic navigation based on directory structure
4. **Search**: Built-in search functionality
5. **Theming**: Professional documentation theme

### Building Documentation

```bash
# Install MkDocs
pip install mkdocs

# Build the documentation
mkdocs build

# Serve locally for development
mkdocs serve
```

## OKH Manifest Template

The generated `okh-manifest.json` includes:

- **Schema Compliance**: Generated by introspecting the `OKHManifest` dataclass
- **Field Documentation**: Each field includes type information and guidance
- **Placeholders**: Clear placeholders for required and optional fields
- **Examples**: Helpful examples based on the template level
- **Validation Hints**: Guidance for proper field completion

## Best Practices

### Project Naming
- Use descriptive, searchable names
- Avoid special characters
- Keep under 100 characters
- Use kebab-case for consistency

### Version Management
- Use semantic versioning (e.g., 1.0.0, 1.2.3)
- Start with 0.1.0 for initial development
- Increment appropriately for releases

### Documentation
- Choose the appropriate template level for your audience
- Update documentation as the project evolves
- Use the MkDocs interface for better navigation
- Include real examples and images

### Organization
- Set the organization field for future packaging
- Use consistent naming across related projects
- Consider namespace implications

## Integration with OME

The scaffolded projects are designed to work seamlessly with the OME ecosystem:

1. **Validation**: Generated manifests can be validated using the OME validation endpoints
2. **Matching**: Projects can be used as OKH requirements in matching operations
3. **Generation**: The structure supports the OME generation workflow
4. **Storage**: Projects can be stored and retrieved using OME storage services

## Troubleshooting

### Common Issues

**404 Error**: Ensure you're using the correct API URL with `/v1` prefix
```
❌ http://localhost:8001/api/okh/scaffold
✅ http://localhost:8001/v1/api/okh/scaffold
```

**Permission Errors**: Ensure the output path is writable for filesystem output
```bash
chmod 755 /path/to/output
```

**Template Level Issues**: Use valid template levels
```
❌ "basic"
✅ "minimal", "standard", "detailed"
```

### Getting Help

- Check the [API Documentation](../api/routes.md) for detailed endpoint information
- Review the [OKH Model Documentation](../models/okh-docs.md) for schema details
- Consult the [Development Guide](../development/developer-guide.md) for setup issues

## Next Steps

1. **Customize**: Update the generated templates with your project-specific information
2. **Develop**: Add your hardware designs, code, and documentation
3. **Validate**: Use OME validation endpoints to ensure OKH compliance
4. **Publish**: Share your project with the open hardware community
5. **Integrate**: Use your project in OME matching and generation workflows

---

For more information, see the [API Reference](../api/routes.md) and [OKH Documentation](../models/okh-docs.md).
