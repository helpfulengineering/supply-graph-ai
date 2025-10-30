# OME CLI Quick Start Guide

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
ome system health
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
ome --help

# See commands in a specific group
ome package --help
```

### 4. Generate Your First Project Scaffold

```bash
# Generate a new OKH-compliant project structure
ome okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ome okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with custom organization
ome okh scaffold microscope-stage --organization "My Lab" --output-format filesystem --output-path ./projects

# Generate minimal scaffold for quick prototyping
ome okh scaffold quick-prototype --template-level minimal --output-format json
```

**Output Formats:**
- `json`: Returns structured JSON (default, great for scripting)
- `zip`: Creates downloadable ZIP archive
- `filesystem`: Writes directly to specified directory

**Template Levels:**
- `minimal`: Basic placeholders for experienced developers
- `standard`: Detailed guidance with examples (default)
- `detailed`: Comprehensive help with best practices

### 4.5. Clean Up a Scaffolded Project

```bash
# Preview cleanup (dry-run)
ome okh scaffold-cleanup ./projects/my-awesome-project

# Apply cleanup (remove unmodified stubs and empty directories)
ome okh scaffold-cleanup ./projects/my-awesome-project --apply

# Keep empty directories during cleanup
ome okh scaffold-cleanup ./projects/my-awesome-project --apply --keep-empty-directories
```

Flags:
- `--apply`: perform changes (default is dry-run)
- `--remove-unmodified-stubs/--keep-unmodified-stubs` (default: remove)
- `--remove-empty-directories/--keep-empty-directories` (default: remove)

### 5. Build Your First Package

```bash
# Validate a manifest (if you have one)
ome okh validate your-manifest.okh.json

# Validate with LLM enhancement
ome okh validate your-manifest.okh.json --use-llm --quality-level professional

# Build a package
ome package build your-manifest.okh.json

# Build with LLM analysis
ome package build your-manifest.okh.json --use-llm --llm-provider anthropic

# List built packages
ome package list-packages
```

### 6. Test LLM Integration

```bash
# Test LLM-enhanced validation
ome okh validate your-manifest.okh.json --use-llm --quality-level professional

# Test LLM-powered matching
ome match requirements your-manifest.okh.json --use-llm --domain manufacturing

# Test LLM-enhanced system analysis
ome system health --use-llm --llm-provider anthropic

# Test utility commands with LLM
ome utility contexts manufacturing --use-llm --quality-level professional
```

### 7. Test Remote Operations

```bash
# List remote packages
ome package list-remote

# Push a package (if you have one built)
ome package push org/project-name 1.0.0

# Pull a package
ome package pull org/project-name 1.0.0
```

## Common Commands

### Package Management
```bash
# Build a package
ome package build manifest.json

# Build with LLM enhancement
ome package build manifest.json --use-llm --quality-level professional

# List local packages
ome package list-packages

# Verify a package
ome package verify org/project 1.0.0

# Verify with LLM analysis
ome package verify org/project 1.0.0 --use-llm --quality-level professional

# Delete a package
ome package delete org/project 1.0.0
```

### System Information
```bash
# Check health
ome system health

# Check health with verbose output
ome system health --verbose

# Check health with LLM analysis
ome system health --use-llm --quality-level professional

# List domains
ome system domains

# Get system info
ome system info
```

### Validation
```bash
# Validate OKH manifest
ome okh validate manifest.json

# Validate OKH manifest with LLM enhancement
ome okh validate manifest.json --use-llm --quality-level professional

# Validate OKW facility
ome okw validate facility.json

# Validate OKW facility with LLM analysis
ome okw validate facility.json --use-llm --quality-level professional
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
ome package build /full/path/to/manifest.json
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
ome okh validate manifest.json --use-llm --llm-provider anthropic

# Test different quality levels
ome okh validate manifest.json --use-llm --quality-level hobby
ome okh validate manifest.json --use-llm --quality-level professional
ome okh validate manifest.json --use-llm --quality-level medical

# Test strict mode
ome okh validate manifest.json --use-llm --strict-mode
```

## Next Steps

1. **Read the full documentation**: [CLI Documentation](index.md)
2. **Explore examples**: Try the commands with your own files
3. **Use verbose mode**: Add `--verbose` for detailed output and execution tracking
4. **Try LLM integration**: Add `--use-llm` for enhanced analysis
5. **Check system status**: Use `ome system health` regularly
6. **Test different quality levels**: Try `hobby`, `professional`, and `medical` quality levels

## Getting Help

```bash
# Get help for any command
ome [COMMAND] --help

# Use verbose mode for debugging
ome --verbose [COMMAND]

# Check system status
ome system health
```
