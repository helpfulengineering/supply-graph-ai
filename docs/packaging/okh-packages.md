# OKH Package Management

## Overview

The Open Hardware Manager (OHM) includes a package management system for OpenKnowHow (OKH) manifests. This system allows you to build self-contained packages that include all externally-linked files, similar to how Docker builds container images from Dockerfiles.

## Package Structure

OKH packages follow a standardized directory structure that organizes all files by type and purpose:

```
{org}/{project-name}/{version}/
├── okh-manifest.json          # The canonical manifest
├── design-files/              # CAD models, technical drawings
│   ├── 3d_model.iges
│   └── technical_drawings.stl
├── manufacturing-files/       # Assembly guides, BOMs, compliance docs
│   ├── assembly_guide.docx
│   ├── bill_of_materials.md
│   └── standards_compliance.md
├── making-instructions/       # Step-by-step build instructions
│   ├── assembly_guide.md
│   └── pcb_assembly_guide.md
├── operating-instructions/    # User manuals, maintenance guides
├── quality-instructions/      # QC checklists, testing protocols
├── risk-assessment/          # Safety and risk documentation
├── software/                 # Firmware, control software
├── tool-settings/            # Machine configurations
├── schematics/               # Electrical schematics
├── parts/                    # Part-specific files organized by part name
│   ├── housing/
│   │   ├── source/          # Source CAD files
│   │   ├── export/          # Exported formats (STEP, etc.)
│   │   ├── auxiliary/       # Supporting documentation
│   │   └── images/
│   └── base/
│       ├── source/
│       ├── export/
│       ├── auxiliary/
│       └── images/
└── metadata/                 # Package metadata
    ├── build-info.json       # Build timestamp, OHM version, etc.
    └── file-manifest.json    # Complete file inventory with checksums
```

## Package Naming

Packages are named using the pattern: `{organization}/{project-name}/{version}`

- **Organization**: Extracted from the `organization.name` field in the manifest, or defaults to "community"
- **Project Name**: Sanitized version of the manifest `title` field
- **Version**: Directly from the manifest `version` field

### Example

For a manifest with:
- `title`: "Arduino-based IoT Sensor Node"
- `version`: "1.2.4"
- `organization.name`: "Fitzpatrick, Knapp and Jackson"

The package would be: `fitzpatrick-knapp-and-jackson/arduino-based-iot-sensor-node/1.2.4`

## Building Packages

### Using the CLI

The OHM provides a command-line interface for building packages:

```bash
# Build from manifest file
ohm package build okh-manifest.json

# Build with selective inclusion
ohm package build okh-manifest.json --no-software --no-operating-instructions

# Build from stored manifest ID
ohm package build-from-storage a736334a-efd3-4745-a59f-a386ba4abdeb

# Specify output directory
ohm package build okh-manifest.json --output-dir ./my-packages/

# Verbose output
ohm package build okh-manifest.json --verbose
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--output-dir`, `-o` | Output directory for built packages |
| `--no-design-files` | Exclude design files |
| `--no-manufacturing-files` | Exclude manufacturing files |
| `--no-making-instructions` | Exclude making instructions |
| `--no-software` | Exclude software |
| `--no-parts` | Exclude parts |
| `--no-operating-instructions` | Exclude operating instructions |
| `--no-quality-instructions` | Exclude quality instructions |
| `--no-risk-assessment` | Exclude risk assessment |
| `--no-schematics` | Exclude schematics |
| `--no-tool-settings` | Exclude tool settings |
| `--no-verify` | Skip download verification |
| `--max-concurrent` | Maximum concurrent downloads (default: 5) |
| `--verbose`, `-v` | Verbose output |

### Using the API

You can also build packages programmatically using the FastAPI endpoints:

```python
import httpx

# Build from manifest data
response = httpx.post("http://localhost:8001/v1/api/package/build", json={
    "manifest": manifest_data,
    "options": {
        "include_design_files": True,
        "include_software": False,
        "max_concurrent_downloads": 10
    }
})

# Build from stored manifest
response = httpx.post("http://localhost:8001/v1/api/package/build/a736334a-efd3-4745-a59f-a386ba4abdeb")
```

## Package Management

### Listing Packages

```bash
# List all built packages
ohm package list-packages

# List with verbose output
ohm package list-packages --verbose
```

### Verifying Packages

