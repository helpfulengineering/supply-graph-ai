# OHM CLI Quick Start Guide

## Getting Started in 5 Minutes


### 1. Prerequisites

```bash
# Activate the conda environment
conda activate supply-graph-ai

# Navigate to the project directory
cd /path/to/supply-graph-ai
```

### 2. Check System Health

```bash
# Verify the CLI is working
ohm system health
```

Expected output:
```
ℹ️  Starting system-health command
ℹ️  Attempting to connect to server...
ℹ️  Checking health via HTTP API...
✅ Connected to server successfully
✅ System is healthy
ℹ️  Status: ok
ℹ️  Version: 1.0.0
ℹ️  Mode: unknown
ℹ️  Registered domains: cooking, manufacturing
✅ Command system-health completed in 0.08 seconds
```

### 3. List Available Commands

```bash
# See all available command groups
ohm --help

# See commands in a specific group
ohm package --help
```

### 4. Generate Your First Project Scaffold

```bash
# Generate a new OKH-compliant project structure
ohm okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ohm okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with custom organization
ohm okh scaffold microscope-stage --organization "My Lab" --output-format filesystem --output-path ./projects

# Generate minimal scaffold for quick prototyping
ohm okh scaffold quick-prototype --template-level minimal --output-format json
```

**Output Formats:**
- `json`: Returns structured JSON (default, great for scripting)
- `zip`: Creates downloadable ZIP archive
- `filesystem`: Writes directly to specified directory

**Template Levels:**
- `minimal`: Basic placeholders for experienced developers (no cross-references)
- `standard`: Detailed guidance with examples and cross-references (default)
- `detailed`: Comprehensive help with grouped cross-references and best practices

**Documentation Linking:**
The scaffold includes comprehensive interlinking between documentation sections:
- **Bi-directional Links**: All section directories link back to `docs/index.md`, and `docs/index.md` links to all sections
- **Cross-References**: Documentation pages (assembly, manufacturing, maintenance, etc.) include links to related sections
- **MkDocs Navigation**: Bridge pages in `docs/sections/` enable full MkDocs navigation while preserving OKH structure

### 4.5. Clean Up a Scaffolded Project

```bash
# Preview cleanup (dry-run)
ohm okh scaffold-cleanup ./projects/my-awesome-project

# Apply cleanup (remove unmodified stubs and empty directories)
ohm okh scaffold-cleanup ./projects/my-awesome-project --apply

# Keep empty directories during cleanup
ohm okh scaffold-cleanup ./projects/my-awesome-project --apply --keep-empty-directories
```

Flags:
- `--apply`: perform changes (default is dry-run)
- `--remove-unmodified-stubs/--keep-unmodified-stubs` (default: remove)
- `--remove-empty-directories/--keep-empty-directories` (default: remove)

**Note**: Cleanup automatically detects broken links after removing files. Broken link warnings are displayed separately for visibility.

### 5. Build Your First Package

```bash
# Validate a manifest (if you have one)
ohm okh validate your-manifest.okh.json

# Validate with LLM enhancement
ohm okh validate your-manifest.okh.json --use-llm --quality-level professional

# Build a package
ohm package build your-manifest.okh.json

# Build with LLM analysis
ohm package build your-manifest.okh.json --use-llm --llm-provider anthropic

# List built packages
ohm package list-packages
```

### 6. Test LLM Integration

```bash
# Test LLM-enhanced validation
ohm okh validate your-manifest.okh.json --use-llm --quality-level professional

# Test LLM-powered matching
ohm match requirements your-manifest.okh.json --use-llm --domain manufacturing

# Test LLM-enhanced system analysis
ohm system health --use-llm --llm-provider anthropic

# Test utility commands with LLM
ohm utility contexts manufacturing --use-llm --quality-level professional
```

### 7. Test Remote Operations

```bash
# List remote packages
ohm package list-remote

# Push a package (if you have one built)
ohm package push org/project-name 1.0.0

# Pull a package
ohm package pull org/project-name 1.0.0
```

## Common Commands

### Package Management
```bash
# Build a package
ohm package build manifest.json

# Build with LLM enhancement
ohm package build manifest.json --use-llm --quality-level professional

# List local packages
ohm package list-packages

# Verify a package
ohm package verify org/project 1.0.0

# Verify with LLM analysis
ohm package verify org/project 1.0.0 --use-llm --quality-level professional

# Delete a package
ohm package delete org/project 1.0.0
```

### System Information
```bash
# Check health
ohm system health

# Check health with verbose output
ohm system health --verbose

# Check health with LLM analysis
ohm system health --use-llm --quality-level professional

# List domains
ohm system domains

# Get system info
ohm system info
```

### Validation
```bash
# Validate OKH manifest
ohm okh validate manifest.json

# Validate OKH manifest with LLM enhancement
ohm okh validate manifest.json --use-llm --quality-level professional

# Validate OKW facility
ohm okw validate facility.json

# Validate OKW facility with LLM analysis
ohm okw validate facility.json --use-llm --quality-level professional
```

## Troubleshooting

### Server Not Running
If you see connection errors, the CLI will automatically fall back to direct mode:
```
⚠️  Server unavailable, using direct service calls...
✅ Command completed successfully
```

### File Not Found
```bash
# Check if file exists
ls -la your-file.json

# Use absolute paths if needed
ohm package build /full/path/to/manifest.json
```

### Permission Issues
```bash
# Check write permissions
ls -la packages/

# Fix permissions if needed
chmod 755 packages/
```

### LLM Configuration Issues
```bash
# Check LLM provider configuration
ohm okh validate manifest.json --use-llm --llm-provider anthropic

# Test different quality levels
ohm okh validate manifest.json --use-llm --quality-level hobby
ohm okh validate manifest.json --use-llm --quality-level professional
ohm okh validate manifest.json --use-llm --quality-level medical

# Test strict mode
ohm okh validate manifest.json --use-llm --strict-mode
```

## Next Steps

1. **Read the full documentation**: [CLI Documentation](index.md)
2. **Explore examples**: Try the commands with your own files
3. **Use verbose mode**: Add `--verbose` for detailed output and execution tracking
4. **Try LLM integration**: Add `--use-llm` for enhanced analysis
5. **Check system status**: Use `ohm system health` regularly
6. **Test different quality levels**: Try `hobby`, `professional`, and `medical` quality levels

## Getting Help

```bash
# Get help for any command
ohm [COMMAND] --help

# Use verbose mode for debugging
ohm --verbose [COMMAND]

# Check system status
ohm system health
```
