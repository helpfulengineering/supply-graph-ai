# OHM CLI Examples

This document provides practical examples of using the OHM CLI for common workflows.

## Project Scaffolding Workflows

### Generate New Projects

```bash
# Generate a basic project scaffold (standard template, JSON output)
ohm okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ohm okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with organization info
ohm okh scaffold microscope-stage \
  --organization "University Lab" \
  --output-format filesystem \
  --output-path ./projects \
  --template-level standard

# Generate minimal scaffold for quick prototyping
ohm okh scaffold quick-prototype \
  --template-level minimal \
  --output-format json \
  --version 0.0.1

# Generate scaffold and immediately validate
ohm okh scaffold test-project --output-format filesystem --output-path ./test
cd ./test/test-project
ohm okh validate okh-manifest.json
```

### Complete Project Lifecycle with Scaffolding

```bash
# 1. Generate a new project
ohm okh scaffold my-hardware-project \
  --template-level detailed \
  --output-format filesystem \
  --output-path ./projects

# 2. Navigate to the project
cd ./projects/my-hardware-project

# 3. Edit the manifest template
# (Edit okh-manifest.json with your project details)

# 4. Validate the customized manifest
ohm okh validate okh-manifest.json

# 5. Build documentation with MkDocs
mkdocs serve  # Or mkdocs build
# The scaffold includes interlinked documentation:
# - Bi-directional links between docs/ and section directories
# - Cross-references in assembly, manufacturing, and maintenance docs
# - Bridge pages in docs/sections/ for full MkDocs navigation

# 6. Use in matching operations
ohm match requirements okh-manifest.json

# Or match a recipe to kitchens (cooking domain)
ohm match requirements recipe.json

# 7. Build package when ready
ohm package build okh-manifest.json
```

### Clean Up Scaffolded Projects

```bash
# 1. Preview cleanup to see what would be removed (dry-run)
ohm okh scaffold-cleanup ./projects/my-hardware-project

# 2. Apply cleanup to remove unmodified stubs and empty directories
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply

# 3. Apply cleanup but keep empty directories
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-empty-directories

# 4. Preview cleanup with user-modified files (shows which files will be preserved)
# (User-modified files are automatically preserved)
ohm okh scaffold-cleanup ./projects/my-hardware-project

# 5. Check for broken links after cleanup
ohm okh scaffold-cleanup ./projects/my-hardware-project --apply
# Output will show "Broken Link Warnings" section if any links are broken
```

**Note on Broken Links:**
Cleanup automatically detects broken links after removing files. If a file you're keeping has links to files that were removed, you'll see warnings like:
```
🔗 Broken Link Warnings:
   ⚠️  Broken link(s) in docs/index.md: ../bom/index.md
```
You can then manually fix these links or restore the removed files if needed.

### Batch Project Generation

```bash
# Generate multiple projects with different configurations
for project in arduino-sensor microscope-stage prosthetic-hand; do
  ohm okh scaffold $project \
    --template-level standard \
    --output-format filesystem \
    --output-path ./generated-projects \
    --organization "My Organization"
done

# Validate all generated manifests
for project in ./generated-projects/*; do
  if [ -f "$project/okh-manifest.json" ]; then
    echo "Validating $(basename $project)..."
    ohm okh validate "$project/okh-manifest.json"
  fi
done
```

## LLM-Enhanced Workflows

### LLM-Powered Validation

```bash
# Enhanced validation with LLM analysis
ohm okh validate manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Strict validation for production use
ohm okh validate manifest.json --use-llm --strict-mode --quality-level medical

# LLM-enhanced facility validation
ohm okw validate facility.json --use-llm --llm-provider openai --quality-level professional
```

### Intelligent Matching with LLM

```bash
# Enhanced matching with LLM analysis
ohm match requirements manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Domain-specific matching with LLM
ohm match requirements manifest.json --domain manufacturing --use-llm --strict-mode

# LLM-powered capability extraction
ohm okw extract-capabilities facility.json --use-llm --quality-level professional
```

### Global LLM Configuration

```bash
# Set global LLM options for all commands
ohm --use-llm --llm-provider anthropic --quality-level professional system health
ohm --use-llm --llm-provider anthropic --quality-level professional package build manifest.json
ohm --use-llm --llm-provider anthropic --quality-level professional okh validate manifest.json
```

## Package Management Workflows

### Complete Package Lifecycle

