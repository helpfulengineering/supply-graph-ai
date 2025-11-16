# Version & Metadata Implementation Specification

## Overview

This specification defines the implementation plan for fixing version and timestamp metadata issues. These are minor but important for accurate package metadata and tracking.

## Current State Analysis

### Issue 1: Hardcoded OME Version

**Location**: `src/core/packaging/builder.py:703`

**Current Implementation:**
```python
# Get OME version (placeholder for now)
ome_version = "1.0.0"  # TODO: Get from actual version
```

**Problems:**
- Hardcoded version string "1.0.0"
- Doesn't reflect actual package version
- Version is defined in `src/cli/__init__.py` as `__version__ = "1.0.0"`
- Also hardcoded in `src/core/main.py:81` as `version="1.0.0"`

**Context:**
- Used in `PackageMetadata.ome_version` field
- Indicates which version of OME built the package
- Important for package tracking and compatibility

### Issue 2: Hardcoded "now" Timestamp

**Location**: `src/core/generation/services/repository_mapping_service.py:183`

**Current Implementation:**
```python
# Update metadata
routing_table.metadata["last_updated"] = "now"  # TODO: Use proper timestamp
```

**Problems:**
- Uses string "now" instead of actual timestamp
- Not useful for tracking when routing table was updated
- Should use ISO format datetime string

**Context:**
- Used in `RepositoryRoutingTable.metadata` dictionary
- Tracks when routing table was last updated
- Used for cache invalidation and debugging

### Version Definition Locations

**Found in codebase:**
- `src/cli/__init__.py`: `__version__ = "1.0.0"`
- `src/core/main.py:81`: `version="1.0.0"` (FastAPI app)
- `src/core/main.py:152`: `version="1.0.0"` (API v1)
- Multiple other places with hardcoded "1.0.0"

## Requirements

### Functional Requirements

1. **Version Management**
   - Single source of truth for OME version
   - Easy to update version in one place
   - Accessible from all modules that need it
   - Support for semantic versioning

2. **Timestamp Management**
   - Use proper ISO format datetime strings
   - Consistent timestamp format across codebase
   - Timezone-aware timestamps (UTC)

3. **Backward Compatibility**
   - Existing code continues to work
   - No breaking changes to APIs
   - Metadata format remains compatible

### Non-Functional Requirements

1. **Maintainability**
   - Easy to update version
   - Clear version definition location
   - Consistent timestamp format

2. **Accuracy**
   - Version reflects actual package version
   - Timestamps are accurate and consistent

## Design Decisions

### Version Management Strategy

**Option 1: Central Version Module (Recommended)**
- Create `src/core/version.py` with `__version__` constant
- Import from this module everywhere
- Single source of truth
- Easy to update

**Option 2: Use importlib.metadata**
- Use `importlib.metadata.version("package-name")`
- Requires package to be installed
- May not work in development mode

**Option 3: Read from pyproject.toml**
- Parse `pyproject.toml` at runtime
- More complex, requires toml parsing
- Version defined in build system

**Decision: Option 1 (Central Version Module)**
- Simplest and most reliable
- Works in all environments
- Easy to maintain
- Can be extended later to read from pyproject.toml if needed

### Timestamp Strategy

**Use datetime.now().isoformat()**
- Standard ISO 8601 format
- Timezone-aware (UTC)
- Consistent with existing codebase patterns
- Easy to parse and compare

## Implementation Specification

### 1. Create Version Module

**File: `src/core/version.py` (new file)**

```python
"""
Version information for Open Matching Engine (OME).

This module provides a single source of truth for the OME version.
Update this value when releasing a new version.
"""

__version__ = "1.0.0"

# Version components for programmatic access
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

def get_version() -> str:
    """Get the current OME version."""
    return __version__

def get_version_tuple() -> tuple:
    """Get version as a tuple (major, minor, patch)."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
```

### 2. Update Package Builder

**File: `src/core/packaging/builder.py`**

**Update import and version usage:**

```python
# Add import at top of file
from ..version import get_version

# Update _generate_package_metadata method
async def _generate_package_metadata(
    self,
    manifest: OKHManifest,
    package_path: Path,
    package_name: str,
    file_inventory: List[FileInfo],
    options: BuildOptions
) -> PackageMetadata:
    """Generate package metadata"""
    # Calculate total size
    total_size = sum(f.size_bytes for f in file_inventory)
    
    # Get OME version from version module
    ome_version = get_version()
    
    return PackageMetadata(
        package_name=package_name,
        version=manifest.version,
        okh_manifest_id=manifest.id,
        build_timestamp=datetime.now(),
        ome_version=ome_version,
        total_files=len(file_inventory),
        total_size_bytes=total_size,
        file_inventory=file_inventory,
        build_options=options,
        package_path=str(package_path)
    )
```

### 3. Update Main Application

**File: `src/core/main.py`**

**Update FastAPI app version:**

```python
# Add import at top of file
from .version import get_version

# Update FastAPI app creation
app = FastAPI(
    title="Open Matching Engine API",
    description="API for matching OKH requirements with OKW capabilities",
    version=get_version(),  # Use version from module
    lifespan=lifespan
)

# Update API v1 creation
api_v1 = FastAPI(
    title="Open Matching Engine API v1",
    description="Version 1 of the Open Matching Engine API",
    version=get_version()  # Use version from module
)

# Update domain metadata (if needed)
# In register_domain_components function:
cooking_metadata = DomainMetadata(
    name="cooking",
    display_name="Cooking & Food Preparation",
    description="Domain for recipe and kitchen capability matching",
    version=get_version(),  # Or keep domain-specific version if different
    # ... rest of metadata
)

manufacturing_metadata = DomainMetadata(
    name="manufacturing",
    display_name="Manufacturing & Hardware Production",
    description="Domain for OKH/OKW manufacturing capability matching",
    version=get_version(),  # Or keep domain-specific version if different
    # ... rest of metadata
)
```