```bash
# Verify package integrity
ohm package verify org/project-name 1.2.4

# Verify with detailed output
ohm package verify org/project-name 1.2.4 --verbose
```

### Deleting Packages

```bash
# Delete package (with confirmation)
ohm package delete org/project-name 1.2.4

# Force delete without confirmation
ohm package delete org/project-name 1.2.4 --force
```

## Remote Package Management

The OHM package management system supports pushing packages to and pulling packages from remote storage, similar to container registries.

### Pushing Packages

```bash
# Push a local package to remote storage
ohm package push org/project-name 1.2.4

# Push with verbose output
ohm package push org/project-name 1.2.4 --verbose
```

### Pulling Packages

```bash
# Pull a package from remote storage
ohm package pull org/project-name 1.2.4

# Pull to specific output directory
ohm package pull org/project-name 1.2.4 --output-dir ./my-packages/

# Pull with verbose output
ohm package pull org/project-name 1.2.4 --verbose
```

### Listing Remote Packages

```bash
# List packages available in remote storage
ohm package list-remote

# List with verbose output (shows modification dates)
ohm package list-remote --verbose
```

### Remote Storage Structure

Packages are stored in Azure Blob Storage using a hierarchical structure:

```
Azure Blob Storage Container
├── okh/
│   └── packages/                 # Built OKH packages
│       ├── community/simple-test-project/1.0.0/
│       │   ├── manifest.json
│       │   ├── build-info.json
│       │   ├── file-manifest.json
│       │   └── files/
│       │       ├── design-files/test.stl
│       │       └── manufacturing-files/README.md
│       └── university-of-bath/openflexure-microscope/5.20/
│           ├── manifest.json
│           ├── build-info.json
│           ├── file-manifest.json
│           └── files/
│               ├── design-files/
│               ├── manufacturing-files/
│               ├── making-instructions/
│               └── parts/
├── okw/                          # OKW facilities (flat structure)
└── supply-trees/                 # Supply tree solutions
```

### Remote Package Operations

| Command | Description | Example |
|---------|-------------|---------|
| `push` | Upload local package to remote storage | `ohm package push community/test 1.0.0` |
| `pull` | Download remote package to local storage | `ohm package pull community/test 1.0.0` |
| `list-remote` | List packages available in remote storage | `ohm package list-remote` |

### PUSH/PULL Workflow Example

```bash
# 1. Build a package locally
ohm package build manifest.json

# 2. Push to remote storage
ohm package push community/my-project 1.0.0
# Output: ✅ Successfully pushed community/my-project:1.0.0
#         📄 Uploaded 5 files
#         💾 Total size: 58,330 bytes

# 3. List remote packages
ohm package list-remote
# Output: 📦 Remote packages:
#         📦 community/my-project
#           📄 1.0.0 (0.1 MB)

# 4. Delete local package
ohm package delete community/my-project 1.0.0

# 5. Pull from remote storage
ohm package pull community/my-project 1.0.0
# Output: ✅ Successfully pulled community/my-project:1.0.0
#         📁 Local path: /path/to/packages/community/my-project/1.0.0
#         📄 Files: 2
#         💾 Size: 58,330 bytes
```

## File Resolution

The package builder automatically downloads and organizes files based on their location in the OKH manifest:

### Document Categories

| Manifest Field | Target Directory | Description |
|----------------|------------------|-------------|
| `manufacturing_files` | `manufacturing-files/` | Assembly guides, BOMs, compliance docs |
| `design_files` | `design-files/` | CAD models, technical drawings |
| `making_instructions` | `making-instructions/` | Step-by-step build instructions |
| `operating_instructions` | `operating-instructions/` | User manuals, maintenance guides |
| `bom` | `manufacturing-files/bom.{ext}` | Bill of materials (single file) |
| `archive_download` | `software/` | Compressed archives |
| `image` | `metadata/project-image.{ext}` | Project image |

### Part-Specific Files

For each part in the `parts` array:

| Part Field | Target Directory | Description |
|------------|------------------|-------------|
| `source` | `parts/{part-name}/source/` | Source CAD files |
| `export` | `parts/{part-name}/export/` | Exported formats (STEP, etc.) |
| `auxiliary` | `parts/{part-name}/auxiliary/` | Supporting documentation |
| `image` | `parts/{part-name}/images/` | Part images |

### Software Files

For each software entry:

