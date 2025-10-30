# Scaffolding Quick Start

## 30-Second Setup

Generate a new OKH project in seconds:

```bash
# Basic project
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{"project_name": "my-project"}'

# With custom settings
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "arduino-sensor",
    "template_level": "detailed",
    "output_format": "zip"
  }'
```

## What You Get

A complete project structure with:
- ✅ OKH-compliant directory layout
- ✅ Documentation stubs in all directories
- ✅ MkDocs configuration for professional docs
- ✅ OKH manifest template with guidance
- ✅ BOM templates (CSV + Markdown)
- ✅ Assembly and manufacturing guides

## Next Steps

1. **Download**: Save the generated structure to your filesystem
2. **Customize**: Fill in the manifest template with your project details
3. **Document**: Add your hardware designs and documentation
4. **Build**: Use MkDocs to build professional documentation
5. **Validate**: Use OME to validate your OKH manifest

## Template Levels

| Level | Use Case | Content |
|-------|----------|---------|
| `minimal` | Experienced developers | Basic placeholders |
| `standard` | Most users | Detailed guidance + examples |
| `detailed` | OKH newcomers | Help + best practices |

## Output Formats

| Format | Best For | Result |
|--------|----------|--------|
| `json` | API integration | Structured data |
| `zip` | Download | Ready-to-use project |
| `filesystem` | Direct creation | Files written to disk |

## Examples

### Arduino Project
```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "arduino-weather-station",
    "template_level": "standard",
    "output_format": "zip"
  }'
```

### Medical Device
```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "open-source-stethoscope",
    "template_level": "detailed",
    "output_format": "filesystem",
    "output_path": "/home/user/medical-devices"
  }'
```

### Research Project
```bash
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "microscope-automation",
    "organization": "University Research Lab",
    "template_level": "minimal",
    "output_format": "json"
  }'
```

## Building Documentation

```bash
# Install MkDocs
pip install mkdocs

# Navigate to your project
cd my-project

# Serve documentation locally
mkdocs serve

# Build static site
mkdocs build
```

## Validation

Validate your generated manifest:

```bash
curl -X POST "http://localhost:8001/v1/api/okh/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest": {
      "title": "my-project",
      "version": "0.1.0",
      "okhv": "OKH-LOSHv1.0",
      "license": "MIT",
      "licensor": "Your Name",
      "documentation_language": "en",
      "function": "Brief description of what it does"
    }
  }'
```

## Need More Help?

- 📖 [Full Scaffolding Guide](index.md)
- 🔧 [API Reference](../api/routes.md)
- 📋 [OKH Documentation](../models/okh-docs.md)
- 🛠️ [Development Guide](../development/developer-guide.md)
