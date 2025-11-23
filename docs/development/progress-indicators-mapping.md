# Progress Indicators: CLI Actions and Service Dependencies Mapping

This document maps CLI commands to their underlying services and operations, identifying where progress indicators should be integrated.

## Architecture Overview

The OME CLI follows a layered architecture:

```
CLI Command (Click)
    ↓
CLIContext / SmartCommand
    ↓
HTTP API (via APIClient) OR Direct Service Calls (fallback)
    ↓
Service Layer (PackageService, OKHService, MatchingService, etc.)
    ↓
Core Operations (PackageBuilder, GenerationEngine, FileResolver, etc.)
```

## Key Design Patterns

1. **Dual Execution Path**: All commands support both HTTP API calls and direct service fallback
2. **SmartCommand Pattern**: `execute_with_fallback()` handles HTTP → service fallback automatically
3. **Service Singleton Pattern**: Services use `get_instance()` for singleton access
4. **Async Operations**: All long-running operations are async
5. **CLIContext**: Central context object passed to all commands with logging, config, and tracking

## CLI Commands and Service Dependencies

### Package Commands (`src/cli/package.py`)

#### 1. `ome package build` (manifest_file)

**CLI Flow:**
```
build() → SmartCommand.execute_with_fallback()
    ├─ http_build() → APIClient.request("POST", "/api/package/build")
    └─ fallback_build() → PackageService.build_package_from_manifest()
```

**Service Dependencies:**
- `PackageService.build_package_from_manifest()`
  - `PackageBuilder.build_package()`
    - `FileResolver.resolve_files()` - Downloads files (KNOWN TOTAL)
    - File organization and structure creation
    - File validation and checksum calculation
    - Package metadata generation

**Long-Running Operations:**
- File downloads (can be 10s-100s of files)
- File validation
- Package structure creation

**Progress Indicators Needed:**
- Stage 1: "Resolving files..." (indeterminate or file count)
- Stage 2: "Downloading files..." (known total: X/Y files)
- Stage 3: "Validating files..." (known total: X/Y files)
- Stage 4: "Organizing package structure..." (indeterminate)
- Stage 5: "Generating metadata..." (indeterminate)

---

#### 2. `ome package build-from-storage` (manifest_id)

**CLI Flow:**
```
build_from_storage() → SmartCommand.execute_with_fallback()
    ├─ http_build_from_storage() → APIClient.request("POST", "/api/package/build/{id}")
    └─ fallback_build_from_storage() → PackageService.build_package_from_storage()
```

**Service Dependencies:**
- `PackageService.build_package_from_storage()`
  - `OKHService.get_by_id()` - Retrieve manifest
  - `PackageBuilder.build_package()` - Same as above

**Progress Indicators Needed:**
- Same as `package build` above

---

#### 3. `ome package push` (package_name, version)

**CLI Flow:**
```
push() → SmartCommand.execute_with_fallback()
    ├─ http_push() → APIClient.request("POST", "/api/package/push")
    └─ fallback_push() → PackageRemoteStorage.push_package()
```

**Service Dependencies:**
- `PackageService.get_package_metadata()`
- `StorageService` (configured)
- `PackageRemoteStorage.push_package()`
  - File uploads to remote storage (KNOWN TOTAL)
  - Upload verification

**Progress Indicators Needed:**
- Stage 1: "Preparing package..." (indeterminate)
- Stage 2: "Uploading files..." (known total: X/Y files, with size info)
- Stage 3: "Verifying upload..." (indeterminate)

---

#### 4. `ome package pull` (package_name, version)

**CLI Flow:**
```
pull() → SmartCommand.execute_with_fallback()
    ├─ http_pull() → APIClient.request("POST", "/api/package/pull")
    └─ fallback_pull() → PackageRemoteStorage.pull_package()
```

**Service Dependencies:**
- `StorageService` (configured)
- `PackageRemoteStorage.pull_package()`
  - File downloads from remote storage (KNOWN TOTAL)
  - Package verification

**Progress Indicators Needed:**
- Stage 1: "Fetching package metadata..." (indeterminate)
- Stage 2: "Downloading files..." (known total: X/Y files, with size info)
- Stage 3: "Verifying package..." (indeterminate)

---

### OKH Commands (`src/cli/okh.py`)

#### 5. `ome okh generate-from-url` (url)

**CLI Flow:**
```
generate_from_url() → SmartCommand.execute_with_fallback()
    ├─ http_generate() → APIClient.request("POST", "/api/okh/generate-from-url")
    └─ fallback_generate() → OKHService.generate_from_url()
```

**Service Dependencies:**
- `OKHService.generate_from_url()`
  - `URLRouter` - URL validation and platform detection
  - `GitHubExtractor` or `GitLabExtractor` - Repository extraction
    - Repository cloning (if --clone flag)
    - File listing and metadata extraction
    - Content analysis
  - `GenerationEngine.generate_manifest_async()`
    - Project data analysis (INDETERMINATE)
    - LLM-based field generation (if LLM enabled) (INDETERMINATE)
    - File categorization (Layer 1: Heuristics, Layer 2: LLM) (INDETERMINATE)
    - Manifest generation
  - `ReviewInterface.review()` - Interactive review (if not --no-review)

