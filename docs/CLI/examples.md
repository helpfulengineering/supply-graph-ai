# OME CLI Examples

This document provides practical examples of using the OME CLI for common workflows.

## Project Scaffolding Workflows

### Generate New Projects

```bash
# Generate a basic project scaffold (standard template, JSON output)
ome okh scaffold my-awesome-project

# Generate with detailed templates and ZIP output
ome okh scaffold arduino-sensor --template-level detailed --output-format zip

# Generate to filesystem with organization info
ome okh scaffold microscope-stage \
  --organization "University Lab" \
  --output-format filesystem \
  --output-path ./projects \
  --template-level standard

# Generate minimal scaffold for quick prototyping
ome okh scaffold quick-prototype \
  --template-level minimal \
  --output-format json \
  --version 0.0.1

# Generate scaffold and immediately validate
ome okh scaffold test-project --output-format filesystem --output-path ./test
cd ./test/test-project
ome okh validate okh-manifest.json
```

### Complete Project Lifecycle with Scaffolding

```bash
# 1. Generate a new project
ome okh scaffold my-hardware-project \
  --template-level detailed \
  --output-format filesystem \
  --output-path ./projects

# 2. Navigate to the project
cd ./projects/my-hardware-project

# 3. Edit the manifest template
# (Edit okh-manifest.json with your project details)

# 4. Validate the customized manifest
ome okh validate okh-manifest.json

# 5. Build documentation with MkDocs
mkdocs serve  # Or mkdocs build
# The scaffold includes interlinked documentation:
# - Bi-directional links between docs/ and section directories
# - Cross-references in assembly, manufacturing, and maintenance docs
# - Bridge pages in docs/sections/ for full MkDocs navigation

# 6. Use in matching operations
ome match requirements okh-manifest.json

# Or match a recipe to kitchens (cooking domain)
ome match requirements recipe.json

# 7. Build package when ready
ome package build okh-manifest.json
```

### Clean Up Scaffolded Projects

```bash
# 1. Preview cleanup to see what would be removed (dry-run)
ome okh scaffold-cleanup ./projects/my-hardware-project

# 2. Apply cleanup to remove unmodified stubs and empty directories
ome okh scaffold-cleanup ./projects/my-hardware-project --apply

# 3. Apply cleanup but keep empty directories
ome okh scaffold-cleanup ./projects/my-hardware-project --apply --keep-empty-directories

# 4. Preview cleanup with user-modified files (shows which files will be preserved)
# (User-modified files are automatically preserved)
ome okh scaffold-cleanup ./projects/my-hardware-project

# 5. Check for broken links after cleanup
ome okh scaffold-cleanup ./projects/my-hardware-project --apply
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
  ome okh scaffold $project \
    --template-level standard \
    --output-format filesystem \
    --output-path ./generated-projects \
    --organization "My Organization"
done

# Validate all generated manifests
for project in ./generated-projects/*; do
  if [ -f "$project/okh-manifest.json" ]; then
    echo "Validating $(basename $project)..."
    ome okh validate "$project/okh-manifest.json"
  fi
done
```

## LLM-Enhanced Workflows

### LLM-Powered Validation

```bash
# Enhanced validation with LLM analysis
ome okh validate manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Strict validation for production use
ome okh validate manifest.json --use-llm --strict-mode --quality-level medical

# LLM-enhanced facility validation
ome okw validate facility.json --use-llm --llm-provider openai --quality-level professional
```

### Intelligent Matching with LLM

```bash
# Enhanced matching with LLM analysis
ome match requirements manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Domain-specific matching with LLM
ome match requirements manifest.json --domain manufacturing --use-llm --strict-mode

# LLM-powered capability extraction
ome okw extract-capabilities facility.json --use-llm --quality-level professional
```

### Global LLM Configuration

```bash
# Set global LLM options for all commands
ome --use-llm --llm-provider anthropic --quality-level professional system health
ome --use-llm --llm-provider anthropic --quality-level professional package build manifest.json
ome --use-llm --llm-provider anthropic --quality-level professional okh validate manifest.json
```

## Package Management Workflows

### Complete Package Lifecycle

