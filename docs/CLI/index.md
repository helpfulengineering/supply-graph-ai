# Open Hardware Manager (OHM) CLI Documentation

## Overview

The Open Hardware Manager (OHM) Command Line Interface provides a set of tools for managing OKH packages, OKW facilities, matching operations, and system administration. The CLI supports both HTTP API mode (when connected to a server) and fallback mode (direct service calls).


## Documentation Structure

This directory contains documentation for the OHM CLI:

- **📖 [Main Documentation](index.md)** - Complete CLI reference with all commands, options, and examples
- **🚀 [Quick Start Guide](quick-start.md)** - Get up and running with the OHM CLI in 5 minutes
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
- OHM server running (optional, for HTTP mode)

### Basic Usage

```bash
# Activate the conda environment
conda activate supply-graph-ai

# Navigate to the project directory
cd supply-graph-ai

# Run the CLI
python ohm [COMMAND] [OPTIONS]
```

## Global Options

The OHM CLI supports several global options that apply to all commands:

```bash
ohm [GLOBAL_OPTIONS] [COMMAND] [COMMAND_OPTIONS]
```

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server-url TEXT` | OHM server URL | `http://localhost:8001` |
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
ohm --verbose system health

# Get JSON output
ohm --json package list-packages

# Set custom timeout
ohm --timeout 60 package build manifest.json

# Use LLM integration for enhanced analysis
ohm --use-llm --llm-provider anthropic --quality-level professional okh validate manifest.json

# Global LLM configuration
ohm --use-llm --quality-level medical --strict-mode system health
```

## Command Groups

The OHM CLI is organized into 7 main command groups with 53 total commands:

1. **[Match Commands](#match-commands)** - Requirements-to-capabilities matching and rules management
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

### `ohm package build`

Build an OKH package from a manifest file.

```bash
ohm package build MANIFEST_FILE [OPTIONS]
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
ohm package build openflexure-microscope.okh.json

# Build with LLM enhancement
ohm package build manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Build with custom options
ohm package build manifest.json --no-design-files --output-dir ./my-packages/
```

### `ohm package build-from-storage`

Build an OKH package from a stored manifest.

```bash
ohm package build-from-storage MANIFEST_ID [OPTIONS]
```

**Arguments:**
- `MANIFEST_ID` - UUID of the stored manifest

**Options:**
- `--output-dir TEXT` - Output directory for built package
- `--no-design-files` - Skip downloading design files
- `--no-manufacturing-files` - Skip downloading manufacturing files
- `--no-software` - Skip downloading software files

### `ohm package list-packages`

List all built packages.

```bash
ohm package list-packages
```

**Output:**
- Package name and version
- Local path
- File count and size
- Build timestamp

### `ohm package verify`

Verify a package's integrity.

```bash
ohm package verify PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

### `ohm package delete`

Delete a package.

```bash
ohm package delete PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

### `ohm package push`

Push a local package to remote storage.

```bash
ohm package push PACKAGE_NAME VERSION
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

**Examples:**
```bash
# Push a package to remote storage
ohm package push community/simple-test-project 1.0.0
```

### `ohm package pull`

Pull a remote package to local storage.

```bash
ohm package pull PACKAGE_NAME VERSION [OPTIONS]
```

**Arguments:**
- `PACKAGE_NAME` - Package name (e.g., "org/project")
- `VERSION` - Package version

**Options:**
- `--output-dir TEXT` - Output directory for pulled package

**Examples:**
```bash
# Pull a package from remote storage
ohm package pull community/simple-test-project 1.0.0

# Pull to specific directory
ohm package pull org/project 1.0.0 --output-dir ./my-packages/
```

### `ohm package list-remote`

List packages available in remote storage.

```bash
ohm package list-remote
```

**Output:**
- Remote package names and versions
- Package sizes
- Total count

---

## OKH Commands

Manage OpenKnowHow (OKH) manifests for hardware designs.

### `ohm okh validate`

Validate an OKH manifest with domain-aware validation support.

```bash
ohm okh validate MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--domain [manufacturing|cooking]` - Domain for validation (auto-detected from file if not provided)
- `--quality-level [hobby|professional|medical|home|commercial]` - Validation quality level
  - Manufacturing: `hobby`, `professional`, `medical`
  - Cooking: `home`, `commercial`, `professional`
- `--strict-mode` - Enable strict validation mode
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use

**Examples:**
```bash
# Validate manufacturing manifest (auto-detected)
ohm okh validate my-design.okh.json

# Validate cooking recipe with explicit domain
ohm okh validate recipe.json --domain cooking --quality-level home

# Validate with strict mode
ohm okh validate manifest.json --strict-mode --quality-level professional
```