```bash
# Option 1: Start from scratch with scaffolding
# 1. Generate a new project scaffold
ohm okh scaffold my-new-project --output-format filesystem --output-path ./projects
cd ./projects/my-new-project

# 1a. Customize the manifest template
# (Edit okh-manifest.json with your project details)

# 1b. Validate the manifest (with LLM enhancement)
ohm okh validate okh-manifest.json --use-llm --quality-level professional

# Option 2: Work with existing manifest
# 1. Validate a manifest before building (with LLM enhancement)
ohm okh validate openflexure-microscope.okh.json --use-llm --quality-level professional

# 2. Build the package (with LLM-powered analysis)
ohm package build openflexure-microscope.okh.json --use-llm --llm-provider anthropic

# 3. Verify the built package
ohm package verify university-of-bath/openflexure-microscope 5.20

# 4. Push to remote storage
ohm package push university-of-bath/openflexure-microscope 5.20

# 5. List remote packages
ohm package list-remote

# 6. Pull the package back (simulating download)
ohm package delete university-of-bath/openflexure-microscope 5.20
ohm package pull university-of-bath/openflexure-microscope 5.20
```

### Batch Package Operations

```bash
# Build multiple packages from manifests with LLM enhancement
for manifest in *.okh.json; do
    echo "Building package from $manifest with LLM analysis"
    ohm package build "$manifest" --use-llm --quality-level professional
done

# List all packages in JSON format for scripting
ohm --json package list-packages > packages.json

# Verify all packages with enhanced validation
ohm package list-packages | grep "📦" | while read line; do
    package_name=$(echo "$line" | cut -d' ' -f2)
    version=$(echo "$line" | cut -d' ' -f3)
    echo "Verifying $package_name:$version with LLM analysis"
    ohm package verify "$package_name" "$version" --use-llm --quality-level professional
done
```

### Package Management with Custom Options

```bash
# Build package without design files (faster for testing)
ohm package build manifest.json --no-design-files

# Build to custom directory
ohm package build manifest.json --output-dir ./custom-packages/

# Build with file size limits
ohm package build manifest.json --max-file-size 10485760  # 10MB limit

# Build with custom timeout
ohm package build manifest.json --timeout 120
```

## System Administration

### Health Monitoring

```bash
# Basic health check
ohm system health

# Detailed health check with verbose output
ohm system health --verbose

# Health check with LLM analysis
ohm system health --use-llm --llm-provider anthropic --quality-level professional

# Detailed system status
ohm system status

# Check specific domains
ohm system domains

# Ping server
ohm system ping
```

### System Information Gathering

```bash
# Get system info in JSON format
ohm --json system info

# List all domains with descriptions
ohm system domains

# Check validation contexts
ohm utility contexts manufacturing
ohm utility contexts cooking
```

## Validation and Fix Workflows

### OKH Manifest Validation

```bash
# Basic validation
ohm okh validate manifest.json

# Validate cooking domain recipe
ohm okh validate recipe.json --domain cooking --quality-level home

# Enhanced validation with LLM analysis
ohm okh validate manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Strict validation for production
ohm okh validate manifest.json --use-llm --quality-level medical --strict-mode

# Upload and validate with LLM enhancement
ohm okh upload manifest.json --use-llm --quality-level professional
```

### OKH Manifest Auto-Fix

```bash
# Fix validation issues interactively
ohm okh fix manifest.json

# Preview fixes without applying
ohm okh fix manifest.json --dry-run

# Fix with backup and auto-confirm
ohm okh fix manifest.json --backup --yes

# Fix cooking domain recipe
ohm okh fix recipe.json --domain cooking --confidence-threshold 0.7

# Fix with verbose output to see all issues
ohm okh fix manifest.json --verbose
```

### OKW Facility Validation

```bash
# Validate facility capabilities
ohm okw validate facility.json

# Validate cooking domain kitchen
ohm okw validate kitchen.json --domain cooking

# Enhanced validation with LLM analysis
ohm okw validate facility.json --use-llm --llm-provider anthropic --quality-level professional

# Extract capabilities with LLM enhancement
ohm okw extract-capabilities facility.json --use-llm --quality-level professional

# Search for specific capabilities
ohm okw search --capability "3d-printing"
ohm okw search --location "San Francisco"
```

### OKW Facility Auto-Fix