```bash
# Option 1: Start from scratch with scaffolding
# 1. Generate a new project scaffold
ome okh scaffold my-new-project --output-format filesystem --output-path ./projects
cd ./projects/my-new-project

# 1a. Customize the manifest template
# (Edit okh-manifest.json with your project details)

# 1b. Validate the manifest (with LLM enhancement)
ome okh validate okh-manifest.json --use-llm --quality-level professional

# Option 2: Work with existing manifest
# 1. Validate a manifest before building (with LLM enhancement)
ome okh validate openflexure-microscope.okh.json --use-llm --quality-level professional

# 2. Build the package (with LLM-powered analysis)
ome package build openflexure-microscope.okh.json --use-llm --llm-provider anthropic

# 3. Verify the built package
ome package verify university-of-bath/openflexure-microscope 5.20

# 4. Push to remote storage
ome package push university-of-bath/openflexure-microscope 5.20

# 5. List remote packages
ome package list-remote

# 6. Pull the package back (simulating download)
ome package delete university-of-bath/openflexure-microscope 5.20
ome package pull university-of-bath/openflexure-microscope 5.20
```

### Batch Package Operations

```bash
# Build multiple packages from manifests with LLM enhancement
for manifest in *.okh.json; do
    echo "Building package from $manifest with LLM analysis"
    ome package build "$manifest" --use-llm --quality-level professional
done

# List all packages in JSON format for scripting
ome --json package list-packages > packages.json

# Verify all packages with enhanced validation
ome package list-packages | grep "📦" | while read line; do
    package_name=$(echo "$line" | cut -d' ' -f2)
    version=$(echo "$line" | cut -d' ' -f3)
    echo "Verifying $package_name:$version with LLM analysis"
    ome package verify "$package_name" "$version" --use-llm --quality-level professional
done
```

### Package Management with Custom Options

```bash
# Build package without design files (faster for testing)
ome package build manifest.json --no-design-files

# Build to custom directory
ome package build manifest.json --output-dir ./custom-packages/

# Build with file size limits
ome package build manifest.json --max-file-size 10485760  # 10MB limit

# Build with custom timeout
ome package build manifest.json --timeout 120
```

## System Administration

### Health Monitoring

```bash
# Basic health check
ome system health

# Detailed health check with verbose output
ome system health --verbose

# Health check with LLM analysis
ome system health --use-llm --llm-provider anthropic --quality-level professional

# Detailed system status
ome system status

# Check specific domains
ome system domains

# Ping server
ome system ping
```

### System Information Gathering

```bash
# Get system info in JSON format
ome --json system info

# List all domains with descriptions
ome system domains

# Check validation contexts
ome utility contexts manufacturing
ome utility contexts cooking
```

## Validation Workflows

### OKH Manifest Validation

```bash
# Basic validation
ome okh validate manifest.json

# Enhanced validation with LLM analysis
ome okh validate manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Strict validation for production
ome okh validate manifest.json --use-llm --quality-level medical --strict-mode

# Upload and validate with LLM enhancement
ome okh upload manifest.json --use-llm --quality-level professional
```

### OKW Facility Validation

```bash
# Validate facility capabilities
ome okw validate facility.json

# Enhanced validation with LLM analysis
ome okw validate facility.json --use-llm --llm-provider anthropic --quality-level professional

# Extract capabilities with LLM enhancement
ome okw extract-capabilities facility.json --use-llm --quality-level professional

# Search for specific capabilities
ome okw search --capability "3d-printing"
ome okw search --location "San Francisco"
```

## Matching Operations

### Basic Matching

```bash
# Match requirements to capabilities
ome match requirements manifest.json

# Enhanced matching with LLM analysis
ome match requirements manifest.json --use-llm --llm-provider anthropic --quality-level professional

# Match with specific domain and LLM enhancement
ome match requirements manifest.json --domain manufacturing --use-llm --quality-level professional

# Match with specific context and LLM analysis
ome match requirements manifest.json --context professional --use-llm --strict-mode
```

### Advanced Matching

```bash
# Match against specific facility with LLM analysis
ome match requirements manifest.json --facility-id 123e4567-e89b-12d3-a456-426614174000 --use-llm --quality-level professional

# Match with quality level and LLM enhancement
ome match requirements manifest.json --use-llm --quality-level medical --strict-mode

# List recent matches
ome match list-recent --limit 10
```