### `ohm okh create`

Create and store an OKH manifest.

```bash
ohm okh create MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm okh get`

Get an OKH manifest by ID and display the full JSON to stdout.

```bash
ohm okh get MANIFEST_ID [OPTIONS]
```

**Arguments:**
- `MANIFEST_ID` - UUID of the manifest

**Options:**
- `--output, -o PATH` - Save manifest to file instead of stdout
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level TEXT` - Quality level for LLM processing
- `--strict-mode` - Enable strict validation mode
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Get manifest and display to stdout
ohm okh get 8f14e3c4-09f2-4a5e-8bd9-4b5bb5d0a9cd

# Get manifest and save to file
ohm okh get 8f14e3c4-09f2-4a5e-8bd9-4b5bb5d0a9cd --output manifest.json

# Pipe to another command
ohm okh get 8f14e3c4-09f2-4a5e-8bd9-4b5bb5d0a9cd | jq '.title'
```

**Output:**
The command outputs the complete manifest JSON to stdout by default, making it easy to pipe to other commands or save to files.

### `ohm okh list-manifests`

List stored OKH manifests with detailed information.

```bash
ohm okh list-manifests [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results (default: 10)
- `--offset INTEGER` - Number of results to skip (default: 0)
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level TEXT` - Quality level for LLM processing
- `--strict-mode` - Enable strict validation mode
- `--verbose, -v` - Enable verbose output

**Output:**
The command displays a numbered list of manifests with:
- Manifest title (name)
- Manifest ID (UUID)
- Version
- Organization name

**Examples:**
```bash
# List all manifests
ohm okh list-manifests

# List with pagination
ohm okh list-manifests --limit 20 --offset 10

# List in JSON format
ohm okh list-manifests --json
```

**Example Output:**
```
📄 Found 1 OKH manifest(s):

  1. Chocolate Chip Cookies
     Manifest ID: 8f14e3c4-09f2-4a5e-8bd9-4b5bb5d0a9cd
     Version: 0.0.1 | Organization: Helpful Engineering, non-profit

Total: 1 manifest(s)
```

### `ohm okh delete`

Delete an OKH manifest.

```bash
ohm okh delete MANIFEST_ID
```

**Arguments:**
- `MANIFEST_ID` - UUID of the manifest

### `ohm okh fix`

Automatically fix validation issues in an OKH manifest.

```bash
ohm okh fix MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--output, -o PATH` - Output file path (default: overwrites input file)
- `--dry-run` - Preview fixes without applying them
- `--backup` - Create backup of original file before fixing
- `--confidence-threshold FLOAT` - Minimum confidence for auto-applying fixes (0.0-1.0, default: 0.5)
- `--domain [manufacturing|cooking]` - Domain for validation (auto-detected if not provided)
- `--yes` - Auto-confirm all fixes without prompting
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level TEXT` - Quality level for validation
- `--strict-mode` - Enable strict validation mode
- `--verbose, -v` - Enable verbose output with detailed fix report

**Examples:**
```bash
# Fix manifest issues interactively
ohm okh fix manifest.json

# Preview fixes without applying
ohm okh fix manifest.json --dry-run

# Fix with backup and auto-confirm
ohm okh fix manifest.json --backup --yes

# Fix with custom confidence threshold
ohm okh fix manifest.json --confidence-threshold 0.7

# Fix cooking domain recipe
ohm okh fix recipe.json --domain cooking
```

**Output:**
The command displays a detailed fix report including:
- Number of fixes applied and skipped
- Original and remaining warnings/errors
- Status: complete success, partial success, or failure
- Detailed list of all fixes (when verbose)

### `ohm okh extract`

Extract requirements from an OKH manifest.

```bash
ohm okh extract MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Extraction quality level
- `--strict-mode` - Enable strict extraction mode

### `ohm okh upload`

Upload and validate an OKH manifest file.

```bash
ohm okh upload MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm okh scaffold`

Generate an OKH-compliant project scaffold with documentation stubs and manifest template.

```bash
ohm okh scaffold PROJECT_NAME [OPTIONS]
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
ohm okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ohm okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with custom organization
ohm okh scaffold microscope-stage --organization "University Lab" --output-format filesystem --output-path ./projects

# Generate minimal scaffold for experienced developers
ohm okh scaffold quick-prototype --template-level minimal --output-format json
```

### `ohm okh scaffold-cleanup`

Clean and optimize a scaffolded OKH project directory by removing unmodified documentation stubs and empty directories.