**Long-Running Operations:**
- Repository cloning (if enabled)
- File extraction and analysis
- LLM generation (can take 30s-5min+)
- File categorization (especially with LLM)

**Progress Indicators Needed:**
- Stage 1: "Validating URL..." (indeterminate)
- Stage 2: "Cloning repository..." (if --clone) (indeterminate, with size info)
- Stage 3: "Extracting project data..." (indeterminate)
- Stage 4: "Analyzing files..." (known total: X/Y files)
- Stage 5: "Categorizing files..." (known total: X/Y files)
  - Sub-stage: "Using heuristics..." (fast)
  - Sub-stage: "Using LLM analysis..." (slow, if LLM enabled)
- Stage 6: "Generating manifest..." (indeterminate)
  - Sub-stage: "LLM generation..." (if LLM enabled) (indeterminate)
- Stage 7: "Reviewing manifest..." (if interactive) (indeterminate)

---

#### 6. `ome okh validate` (manifest_file)

**CLI Flow:**
```
validate() → SmartCommand.execute_with_fallback()
    ├─ http_validate() → APIClient.request("POST", "/api/okh/validate")
    └─ fallback_validate() → OKHService.validate()
```

**Service Dependencies:**
- `OKHService.validate()`
  - `OKHValidator.validate()` - Schema validation
  - Field completeness checks
  - LLM validation (if enabled) (INDETERMINATE)

**Progress Indicators Needed:**
- Stage 1: "Reading manifest..." (indeterminate)
- Stage 2: "Validating schema..." (indeterminate)
- Stage 3: "Checking completeness..." (indeterminate)
- Stage 4: "LLM validation..." (if LLM enabled) (indeterminate)

---

#### 7. `ome okh create` (manifest_file)

**CLI Flow:**
```
create() → SmartCommand.execute_with_fallback()
    ├─ http_create() → APIClient.request("POST", "/api/okh/create")
    └─ fallback_create() → OKHService.create()
```

**Service Dependencies:**
- `OKHService.create()`
  - Manifest validation
  - Storage service operations
  - Database operations

**Progress Indicators Needed:**
- Stage 1: "Validating manifest..." (indeterminate)
- Stage 2: "Storing manifest..." (indeterminate)

---

### Matching Commands (`src/cli/match.py`)

#### 8. `ome match requirements` (input_file)

**CLI Flow:**
```
requirements() → SmartCommand.execute_with_fallback()
    ├─ http_match() → APIClient.request("POST", "/api/match")
    └─ fallback_match() → MatchingService.find_matches_with_manifest()
```

**Service Dependencies:**
- `MatchingService.find_matches_with_manifest()`
  - `OKHExtractor.extract_requirements()` - Extract requirements from manifest
  - `OKWService.list()` - Get facilities (INDETERMINATE - depends on storage)
  - `OKHMatcher.match()` - Match requirements to facilities
    - For each facility: capability matching (KNOWN TOTAL: X/Y facilities)
    - Confidence scoring
  - LLM matching (if enabled) (INDETERMINATE)

**Long-Running Operations:**
- Facility loading (can be many facilities)
- Matching algorithm execution (can be slow with many facilities)
- LLM matching (if enabled)

**Progress Indicators Needed:**
- Stage 1: "Reading input file..." (indeterminate)
- Stage 2: "Extracting requirements..." (indeterminate)
- Stage 3: "Loading facilities..." (indeterminate)
- Stage 4: "Matching requirements..." (known total: X/Y facilities)
  - Sub-stage: "LLM matching..." (if LLM enabled) (indeterminate)
- Stage 5: "Ranking results..." (indeterminate)

---

### LLM Commands (`src/cli/llm.py`)

#### 9. `ome llm generate-okh` (project_url)

**CLI Flow:**
```
generate_okh() → _generate_okh_manifest()
    → GenerationEngine.generate_manifest_async()
```

**Service Dependencies:**
- `GenerationEngine.generate_manifest_async()`
  - Repository extraction
  - LLM generation (INDETERMINATE, can be 1-5+ minutes)
  - Manifest assembly

**Progress Indicators Needed:**
- Stage 1: "Extracting project data..." (indeterminate)
- Stage 2: "Generating manifest with LLM..." (indeterminate, with token usage if available)
- Stage 3: "Assembling manifest..." (indeterminate)

---

## Service Layer Details

### PackageService (`src/core/services/package_service.py`)

**Key Methods:**
- `build_package_from_manifest()` → `PackageBuilder.build_package()`
- `build_package_from_storage()` → Retrieves manifest, then builds
- `verify_package()` → File verification
- `list_built_packages()` → Quick operation
- `delete_package()` → Quick operation

**Integration Points for Progress:**
- `PackageBuilder.build_package()` - Main build operation
- `FileResolver.resolve_files()` - File download operations

---

### OKHService (`src/core/services/okh_service.py`)

**Key Methods:**
- `generate_from_url()` → `GenerationEngine.generate_manifest_async()`
- `validate()` → `OKHValidator.validate()`
- `create()` → Storage operations
- `extract_requirements()` → Requirement extraction