## Supply Tree Operations

### Supply Tree Management

```bash
# Create supply tree
ome supply-tree create manifest-id facility-id

# Get supply tree details
ome supply-tree get supply-tree-id

# List all supply trees
ome supply-tree list

# Validate supply tree
ome supply-tree validate supply-tree-id
```

## Utility Operations

### Domain and Context Management

```bash
# List all domains
ome utility domains

# List contexts for manufacturing
ome utility contexts manufacturing

# List contexts for cooking
ome utility contexts cooking

# Filter domains by name
ome utility domains --name manufacturing
```

## Error Handling Examples

### Graceful Degradation

```bash
# Server unavailable - CLI falls back to direct mode
ome system health
# Output: ⚠️  Server unavailable, using direct service calls...
#         ✅ System is healthy

# File not found with helpful suggestion
ome package verify nonexistent/package 1.0.0
# Output: ❌ Error: Package nonexistent/package:1.0.0 not found
#            Suggestion: Use 'ome package list-packages' to see available packages

# Invalid domain with specific guidance
ome utility contexts nonexistent-domain
# Output: ❌ Error: Invalid domain 'nonexistent-domain'. Valid domains are: manufacturing, cooking
#            Suggestion: Use 'ome utility domains' to see available domains
```

### Validation Errors

```bash
# Invalid manifest with LLM analysis
ome okh validate invalid-manifest.json --use-llm
# Output: ❌ Error: Invalid manifest: Missing required field 'title'
#            Suggestion: Add required 'title' field to manifest

# Invalid facility with enhanced validation
ome okw validate invalid-facility.json --use-llm --quality-level professional
# Output: ❌ Error: Invalid facility: Missing required field 'name'
#            Suggestion: Add required 'name' field to facility specification

# LLM configuration error
ome okh validate manifest.json --use-llm --llm-provider invalid-provider
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
if ome package verify "$PACKAGE_NAME" "$VERSION" $LLM_OPTS 2>/dev/null; then
    echo "Package already exists, skipping build"
else
    echo "Building package with enhanced validation..."
    ome package build "$MANIFEST_FILE" $LLM_OPTS
fi

# Push to remote storage
echo "Pushing to remote storage..."
ome package push "$PACKAGE_NAME" "$VERSION"

echo "Package management complete!"
```

### Python Script for Batch Operations

```python
#!/usr/bin/env python3
import subprocess
import json
import sys

def run_ome_command(args):
    """Run an OME CLI command and return the result"""
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
    output = run_ome_command(['--json', 'package', 'list-packages'])
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
        
        result = run_ome_command(['package', 'verify', name, version] + llm_args)
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
            python ome okh validate "$manifest" --use-llm --quality-level medical --strict-mode
          done
      
      - name: Build packages
        run: |
          for manifest in *.okh.json; do
            echo "Building package from $manifest with LLM analysis"
            python ome package build "$manifest" --use-llm --quality-level professional
          done
      
      - name: Verify packages
        run: |
          python ome package list-packages
          # Add verification logic here
```

### Docker Integration

```dockerfile
# Dockerfile for OME CLI
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
ome --server-url https://api.ome.org system health

# Use custom timeout
ome --timeout 60 package build large-manifest.json

# Use custom output format
ome --json --table system domains
```

### Verbose Debugging

```bash
# Debug package building with detailed output
ome --verbose package build manifest.json

# Debug system health with execution tracking
ome --verbose system health

# Debug remote operations with connection details
ome --verbose package push org/project 1.0.0

# Debug LLM operations with detailed analysis
ome --verbose okh validate manifest.json --use-llm --quality-level professional

# Debug utility operations with domain validation
ome --verbose utility contexts manufacturing
```

### Output Processing

```bash
# Extract package names only
ome --json package list-packages | jq -r '.packages[].name'

# Count packages by organization
ome --json package list-packages | jq -r '.packages[].name' | cut -d'/' -f1 | sort | uniq -c

# Get package sizes
ome --json package list-packages | jq -r '.packages[] | "\(.name):\(.version) - \(.size) bytes"'
```