| Software Field | Target Directory | Description |
|----------------|------------------|-------------|
| `release` | `software/` | Software releases |
| `installation_guide` | `software/installation/` | Installation guides |

### Type-Based Organization

Files are further organized by their `DocumentationType`:

- `quality-instructions` → `quality-instructions/`
- `risk-assessment` → `risk-assessment/`
- `schematics` → `schematics/`
- `tool-settings` → `tool-settings/`

## Error Handling

The package builder includes robust error handling:

### Network Issues

- **Retry Logic**: Automatic retry with exponential backoff (default: 3 retries)
- **Timeout Handling**: Configurable timeouts for downloads
- **Partial Success**: Package is built even if some files fail to download

### File Issues

- **Missing Files**: Logged as warnings, package continues building
- **Invalid URLs**: Skipped with error logging
- **Checksum Verification**: Optional verification of downloaded files

### Example Error Output

```
HTTP 404 for https://raw.githubusercontent.com/example/missing.pdf
HTTP 404 for https://raw.githubusercontent.com/example/missing.pdf
HTTP 404 for https://raw.githubusercontent.com/example/missing.pdf
Failed to download https://raw.githubusercontent.com/example/missing.pdf after 3 retries
Failed to download file: Failed to download https://raw.githubusercontent.com/example/missing.pdf after 3 retries
✅ Package built successfully!
📦 Package: org/project/1.0.0
📁 Location: packages/org/project/1.0.0
📄 Files: 8
💾 Size: 2,048,576 bytes
```

## Package Metadata

Each built package includes metadata:

### Build Information (`metadata/build-info.json`)

```json
{
  "package_name": "university-of-bath/openflexure-microscope",
  "version": "5.20",
  "okh_manifest_id": "550e8400-e29b-41d4-a716-446655440000",
  "build_timestamp": "2025-10-13T11:06:06.111890",
  "ohm_version": "1.0.0",
  "total_files": 15,
  "total_size_bytes": 1053656,
  "build_options": {
    "include_design_files": true,
    "include_manufacturing_files": true,
    "include_making_instructions": true,
    "include_software": true,
    "include_parts": true,
    "include_operating_instructions": true,
    "include_quality_instructions": true,
    "include_risk_assessment": true,
    "include_schematics": true,
    "include_tool_settings": true,
    "verify_downloads": true,
    "max_concurrent_downloads": 5,
    "output_dir": "packages"
  }
}
```

### File Manifest (`metadata/file-manifest.json`)

```json
{
  "total_files": 15,
  "total_size_bytes": 1053656,
  "files": [
    {
      "original_url": "https://raw.githubusercontent.com/rwb27/openflexure_microscope/master/test.stl",
      "local_path": "packages/university-of-bath/openflexure-microscope/5.20/design-files/test.stl",
      "content_type": "text/plain; charset=utf-8",
      "size_bytes": 52565,
      "checksum_sha256": "40c4b3cd477bea3b41f12cf93764cc1141b51ddbf08fe7312b88c1d8fea147a9",
      "downloaded_at": "2025-10-13T11:06:06.111890",
      "file_type": "design-files",
      "part_name": null
    },
    {
      "original_url": "https://raw.githubusercontent.com/rwb27/openflexure_microscope/master/docs/0_bill_of_materials.md",
      "local_path": "packages/university-of-bath/openflexure-microscope/5.20/manufacturing-files/0_bill_of_materials.md",
      "content_type": "text/plain; charset=utf-8",
      "size_bytes": 3346,
      "checksum_sha256": "5aa96729d37fec274a6433f3541b0de56263859fa4eed65f892c09da5fc08c6f",
      "downloaded_at": "2025-10-13T11:06:06.111890",
      "file_type": "manufacturing-files",
      "part_name": null
    }
  ]
}
```

## Best Practices

### Package Organization

1. **Use Descriptive Names**: Choose clear, descriptive titles for your OKH manifests
2. **Version Consistently**: Use semantic versioning (e.g., 1.2.4)
3. **Organize Files**: Group related files in appropriate directories
4. **Include Metadata**: Provide complete metadata for better organization

### File Management

1. **Use HTTPS URLs**: Ensure all external links use HTTPS
2. **Provide Fallbacks**: Include alternative file formats when possible
3. **Test Downloads**: Verify that all external links are accessible
4. **Optimize File Sizes**: Compress large files when appropriate

### Build Configuration

