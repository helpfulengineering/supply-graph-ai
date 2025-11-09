# Open Matching Engine (OME) CLI Documentation

## Overview

The Open Matching Engine (OME) Command Line Interface provides a set of tools for managing OKH packages, OKW facilities, matching operations, and system administration. The CLI supports both HTTP API mode (when connected to a server) and fallback mode (direct service calls).


## Documentation Structure

This directory contains documentation for the OME CLI:

- **📖 [Main Documentation](index.md)** - Complete CLI reference with all commands, options, and examples
- **🚀 [Quick Start Guide](quick-start.md)** - Get up and running with the OME CLI in 5 minutes
- **💡 [Examples](examples.md)** - Practical examples and workflows for common use cases
- **🏗️ [Architecture](architecture.md)** - Technical architecture and implementation details

## Quick Links

- **Installation**: See [Quick Start Guide](quick-start.md#getting-started-in-5-minutes)
- **All Commands**: See [Command Groups](#command-groups) below
- **Common Workflows**: See [Examples](examples.md#package-management-workflows)
- **Troubleshooting**: See [Troubleshooting](#troubleshooting) section below

## Installation and Setup

### Prerequisites

- Python 3.8+
- Conda environment `supply-graph-ai` activated
- OME server running (optional, for HTTP mode)

### Basic Usage

```bash
# Activate the conda environment
conda activate supply-graph-ai

# Navigate to the project directory
cd supply-graph-ai

# Run the CLI
python ome [COMMAND] [OPTIONS]
```

## Global Options

The OME CLI supports several global options that apply to all commands:

```bash
ome [GLOBAL_OPTIONS] [COMMAND] [COMMAND_OPTIONS]
```

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server-url TEXT` | OME server URL | `http://localhost:8001` |
| `--timeout FLOAT` | Request timeout in seconds | `30.0` |
| `-v, --verbose` | Enable verbose output with execution tracking | `False` |
| `--json` | Output in JSON format | `False` |
| `--table` | Output in table format | `False` |
| `--use-llm` | Enable LLM integration for enhanced analysis | `False` |
| `--llm-provider TEXT` | LLM provider (openai, anthropic, google, azure, local) | `anthropic` |
| `--llm-model TEXT` | Specific LLM model to use | `None` |
| `--quality-level TEXT` | Quality level (hobby, professional, medical) | `professional` |
| `--strict-mode` | Enable strict validation mode | `False` |
| `--help` | Show help message | - |

### Examples

```bash
# Use verbose mode with execution tracking
ome --verbose system health

# Get JSON output
ome --json package list-packages

# Set custom timeout
ome --timeout 60 package build manifest.json

# Use LLM integration for enhanced analysis
ome --use-llm --llm-provider anthropic --quality-level professional okh validate manifest.json

# Global LLM configuration
ome --use-llm --quality-level medical --strict-mode system health
```

## Command Groups

The OME CLI is organized into 7 main command groups with 43 total commands:

1. **[Match Commands](#match-commands)** - Requirements-to-capabilities matching
2. **[OKH Commands](#okh-commands)** - OpenKnowHow manifest management
3. **[OKW Commands](#okw-commands)** - OpenKnowWhere facility management
4. **[Package Commands](#package-commands)** - OKH package management
5. **[LLM Commands](#llm-commands)** - LLM operations and AI features
6. **[System Commands](#system-commands)** - System administration
7. **[Utility Commands](#utility-commands)** - Utility operations

**Note**: Supply Tree Commands are not implemented in the current CLI version.

---

## Package Commands

Manage OKH packages including building, pushing, pulling, and verification. 

### `ome package build`

Build an OKH package from a manifest file.

```bash
ome package build MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--output-dir TEXT` - Output directory for built package
- `--no-design-files` - Skip downloading design files
- `--no-manufacturing-files` - Skip downloading manufacturing files
- `--no-software` - Skip downloading software files
- `--max-file-size INTEGER` - Maximum file size to download (bytes)
- `--timeout INTEGER` - Download timeout per file (seconds)
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--quality-level TEXT` - Quality level (hobby, professional, medical)
- `--strict-mode` - Enable strict validation mode

**Examples:**
```bash
# Build a package from manifest
ome package build openflexure-microscope.okh.json

# Build with LLM enhancement
ome package build manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Build with custom options
ome package build manifest.json --no-design-files --output-dir ./my-packages/
```

### `ome package build-from-storage`

Build an OKH package from a stored manifest.

```bash
ome package build-from-storage MANIFEST_ID [OPTIONS]
```

**Arguments:**
- `MANIFEST_ID` - UUID of the stored manifest

**Options:**
- `--output-dir TEXT` - Output directory for built package
- `--no-design-files` - Skip downloading design files
- `--no-manufacturing-files` - Skip downloading manufacturing files
- `--no-software` - Skip downloading software files

### `ome package list-packages`

List all built packages.

```bash
ome package list-packages
```

**Output:**
- Package name and version
- Local path
- File count and size
- Build timestamp

### `ome package verify`

Verify a package's integrity.

```bash
ome package verify PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

### `ome package delete`

Delete a package.

```bash
ome package delete PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

### `ome package push`

Push a local package to remote storage.

```bash
ome package push PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

**Examples:**
```bash
# Push a package to remote storage
ome package push community/simple-test-project 1.0.0
```

### `ome package pull`

Pull a remote package to local storage.

```bash
ome package pull PACKAGE_NAME VERSION [OPTIONS]
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

**Options:**
- `--output-dir TEXT` - Output directory for pulled package

**Examples:**
```bash
# Pull a package from remote storage
ome package pull community/simple-test-project 1.0.0

# Pull to specific directory
ome package pull org/project 1.0.0 --output-dir ./my-packages/
```

### `ome package list-remote`

List packages available in remote storage.

```bash
ome package list-remote
```

**Output:**
- Remote package names and versions
- Package sizes
- Total count

---

## OKH Commands

Manage OpenKnowHow (OKH) manifests for hardware designs.

### `ome okh validate`

Validate an OKH manifest.

```bash
ome okh validate MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [hobby\|professional\|medical]` - Validation quality level
- `--strict-mode` - Enable strict validation mode
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use

### `ome okh create`

Create and store an OKH manifest.

```bash
ome okh create MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome okh get`

Get an OKH manifest by ID.

```bash
ome okh get MANIFEST_ID
```

**Arguments:**
- `MANIFEST_ID` - UUID of the manifest

### `ome okh list-manifests`

List stored OKH manifests.

```bash
ome okh list-manifests [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip

### `ome okh delete`

Delete an OKH manifest.

```bash
ome okh delete MANIFEST_ID
```

**Arguments:**
- `MANIFEST_ID` - UUID of the manifest

### `ome okh extract`

Extract requirements from an OKH manifest.

```bash
ome okh extract MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Extraction quality level
- `--strict-mode` - Enable strict extraction mode

### `ome okh upload`

Upload and validate an OKH manifest file.

```bash
ome okh upload MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome okh scaffold`

Generate an OKH-compliant project scaffold with documentation stubs and manifest template.

```bash
ome okh scaffold PROJECT_NAME [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME` - Human-friendly project name; used for directory name

**Options:**
- `--version TEXT` - Initial project version (semantic recommended). Default: "0.1.0"
- `--organization TEXT` - Optional organization name for future packaging alignment
- `--template-level [minimal|standard|detailed]` - Amount of guidance in stub docs. Default: "standard"
- `--output-format [json|zip|filesystem]` - Output format. Default: "json"
- `--output-path PATH` - Output path (required for filesystem format)
- `--include-examples/--no-examples` - Include sample files/content. Default: true
- `--okh-version TEXT` - OKH schema version tag. Default: "OKH-LOSHv1.0"

**Features:**
- **MkDocs Integration**: Generates interlinked documentation structure with `mkdocs.yml` configuration
- **Bi-directional Navigation Links**: All section directories link back to main documentation, and `docs/index.md` links to all sections
- **Cross-References**: Related content pages (assembly, manufacturing, maintenance) include links to relevant sections
- **Bridge Pages**: Special navigation pages in `docs/sections/` provide MkDocs access to OKH section directories at project root
- **OKH Schema Compliance**: Manifest template generated by introspecting the `OKHManifest` dataclass
- **Template Levels**: Three levels of documentation detail (minimal, standard, detailed)
  - **Minimal**: Basic content without cross-references
  - **Standard**: Includes cross-references to related sections
  - **Detailed**: Expanded cross-references with grouped sections and detailed descriptions
- **Multiple Output Formats**: JSON blueprint, ZIP archive, or direct filesystem write
- **Dedicated BOM Directory**: Separate `bom/` directory with CSV and Markdown templates
- **Directory Structure**: All OKH-compliant directories with appropriate documentation stubs

**Documentation Linking:**
The scaffold includes comprehensive linking between documentation sections:
- **Section Navigation**: All section `index.md` files include back-links to `docs/index.md`
- **Main Documentation Hub**: `docs/index.md` links to all section directories
- **Cross-References**: Documentation pages reference related sections (assembly, manufacturing, maintenance, getting-started, development)
- **MkDocs Navigation**: Bridge pages enable full MkDocs navigation while preserving OKH structure

**Examples:**
```bash
# Generate basic project scaffold
ome okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ome okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with custom organization
ome okh scaffold microscope-stage --organization "University Lab" --output-format filesystem --output-path ./projects

# Generate minimal scaffold for experienced developers
ome okh scaffold quick-prototype --template-level minimal --output-format json
```

### `ome okh scaffold-cleanup`

Clean and optimize a scaffolded OKH project directory by removing unmodified documentation stubs and empty directories.

```bash
ome okh scaffold-cleanup PROJECT_PATH [OPTIONS]
```

**Arguments:**
- `PROJECT_PATH` - Path to the project root directory

**Options:**
- `--apply` - Apply cleanup (by default runs as dry-run only)
- `--remove-unmodified-stubs/--keep-unmodified-stubs` - Remove unmodified scaffolding stubs. Default: remove
- `--remove-empty-directories/--keep-empty-directories` - Remove empty directories after cleanup. Default: remove

**Features:**
- **Content-Based Detection**: Compares file contents with regenerated templates to identify unmodified stubs
- **Template Level Alignment**: Automatically regenerates templates from scaffolding service, ensuring alignment with scaffold changes
- **Broken Link Detection**: Detects and warns about broken links in remaining markdown files after cleanup
- **Dry Run Mode**: Preview changes before applying cleanup (default behavior)
- **Preserves User Content**: Only removes files that exactly match scaffold-generated templates
- **Empty Directory Cleanup**: Removes directories that become empty after file cleanup

**Cleanup Behavior:**
- **Stub Detection**: Files are considered "unmodified stubs" if their content exactly matches the scaffold-generated template (including links and cross-references)
- **Modified File Preservation**: Files that have been modified by the user are preserved, even if they contain scaffold-generated links
- **Template Level Matching**: Cleanup uses `template_level="standard"` by default. Scaffolds created with different template levels may not match exactly
- **Bridge Pages**: Bridge pages in `docs/sections/` are treated as stubs and can be removed if unmodified

**Broken Link Warnings:**
After removing files, cleanup scans remaining markdown files for links pointing to removed files. Broken link warnings are displayed separately for better visibility:
- **Broken Link Warnings**: Lists files with links pointing to removed files
- **Other Warnings**: General warnings about cleanup operations

**Examples:**
```bash
# Preview cleanup (dry-run) - see what would be removed
ome okh scaffold-cleanup ./projects/my-hardware-project

# Apply cleanup to remove unmodified stubs and empty directories
ome okh scaffold-cleanup ./projects/my-hardware-project --apply

# Apply cleanup but keep empty directories
ome okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-empty-directories

# Keep unmodified stubs but remove empty directories
ome okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-unmodified-stubs
```

**Output:**
```bash
# Dry-run output
✅ Dry run completed

🗑️  Files to remove (5):
   - /path/to/project/README.md
   - /path/to/project/docs/index.md
   ...

📁 Empty directories to remove (2):
   - /path/to/project/bom
   ...

🔗 Broken Link Warnings:
   ⚠️  Broken link(s) in docs/index.md: ../bom/index.md

⚠️  Other Warnings:
   - Any other warnings

# Apply output
✅ Cleanup completed

🗑️  Files removed (5):
   ...
📁 Empty directories removed (2):
   ...
💾 Bytes saved: 12345

🔗 Broken Link Warnings:
   ⚠️  Broken link(s) in docs/index.md: ../bom/index.md
```

---

## OKW Commands

Manage OpenKnowWhere (OKW) facilities for manufacturing capabilities.

### `ome okw validate`

Validate an OKW facility.

```bash
ome okw validate FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome okw create`

Create and store an OKW facility.

```bash
ome okw create FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome okw get`

Get an OKW facility by ID.

```bash
ome okw get FACILITY_ID
```

**Arguments:**
- `FACILITY_ID` - UUID of the facility

### `ome okw list-facilities`

List stored OKW facilities.

```bash
ome okw list-facilities [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip

### `ome okw delete`

Delete an OKW facility.

```bash
ome okw delete FACILITY_ID
```

**Arguments:**
- `FACILITY_ID` - UUID of the facility

### `ome okw extract-capabilities`

Extract capabilities from an OKW facility.

```bash
ome okw extract-capabilities FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Extraction quality level
- `--strict-mode` - Enable strict extraction mode

### `ome okw upload`

Upload and validate an OKW facility file.

```bash
ome okw upload FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome okw search`

Search OKW facilities.

```bash
ome okw search [OPTIONS]
```

**Options:**
- `--query TEXT` - Search query
- `--domain TEXT` - Filter by domain
- `--capability TEXT` - Filter by capability type
- `--location TEXT` - Filter by location
- `--limit INTEGER` - Maximum number of results

**Examples:**
```bash
# Search for facilities with 3D printing capability
ome okw search --capability "3d-printing"

# Search for facilities in a specific location
ome okw search --location "San Francisco"
```

---

## Match Commands

Perform matching operations between OKH requirements and OKW capabilities.

### `ome match requirements`

Match OKH requirements to OKW capabilities.

```bash
ome match requirements MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--facility-id TEXT` - Specific facility ID to match against
- `--domain TEXT` - Domain for matching (e.g., "manufacturing")
- `--context TEXT` - Validation context (e.g., "hobby", "professional")
- `--quality-level [basic\|standard\|premium]` - Matching quality level
- `--strict-mode` - Enable strict matching mode

### `ome match validate`

Validate a match result.

```bash
ome match validate MATCH_FILE [OPTIONS]
```

**Arguments:**
- `MATCH_FILE` - Path to match result file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome match from-file`

Match from file upload.

```bash
ome match from-file MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--facility-id TEXT` - Specific facility ID to match against
- `--domain TEXT` - Domain for matching
- `--context TEXT` - Validation context

### `ome match list-recent`

List recent matches.

```bash
ome match list-recent [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip

---

## LLM Commands

Manage LLM operations and AI features for enhanced OKH manifest generation and facility matching.

### `ome llm generate`

Generate content using the LLM service.

```bash
ome llm generate PROMPT [OPTIONS]
```

**Arguments:**
- `PROMPT` - Text prompt for content generation

**Options:**
- `--provider TEXT` - LLM provider (anthropic, openai, google, local)
- `--model TEXT` - Model name (e.g., claude-sonnet-4-5-20250929)
- `--max-tokens INTEGER` - Maximum tokens to generate (default: 4000)
- `--temperature FLOAT` - Sampling temperature (default: 0.1)
- `--timeout INTEGER` - Request timeout in seconds (default: 60)
- `--output FILE` - Output file (default: stdout)
- `--format TEXT` - Output format (json, text, yaml) (default: text)

**Examples:**
```bash
# Basic generation
ome llm generate "Analyze this hardware project and generate an OKH manifest"

# With specific provider and model
ome llm generate "Generate OKH manifest" \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Save to file with JSON format
ome llm generate "Analyze project" \
  --output manifest.json \
  --format json
```

### `ome llm generate-okh`

Generate an OKH manifest for a hardware project.

```bash
ome llm generate-okh PROJECT_URL [OPTIONS]
```

**Arguments:**
- `PROJECT_URL` - URL of the hardware project (GitHub, GitLab, etc.)

**Options:**
- `--provider TEXT` - LLM provider (anthropic, openai, google, local)
- `--model TEXT` - Model name
- `--max-tokens INTEGER` - Maximum tokens to generate
- `--temperature FLOAT` - Sampling temperature
- `--timeout INTEGER` - Request timeout in seconds
- `--output FILE` - Output file (default: manifest.okh.json)
- `--format TEXT` - Output format (json, yaml, toml)
- `--preserve-context` - Preserve context files for debugging
- `--clone` - Clone repository locally for analysis

**Examples:**
```bash
# Generate from GitHub URL
ome llm generate-okh https://github.com/example/iot-sensor

# With specific provider
ome llm generate-okh https://github.com/example/project \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Clone repository for better analysis
ome llm generate-okh https://github.com/example/project \
  --clone \
  --preserve-context
```

### `ome llm match`

Use LLM to enhance facility matching.

```bash
ome llm match REQUIREMENTS_FILE FACILITIES_FILE [OPTIONS]
```

**Arguments:**
- `REQUIREMENTS_FILE` - Path to requirements JSON file
- `FACILITIES_FILE` - Path to facilities JSON file

**Options:**
- `--provider TEXT` - LLM provider
- `--model TEXT` - Model name
- `--max-tokens INTEGER` - Maximum tokens to generate
- `--temperature FLOAT` - Sampling temperature
- `--timeout INTEGER` - Request timeout in seconds
- `--output FILE` - Output file (default: stdout)
- `--format TEXT` - Output format (json, yaml, table)
- `--min-confidence FLOAT` - Minimum confidence threshold (default: 0.5)

**Examples:**
```bash
# Match requirements with facilities
ome llm match requirements.json facilities.json

# With confidence threshold
ome llm match requirements.json facilities.json \
  --min-confidence 0.7 \
  --output matches.json

# Table format output
ome llm match requirements.json facilities.json \
  --format table \
  --min-confidence 0.6
```

### `ome llm analyze`

Analyze a hardware project and extract information.

```bash
ome llm analyze PROJECT_URL [OPTIONS]
```

**Arguments:**
- `PROJECT_URL` - URL of the hardware project

**Options:**
- `--provider TEXT` - LLM provider
- `--model TEXT` - Model name
- `--max-tokens INTEGER` - Maximum tokens to generate
- `--temperature FLOAT` - Sampling temperature
- `--timeout INTEGER` - Request timeout in seconds
- `--output FILE` - Output file (default: stdout)
- `--format TEXT` - Output format (json, yaml, markdown)
- `--include-code` - Include code analysis
- `--include-docs` - Include documentation analysis

**Examples:**
```bash
# Basic project analysis
ome llm analyze https://github.com/example/project

# Comprehensive analysis
ome llm analyze https://github.com/example/project \
  --include-code \
  --include-docs \
  --output analysis.json \
  --format json

# Markdown report
ome llm analyze https://github.com/example/project \
  --output report.md \
  --format markdown
```

### `ome llm providers`

Manage LLM providers and configuration.

```bash
ome llm providers [COMMAND]
```

**Subcommands:**
- `list` - List available providers
- `status` - Show provider status
- `set` - Set active provider
- `test` - Test provider connection

**Examples:**
```bash
# List all providers
ome llm providers list

# Show provider status
ome llm providers status

# Set active provider
ome llm providers set anthropic

# Test provider connection
ome llm providers test anthropic
```

### `ome llm service`

Manage LLM service and metrics.

```bash
ome llm service [COMMAND]
```

**Subcommands:**
- `status` - Show service status
- `metrics` - Show usage metrics
- `health` - Check service health
- `reset` - Reset service state

**Examples:**
```bash
# Show service status
ome llm service status

# Show usage metrics
ome llm service metrics

# Check health
ome llm service health

# Reset service
ome llm service reset
```

---

## System Commands

System administration and monitoring commands. 

### `ome system health`

Check system health and status.

```bash
ome system health
```

**Output:**
- System status (ok/error)
- Version information
- Mode (HTTP/fallback)
- Registered domains

### `ome system domains`

List available domains and their status.

```bash
ome system domains
```

**Output:**
- Domain IDs and names
- Domain descriptions
- Domain status

### `ome system status`

Show detailed system status.

```bash
ome system status
```

**Output:**
- System information
- Health status
- Domain information
- Version details

### `ome system ping`

Ping the OME server.

```bash
ome system ping
```

**Output:**
- Server response time
- Connection status

### `ome system info`

Show OME system information.

```bash
ome system info
```

**Output:**
- System version
- Configuration details
- Runtime information

---

## Supply Tree Commands

**⚠️ Note**: Supply Tree Commands are not implemented in the current CLI version. These commands are documented for future reference but are not available for use.

### `ome supply-tree create`

Create a new supply tree from OKH manifest and OKW facility.

```bash
ome supply-tree create OKH_MANIFEST_ID OKW_FACILITY_ID [OPTIONS]
```

**Arguments:**
- `OKH_MANIFEST_ID` - UUID of the OKH manifest
- `OKW_FACILITY_ID` - UUID of the OKW facility

**Options:**
- `--context TEXT` - Validation context
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ome supply-tree get`

Get a supply tree by ID.

```bash
ome supply-tree get SUPPLY_TREE_ID
```

**Arguments:**
- `SUPPLY_TREE_ID` - UUID of the supply tree

### `ome supply-tree list`

List all supply trees.

```bash
ome supply-tree list [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip
- `--status TEXT` - Filter by status

### `ome supply-tree delete`

Delete a supply tree.

```bash
ome supply-tree delete SUPPLY_TREE_ID
```

**Arguments:**
- `SUPPLY_TREE_ID` - UUID of the supply tree

### `ome supply-tree validate`

Validate a supply tree.

```bash
ome supply-tree validate SUPPLY_TREE_ID [OPTIONS]
```

**Arguments:**
- `SUPPLY_TREE_ID` - UUID of the supply tree

**Options:**
- `--context TEXT` - Validation context
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

---

## Utility Commands

Utility operations for domains and contexts.

### `ome utility domains`

List available domains.

```bash
ome utility domains [OPTIONS]
```

**Options:**
- `--name TEXT` - Filter domains by name

**Output:**
- Domain IDs and names
- Domain descriptions
- Domain status

### `ome utility contexts`

List validation contexts for a specific domain.

```bash
ome utility contexts DOMAIN [OPTIONS]
```

**Arguments:**
- `DOMAIN` - Domain name (e.g., "manufacturing", "cooking")

**Options:**
- `--name TEXT` - Filter contexts by name

**Examples:**
```bash
# List contexts for manufacturing domain
ome utility contexts manufacturing

# List contexts for cooking domain
ome utility contexts cooking
```

---

## Output Formats

The CLI supports multiple output formats:

### Text Format (Default)
Human-readable text output with icons and formatting.

### JSON Format
```bash
ome --json package list-packages
```

### Table Format
```bash
ome --table system domains
```

### Verbose Mode
```bash
ome --verbose system health
```

Shows additional debugging information and connection details.

---

## Error Handling

The CLI provides clear error messages and handles various failure scenarios:

### Common Error Types

1. **Connection Errors**: When server is unavailable, CLI automatically falls back to direct service calls
2. **Validation Errors**: Clear messages for invalid input files or parameters with specific guidance
3. **File Not Found**: Helpful messages when files or packages don't exist with suggestions
4. **Permission Errors**: Clear indication of access issues with resolution steps
5. **API Format Errors**: Automatic handling of request/response format mismatches
6. **Domain Registration**: Automatic domain initialization in fallback mode

### Error Examples

```bash
# File not found with helpful suggestion
❌ Error: Package community/nonexistent:1.0.0 not found
   Suggestion: Use 'ome package list-packages' to see available packages

# Server connection failed (falls back to direct mode)
⚠️  Server unavailable, using direct service calls...
✅ Package built successfully

# Validation error with specific guidance
❌ Error: Invalid domain 'nonexistent-domain'. Valid domains are: manufacturing, cooking
   Suggestion: Use 'ome utility domains' to see available domains

# LLM configuration error
❌ Error: LLM provider 'invalid-provider' not supported
   Suggestion: Use one of: openai, anthropic, google, azure, local
```

---

## Best Practices

### 1. Use Verbose Mode for Debugging
```bash
ome --verbose package build manifest.json
```

### 2. Check System Health First
```bash
ome system health
```

### 3. Use JSON Output for Scripting
```bash
ome --json package list-packages | jq '.packages[].name'
```

### 4. Validate Before Building
```bash
ome okh validate manifest.json
ome package build manifest.json
```

### 5. Use Appropriate Quality Levels
```bash
# For development
ome okh validate manifest.json --quality-level hobby

# For production
ome okh validate manifest.json --quality-level medical --strict-mode

# With LLM enhancement
ome okh validate manifest.json --use-llm --quality-level professional --strict-mode
```

---

## Troubleshooting

### Common Issues

#### 1. Server Connection Issues
```bash
# Check if server is running
ome system health

# Try with different server URL
ome --server-url http://localhost:8000 system health
```

#### 2. Package Build Failures
```bash
# Check manifest validity first
ome okh validate manifest.json

# Use verbose mode for details
ome --verbose package build manifest.json
```

#### 3. File Download Issues
```bash
# Check network connectivity
ome system ping

# Use fallback mode if server issues
ome package build manifest.json
```

#### 4. Permission Issues
```bash
# Check file permissions
ls -la manifest.json

# Ensure write access to output directory
mkdir -p ./packages && chmod 755 ./packages
```

#### 5. Domain Registration Issues (Fixed)
```bash
# Domain registration is now automatic in fallback mode
# No manual intervention required
ome okh validate manifest.json
ome okw validate facility.json
```

#### 6. API Format Issues (Fixed)
```bash
# API format mismatches are now automatically handled
# Commands work seamlessly in both HTTP and fallback modes
ome okh upload manifest.json
ome okw upload facility.json
```

### Getting Help

```bash
# Get help for any command
ome [COMMAND] --help

# Get help for command groups
ome [GROUP] --help

# Get general help
ome --help
```

---

## Examples

### Complete Workflow Example

```bash
# 1. Check system health
ome system health

# 2. Validate a manifest (now works in both HTTP and fallback modes)
ome okh validate openflexure-microscope.okh.json

# 3. Build a package
ome package build openflexure-microscope.okh.json

# 4. Verify the package
ome package verify university-of-bath/openflexure-microscope 5.20

# 5. Push to remote storage
ome package push university-of-bath/openflexure-microscope 5.20

# 6. List remote packages
ome package list-remote

# 7. Work with OKW facilities (now fully functional)
ome okw validate facility.okw.json
ome okw create facility.okw.json
ome okw list-facilities

# 8. Perform matching operations (now fully functional)
ome match requirements openflexure-microscope.okh.json
ome match domains
```

### Batch Operations

```bash
# Build multiple packages
for manifest in *.okh.json; do
    ome package build "$manifest"
done

# List all packages in JSON format
ome --json package list-packages > packages.json
```

### Integration with Scripts

```bash
#!/bin/bash
# Check if package exists before building
if ! ome package verify "$PACKAGE_NAME" "$VERSION" 2>/dev/null; then
    echo "Building package $PACKAGE_NAME:$VERSION"
    ome package build "$MANIFEST_FILE"
else
    echo "Package $PACKAGE_NAME:$VERSION already exists"
fi
```

---

## API Integration

The CLI automatically detects whether to use HTTP API mode or fallback mode:

- **HTTP Mode**: When server is available, commands use REST API endpoints
- **Fallback Mode**: When server is unavailable, commands use direct service calls

Both modes provide the same functionality and output format.

---

## Version Information

```bash
# Get CLI version
ome version

# Get system information
ome system info
```

---

## Support

For additional help and support:

1. Check the help system: `ome [COMMAND] --help`
2. Use verbose mode for debugging: `ome --verbose [COMMAND]`
3. Review error messages for specific guidance
4. Check system health: `ome system health`

The OME CLI is designed to be intuitive and provide clear feedback for all operations.

---