```bash
ohm okh scaffold-cleanup PROJECT_PATH [OPTIONS]
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
- **Empty Directory Cleanup**: Removes directories that becohm empty after file cleanup

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
ohm okh scaffold-cleanup ./projects/my-hardware-project

# Apply cleanup to remove unmodified stubs and empty directories
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply

# Apply cleanup but keep empty directories
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-empty-directories

# Keep unmodified stubs but remove empty directories
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-unmodified-stubs
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

### `ohm okh export`

Export the JSON schema for the OKH (OpenKnowHow) domain model.

```bash
ohm okh export [OPTIONS]
```

**Description:**
This command generates and exports the JSON schema for the OKHManifest dataclass in canonical JSON Schema format (draft-07). The schema represents the complete structure of the OKH domain model including all fields, types, and constraints.

The exported schema can be used for:
- Validation of OKH manifests
- Documentation generation
- API contract specification
- Integration with other systems

**Options:**
- `--output, -o PATH` - Output file path for the JSON schema
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Export schema to console
ohm okh export

# Export schema to file
ohm okh export --output okh-schema.json

# Export with JSON output format
ohm okh export --output okh-schema.json --json
```

---

## OKW Commands

Manage OpenKnowWhere (OKW) facilities for manufacturing capabilities.

### `ohm okw validate`

Validate an OKW facility.

```bash
ohm okw validate FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm okw create`

Create and store an OKW facility.

```bash
ohm okw create FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm okw get`

Get an OKW facility by ID and display the full JSON to stdout.

```bash
ohm okw get FACILITY_ID [OPTIONS]
```

**Arguments:**
- `FACILITY_ID` - UUID of the facility (full UUID required)

**Options:**
- `--output, -o PATH` - Save facility to file instead of stdout
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level TEXT` - Quality level for LLM processing
- `--strict-mode` - Enable strict validation mode
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Get facility and display to stdout
ohm okw get 550e8400-e29b-41d4-a716-446655440001

# Get facility and save to file
ohm okw get 550e8400-e29b-41d4-a716-446655440001 --output facility.json

# Pipe to another command
ohm okw get 550e8400-e29b-41d4-a716-446655440001 | jq '.name'
```

**Output:**
The command outputs the complete facility JSON to stdout by default, making it easy to pipe to other commands or save to files.

**Note:** The facility ID must be the full UUID. Use `ohm okw list-files` to find facility IDs.

### `ohm okw list-files`

List OKW files in Azure blob storage with facility IDs.

```bash
ohm okw list-files [OPTIONS]
```

**Options:**
- `--prefix TEXT` - Filter by prefix (default: `okw/`)
- `--output, -o PATH` - Save list to file (JSON format)
- `--format [json|text]` - Output format (default: `text`)
- `--verbose, -v` - Enable verbose output

**Output:**
The command displays a numbered list of OKW files with:
- File key (storage path)
- Facility ID (UUID) - required for `ohm okw get` command
- File size (in KB)
- Last modified date

**Examples:**
```bash
# List all OKW files
ohm okw list-files

# List files with specific prefix
ohm okw list-files --prefix okw/facilities/

# Save list to JSON file
ohm okw list-files --output files.json --format json
```

**Example Output:**
```
📁 Found 4 OKW file(s):

  1. okw/RobDessertKitchen.json
     Facility ID: 550e8400-e29b-41d4-a716-446655440001
     Size: 2.4 KB | Modified: 2025-11-13 23:35:39+00:00

Total: 4 file(s)
```

### `ohm okw list-facilities`

List stored OKW facilities.

```bash
ohm okw list-facilities [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip

### `ohm okw delete`

Delete an OKW facility.

```bash
ohm okw delete FACILITY_ID
```

**Arguments:**
- `FACILITY_ID` - UUID of the facility

### `ohm okw fix`

Automatically fix validation issues in an OKW facility.

```bash
ohm okw fix FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--output, -o PATH` - Output file path (default: overwrites input file)
- `--dry-run` - Preview fixes without applying them
- `--backup` - Create backup of original file before fixing
- `--confidence-threshold FLOAT` - Minimum confidence for auto-applying fixes (0.0-1.0, default: 0.5)
- `--domain [manufacturing|cooking]` - Domain for validation (auto-detected if not provided)
- `--yes` - Auto-confirm all fixes without prompting
- `--use-llm` - Enable LLM integration for enhanced analysis
- `--llm-provider TEXT` - LLM provider (openai, anthropic, google, azure, local)
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level TEXT` - Quality level for validation
- `--strict-mode` - Enable strict validation mode
- `--verbose, -v` - Enable verbose output with detailed fix report

**Examples:**
```bash
# Fix facility issues interactively
ohm okw fix facility.json

# Preview fixes without applying
ohm okw fix facility.json --dry-run

# Fix with backup and auto-confirm
ohm okw fix facility.json --backup --yes

# Fix with custom confidence threshold
ohm okw fix facility.json --confidence-threshold 0.7

# Fix cooking domain kitchen
ohm okw fix kitchen.json --domain cooking
```

