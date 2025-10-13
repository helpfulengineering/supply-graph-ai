# Open Matching Engine (OME) CLI Documentation

## Overview

The Open Matching Engine (OME) Command Line Interface provides a set of tools for managing OKH packages, OKW facilities, matching operations, and system administration. The CLI supports both HTTP API mode (when connected to a server) and fallback mode (direct service calls).

## Documentation Structure

This directory contains comprehensive documentation for the OME CLI:

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
cd /path/to/supply-graph-ai

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
| `-v, --verbose` | Enable verbose output | `False` |
| `--json` | Output in JSON format | `False` |
| `--table` | Output in table format | `False` |
| `--help` | Show help message | - |

### Examples

```bash
# Use verbose mode
ome --verbose system health

# Get JSON output
ome --json package list-packages

# Set custom timeout
ome --timeout 60 package build manifest.json
```

## Command Groups

The OME CLI is organized into 7 main command groups:

1. **[Package Commands](#package-commands)** - OKH package management
2. **[OKH Commands](#okh-commands)** - OpenKnowHow manifest management
3. **[OKW Commands](#okw-commands)** - OpenKnowWhere facility management
4. **[Match Commands](#match-commands)** - Matching operations
5. **[System Commands](#system-commands)** - System administration
6. **[Supply Tree Commands](#supply-tree-commands)** - Supply tree management
7. **[Utility Commands](#utility-commands)** - Utility operations

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

**Examples:**
```bash
# Build a package from manifest
ome package build openflexure-microscope.okh.json

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
- `--quality-level [basic\|standard\|premium]` - Validation quality level
- `--strict-mode` - Enable strict validation mode

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
- Comprehensive system information
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

Manage supply trees for manufacturing solutions.

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

1. **Connection Errors**: When server is unavailable, CLI falls back to direct service calls
2. **Validation Errors**: Clear messages for invalid input files or parameters
3. **File Not Found**: Helpful messages when files or packages don't exist
4. **Permission Errors**: Clear indication of access issues

### Error Examples

```bash
# File not found
Error: Package community/nonexistent:1.0.0 not found

# Server connection failed (falls back to direct mode)
ℹ️  Server unavailable, using direct mode
✅ Package built successfully

# Validation error
Error: Invalid manifest: Missing required field 'title'
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
ome okh validate manifest.json --quality-level basic

# For production
ome okh validate manifest.json --quality-level premium --strict-mode
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

# 2. Validate a manifest
ome okh validate openflexure-microscope.okh.json

# 3. Build a package
ome package build openflexure-microscope.okh.json

# 4. Verify the package
ome package verify university-of-bath/openflexure-microscope 5.20

# 5. Push to remote storage
ome package push university-of-bath/openflexure-microscope 5.20

# 6. List remote packages
ome package list-remote
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

## Documentation Status

✅ **Complete**: All 39 CLI commands documented  
✅ **Tested**: All examples verified working  
✅ **Current**: Documentation matches implementation  

The OME CLI documentation is comprehensive and ready for production use.

## Contributing

To contribute to the CLI documentation:

1. Follow the existing documentation structure
2. Include practical examples
3. Test all code examples
4. Update the table of contents when adding new sections