### 4. Update Repository Mapping Service

**File: `src/core/generation/services/repository_mapping_service.py`**

**Update timestamp usage:**

```python
# Add import at top of file
from datetime import datetime

# Update update_routing_table method
async def update_routing_table(
    self,
    routing_table: RepositoryRoutingTable,
    categorizations: Dict[str, FileCategorizationResult]
) -> RepositoryRoutingTable:
    """Update routing table with new categorizations."""
    # ... existing code ...
    
    # Update metadata with proper timestamp
    routing_table.metadata["last_updated"] = datetime.now().isoformat()
    routing_table.metadata["updated_routes"] = updated_count
    
    # ... rest of method ...
```

### 5. Update CLI Version

**File: `src/cli/__init__.py`**

**Update to import from version module:**

```python
"""
CLI package for Open Matching Engine.
"""

from ...core.version import __version__

__all__ = ["__version__"]
```

### 6. Optional: Update Other Hardcoded Versions

**Files with hardcoded "1.0.0":**

Consider updating these to use `get_version()` if they should reflect OME version:

- `src/core/services/base.py:95` - ServiceConfig default version
- `src/core/services/okw_service.py:316,337` - OKW service responses
- `src/core/services/matching_service.py:755,776` - Matching service responses
- `src/core/services/service_registry.py:266,289` - Service registry
- `src/config/domains.py:54,67` - Domain configurations

**Decision:** Only update if these should reflect OME version. Some may be domain-specific or service-specific versions that should remain separate.

### 7. Update Documentation

**File: `README.md` or version documentation**

**Add version management section:**

```markdown
## Version Management

The OME version is defined in `src/core/version.py`. To update the version:

1. Update `__version__` in `src/core/version.py`
2. Update `VERSION_MAJOR`, `VERSION_MINOR`, `VERSION_PATCH` if needed
3. The version will automatically be used throughout the codebase

The version follows semantic versioning (MAJOR.MINOR.PATCH).
```

## Integration Points

### 1. Package Metadata

- `PackageMetadata.ome_version` now uses actual version
- Important for package tracking and compatibility checking

### 2. API Versioning

- FastAPI app version reflects actual OME version
- API documentation shows correct version

### 3. Routing Table Metadata

- Timestamps are now ISO format datetime strings
- Can be parsed and compared programmatically
- Useful for cache invalidation

### 4. CLI Version

- CLI version command (if exists) shows correct version
- Consistent with package version

## Testing Considerations

### Unit Tests

1. **Version Module Tests:**
   - Test `get_version()` returns correct version
   - Test `get_version_tuple()` returns correct tuple
   - Test version format is valid semantic version

2. **Package Builder Tests:**
   - Test `ome_version` in PackageMetadata uses actual version
   - Test version is not hardcoded

3. **Repository Mapping Tests:**
   - Test timestamp is ISO format
   - Test timestamp is current (within reasonable range)

### Integration Tests

1. **End-to-End Version:**
   - Test package metadata includes correct version
   - Test API responses include correct version

## Migration Plan

### Phase 1: Implementation (Current)
- Create version module
- Update package builder
- Update repository mapping service
- Update main application
- Update CLI

### Phase 2: Cleanup (Optional)
- Update other hardcoded versions if needed
- Add version command to CLI
- Add version endpoint to API

## Success Criteria

1. ✅ Version is defined in single location
2. ✅ Package metadata uses actual version
3. ✅ Timestamps use proper ISO format
4. ✅ All TODOs are resolved
5. ✅ No hardcoded version strings in critical paths
6. ✅ Backward compatibility maintained
7. ✅ Tests pass

## Open Questions / Future Enhancements

1. **Version from pyproject.toml:**
   - Should version be read from pyproject.toml?
   - Would require toml parsing library
   - More complex but keeps version in build system

2. **Automatic Version Bumping:**
   - Should version be automatically bumped on release?
   - Could use git tags or CI/CD
   - Requires build/release automation

3. **Version Endpoint:**
   - Should API expose version endpoint?
   - Useful for client compatibility checking
   - Could include version, build date, git commit

4. **Version in Logs:**
   - Should version be included in startup logs?
   - Useful for debugging and support
   - Easy to add

## Dependencies

### No New Dependencies

- Uses only standard library (`datetime`)
- No external packages required

## Implementation Order

1. Create `src/core/version.py` module
2. Update `src/core/packaging/builder.py` to use version
3. Update `src/core/generation/services/repository_mapping_service.py` to use proper timestamp
4. Update `src/core/main.py` to use version
5. Update `src/cli/__init__.py` to import version
6. Update other hardcoded versions (optional)
7. Write tests
8. Update documentation

## Notes

### Version Format

- Currently using semantic versioning: `MAJOR.MINOR.PATCH`
- Example: `1.0.0`
- Can be extended to include pre-release or build metadata if needed

### Timestamp Format

- ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.ffffff`
- Example: `2024-01-15T12:30:45.123456`
- UTC timezone (no timezone offset in string, assumed UTC)
- Can be extended to include timezone if needed

### Backward Compatibility

- Existing PackageMetadata with hardcoded version will still work
- New packages will use actual version
- Timestamp format change is backward compatible (strings can be parsed)