**Output:**
The command displays a detailed fix report including:
- Number of fixes applied and skipped
- Original and remaining warnings/errors
- Status: complete success, partial success, or failure
- Detailed list of all remaining issues (when verbose)

### `ohm okw extract-capabilities`

Extract capabilities from an OKW facility.

```bash
ohm okw extract-capabilities FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Extraction quality level
- `--strict-mode` - Enable strict extraction mode

### `ohm okw upload`

Upload and validate an OKW facility file.

```bash
ohm okw upload FACILITY_FILE [OPTIONS]
```

**Arguments:**
- `FACILITY_FILE` - Path to OKW facility file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm okw search`

Search OKW facilities.

```bash
ohm okw search [OPTIONS]
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
ohm okw search --capability "3d-printing"

# Search for facilities in a specific location
ohm okw search --location "San Francisco"
```

### `ohm okw export`

Export the JSON schema for the OKW (OpenKnowWhere) domain model.

```bash
ohm okw export [OPTIONS]
```

**Description:**
This command generates and exports the JSON schema for the ManufacturingFacility dataclass in canonical JSON Schema format (draft-07). The schema represents the complete structure of the OKW domain model including all fields, types, and constraints.

The exported schema can be used for:
- Validation of OKW facilities
- Documentation generation
- API contract specification
- Integration with other systems

**Options:**
- `--output, -o PATH` - Output file path for the JSON schema
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Export schema to console
ohm okw export

# Export schema to file
ohm okw export --output okw-schema.json

# Export with JSON output format
ohm okw export --output okw-schema.json --json
```

---

## Match Commands

Perform matching operations between requirements and capabilities across multiple domains. Supports both **manufacturing domain** (OKH/OKW) and **cooking domain** (recipe/kitchen).

### `ohm match requirements`

Match requirements to capabilities across multiple domains. Supports both **manufacturing domain** (OKH/OKW) and **cooking domain** (recipe/kitchen).

```bash
ohm match requirements INPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input file:
  - **Manufacturing**: OKH manifest file (JSON or YAML)
  - **Cooking**: Recipe file (JSON or YAML)

**Domain Detection:**
The command automatically detects the domain from the input file structure:
- **Manufacturing**: Detected from OKH manifest structure (presence of `title`, `version`, `manufacturing_specs`)
- **Cooking**: Detected from recipe structure (presence of `ingredients`, `instructions`, `name`)

You can also explicitly specify the domain using the `--domain` option.

**Options:**
- `--domain [manufacturing|cooking]` - Explicit domain override. Auto-detected if not provided
- `--facility-file PATH` - Path to local facility file (cooking domain only, forces fallback mode)
- `--access-type [public|private|restricted]` - Filter by facility access type
- `--facility-status [active|inactive|maintenance]` - Filter by facility status
- `--location TEXT` - Filter by location (city, country, or region)
- `--capabilities TEXT` - Comma-separated list of required capabilities
- `--materials TEXT` - Comma-separated list of required materials
- `--min-confidence FLOAT` - Minimum confidence threshold (0.0-1.0, default: 0.7)
- `--max-results INTEGER` - Maximum number of results (default: 10)
- `--output, -o TEXT` - Output file path
- `--use-llm` - Enable LLM integration for enhanced matching
- `--llm-provider [anthropic|openai|google|azure|local]` - LLM provider
- `--llm-model TEXT` - Specific LLM model to use
- `--quality-level [hobby|professional|medical]` - Quality level for LLM processing
- `--strict-mode` - Enable strict validation mode
- `--json` - Output results in JSON format
- `--table` - Output results in table format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Match OKH requirements (manufacturing domain)
ohm match requirements my-design.okh.json

# Match recipe requirements (cooking domain)
ohm match requirements chocolate-chip-cookies-recipe.json

# Match with explicit domain override
ohm match requirements input.json --domain cooking

# Match with local facility file (cooking domain)
ohm match requirements recipe.json --domain cooking --facility-file kitchen.json

# Match with location filter
ohm match requirements my-design.okh.json --location "San Francisco"

# Match with high confidence threshold
ohm match requirements my-design.okh.json --min-confidence 0.9

# Match with LLM enhancement
ohm match requirements my-design.okh.json --use-llm --quality-level professional