```bash
# Fix validation issues interactively
ohm okw fix facility.json

# Preview fixes without applying
ohm okw fix facility.json --dry-run

# Fix with backup and auto-confirm
ohm okw fix facility.json --backup --yes

# Fix cooking domain kitchen
ohm okw fix kitchen.json --domain cooking --confidence-threshold 0.7

# Fix with verbose output to see all issues
ohm okw fix facility.json --verbose
```

## Matching Operations

### Basic Matching

```bash
# Match requirements to capabilities (manufacturing domain)
ohm match requirements manifest.json

# Match recipe to kitchens (cooking domain)
ohm match requirements recipe.json

# Match with explicit domain override
ohm match requirements input.json --domain cooking

# Enhanced matching with LLM analysis
ohm match requirements manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Match with specific domain and LLM enhancement
ohm match requirements manifest.json --domain manufacturing --use-llm --quality-level professional

# Match with specific context and LLM analysis
ohm match requirements manifest.json --context professional --use-llm --strict-mode
```

### Advanced Matching

```bash
# Match against specific facility with LLM analysis
ohm match requirements manifest.json --facility-id 123e4567-e89b-12d3-a456-426614174000 --use-llm --quality-level professional

# Match recipe with local kitchen file (cooking domain)
ohm match requirements recipe.json --domain cooking --facility-file kitchen.json

# Match with quality level and LLM enhancement
ohm match requirements manifest.json --use-llm --quality-level medical --strict-mode

# Match with location filter
ohm match requirements manifest.json --location "San Francisco" --min-confidence 0.8

# List recent matches
ohm match list-recent --limit 10
```

### Working with OKH and OKW Files

```bash
# List all OKH manifests
ohm okh list-manifests

# Get a specific manifest and save to file
ohm okh get 8f14e3c4-09f2-4a5e-8bd9-4b5bb5d0a9cd --output manifest.json

# List OKW files in storage with facility IDs
ohm okw list-files

# Get a specific facility and save to file
ohm okw get 550e8400-e29b-41d4-a716-446655440001 --output facility.json

# Use facility ID from list-files output in matching
FACILITY_ID=$(ohm okw list-files --format json | jq -r '.files[0].facility_id')
ohm okw get "$FACILITY_ID"
```

## Supply Tree Operations

### Supply Tree Management

```bash
# Create supply tree
ohm supply-tree create manifest-id facility-id

# Get supply tree details
ohm supply-tree get supply-tree-id

# List all supply trees
ohm supply-tree list

# Validate supply tree
ohm supply-tree validate supply-tree-id
```

## Utility Operations

### Domain and Context Management

```bash
# List all domains
ohm utility domains

# List contexts for manufacturing
ohm utility contexts manufacturing

# List contexts for cooking
ohm utility contexts cooking

# Filter domains by name
ohm utility domains --name manufacturing
```

## Error Handling Examples

### Graceful Degradation

```bash
# Server unavailable - CLI falls back to direct mode
ohm system health
# Output: ⚠️  Server unavailable, using direct service calls...
#         ✅ System is healthy

# File not found with helpful suggestion
ohm package verify nonexistent/package 1.0.0
# Output: ❌ Error: Package nonexistent/package:1.0.0 not found
#            Suggestion: Use 'ohm package list-packages' to see available packages

# Invalid domain with specific guidance
ohm utility contexts nonexistent-domain
# Output: ❌ Error: Invalid domain 'nonexistent-domain'. Valid domains are: manufacturing, cooking
#            Suggestion: Use 'ohm utility domains' to see available domains
```

### Validation Errors

```bash
# Invalid manifest with LLM analysis
ohm okh validate invalid-manifest.json --use-llm
# Output: ❌ Error: Invalid manifest: Missing required field 'title'
#            Suggestion: Add required 'title' field to manifest

# Invalid facility with enhanced validation
ohm okw validate invalid-facility.json --use-llm --quality-level professional
# Output: ❌ Error: Invalid facility: Missing required field 'name'
#            Suggestion: Add required 'name' field to facility specification

# LLM configuration error
ohm okh validate manifest.json --use-llm --llm-provider invalid-provider
# Output: ❌ Error: LLM provider 'invalid-provider' not supported
#            Suggestion: Use one of: openai, anthropic, google, azure, local
```

## Scripting Examples

### Bash Script for Package Management