**Integration Points for Progress:**
- `GenerationEngine.generate_manifest_async()` - Long-running generation
- `GitHubExtractor.extract_project()` - Repository extraction
- `GitLabExtractor.extract_project()` - Repository extraction

---

### MatchingService (`src/core/services/matching_service.py`)

**Key Methods:**
- `find_matches_with_manifest()` → Matching algorithm
- `get_available_domains()` → Quick operation

**Integration Points for Progress:**
- `find_matches_with_manifest()` - Matching loop over facilities
- Facility loading operations

---

### GenerationEngine (`src/core/generation/engine.py`)

**Key Methods:**
- `generate_manifest_async()` - Main generation method
  - Project data analysis
  - LLM field generation
  - File categorization
  - Manifest assembly

**Integration Points for Progress:**
- File analysis loop
- LLM generation calls
- File categorization loop

---

### PackageBuilder (`src/core/packaging/builder.py`)

**Key Methods:**
- `build_package()` - Main build method
  - File resolution
  - File downloads
  - Structure creation
  - Validation

**Integration Points for Progress:**
- File download loop (known total)
- File validation loop (known total)
- Structure creation (indeterminate)

---

## Progress Indicator Integration Strategy

### Layer 1: CLI Command Level (Recommended Starting Point)

**Location:** `src/cli/package.py`, `src/cli/okh.py`, `src/cli/match.py`

**Approach:**
- Add progress tracking at the CLI command level
- Wrap service calls with progress context managers
- Use `CLIContext` to manage progress state

**Advantages:**
- Works for both HTTP and fallback paths
- No changes to service layer required initially
- Can be implemented incrementally

**Limitations:**
- Less granular progress for HTTP API calls
- Progress updates only at command boundaries

---

### Layer 2: Service Level (Future Enhancement)

**Location:** `src/core/services/*.py`

**Approach:**
- Add progress callbacks to service methods
- Services report progress to CLI via callbacks
- More granular progress updates

**Advantages:**
- More detailed progress information
- Works for both CLI and API usage
- Better integration with metrics system

**Limitations:**
- Requires changes to service interfaces
- More complex implementation

---

### Layer 3: Core Operation Level (Advanced)

**Location:** `src/core/packaging/builder.py`, `src/core/generation/engine.py`

**Approach:**
- Progress tracking at the lowest level
- Operations report progress directly
- Maximum granularity

**Advantages:**
- Most detailed progress information
- Can track individual file operations

**Limitations:**
- Most invasive changes
- Requires careful design to avoid performance impact

---

## Recommended Implementation Plan

### Phase 1: CLI-Level Progress (Quick Wins)

1. **Create Progress Utility Module** (`src/cli/progress.py`)
   - Progress context managers
   - Integration with `CLIContext`
   - Support for both determinate and indeterminate progress

2. **Implement in High-Value Commands:**
   - `ome package build` - File downloads (known total)
   - `ome package push/pull` - File transfers (known total)
   - `ome okh generate-from-url` - Multi-stage operation

3. **Integration Points:**
   - Wrap `SmartCommand.execute_with_fallback()` calls
   - Add progress stages before/after service calls
   - Use `CLIContext` for progress state management

### Phase 2: Service-Level Callbacks (Enhanced Detail)

1. **Add Progress Callback Interface**
   - Define `ProgressCallback` protocol
   - Services accept optional progress callbacks
   - CLI provides callbacks to services

2. **Implement in Key Services:**
   - `PackageBuilder` - File download progress
   - `GenerationEngine` - Generation stages
   - `MatchingService` - Matching progress

### Phase 3: Metrics Integration (Smart ETAs)

1. **Integrate with Metrics System**
   - Use historical data for ETA estimation
   - Report progress milestones to metrics
   - Stage-level performance tracking

---

## Key Considerations

### 1. HTTP vs Direct Service Calls

- **HTTP Path**: Progress indicators must work with async HTTP requests
  - Can show connection status
  - Limited granularity (only know when request completes)
  - May need streaming responses for detailed progress

- **Direct Service Path**: Full control over progress reporting
  - Can track individual operations
  - More granular progress updates
  - Better integration opportunities

### 2. Async Compatibility

- All progress updates must be async-safe
- Use async-compatible progress libraries (`rich.progress` or `tqdm.asyncio`)
- Avoid blocking the event loop

### 3. Output Format Handling

- Suppress progress in `--json` mode
- Respect `--verbose` flag
- Handle terminal redirection gracefully

### 4. Error Handling

- Progress indicators must clean up on errors
- Don't leave progress bars hanging
- Clear error messages

### 5. Performance Impact

- Progress updates should be lightweight
- Batch updates when possible
- Don't update on every iteration (throttle)

---

## Next Steps

1. **Review and Validate Mapping**: Confirm accuracy of service dependencies
2. **Choose Integration Layer**: Decide on Phase 1, 2, or 3 approach
3. **Design Progress API**: Define interfaces for progress reporting
4. **Implement Proof of Concept**: Start with one command (e.g., `package build`)
5. **Iterate and Expand**: Add progress to other commands incrementally