# Save results to file
ohm match requirements my-design.okh.json --output matches.json
```

**Output:**
The command displays matching facilities with:
- Facility name
- **Full facility ID (UUID)** - required for `ohm okw get` command
- Confidence score
- Match type (manufacturing or cooking)
- Location (if available)

**Note:** Facility IDs are displayed as full UUIDs. Use the full ID with `ohm okw get` to retrieve facility details.

### `ohm match validate`

Validate a match result.

```bash
ohm match validate MATCH_FILE [OPTIONS]
```

**Arguments:**
- `MATCH_FILE` - Path to match result file

**Options:**
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm match from-file`

Match from file upload.

```bash
ohm match from-file MANIFEST_FILE [OPTIONS]
```

**Arguments:**
- `MANIFEST_FILE` - Path to OKH manifest file

**Options:**
- `--facility-id TEXT` - Specific facility ID to match against
- `--domain TEXT` - Domain for matching
- `--context TEXT` - Validation context

### `ohm match list-recent`

List recent matches.

```bash
ohm match list-recent [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip

### Rules Management Commands

Manage capability-centric heuristic matching rules. These commands allow you to inspect, modify, import, export, and validate the rules used for matching requirements to capabilities.

**Base Command:** `ohm match rules`

#### `ohm match rules list`

List all matching rules, optionally filtered by domain or tag.

```bash
ohm match rules list [OPTIONS]
```

**Options:**
- `--domain TEXT` - Filter rules by domain (e.g., "manufacturing", "cooking")
- `--tag TEXT` - Filter rules by tag
- `--include-metadata` - Include creation/update timestamps in output
- `--json` - Output in JSON format
- `--table` - Output in table format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# List all rules
ohm match rules list

# List rules for a specific domain
ohm match rules list --domain cooking

# List rules with a specific tag
ohm match rules list --tag "technique"

# List rules with metadata
ohm match rules list --include-metadata --json
```

#### `ohm match rules get`

Get a specific rule by domain and ID.

```bash
ohm match rules get DOMAIN RULE_ID [OPTIONS]
```

**Arguments:**
- `DOMAIN` - Domain name (e.g., "manufacturing", "cooking")
- `RULE_ID` - Rule identifier

**Options:**
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Get a specific rule
ohm match rules get cooking sauté_capability

# Get rule in JSON format
ohm match rules get manufacturing cnc_machining_capability --json
```

#### `ohm match rules create`

Create a new rule from file or interactively.

```bash
ohm match rules create [OPTIONS]
```

**Options:**
- `--file PATH` - Path to rule file (YAML or JSON)
- `--interactive, -i` - Interactive mode (prompts for rule fields)
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Create rule from file
ohm match rules create --file rule.yaml

# Create rule interactively
ohm match rules create --interactive

# Create rule from file with JSON output
ohm match rules create --file rule.json --json
```

**Interactive Mode:**
When using `--interactive`, the command will prompt for:
- Rule ID
- Capability
- Requirements (one per line, empty line to finish)
- Confidence (0.0-1.0)
- Domain
- Description
- Tags (comma-separated)

#### `ohm match rules update`

Update an existing rule from file or interactively.

```bash
ohm match rules update DOMAIN RULE_ID [OPTIONS]
```

**Arguments:**
- `DOMAIN` - Domain name
- `RULE_ID` - Rule identifier

**Options:**
- `--file PATH` - Path to updated rule file (YAML or JSON)
- `--interactive, -i` - Interactive mode (prompts for rule fields)
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Update rule from file
ohm match rules update cooking sauté_capability --file updated_rule.yaml

# Update rule interactively
ohm match rules update manufacturing cnc_machining_capability --interactive
```

**Interactive Mode:**
Interactive mode shows current values and allows you to update them. Press Enter to keep existing values.

#### `ohm match rules delete`

Delete a rule.

```bash
ohm match rules delete DOMAIN RULE_ID [OPTIONS]
```

**Arguments:**
- `DOMAIN` - Domain name
- `RULE_ID` - Rule identifier

**Options:**
- `--confirm` - Skip confirmation prompt
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Delete a rule (with confirmation prompt)
ohm match rules delete cooking sauté_capability

# Delete a rule without confirmation
ohm match rules delete manufacturing cnc_machining_capability --confirm
```

#### `ohm match rules import`

Import rules from YAML or JSON file.

```bash
ohm match rules import FILE [OPTIONS]
```

**Arguments:**
- `FILE` - Path to rule file (YAML or JSON)

**Options:**
- `--domain TEXT` - Target domain (if importing single domain)
- `--partial-update` - Allow partial updates (default: true)
- `--no-partial-update` - Disable partial updates
- `--dry-run` - Validate without applying changes
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Import rules from file
ohm match rules import rules.yaml

# Import rules with dry-run (preview changes)
ohm match rules import rules.yaml --dry-run