1. **Selective Inclusion**: Use build options to exclude unnecessary files
2. **Concurrent Downloads**: Adjust `max_concurrent_downloads` based on your network
3. **Verification**: Enable download verification for critical packages
4. **Output Organization**: Use consistent output directories

## Real-World Testing

The package management system has been successfully tested with real open-source hardware projects:

### OpenFlexure Microscope

The system successfully built a package from the OpenFlexure Microscope project:

```bash
# Build the OpenFlexure Microscope package
ohm package build test-data/openflexure-microscope.okh.json --output-dir packages --verbose
```

**Results:**
- ✅ **15 files downloaded** (1,053,656 bytes)
- ✅ **Real GitHub URLs** from `https://github.com/rwb27/openflexure_microscope`
- ✅ **Mixed file types**: STL files, Markdown documentation, OpenSCAD source files
- ✅ **Graceful error handling**: 2 failed downloads handled without breaking the build
- ✅ **Complete package structure** with all metadata files

**Package Structure Created:**
```
university-of-bath/openflexure-microscope/5.20/
├── design-files/
│   ├── test.stl
│   ├── actuator_assembly_tools.stl
│   └── actuator_column.stl
├── manufacturing-files/
│   ├── 0_bill_of_materials.md
│   ├── 0_printing.md
│   ├── COMPILE.md
│   └── Makefile.bin
├── making-instructions/
│   ├── README.md
│   ├── 1_actuator_assembly.md
│   └── 2a_basic_optics_module.md
├── parts/
│   ├── actuator-assembly-tools/
│   │   ├── source/actuator_assembly_tools.scad
│   │   ├── export/actuator_assembly_tools.stl
│   │   └── auxiliary/1_actuator_assembly.md
│   └── actuator-column/
│       ├── export/actuator_column.stl
│       └── auxiliary/1_actuator_assembly.md
└── metadata/
    ├── build-info.json
    └── file-manifest.json
```

## Troubleshooting

### Common Issues

#### Network Timeouts

```bash
# Increase timeout and retry count
ohm package build manifest.json --max-concurrent 3
```

#### Missing Files

```bash
# Check which files failed
ohm package verify org/project 1.0.0 --verbose
```

#### Invalid URLs

```bash
# Build with verbose output to see URL issues
ohm package build manifest.json --verbose
```

#### Package Listing Issues

If packages don't appear in the list, check the output directory:

```bash
# Verify packages directory exists
ls -la packages/

# Check package structure
find packages/ -name "*.json" | head -5
```

### Debug Mode

For detailed debugging, you can enable debug logging:

```bash
# Set environment variable for debug logging
export LOG_LEVEL=DEBUG
ohm package build manifest.json --verbose
```

## Integration with OHM

The package management system integrates seamlessly with the Open Hardware Manager:

- **Storage Integration**: Built packages can be stored using the existing storage service
- **API Endpoints**: Full REST API for programmatic access
- **CLI Tools**: Command-line interface for interactive use
- **Validation**: Built-in validation using OHM's validation engine

## Current Status

The OKH Package Management system is **fully functional** and ready for production use:

### ✅ Implemented Features

- **Package Building**: Complete package creation from OKH manifests
- **File Resolution**: Automatic downloading and organization of external files
- **Error Handling**: Robust retry logic and graceful failure handling
- **CLI Interface**: Full command-line interface with all operations
- **API Integration**: REST API endpoints for programmatic access
- **Package Management**: List, verify, and delete packages
- **Remote Storage**: PUSH/PULL functionality with Azure Blob Storage
- **Real-World Testing**: Successfully tested with actual open-source hardware projects
- **Metadata Generation**: Package metadata with checksums
- **Standardized Structure**: Consistent directory organization

### Working Commands

```bash
# Build packages
ohm package build manifest.json --output-dir packages --verbose

# List all packages
ohm package list-packages

# Verify package integrity
ohm package verify org/project-name version

# Delete packages
ohm package delete org/project-name version

# Push to remote storage
ohm package push org/project-name version

# Pull from remote storage
ohm package pull org/project-name version

# List remote packages
ohm package list-remote
```

### Remote Storage Integration

- **Azure Blob Storage**: Hierarchical storage structure implemented
- **Package Discovery**: Remote package listing and metadata retrieval
- **Complete Workflow**: Build → Push → Pull → Verify cycle tested
- **Error Handling**: Robust error handling for network and storage issues
- **Metadata Preservation**: All package metadata maintained in remote storage