```bash
#!/bin/bash
# package-manager.sh

PACKAGE_NAME="$1"
VERSION="$2"
MANIFEST_FILE="$3"
USE_LLM="${4:-false}"

if [ -z "$PACKAGE_NAME" ] || [ -z "$VERSION" ] || [ -z "$MANIFEST_FILE" ]; then
    echo "Usage: $0 <package-name> <version> <manifest-file> [use-llm]"
    exit 1
fi

echo "Managing package: $PACKAGE_NAME:$VERSION"

# Set LLM options if enabled
LLM_OPTS=""
if [ "$USE_LLM" = "true" ]; then
    LLM_OPTS="--use-llm --llm-provider anthropic --quality-level professional"
    echo "Using LLM enhancement for package management"
fi

# Check if package already exists
if ohm package verify "$PACKAGE_NAME" "$VERSION" $LLM_OPTS 2>/dev/null; then
    echo "Package already exists, skipping build"
else
    echo "Building package with enhanced validation..."
    ohm package build "$MANIFEST_FILE" $LLM_OPTS
fi

# Push to remote storage
echo "Pushing to remote storage..."
ohm package push "$PACKAGE_NAME" "$VERSION"

echo "Package management complete!"
```

### Python Script for Batch Operations

```python
#!/usr/bin/env python3
import subprocess
import json
import sys

def run_ohm_command(args):
    """Run an OHM CLI command and return the result"""
    try:
        result = subprocess.run(
            ['python', 'ome'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return None

def list_packages():
    """List all packages in JSON format"""
    output = run_ohm_command(['--json', 'package', 'list-packages'])
    if output:
        return json.loads(output)
    return None

def verify_all_packages(use_llm=False):
    """Verify all built packages with optional LLM enhancement"""
    packages = list_packages()
    if not packages:
        print("No packages found")
        return
    
    llm_args = ['--use-llm', '--llm-provider', 'anthropic', '--quality-level', 'professional'] if use_llm else []
    
    for package in packages.get('packages', []):
        name = package['name']
        version = package['version']
        print(f"Verifying {name}:{version}" + (" with LLM analysis" if use_llm else ""))
        
        result = run_ohm_command(['package', 'verify', name, version] + llm_args)
        if result and "✅" in result:
            print(f"  ✅ {name}:{version} verified")
        else:
            print(f"  ❌ {name}:{version} verification failed")

if __name__ == "__main__":
    verify_all_packages()
```

## Integration Examples

### CI/CD Pipeline Integration

```yaml
# .github/workflows/package-validation.yml
name: Package Validation

on:
  push:
    paths:
      - '*.okh.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Validate OKH manifests
        run: |
          for manifest in *.okh.json; do
            echo "Validating $manifest with LLM enhancement"
            python ohm okh validate "$manifest" --use-llm --quality-level medical --strict-mode
          done
      
      - name: Build packages
        run: |
          for manifest in *.okh.json; do
            echo "Building package from $manifest with LLM analysis"
            python ohm package build "$manifest" --use-llm --quality-level professional
          done
      
      - name: Verify packages
        run: |
          python ohm package list-packages
          # Add verification logic here
```

### Docker Integration

```dockerfile
# Dockerfile for OHM CLI
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Make CLI executable
RUN chmod +x ome

# Set entrypoint
ENTRYPOINT ["./ome"]
```

```bash
# Use in Docker
docker build -t ome-cli .
docker run ome-cli system health
docker run ome-cli package list-packages
```

## Advanced Usage

### Custom Server Configuration

```bash
# Use custom server
ohm --server-url https://api.ome.org system health

# Use custom timeout
ohm --timeout 60 package build large-manifest.json

# Use custom output format
ohm --json --table system domains
```

### Verbose Debugging

```bash
# Debug package building with detailed output
ohm --verbose package build manifest.json

# Debug system health with execution tracking
ohm --verbose system health

# Debug remote operations with connection details
ohm --verbose package push org/project 1.0.0

# Debug LLM operations with detailed analysis
ohm --verbose okh validate manifest.json --use-llm --quality-level professional

# Debug utility operations with domain validation
ohm --verbose utility contexts manufacturing
```

### Output Processing

```bash
# Extract package names only
ohm --json package list-packages | jq -r '.packages[].name'

# Count packages by organization
ohm --json package list-packages | jq -r '.packages[].name' | cut -d'/' -f1 | sort | uniq -c

# Get package sizes
ohm --json package list-packages | jq -r '.packages[] | "\(.name):\(.version) - \(.size) bytes"'
```