# Import rules for specific domain
ohm match rules import rules.yaml --domain manufacturing

# Import rules without partial updates
ohm match rules import rules.yaml --no-partial-update
```

#### `ohm match rules export`

Export rules to YAML or JSON file.

```bash
ohm match rules export OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `OUTPUT_FILE` - Path to output file

**Options:**
- `--domain TEXT` - Export specific domain (all if not specified)
- `--format [yaml|json]` - Export format (default: yaml)
- `--include-metadata` - Include creation/update timestamps
- `--json` - Output metadata in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Export all rules to YAML
ohm match rules export rules.yaml

# Export rules to JSON
ohm match rules export rules.json --format json

# Export specific domain
ohm match rules export cooking_rules.yaml --domain cooking

# Export with metadata
ohm match rules export rules.yaml --include-metadata
```

#### `ohm match rules validate`

Validate rule file without importing.

```bash
ohm match rules validate FILE [OPTIONS]
```

**Arguments:**
- `FILE` - Path to rule file (YAML or JSON)

**Options:**
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Validate rule file
ohm match rules validate rules.yaml

# Validate rule file with JSON output
ohm match rules validate rules.json --json
```

**Output:**
The command displays validation results:
- `valid`: Whether the file is valid
- `errors`: List of validation errors (if any)
- `warnings`: List of validation warnings (if any)

#### `ohm match rules compare`

Compare rules file with current rules (dry-run import).

```bash
ohm match rules compare FILE [OPTIONS]
```

**Arguments:**
- `FILE` - Path to rule file (YAML or JSON)

**Options:**
- `--domain TEXT` - Compare specific domain
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Compare rules file with current rules
ohm match rules compare rules.yaml

# Compare rules for specific domain
ohm match rules compare rules.yaml --domain manufacturing

# Compare with JSON output
ohm match rules compare rules.yaml --json
```

**Output:**
The command displays comparison results:
- `added`: Rules that would be added
- `updated`: Rules that would be updated
- `deleted`: Rules that would be deleted
- Summary counts for each category

#### `ohm match rules reset`

Reset all rules (clear all rule sets).

```bash
ohm match rules reset [OPTIONS]
```

**Options:**
- `--confirm` - Skip confirmation prompt
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Reset all rules (with confirmation prompt)
ohm match rules reset

# Reset all rules without confirmation
ohm match rules reset --confirm
```

**Warning:** This command permanently deletes all rules. Use with caution.

---

## LLM Commands

Manage LLM operations and AI features for enhanced OKH manifest generation and facility matching.

### `ohm llm generate`

Generate content using the LLM service.

```bash
ohm llm generate PROMPT [OPTIONS]
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
ohm llm generate "Analyze this hardware project and generate an OKH manifest"

# With specific provider and model
ohm llm generate "Generate OKH manifest" \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Save to file with JSON format
ohm llm generate "Analyze project" \
  --output manifest.json \
  --format json
```

### `ohm llm generate-okh`

Generate an OKH manifest for a hardware project.

```bash
ohm llm generate-okh PROJECT_URL [OPTIONS]
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
ohm llm generate-okh https://github.com/example/iot-sensor

# With specific provider
ohm llm generate-okh https://github.com/example/project \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Clone repository for better analysis
ohm llm generate-okh https://github.com/example/project \
  --clone \
  --preserve-context
```

### `ohm llm match`

Use LLM to enhance facility matching.

```bash
ohm llm match REQUIREMENTS_FILE FACILITIES_FILE [OPTIONS]
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
ohm llm match requirements.json facilities.json

# With confidence threshold
ohm llm match requirements.json facilities.json \
  --min-confidence 0.7 \
  --output matches.json

# Table format output
ohm llm match requirements.json facilities.json \
  --format table \
  --min-confidence 0.6
```

### `ohm llm analyze`

Analyze a hardware project and extract information.

```bash
ohm llm analyze PROJECT_URL [OPTIONS]
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
ohm llm analyze https://github.com/example/project

# Comprehensive analysis
ohm llm analyze https://github.com/example/project \
  --include-code \
  --include-docs \
  --output analysis.json \
  --format json

# Markdown report
ohm llm analyze https://github.com/example/project \
  --output report.md \
  --format markdown
```

### `ohm llm providers`

Manage LLM providers and configuration.

```bash
ohm llm providers [COMMAND]
```

**Subcommands:**
- `list` - List available providers
- `status` - Show provider status
- `set` - Set active provider
- `test` - Test provider connection

**Examples:**
```bash
# List all providers
ohm llm providers list

# Show provider status
ohm llm providers status

# Set active provider
ohm llm providers set anthropic

# Test provider connection
ohm llm providers test anthropic
```