## Package Pinning (#174)

A **pin record** captures the cryptographic state of a built package at a point in time.
Pinning lets you verify later that no files have changed since the pin was created.

### Creating a Pin

```bash
# Pin via CLI
ohm package pin community/my-project 1.0.0 --by alice --note "pre-release freeze"

# Pin via API
curl -X POST "http://localhost:8001/v1/api/package/community/my-project/1.0.0/pin" \
  -G --data-urlencode "pinned_by=alice" --data-urlencode "note=pre-release freeze"
```

The response includes a `pin_record` with the manifest content hash at pin time:

```json
{
  "status": "success",
  "data": {
    "pin_record": {
      "pinned_at": "2026-06-19T12:00:00Z",
      "pinned_by": "alice",
      "note": "pre-release freeze",
      "manifest_content_hash": "sha256:abc123..."
    }
  }
}
```

### Verifying a Pin

```bash
# Verify via CLI (checks current files against stored pin hash)
ohm package verify-pin community/my-project 1.0.0

# Verify via API
curl "http://localhost:8001/v1/api/package/community/my-project/1.0.0/verify-pin"
```

Response:

```json
{
  "data": {
    "verified": true,
    "changed_files": []
  }
}
```

`verified: false` means at least one file has changed since pinning. `changed_files` lists
the specific paths that differ.

---

## Package Signing (#175)

OHM supports verifying cryptographic signatures attached to built packages.

### Verifying a Signature

```bash
# Verify via CLI
ohm package verify-signature community/my-project 1.0.0

# Verify via API
curl "http://localhost:8001/v1/api/package/community/my-project/1.0.0/verify-signature"
```

Response when valid:

```json
{
  "data": {
    "valid": true,
    "signature_record": {
      "signed_at": "2026-06-19T10:00:00Z",
      "signer": "alice@example.com",
      "algorithm": "ed25519"
    }
  }
}
```

A 404 is returned if the package has no attached signature.

---

## OKH Collection Management (#176)

OHM can export, import, and diff the entire local OKH manifest collection as a zip archive.
This supports backup, sharing between OHM instances, and federation scenarios.

### Archive Format

Each collection archive is a zip file containing:

```
collection-index.json                # Array of summary entries (title, version, content_hash)
manifests/sha256_<first12>.okh.json  # One file per manifest, named by content hash
```

### Exporting a Collection

```bash
# Export via CLI
ohm okh export-collection --output collection.zip

# Export via API
curl "http://localhost:8001/v1/api/okh/export-collection" --output collection.zip
```

Returns a `application/zip` response with `Content-Disposition: attachment; filename=ohm-collection.zip`.
Returns 404 if the collection is empty.

### Importing a Collection

```bash
# Dry run — see what would be imported without writing
ohm okh import-collection collection.zip --dry-run

# Live import
ohm okh import-collection collection.zip
```

**API:**

```bash
curl -X POST "http://localhost:8001/v1/api/okh/import-collection?dry_run=true" \
  -F "file=@collection.zip"
```

Response:

```json
{
  "status": "success",
  "new": [ /* manifests not yet in local collection */ ],
  "duplicate": [ /* manifests already present with same hash */ ],
  "conflict": [ /* manifests with same title+version but different content */ ],
  "imported": 5,
  "dry_run": true
}
```

In dry-run mode `imported` is always 0. In live mode it counts how many new manifests were
written. Duplicates are silently skipped; conflicts are reported but not written.

### Diffing a Collection

```bash
# Compare an archive against the local collection
ohm okh diff-collection collection.zip
```

**API:**

```bash
curl -X POST "http://localhost:8001/v1/api/okh/diff-collection" \
  -F "file=@collection.zip"
```

Response:

```json
{
  "only_in_archive": [ /* summary entries present in the archive but not locally */ ],
  "only_local":    [ /* local manifests not in the archive */ ]
}
```

Diff compares by content hash — identical manifests on both sides are considered equal
regardless of when they were created.

---

## Future Enhancements

Planned features for future releases:

- **Dependency Resolution**: Automatic resolution of package dependencies
- **Delta Updates**: Efficient updates for package versions
- **Package Caching**: Local caching for improved performance
- **Multi-Provider Support**: Support for additional storage providers (S3, GCS, etc.)
- **Package Search**: Advanced search and filtering capabilities
