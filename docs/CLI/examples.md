# OME CLI Examples

This document provides practical examples of using the OME CLI for common workflows.

## Package Management Workflows

### Complete Package Lifecycle

```bash
# 1. Validate a manifest before building
ome okh validate openflexure-microscope.okh.json

# 2. Build the package
ome package build openflexure-microscope.okh.json

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
# Build multiple packages from manifests
for manifest in *.okh.json; do
    echo "Building package from $manifest"
    ome package build "$manifest"
done

# List all packages in JSON format for scripting
ome --json package list-packages > packages.json

# Verify all packages
ome package list-packages | grep "📦" | while read line; do
    package_name=$(echo "$line" | cut -d' ' -f2)
    version=$(echo "$line" | cut -d' ' -f3)
    echo "Verifying $package_name:$version"
    ome package verify "$package_name" "$version"
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

# Strict validation for production
ome okh validate manifest.json --quality-level premium --strict-mode

# Upload and validate
ome okh upload manifest.json --quality-level standard
```

### OKW Facility Validation

```bash
# Validate facility capabilities
ome okw validate facility.json

# Extract capabilities
ome okw extract-capabilities facility.json

# Search for specific capabilities
ome okw search --capability "3d-printing"
ome okw search --location "San Francisco"
```

## Matching Operations

### Basic Matching

```bash
# Match requirements to capabilities
ome match requirements manifest.json

# Match with specific domain
ome match requirements manifest.json --domain manufacturing

# Match with specific context
ome match requirements manifest.json --context professional
```

### Advanced Matching

```bash
# Match against specific facility
ome match requirements manifest.json --facility-id 123e4567-e89b-12d3-a456-426614174000

# Match with quality level
ome match requirements manifest.json --quality-level premium

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
# Output: ℹ️  Server unavailable, using direct mode
#         ✅ System is healthy

# File not found
ome package verify nonexistent/package 1.0.0
# Output: Error: Package nonexistent/package:1.0.0 not found
```

### Validation Errors

```bash
# Invalid manifest
ome okh validate invalid-manifest.json
# Output: Error: Invalid manifest: Missing required field 'title'

# Invalid facility
ome okw validate invalid-facility.json
# Output: Error: Invalid facility: Missing required field 'name'
```

## Scripting Examples

### Bash Script for Package Management

```bash
#!/bin/bash
# package-manager.sh

PACKAGE_NAME="$1"
VERSION="$2"
MANIFEST_FILE="$3"

if [ -z "$PACKAGE_NAME" ] || [ -z "$VERSION" ] || [ -z "$MANIFEST_FILE" ]; then
    echo "Usage: $0 <package-name> <version> <manifest-file>"
    exit 1
fi

echo "Managing package: $PACKAGE_NAME:$VERSION"

# Check if package already exists
if ome package verify "$PACKAGE_NAME" "$VERSION" 2>/dev/null; then
    echo "Package already exists, skipping build"
else
    echo "Building package..."
    ome package build "$MANIFEST_FILE"
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

def verify_all_packages():
    """Verify all built packages"""
    packages = list_packages()
    if not packages:
        print("No packages found")
        return
    
    for package in packages.get('packages', []):
        name = package['name']
        version = package['version']
        print(f"Verifying {name}:{version}")
        
        result = run_ome_command(['package', 'verify', name, version])
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
            echo "Validating $manifest"
            python ome okh validate "$manifest" --quality-level premium
          done
      
      - name: Build packages
        run: |
          for manifest in *.okh.json; do
            echo "Building package from $manifest"
            python ome package build "$manifest"
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
# Debug package building
ome --verbose package build manifest.json

# Debug system health
ome --verbose system health

# Debug remote operations
ome --verbose package push org/project 1.0.0
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

These examples demonstrate the flexibility and power of the OME CLI for various use cases and workflows.