### `ohm llm service`

Manage LLM service and metrics.

```bash
ohm llm service [COMMAND]
```

**Subcommands:**
- `status` - Show service status
- `metrics` - Show usage metrics
- `health` - Check service health
- `reset` - Reset service state

**Examples:**
```bash
# Show service status
ohm llm service status

# Show usage metrics
ohm llm service metrics

# Check health
ohm llm service health

# Reset service
ohm llm service reset
```

---

## System Commands

System administration and monitoring commands. 

### `ohm system health`

Check system health and status.

```bash
ohm system health
```

**Output:**
- System status (ok/error)
- Version information
- Mode (HTTP/fallback)
- Registered domains

### `ohm system domains`

List available domains and their status.

```bash
ohm system domains
```

**Output:**
- Domain IDs and names
- Domain descriptions
- Domain status

### `ohm system status`

Show detailed system status.

```bash
ohm system status
```

**Output:**
- System information
- Health status
- Domain information
- Version details

### `ohm system ping`

Ping the OHM server.

```bash
ohm system ping
```

**Output:**
- Server response time
- Connection status

### `ohm system info`

Show OHM system information.

```bash
ohm system info
```

**Output:**
- System version
- Configuration details
- Runtime information

---

## Supply Tree Commands

**⚠️ Note**: Supply Tree Commands are not implemented in the current CLI version. These commands are documented for future reference but are not available for use.

### `ohm supply-tree create`

Create a new supply tree from OKH manifest and OKW facility.

```bash
ohm supply-tree create OKH_MANIFEST_ID OKW_FACILITY_ID [OPTIONS]
```

**Arguments:**
- `OKH_MANIFEST_ID` - UUID of the OKH manifest
- `OKW_FACILITY_ID` - UUID of the OKW facility

**Options:**
- `--context TEXT` - Validation context
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

### `ohm supply-tree get`

Get a supply tree by ID.

```bash
ohm supply-tree get SUPPLY_TREE_ID
```

**Arguments:**
- `SUPPLY_TREE_ID` - UUID of the supply tree

### `ohm supply-tree list`

List all supply trees.

```bash
ohm supply-tree list [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Maximum number of results
- `--offset INTEGER` - Number of results to skip
- `--status TEXT` - Filter by status

### `ohm supply-tree delete`

Delete a supply tree.

```bash
ohm supply-tree delete SUPPLY_TREE_ID
```

**Arguments:**
- `SUPPLY_TREE_ID` - UUID of the supply tree

### `ohm supply-tree validate`

Validate a supply tree.

```bash
ohm supply-tree validate SUPPLY_TREE_ID [OPTIONS]
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

### `ohm utility domains`

List available domains.

```bash
ohm utility domains [OPTIONS]
```

**Options:**
- `--name TEXT` - Filter domains by name

**Output:**
- Domain IDs and names
- Domain descriptions
- Domain status

### `ohm utility contexts`

List validation contexts for a specific domain.

```bash
ohm utility contexts DOMAIN [OPTIONS]
```

**Arguments:**
- `DOMAIN` - Domain name (e.g., "manufacturing", "cooking")

**Options:**
- `--name TEXT` - Filter contexts by name

**Examples:**
```bash
# List contexts for manufacturing domain
ohm utility contexts manufacturing

# List contexts for cooking domain
ohm utility contexts cooking
```

### `ohm utility metrics`

Get system metrics including request tracking, performance, and LLM usage.

```bash
ohm utility metrics [OPTIONS]
```

**Description:**
This command provides access to the MetricsTracker data, including:
- Overall request statistics
- Endpoint-level metrics with processing times
- Error summaries
- Performance metrics
- LLM usage and costs

**Options:**
- `--endpoint TEXT` - Filter metrics by endpoint (format: "METHOD /path")
- `--summary / --no-summary` - Show summary only (default: True)
- `--json` - Output in JSON format
- `--verbose, -v` - Enable verbose output

**Examples:**
```bash
# Get overall metrics summary
ohm utility metrics

# Get detailed metrics with all endpoints
ohm utility metrics --no-summary

# Get metrics for a specific endpoint
ohm utility metrics --endpoint "GET /health"

# Get metrics for a specific API endpoint
ohm utility metrics --endpoint "POST /v1/api/match"

# Output in JSON format
ohm utility metrics --json
```

**Output:**
The command displays:
- Total requests and recent activity
- Endpoint-level statistics (requests, success rate, processing times)
- Error summaries
- Performance metrics
- LLM usage and costs (if applicable)

**Note:** Metrics are only available when connected to the API server. The command will show an error if the server is not accessible.

---

## Output Formats

The CLI supports multiple output formats:

