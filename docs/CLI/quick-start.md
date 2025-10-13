# OME CLI Quick Start Guide

## Getting Started in 5 Minutes

This guide will get you up and running with the OME CLI quickly.

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
✅ System is healthy
Status: ok
Version: 1.0.0
Mode: unknown
Registered domains: cooking, manufacturing
```

### 3. List Available Commands

```bash
# See all available command groups
ome --help

# See commands in a specific group
ome package --help
```

### 4. Build Your First Package

```bash
# Validate a manifest (if you have one)
ome okh validate your-manifest.okh.json

# Build a package
ome package build your-manifest.okh.json

# List built packages
ome package list-packages
```

### 5. Test Remote Operations

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

# List local packages
ome package list-packages

# Verify a package
ome package verify org/project 1.0.0

# Delete a package
ome package delete org/project 1.0.0
```

### System Information
```bash
# Check health
ome system health

# List domains
ome system domains

# Get system info
ome system info
```

### Validation
```bash
# Validate OKH manifest
ome okh validate manifest.json

# Validate OKW facility
ome okw validate facility.json
```

## Troubleshooting

### Server Not Running
If you see connection errors, the CLI will automatically fall back to direct mode:
```
ℹ️  Server unavailable, using direct mode
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

## Next Steps

1. **Read the full documentation**: [CLI Documentation](index.md)
2. **Explore examples**: Try the commands with your own files
3. **Use verbose mode**: Add `--verbose` for detailed output
4. **Check system status**: Use `ome system health` regularly

## Getting Help

```bash
# Get help for any command
ome [COMMAND] --help

# Use verbose mode for debugging
ome --verbose [COMMAND]

# Check system status
ome system health
```

That's it! You're ready to use the OME CLI. 🚀