### Text Format (Default)
Human-readable text output with icons and formatting.

### JSON Format
```bash
ohm --json package list-packages
```

### Table Format
```bash
ohm --table system domains
```

### Verbose Mode
```bash
ohm --verbose system health
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
   Suggestion: Use 'ohm package list-packages' to see available packages

# Server connection failed (falls back to direct mode)
⚠️  Server unavailable, using direct service calls...
✅ Package built successfully

# Validation error with specific guidance
❌ Error: Invalid domain 'nonexistent-domain'. Valid domains are: manufacturing, cooking
   Suggestion: Use 'ohm utility domains' to see available domains

# LLM configuration error
❌ Error: LLM provider 'invalid-provider' not supported
   Suggestion: Use one of: openai, anthropic, google, azure, local
```

---

## Best Practices

### Rules Management

When working with matching rules, follow these best practices:

- **Always validate before importing**: Use `ohm match rules validate` to check rule files before importing them
- **Use compare to preview changes**: Use `ohm match rules compare` to see what changes will be made before importing
- **Export rules as backup**: Export rules before making major changes using `ohm match rules export`
- **Use interactive mode for complex rules**: Use `--interactive` flag when creating or updating rules to ensure all fields are properly set
- **Test with dry-run**: Use `--dry-run` flag when importing to preview changes without applying them
- **Version control rule files**: Keep rule files in version control to track changes over time
- **Document rule changes**: Add descriptions to rules explaining their purpose and when they should be used

## Best Practices

### 1. Use Verbose Mode for Debugging
```bash
ohm --verbose package build manifest.json
```

### 2. Check System Health First
```bash
ohm system health
```

### 3. Use JSON Output for Scripting
```bash
ohm --json package list-packages | jq '.packages[].name'
```

### 4. Validate Before Building
```bash
ohm okh validate manifest.json
ohm package build manifest.json
```

### 5. Use Appropriate Quality Levels
```bash
# For development
ohm okh validate manifest.json --quality-level hobby

# For production
ohm okh validate manifest.json --quality-level medical --strict-mode

# With LLM enhancement
ohm okh validate manifest.json --use-llm --quality-level professional --strict-mode
```

---

## Troubleshooting

### Common Issues

#### 1. Server Connection Issues
```bash
# Check if server is running
ohm system health

# Try with different server URL
ohm --server-url http://localhost:8001 system health
```

#### 2. Package Build Failures
```bash
# Check manifest validity first
ohm okh validate manifest.json

# Use verbose mode for details
ohm --verbose package build manifest.json
```

#### 3. File Download Issues
```bash
# Check network connectivity
ohm system ping

# Use fallback mode if server issues
ohm package build manifest.json
```

#### 4. Permission Issues
```bash
# Check file permissions
ls -la manifest.json

# Ensure write access to output directory
mkdir -p ./packages && chmod 755 ./packages
```


### Getting Help

```bash
# Get help for any command
ohm [COMMAND] --help

# Get help for command groups
ohm [GROUP] --help

# Get general help
ohm --help
```

---

## Examples

### Complete Workflow Example

```bash
# 1. Check system health
ohm system health

# 2. Validate a manifest (now works in both HTTP and fallback modes)
ohm okh validate openflexure-microscope.okh.json

# 3. Build a package
ohm package build openflexure-microscope.okh.json

# 4. Verify the package
ohm package verify university-of-bath/openflexure-microscope 5.20

# 5. Push to remote storage
ohm package push university-of-bath/openflexure-microscope 5.20

# 6. List remote packages
ohm package list-remote

# 7. Work with OKW facilities (now fully functional)
ohm okw validate facility.okw.json
ohm okw create facility.okw.json
ohm okw list-facilities

# 8. Perform matching operations (now fully functional)
ohm match requirements openflexure-microscope.okh.json
ohm match domains
```

### Batch Operations

```bash
# Build multiple packages
for manifest in *.okh.json; do
    ohm package build "$manifest"
done

# List all packages in JSON format
ohm --json package list-packages > packages.json
```

### Integration with Scripts

```bash
#!/bin/bash
# Check if package exists before building
if ! ohm package verify "$PACKAGE_NAME" "$VERSION" 2>/dev/null; then
    echo "Building package $PACKAGE_NAME:$VERSION"
    ohm package build "$MANIFEST_FILE"
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
ohm version

# Get system information
ohm system info
```

---

## Support

For additional help and support:

1. Check the help system: `ohm [COMMAND] --help`
2. Use verbose mode for debugging: `ohm --verbose [COMMAND]`
3. Review error messages for specific guidance
4. Check system health: `ohm system health`

The OHM CLI is designed to be intuitive and provide clear feedback for all operations.

---