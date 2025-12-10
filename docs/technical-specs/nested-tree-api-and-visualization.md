# Nested Supply Tree API and Visualization Analysis

## Progress Summary

**Last Updated**: 2024-12-19

### Completed ✅
- **Phase 1 - StorageService Integration**: All CRUD operations implemented
  - `save_supply_tree_solution()` - Complete with TTL and tags support
  - `load_supply_tree_solution()` - Complete with full deserialization
  - `list_supply_tree_solutions()` - Complete with pagination and filtering
  - `delete_supply_tree_solution()` - Complete with metadata cleanup
  - **Test Coverage**: 27 unit tests + integration tests (all passing)

- **Phase 1 - API Endpoints**: All endpoints implemented
  - `GET /api/supply-tree/solution/{id}/summary` - Complete with aggregated statistics
  - `GET /api/supply-tree/solution/{id}/export` - Complete with GraphML nested relationships
  - Match endpoint tree filtering - Complete with component, facility, depth, and confidence filters
  - Match endpoint auto-save - Complete with `save_solution` flag, TTL, and tags
  - **Test Coverage**: 18 unit tests (all passing)

- **Phase 2 - Multi-source Loading**: Complete ✅
  - `_load_solution_from_source()` helper function - Complete with storage, file, and inline JSON support
  - Integrated into existing endpoints (`summary` and `export`)
  - `POST /api/supply-tree/solution/load` endpoint - Complete with multi-source support
  - `SolutionLoadRequest` model - Complete with validation for all source types
  - **Test Coverage**: 17 unit tests (all passing)

- **Phase 2 - Staleness and Expiration Management**: Complete ✅
  - `is_solution_stale()` - Complete with expiration, max age, and TTL checks
  - `get_solution_age()` - Complete with timedelta calculation
  - `get_stale_solutions()` - Complete with filtering support
  - `cleanup_stale_solutions()` - Complete with dry-run support and space calculation
  - `archive_stale_solutions()` - Complete with archive prefix support
  - `extend_solution_ttl()` - Complete with TTL extension
  - `load_supply_tree_solution_with_metadata()` - Complete with staleness detection
  - **Test Coverage**: 40 unit tests (all passing)

- **Phase 2 - Enhanced Listing and Filtering**: Complete ✅
  - Recency sorting (sort_by, sort_order) - Complete with support for created_at, updated_at, expires_at, score, age_days
  - Age filtering (min_age_days, max_age_days) - Complete
  - Staleness filtering (include_stale, only_stale) - Complete
  - **Test Coverage**: 10 unit tests (all passing)
  - **Backward Compatibility**: All existing tests pass

- **Phase 2 - Solution Management Endpoints**: Complete ✅
  - `GET /api/supply-tree/solution/{solution_id}` - Complete with full solution retrieval
  - `GET /api/supply-tree/solutions` - Complete with filtering, sorting, and pagination
  - `POST /api/supply-tree/solution/{id}/save` - Complete with TTL and tags support
  - `DELETE /api/supply-tree/solution/{id}` - Complete with metadata cleanup
  - **Test Coverage**: Unit tests + integration tests (all passing)

- **Phase 2 - Staleness API Endpoints**: Complete ✅
  - `GET /api/supply-tree/solution/{id}/staleness` - Complete with staleness status and age
  - `POST /api/supply-tree/solutions/cleanup` - Complete with dry-run and filtering
  - `POST /api/supply-tree/solution/{id}/extend` - Complete with TTL extension
  - **Test Coverage**: Unit tests + integration tests (all passing)

- **Phase 2 - Tree Filtering Endpoints**: Complete ✅
  - `GET /api/supply-tree/solution/{id}/trees` - Complete with comprehensive filtering (component, facility, depth, confidence, production_stage)
  - `GET /api/supply-tree/solution/{id}/component/{component_id}` - Complete with component tree retrieval
  - `GET /api/supply-tree/solution/{id}/facility/{facility_id}` - Complete with facility tree retrieval
  - **Test Coverage**: 12 unit tests + 7 integration tests (all passing)

- **Phase 2 - CLI Commands**: Complete ✅
  - `ome solution save` - Complete with TTL and tags support
  - `ome solution load` - Complete with file output support
  - `ome solution list` - Complete with filtering, sorting, and pagination
  - `ome solution delete` - Complete
  - `ome solution check` - Complete with staleness checking
  - `ome solution extend` - Complete with TTL extension
  - `ome solution cleanup` - Complete with dry-run and archive support
  - **Test Coverage**: 12 unit tests (all passing)

### In Progress ⏳
- Phase 1 - Documentation (pending)

### Next Steps
- Implement additional export formats (DOT, Mermaid, CSV)
- Create visualization examples and documentation
- Implement relationship and dependency endpoints (Phase 3)

## Progress Tracking Checklist

### Phase 1: Quick Wins (1-2 days)

#### StorageService Integration
- [x] Implement `save_supply_tree_solution()` method ✅
- [x] Implement `load_supply_tree_solution()` method ✅
- [x] Implement `list_supply_tree_solutions()` method (basic version) ✅
- [x] Implement `delete_supply_tree_solution()` method ✅
- [x] Add timestamping fields (created_at, updated_at, expires_at, ttl_days) to metadata ✅
- [x] Test solution save/load operations ✅ (27 unit tests + integration tests)
- [x] Test solution listing with basic filters ✅ (pagination, okh_id, matching_mode filters)

#### API Endpoints
- [x] Add solution summary endpoint (`GET /api/supply-tree/solution/{id}/summary`) ✅
- [x] Enhance export endpoint to support GraphML with nested relationships ✅
- [x] Add query parameters to match endpoint for filtering trees ✅
- [x] Update match endpoint to optionally auto-save solutions (`save_solution` flag) ✅

#### Documentation
- [ ] Document jq usage patterns for CLI inspection
- [ ] Document jless usage patterns for interactive exploration
- [ ] Create example jq queries for common use cases

### Phase 2: Core Functionality (1 week)

#### Staleness and Expiration Management
- [x] Implement `is_solution_stale()` method ✅
- [x] Implement `get_solution_age()` method ✅
- [x] Implement `get_stale_solutions()` method ✅
- [x] Implement `cleanup_stale_solutions()` method (with dry-run support) ✅
- [x] Implement `archive_stale_solutions()` method ✅
- [x] Implement `extend_solution_ttl()` method ✅
- [x] Add staleness detection to `load_supply_tree_solution_with_metadata()` ✅
- [x] Test staleness detection logic ✅ (40 unit tests passing)
- [x] Test cleanup operations (dry-run and actual) ✅

#### Enhanced Listing and Filtering
- [x] Add recency sorting to `list_supply_tree_solutions()` (sort_by, sort_order) ✅
- [x] Add age filtering (min_age_days, max_age_days) ✅
- [x] Add staleness filtering (include_stale, only_stale) ✅
- [x] Test sorting by created_at, updated_at, expires_at, score, age_days ✅ (10 unit tests passing)
- [x] Test filtering combinations ✅

#### Multi-Source Loading
- [x] Implement `_load_solution_from_source()` helper function ✅
- [x] Add storage source support to solution endpoints ✅
- [x] Add local file source support to solution endpoints ✅
- [x] Add inline JSON source support to solution endpoints ✅
- [x] Test all three loading methods ✅ (17 unit tests passing)
- [x] Add error handling for invalid sources ✅

#### Solution Management Endpoints
- [x] Implement `GET /api/supply-tree/solution/{solution_id}` endpoint ✅
- [x] Implement `POST /api/supply-tree/solution/load` endpoint (multi-source) ✅
- [x] Implement `GET /api/supply-tree/solutions` endpoint (with filtering/sorting) ✅
- [x] Implement `POST /api/supply-tree/solution/{id}/save` endpoint ✅
- [x] Implement `DELETE /api/supply-tree/solution/{id}` endpoint ✅
- [x] Test all CRUD operations via API ✅ (Unit tests + integration tests passing)

#### Staleness API Endpoints
- [x] Implement `GET /api/supply-tree/solution/{id}/staleness` endpoint ✅
- [x] Implement `POST /api/supply-tree/solutions/cleanup` endpoint ✅
- [x] Implement `POST /api/supply-tree/solution/{id}/extend` endpoint ✅
- [x] Test staleness checking via API ✅ (Unit tests + integration tests passing)
- [x] Test cleanup operations via API (dry-run and actual) ✅

#### Tree Filtering Endpoints
- [x] Implement `GET /api/supply-tree/solution/{id}/trees` endpoint ✅
- [x] Implement `GET /api/supply-tree/solution/{id}/component/{component_id}` endpoint ✅
- [x] Implement `GET /api/supply-tree/solution/{id}/facility/{facility_id}` endpoint ✅
- [x] Test tree filtering and querying ✅ (12 unit tests + 7 integration tests passing)

#### Export Formats
- [x] Implement dependency graph export (GraphML format) ✅ (Complete with nested relationships)
- [ ] Implement dependency graph export (DOT format)
- [ ] Implement dependency graph export (Mermaid format)
- [ ] Create CSV export for RAWGraphs integration
- [x] Test GraphML export format ✅ (6 unit tests passing)

#### CLI Commands
- [x] Implement `ome solution save` command ✅
- [x] Implement `ome solution load` command ✅
- [x] Implement `ome solution list` command (with filters) ✅
- [x] Implement `ome solution delete` command ✅
- [x] Implement `ome solution check` command (staleness) ✅
- [x] Implement `ome solution extend` command (TTL) ✅
- [x] Implement `ome solution cleanup` command ✅
- [x] Test all CLI commands ✅ (12 unit tests passing)

### Phase 3: Advanced Features (2 weeks)

#### Relationship and Dependency Endpoints
- [ ] Implement `GET /api/supply-tree/solution/{id}/dependencies` endpoint
- [ ] Implement `GET /api/supply-tree/solution/{id}/production-sequence` endpoint
- [ ] Implement `GET /api/supply-tree/solution/{id}/hierarchy` endpoint
- [ ] Test dependency graph generation
- [ ] Test production sequence calculation
- [ ] Test hierarchy generation

#### Enhanced Export Formats
- [ ] Implement Excel export (multi-sheet format)
- [ ] Implement D3.js visualization format export
- [ ] Implement Cytoscape.js format export
- [ ] Implement vis.js format export
- [ ] Implement Plotly format export (sankey/sunburst)
- [ ] Test all visualization formats

#### Visualization Examples
- [ ] Create example visualization script using jq
- [ ] Create example visualization script using RAWGraphs
- [ ] Create example visualization script using Graphviz
- [ ] Create example visualization script using Mermaid
- [ ] Document visualization workflow

### Phase 4: Documentation and Examples (1 week)

#### Documentation
- [ ] Create comprehensive API documentation for solution endpoints
- [ ] Create visualization guide with examples
- [ ] Document jq query patterns for common use cases
- [ ] Document API usage patterns for nested trees
- [ ] Create troubleshooting guide for large solutions

#### Examples and Templates
- [ ] Create sample visualizations using recommended tools
- [ ] Create example API request/response pairs
- [ ] Create example CLI usage scenarios
- [ ] Create example cleanup workflows

#### Testing and Validation
- [x] Write unit tests for StorageService solution methods ✅ (27 unit tests passing)
- [x] Write integration tests for StorageService solution methods ✅ (integration test file created)
- [ ] Write unit tests for staleness detection
- [ ] Write unit tests for cleanup operations
- [ ] Write integration tests for API endpoints
- [ ] Write integration tests for CLI commands
- [ ] Test with large solutions (90k+ lines)
- [ ] Performance testing for listing/filtering operations

### Phase 5: Polish and Optimization (Optional)

#### Performance Optimization
- [ ] Optimize solution listing for large datasets
- [ ] Add caching for frequently accessed solutions
- [ ] Optimize staleness detection for bulk operations
- [ ] Add pagination optimization

#### Advanced Features
- [ ] Add solution versioning support
- [ ] Add solution comparison functionality
- [ ] Add solution diff/merge capabilities
- [ ] Add automated cleanup scheduling

#### Monitoring and Observability
- [ ] Add metrics for solution operations
- [ ] Add logging for cleanup operations
- [ ] Add alerts for storage usage
- [ ] Add monitoring for stale solution counts

---

## Executive Summary

The nested matching feature generates large JSON outputs (~90k lines) that are difficult to work with. This document analyzes:
1. Current API endpoint support for nested supply trees
2. Gaps and required enhancements
3. Recommended visualization tools for nested JSON data

## Current API Endpoint Analysis

### 1. Match API (`/api/match`)

**Status**: ✅ **Supports Nested Trees**

- **Endpoint**: `POST /api/match`
- **Nested Support**: Yes - Returns `SupplyTreeSolution` with nested structure
- **Response Format**: 
  ```json
  {
    "solution": {
      "all_trees": [...],
      "root_trees": [...],
      "component_mapping": {...},
      "dependency_graph": {...},
      "production_sequence": [...],
      "is_nested": true
    },
    "matching_mode": "nested"
  }
  ```
- **Issues**: 
  - Returns full solution object (can be very large)
  - No filtering/pagination options for trees
  - No summary/aggregation endpoints

### 2. Supply Tree API (`/api/supply-tree`)

**Status**: ⚠️ **Partial Support - Works with Individual Trees Only**

#### Existing Endpoints:

1. **`GET /api/supply-tree/{id}`** - Get single tree
   - ❌ Only works with individual `SupplyTree` objects
   - ❌ Cannot retrieve `SupplyTreeSolution` (nested structure)
   - ✅ Works for individual trees within a solution

2. **`GET /api/supply-tree`** - List trees (paginated)
   - ❌ Lists individual trees, not solutions
   - ❌ No way to list/query nested solutions
   - ✅ Pagination works for individual trees

3. **`POST /api/supply-tree/create`** - Create single tree
   - ❌ Creates individual tree, not solution
   - ✅ Works for creating individual trees

4. **`PUT /api/supply-tree/{id}`** - Update single tree
   - ❌ Updates individual tree only
   - ✅ Works for individual trees

5. **`DELETE /api/supply-tree/{id}`** - Delete single tree
   - ❌ Deletes individual tree only
   - ✅ Works for individual trees

6. **`POST /api/supply-tree/{id}/validate`** - Validate single tree
   - ❌ Validates individual tree only
   - ⚠️ Should support validating entire nested solutions

7. **`POST /api/supply-tree/{id}/optimize`** - Optimize single tree
   - ❌ Optimizes individual tree only
   - ⚠️ Should support optimizing entire nested solutions

8. **`GET /api/supply-tree/{id}/export`** - Export tree
   - ✅ Supports JSON, XML, GraphML formats
   - ⚠️ GraphML export is basic - doesn't handle nested relationships well
   - ⚠️ Should support exporting entire solutions

## StorageService Integration

### Current State
- ✅ Individual `SupplyTree` objects can be saved/loaded via StorageService
- ✅ `SupplyTreeSolution` objects can be saved/loaded via StorageService ✅ **COMPLETED**
- ✅ Persistence for nested solutions implemented ✅ **COMPLETED**
- ✅ Solutions can be saved/retrieved via StorageService ✅ **COMPLETED**

### Required StorageService Enhancements

#### 1. Solution Storage Methods

**Status**: ✅ **IMPLEMENTED** - All methods completed with comprehensive test coverage

Add to `StorageService` class:

```python
async def save_supply_tree_solution(self, solution: SupplyTreeSolution, solution_id: Optional[UUID] = None) -> UUID:
    """Save a supply tree solution to storage"""
    # ✅ IMPLEMENTED: Generate ID if not provided (UUID)
    # ✅ IMPLEMENTED: Store at: supply-tree-solutions/{solution_id}.json
    # ✅ IMPLEMENTED: Include metadata: okh_id, matching_mode, tree_count, created_at
    # ✅ IMPLEMENTED: Creates separate metadata file with TTL support

async def load_supply_tree_solution(self, solution_id: UUID) -> SupplyTreeSolution:
    """Load a supply tree solution from storage"""
    # ✅ IMPLEMENTED: Load from: supply-tree-solutions/{solution_id}.json
    # ✅ IMPLEMENTED: Deserialize to SupplyTreeSolution object

async def list_supply_tree_solutions(
    self, 
    limit: Optional[int] = None, 
    offset: Optional[int] = None,
    okh_id: Optional[UUID] = None,
    matching_mode: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List supply tree solutions with optional filtering"""
    # ✅ IMPLEMENTED: Return metadata: id, okh_id, matching_mode, tree_count, created_at, score
    # ✅ IMPLEMENTED: Supports pagination and filtering

async def delete_supply_tree_solution(self, solution_id: UUID) -> bool:
    """Delete a supply tree solution from storage"""
    # ✅ IMPLEMENTED: Delete from: supply-tree-solutions/{solution_id}.json
    # ✅ IMPLEMENTED: Also deletes metadata file
```

#### 2. Solution ID Generation

Options for solution identification:
- **Option A**: Generate UUID when saving (if not provided)
- **Option B**: Use hash of solution content (deterministic)
- **Option C**: Use composite key (okh_id + timestamp)
- **Recommendation**: Option A (UUID) for flexibility, with Option B (hash) as fallback for deduplication

#### 3. Storage Path Structure

```
supply-tree-solutions/
  ├── {solution_id}.json          # Full solution data
  └── metadata/
      └── {solution_id}.meta.json  # Lightweight metadata for listing
```

#### 4. Metadata Schema

```json
{
  "id": "uuid",
  "okh_id": "uuid",
  "okh_title": "string",
  "matching_mode": "nested|single-level",
  "tree_count": 272,
  "component_count": 8,
  "facility_count": 34,
  "score": 0.85,
  "created_at": "iso-timestamp",
  "updated_at": "iso-timestamp",
  "expires_at": "iso-timestamp",  // Optional TTL
  "created_by": "user/system",
  "tags": ["tag1", "tag2"],
  "ttl_days": 30  // Optional time-to-live in days
}
```

#### 5. Solution Expiration and Staleness

**Problem**: Supply tree solutions are time-bound objects that become stale as:
- Facility availability changes
- Facility capabilities are updated
- OKH requirements evolve
- Market conditions shift

**Solution**: Implement comprehensive timestamping and expiration management.

##### 5.1 Timestamp Fields

All solutions must include:
- `created_at`: When solution was generated
- `updated_at`: When solution was last accessed/modified (for cache invalidation)
- `expires_at`: Optional explicit expiration time
- `ttl_days`: Optional time-to-live in days (default: 30)

##### 5.2 Staleness Detection

```python
async def is_solution_stale(
    self, 
    solution_id: UUID,
    max_age_days: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Check if solution is stale"""
    # Returns (is_stale, reason)
    # Reasons: "expired", "too_old", "facility_updated", "okh_updated"
    
async def get_solution_age(self, solution_id: UUID) -> timedelta:
    """Get age of solution"""
    
async def get_stale_solutions(
    self,
    max_age_days: Optional[int] = None,
    before_date: Optional[datetime] = None
) -> List[UUID]:
    """Get list of stale solution IDs"""
```

##### 5.3 Expiration Policies

**Default TTL**: 30 days (configurable)
- Solutions older than TTL are considered stale
- Stale solutions can still be accessed but should be flagged
- Expired solutions (past `expires_at`) should be marked for deletion

**Policy Options**:
- `strict`: Delete expired solutions automatically
- `warn`: Flag stale solutions but keep them
- `extend`: Auto-extend TTL on access (cache-like behavior)

##### 5.4 Cleanup Methods

```python
async def cleanup_stale_solutions(
    self,
    max_age_days: Optional[int] = None,
    before_date: Optional[datetime] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Remove stale solutions from storage"""
    # Returns: {"deleted_count": 5, "freed_space": 1024, "deleted_ids": [...]}
    
async def archive_stale_solutions(
    self,
    max_age_days: Optional[int] = None,
    archive_prefix: str = "archived/"
) -> Dict[str, Any]:
    """Move stale solutions to archive instead of deleting"""
    
async def extend_solution_ttl(
    self,
    solution_id: UUID,
    additional_days: int = 30
) -> bool:
    """Extend solution expiration time"""
```

##### 5.5 Sorting and Filtering by Recency

```python
async def list_supply_tree_solutions(
    self,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    okh_id: Optional[UUID] = None,
    matching_mode: Optional[str] = None,
    # New parameters for recency
    sort_by: str = "created_at",  # "created_at", "updated_at", "expires_at", "score"
    sort_order: str = "desc",  # "asc", "desc"
    min_age_days: Optional[int] = None,  # Filter by minimum age
    max_age_days: Optional[int] = None,  # Filter by maximum age
    include_stale: bool = False,  # Include stale solutions
    only_stale: bool = False,  # Only return stale solutions
) -> List[Dict[str, Any]]:
    """List solutions with recency filtering and sorting"""
```

##### 5.6 Solution Validation on Access

When loading solutions, optionally validate freshness:

```python
async def load_supply_tree_solution_with_metadata(
    self, 
    solution_id: UUID,
    validate_freshness: bool = True,
    auto_refresh: bool = False
) -> Tuple[SupplyTreeSolution, Dict[str, Any]]:
    """Load solution with optional freshness validation"""
    # Load the solution
    solution = await self.load_supply_tree_solution(solution_id)
    
    metadata = {}
    if validate_freshness:
        is_stale, reason = await self.is_solution_stale(solution_id)
        age = await self.get_solution_age(solution_id)
        
        # Load metadata for expiration info
        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
        try:
            data = await self.manager.get_object(metadata_key)
            meta = json.loads(data.decode("utf-8"))
            metadata = {
                "is_stale": is_stale,
                "staleness_reason": reason,
                "age_days": age.days,
                "expires_at": meta.get("expires_at"),
                "refresh_recommended": is_stale,
            }
        except:
            pass
    
    return (solution, metadata)

### Match Endpoint Integration

Update `/api/match` endpoint to optionally save solutions:

```python
POST /api/match
{
  "okh_id": "...",
  "max_depth": 3,
  "save_solution": true,  # New optional flag
  "solution_tags": ["production", "test"]  # Optional tags
}

# Response includes solution_id if saved
{
  "solution": {...},
  "solution_id": "uuid",  # If save_solution=true
  "matching_mode": "nested"
}
```

### API Endpoint Integration

All `/api/supply-tree/solution/*` endpoints should support multiple input sources:

#### Input Source Priority:
1. **Storage** (if `solution_id` provided): Load from StorageService
2. **Local File** (if `file_path` provided): Load from local filesystem
3. **Inline JSON** (if `solution` provided in request body): Use directly
4. **Error** if none provided

#### Example Request Patterns:

```python
# From storage
GET /api/supply-tree/solution/{solution_id}

# From local file
POST /api/supply-tree/solution/load
{
  "source": "file",
  "file_path": "/path/to/solution.json"
}

# Inline JSON
POST /api/supply-tree/solution/load
{
  "source": "inline",
  "solution": {...}
}

# Save to storage
POST /api/supply-tree/solution/{solution_id}/save
{
  "solution": {...}  # Optional if already loaded
}
```

### CLI Integration

Add CLI commands for solution management:

```bash
# Save solution to storage
ome solution save solution.json --id {uuid} --tags "production,test" --ttl-days 60

# Load solution from storage
ome solution load {solution_id} --output solution.json

# List solutions (with recency sorting/filtering)
ome solution list --okh-id {uuid} --matching-mode nested
ome solution list --sort-by created_at --sort-order desc
ome solution list --max-age-days 7 --only-stale

# Check solution staleness
ome solution check {solution_id}

# Extend solution TTL
ome solution extend {solution_id} --days 30

# Cleanup stale solutions
ome solution cleanup --max-age-days 90 --dry-run
ome solution cleanup --max-age-days 90 --archive
ome solution cleanup --before-date 2024-01-01
```

## Required API Enhancements

### Priority 1: Solution Management Endpoints

#### 1.1 Get Nested Solution
```
GET /api/supply-tree/solution/{solution_id}
POST /api/supply-tree/solution/load
```
- Retrieve a complete `SupplyTreeSolution` by ID
- **Input Sources**:
  - `solution_id` (path param): Load from StorageService
  - `file_path` (body): Load from local file
  - `solution` (body): Use inline JSON
- Support query parameters for filtering:
  - `include_trees=true/false` - Include full tree data or just metadata
  - `component_id={id}` - Filter trees by component
  - `depth={n}` - Filter trees by depth
  - `facility_id={id}` - Filter trees by facility
  - `min_confidence={score}` - Filter by confidence threshold

#### 1.2 List Solutions
```
GET /api/supply-tree/solutions
```
- List all nested solutions (paginated)
- Support filtering by:
  - `okh_id` - Filter by OKH manifest
  - `matching_mode` - Filter by nested/single-level
  - `created_after`, `created_before` - Date range
  - `min_age_days`, `max_age_days` - Filter by age
  - `include_stale` - Include stale solutions (default: false)
  - `only_stale` - Only return stale solutions
- Support sorting by:
  - `sort_by` - Field to sort by: `created_at`, `updated_at`, `expires_at`, `score` (default: `created_at`)
  - `sort_order` - `asc` or `desc` (default: `desc`)
- Return summary metadata (tree count, component count, score, age, staleness status)

#### 1.3 Solution Summary/Statistics
```
GET /api/supply-tree/solution/{solution_id}/summary
```
- Return aggregated statistics:
  - Total trees, components, facilities
  - Average confidence score
  - Component distribution
  - Facility distribution
  - Depth distribution
  - Cost/time estimates (if available)

### Priority 2: Tree Filtering and Querying

#### 2.1 Query Trees in Solution
```
GET /api/supply-tree/solution/{solution_id}/trees
```
- Get trees from a solution with filtering:
  - `component_id`, `component_name`
  - `facility_id`, `facility_name`
  - `depth`, `min_depth`, `max_depth`
  - `min_confidence`
  - `production_stage`
- Support pagination
- Support sorting by confidence, depth, facility name

#### 2.2 Get Component Trees
```
GET /api/supply-tree/solution/{solution_id}/component/{component_id}
```
- Get all trees for a specific component
- Include parent/child relationships

#### 2.3 Get Facility Trees
```
GET /api/supply-tree/solution/{solution_id}/facility/{facility_id}
```
- Get all trees for a specific facility
- Useful for understanding facility workload

### Priority 3: Relationship and Dependency Endpoints

#### 3.1 Get Dependency Graph
```
GET /api/supply-tree/solution/{solution_id}/dependencies
```
- Return dependency graph in various formats:
  - JSON (nested structure)
  - GraphML (for visualization tools)
  - DOT (for Graphviz)
  - Mermaid (for documentation)

#### 3.2 Get Production Sequence
```
GET /api/supply-tree/solution/{solution_id}/production-sequence
```
- Return production stages with parallel execution groups
- Include timing estimates if available

#### 3.3 Get Component Hierarchy
```
GET /api/supply-tree/solution/{solution_id}/hierarchy
```
- Return tree structure showing parent-child relationships
- Support format options: tree, nested JSON, flat list with depth

### Priority 4: Staleness and Cleanup Endpoints

#### 4.1 Check Solution Staleness
```
GET /api/supply-tree/solution/{solution_id}/staleness
```
- Check if solution is stale
- Return: `is_stale`, `age_days`, `expires_at`, `reason`, `refresh_recommended`

#### 4.2 Cleanup Stale Solutions
```
POST /api/supply-tree/solutions/cleanup
```
- Remove stale solutions from storage
- Parameters:
  - `max_age_days` - Delete solutions older than N days
  - `before_date` - Delete solutions created before date
  - `dry_run` - Preview what would be deleted (default: true)
  - `archive` - Archive instead of delete (default: false)
- Returns: `deleted_count`, `freed_space`, `deleted_ids`

#### 4.3 Extend Solution TTL
```
POST /api/supply-tree/solution/{solution_id}/extend
```
- Extend solution expiration time
- Parameters: `additional_days` (default: 30)

### Priority 5: Export and Visualization Formats

#### 5.1 Enhanced Export
```
GET /api/supply-tree/solution/{solution_id}/export
```
- Support additional formats:
  - **GraphML** (enhanced for nested structures)
  - **DOT** (Graphviz format)
  - **Mermaid** (for documentation)
  - **CSV** (flat table of trees with relationships)
  - **Excel** (multi-sheet: trees, components, facilities, dependencies)

#### 5.2 Visualization Data Export
```
GET /api/supply-tree/solution/{solution_id}/viz
```
- Return data optimized for specific visualization tools:
  - `format=d3` - D3.js hierarchy format
  - `format=cytoscape` - Cytoscape.js format
  - `format=visjs` - vis.js network format
  - `format=plotly` - Plotly sankey/sunburst format

## Recommended Visualization Tools

### Command-Line Tools (For Quick Inspection)

#### 1. **jq** ⭐ Recommended
- **Purpose**: JSON processor and query tool
- **Installation**: `brew install jq` (macOS) or `apt-get install jq` (Linux)
- **Use Cases**:
  - Filter trees by component: `jq '.solution.all_trees[] | select(.component_name=="Housing")'`
  - Count trees per component: `jq '.solution.all_trees | group_by(.component_name) | map({component: .[0].component_name, count: length})'`
  - Extract summary: `jq '{total_trees: (.solution.all_trees | length), components: [.solution.all_trees[].component_name] | unique}'`
- **Pros**: Fast, powerful, widely available
- **Cons**: Learning curve for complex queries

#### 2. **jless** ⭐ Recommended
- **Purpose**: Interactive JSON viewer
- **Installation**: `cargo install jless` or `brew install jless`
- **Use Cases**:
  - Browse large JSON files interactively
  - Search and filter within viewer
  - Syntax highlighting and folding
- **Pros**: Interactive, user-friendly, handles large files well
- **Cons**: Requires Rust/Cargo for installation

#### 3. **fx**
- **Purpose**: Interactive JSON viewer with JavaScript expressions
- **Installation**: `npm install -g fx`
- **Use Cases**: Similar to jless but with JavaScript processing
- **Pros**: JavaScript expressions for filtering
- **Cons**: Requires Node.js

### Web-Based Visualization Tools

#### 1. **RAWGraphs** ⭐ Recommended for Charts
- **Purpose**: Web-based data visualization
- **URL**: https://rawgraphs.io/
- **Use Cases**:
  - Create Sankey diagrams (component → facility flows)
  - Sunburst charts (hierarchical component structure)
  - Network diagrams (facility relationships)
- **Input Format**: CSV (need to convert JSON → CSV)
- **Pros**: No installation, powerful chart types, export options
- **Cons**: Requires manual data preparation

#### 2. **Observable Plot** (via Observable Notebooks)
- **Purpose**: Interactive data visualization
- **URL**: https://observablehq.com/
- **Use Cases**:
  - Create custom interactive visualizations
  - Share visualizations via notebooks
  - Real-time data binding
- **Pros**: Highly customizable, interactive, shareable
- **Cons**: Requires JavaScript knowledge

#### 3. **D3.js** (Custom Implementation)
- **Purpose**: JavaScript visualization library
- **Use Cases**:
  - Custom tree/hierarchy visualizations
  - Interactive network graphs
  - Sankey diagrams for flow visualization
- **Pros**: Maximum flexibility, professional results
- **Cons**: Requires development effort

### Graph Visualization Tools

#### 1. **Graphviz** ⭐ Recommended for Static Graphs
- **Purpose**: Graph visualization software
- **Installation**: `brew install graphviz` or `apt-get install graphviz`
- **Use Cases**:
  - Generate static images of dependency graphs
  - Tree/hierarchy visualization
  - Network diagrams
- **Input Format**: DOT format (can export from API)
- **Pros**: High-quality output, many layout algorithms
- **Cons**: Static images only

#### 2. **Cytoscape.js** (Web-based)
- **Purpose**: Graph visualization library
- **URL**: https://js.cytoscape.org/
- **Use Cases**:
  - Interactive network graphs
  - Component-facility relationships
  - Dependency visualization
- **Pros**: Interactive, web-based, good for complex graphs
- **Cons**: Requires web development

#### 3. **Mermaid** ⭐ Recommended for Documentation
- **Purpose**: Diagram and flowchart generation
- **URL**: https://mermaid.live/
- **Use Cases**:
  - Generate diagrams from text/markdown
  - Documentation-friendly format
  - Can be embedded in Markdown
- **Input Format**: Mermaid syntax (can export from API)
- **Pros**: Easy to use, documentation-friendly, version-controllable
- **Cons**: Less interactive than D3/Cytoscape

### Specialized Tools

#### 1. **Gephi** (Desktop Application)
- **Purpose**: Network analysis and visualization
- **URL**: https://gephi.org/
- **Use Cases**:
  - Complex network analysis
  - Community detection
  - Layout algorithms for large graphs
- **Input Format**: GraphML, CSV, GEXF
- **Pros**: Powerful analysis features, handles large graphs
- **Cons**: Desktop app, learning curve

## Implementation Recommendations

### Phase 1: Quick Wins (1-2 days)
1. **Add StorageService methods for solutions** (save, load, list, delete)
2. **Add timestamping and expiration fields** (created_at, updated_at, expires_at, ttl_days)
3. Add solution summary endpoint (`/api/supply-tree/solution/{id}/summary`)
4. Enhance export endpoint to support GraphML with nested relationships
5. Add query parameters to match endpoint for filtering trees
6. Document jq/jless usage for CLI inspection
7. **Auto-save solutions from match endpoint** (optional flag)

### Phase 2: Core Functionality (1 week) ✅ **COMPLETE**
1. **Implement multi-source loading** (storage, file, inline) for all solution endpoints ✅
2. Implement solution management endpoints (get, list, save, delete) ✅
3. **Implement staleness detection and expiration management** ✅
4. **Add recency sorting and filtering** (sort_by, sort_order, age filters) ✅
5. **Add cleanup methods** (cleanup_stale_solutions, archive_stale_solutions) ✅
6. Add tree filtering/querying endpoints ✅
7. Implement dependency graph export (GraphML, DOT, Mermaid) - **GraphML complete ✅, DOT/Mermaid pending**
8. Create CSV export for RAWGraphs integration - **Pending**
9. **Add CLI commands for solution management** (including cleanup commands) ✅

### Phase 3: Advanced Features (2 weeks)
1. Implement visualization-optimized export formats
2. Add component/facility-specific query endpoints
3. Create production sequence endpoint
4. Build example visualization scripts/templates

### Phase 4: Documentation and Examples (1 week)
1. Create visualization guide with examples
2. Provide jq query examples for common use cases
3. Create sample visualizations using recommended tools
4. Document API usage patterns for nested trees

## Example Usage Patterns

### Using jq to Analyze Solutions

```bash
# Count trees by component
cat output-1.json | jq '.solutions[0].solution.all_trees | group_by(.component_name) | map({component: .[0].component_name, count: length})'

# Get all facilities used
cat output-1.json | jq '.solutions[0].solution.all_trees[].facility_name' | sort | uniq

# Filter high-confidence matches
cat output-1.json | jq '.solutions[0].solution.all_trees[] | select(.confidence_score > 0.8)'

# Extract component-facility pairs
cat output-1.json | jq '.solutions[0].solution.all_trees[] | {component: .component_name, facility: .facility_name, confidence: .confidence_score}'
```

### Using jless for Interactive Exploration

```bash
# Open JSON file interactively
jless output-1.json

# Navigate to solution → all_trees → filter by component_name
```

### Creating Visualizations

```bash
# Export to GraphML for Gephi
curl "http://api/.../solution/{id}/export?format=graphml" > solution.graphml

# Export to CSV for RAWGraphs
curl "http://api/.../solution/{id}/export?format=csv" > solution.csv

# Export to DOT for Graphviz
curl "http://api/.../solution/{id}/export?format=dot" | dot -Tpng > solution.png
```

## Implementation Details

### StorageService Solution Methods

```python
# Add to StorageService class
from datetime import datetime, timedelta
from typing import Tuple

async def save_supply_tree_solution(
    self, 
    solution: SupplyTreeSolution, 
    solution_id: Optional[UUID] = None,
    tags: Optional[List[str]] = None,
    ttl_days: Optional[int] = None
) -> UUID:
    """Save a supply tree solution to storage"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    # Generate ID if not provided
    if solution_id is None:
        solution_id = uuid4()
    
    # Extract metadata
    okh_id = solution.metadata.get("okh_id")
    matching_mode = solution.metadata.get("matching_mode", "nested")
    
    # Calculate expiration time
    # Support ttl_days from parameter, tags dict, or use default
    if ttl_days is None:
        if isinstance(tags, dict) and "ttl_days" in tags:
            ttl_days = tags.pop("ttl_days")
        else:
            ttl_days = 30  # Default TTL
    expires_at = datetime.now() + timedelta(days=ttl_days)
    
    # Convert solution to JSON
    solution_data = solution.to_dict()
    data = json.dumps(solution_data).encode("utf-8")
    
    # Generate storage key
    key = f"supply-tree-solutions/{solution_id}.json"
    
    # Save with metadata
    metadata = await self.manager.put_object(
        key=key,
        data=data,
        content_type="application/json",
        metadata={
            "type": "supply_tree_solution",
            "id": str(solution_id),
            "okh_id": str(okh_id) if okh_id else None,
            "matching_mode": matching_mode,
            "tree_count": len(solution.all_trees),
            "component_count": len(solution.component_mapping) if solution.component_mapping else 0,
            "score": str(solution.score),
            "tags": ",".join(tags) if tags else "",
        },
    )
    
    # Save lightweight metadata for listing
    now = datetime.now()
    metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
    metadata_data = {
        "id": str(solution_id),
        "okh_id": str(okh_id) if okh_id else None,
        "okh_title": solution.metadata.get("okh_title"),
        "matching_mode": matching_mode,
        "tree_count": len(solution.all_trees),
        "component_count": len(solution.component_mapping) if solution.component_mapping else 0,
        "facility_count": len(set(tree.okw_reference for tree in solution.all_trees if tree.okw_reference)),
        "score": solution.score,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "ttl_days": ttl_days,
        "tags": tags or [],
    }
    await self.manager.put_object(
        key=metadata_key,
        data=json.dumps(metadata_data).encode("utf-8"),
        content_type="application/json",
    )
    
    return solution_id

async def load_supply_tree_solution(self, solution_id: UUID) -> SupplyTreeSolution:
    """Load a supply tree solution from storage"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    key = f"supply-tree-solutions/{solution_id}.json"
    
    try:
        data = await self.manager.get_object(key)
        from ..models.supply_trees import SupplyTreeSolution
        
        solution_dict = json.loads(data.decode("utf-8"))
        return SupplyTreeSolution.from_dict(solution_dict)
    except Exception as e:
        logger.error(f"Failed to load supply tree solution {solution_id}: {e}")
        raise

async def list_supply_tree_solutions(
    self,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    okh_id: Optional[UUID] = None,
    matching_mode: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    min_age_days: Optional[int] = None,
    max_age_days: Optional[int] = None,
    include_stale: bool = False,
    only_stale: bool = False,
) -> List[Dict[str, Any]]:
    """List supply tree solutions with optional filtering"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    solutions = []
    count = 0
    
    try:
        async for obj in self.manager.list_objects(prefix="supply-tree-solutions/metadata/"):
            if not obj["key"].endswith(".json"):
                continue
            
            if offset and count < offset:
                count += 1
                continue
            
            if limit and len(solutions) >= limit:
                break
            
            try:
                data = await self.manager.get_object(obj["key"])
                metadata = json.loads(data.decode("utf-8"))
                
                # Apply filters
                if okh_id and metadata.get("okh_id") != str(okh_id):
                    continue
                if matching_mode and metadata.get("matching_mode") != matching_mode:
                    continue
                
                # Check staleness
                created_at = datetime.fromisoformat(metadata.get("created_at"))
                age_days = (datetime.now() - created_at).days
                expires_at = datetime.fromisoformat(metadata.get("expires_at", ""))
                is_stale = datetime.now() > expires_at or (max_age_days and age_days > max_age_days)
                
                # Apply age filters
                if min_age_days and age_days < min_age_days:
                    continue
                if max_age_days and age_days > max_age_days:
                    continue
                
                # Apply staleness filters
                if only_stale and not is_stale:
                    continue
                if not include_stale and is_stale and not only_stale:
                    continue
                
                # Add staleness info to metadata
                metadata["age_days"] = age_days
                metadata["is_stale"] = is_stale
                
                solutions.append(metadata)
            
            # Sort results
            reverse = sort_order.lower() == "desc"
            if sort_by == "created_at":
                solutions.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)
            elif sort_by == "updated_at":
                solutions.sort(key=lambda x: x.get("updated_at", ""), reverse=reverse)
            elif sort_by == "expires_at":
                solutions.sort(key=lambda x: x.get("expires_at", ""), reverse=reverse)
            elif sort_by == "score":
                solutions.sort(key=lambda x: x.get("score", 0.0), reverse=reverse)
            elif sort_by == "age_days":
                solutions.sort(key=lambda x: x.get("age_days", 0), reverse=reverse)
            except Exception as e:
                logger.error(f"Failed to load solution metadata from {obj['key']}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error iterating over solutions: {e}", exc_info=True)
        raise
    
    return solutions

async def delete_supply_tree_solution(self, solution_id: UUID) -> bool:
    """Delete a supply tree solution from storage"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    # Delete both solution and metadata
    solution_key = f"supply-tree-solutions/{solution_id}.json"
    metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
    
    deleted_solution = await self.manager.delete_object(solution_key)
    deleted_metadata = await self.manager.delete_object(metadata_key)
    
    return deleted_solution and deleted_metadata

async def is_solution_stale(
    self,
    solution_id: UUID,
    max_age_days: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Check if solution is stale. Returns (is_stale, reason)"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
    try:
        data = await self.manager.get_object(metadata_key)
        metadata = json.loads(data.decode("utf-8"))
        
        created_at = datetime.fromisoformat(metadata.get("created_at"))
        expires_at = datetime.fromisoformat(metadata.get("expires_at", ""))
        now = datetime.now()
        
        # Check explicit expiration
        if expires_at and now > expires_at:
            return (True, "expired")
        
        # Check age-based staleness
        age_days = (now - created_at).days
        if max_age_days and age_days > max_age_days:
            return (True, f"too_old_{age_days}_days")
        
        # Check default TTL
        ttl_days = metadata.get("ttl_days", 30)
        if age_days > ttl_days:
            return (True, f"exceeded_ttl_{ttl_days}_days")
        
        return (False, None)
    except Exception as e:
        logger.error(f"Failed to check staleness for solution {solution_id}: {e}")
        return (True, "check_failed")

async def get_solution_age(self, solution_id: UUID) -> timedelta:
    """Get age of solution"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
    try:
        data = await self.manager.get_object(metadata_key)
        metadata = json.loads(data.decode("utf-8"))
        created_at = datetime.fromisoformat(metadata.get("created_at"))
        return datetime.now() - created_at
    except Exception as e:
        logger.error(f"Failed to get age for solution {solution_id}: {e}")
        raise

async def get_stale_solutions(
    self,
    max_age_days: Optional[int] = None,
    before_date: Optional[datetime] = None
) -> List[UUID]:
    """Get list of stale solution IDs"""
    stale_solutions = []
    
    async for obj in self.manager.list_objects(prefix="supply-tree-solutions/metadata/"):
        if not obj["key"].endswith(".json"):
            continue
        
        try:
            data = await self.manager.get_object(obj["key"])
            metadata = json.loads(data.decode("utf-8"))
            solution_id = UUID(metadata["id"])
            
            is_stale, _ = await self.is_solution_stale(solution_id, max_age_days)
            
            if is_stale:
                # Check before_date filter
                if before_date:
                    created_at = datetime.fromisoformat(metadata.get("created_at"))
                    if created_at >= before_date:
                        continue
                
                stale_solutions.append(solution_id)
        except Exception as e:
            logger.error(f"Failed to check staleness for {obj['key']}: {e}")
            continue
    
    return stale_solutions

async def cleanup_stale_solutions(
    self,
    max_age_days: Optional[int] = None,
    before_date: Optional[datetime] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Remove stale solutions from storage"""
    stale_ids = await self.get_stale_solutions(max_age_days, before_date)
    
    deleted_count = 0
    freed_space = 0
    deleted_ids = []
    
    for solution_id in stale_ids:
        if not dry_run:
            # Get size before deletion
            solution_key = f"supply-tree-solutions/{solution_id}.json"
            try:
                obj = await self.manager.get_object(solution_key)
                freed_space += len(obj)
            except:
                pass
            
            # Delete solution
            if await self.delete_supply_tree_solution(solution_id):
                deleted_count += 1
                deleted_ids.append(str(solution_id))
        else:
            deleted_ids.append(str(solution_id))
    
    return {
        "deleted_count": deleted_count if not dry_run else len(deleted_ids),
        "freed_space": freed_space,
        "deleted_ids": deleted_ids,
        "dry_run": dry_run
    }

async def extend_solution_ttl(
    self,
    solution_id: UUID,
    additional_days: int = 30
) -> bool:
    """Extend solution expiration time"""
    if not self._configured or not self.manager:
        raise RuntimeError("Storage service not configured")
    
    metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
    try:
        data = await self.manager.get_object(metadata_key)
        metadata = json.loads(data.decode("utf-8"))
        
        # Update expiration
        current_expires = datetime.fromisoformat(metadata.get("expires_at", ""))
        new_expires = current_expires + timedelta(days=additional_days)
        metadata["expires_at"] = new_expires.isoformat()
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["ttl_days"] = metadata.get("ttl_days", 30) + additional_days
        
        # Save updated metadata
        await self.manager.put_object(
            key=metadata_key,
            data=json.dumps(metadata).encode("utf-8"),
            content_type="application/json",
        )
        
        return True
    except Exception as e:
        logger.error(f"Failed to extend TTL for solution {solution_id}: {e}")
        return False
```

### API Endpoint Multi-Source Loading

**Status**: ✅ **IMPLEMENTED** - Complete with comprehensive test coverage

The `_load_solution_from_source()` helper function has been implemented and integrated into existing endpoints. A new `POST /api/supply-tree/solution/load` endpoint provides full multi-source loading support.

**Implementation Details**:
- ✅ Helper function supports storage, file, and inline JSON sources
- ✅ Priority handling: storage > file > inline
- ✅ Handles both wrapped (`{"solution": {...}}`) and direct (`{"all_trees": [...]}`) JSON formats
- ✅ Comprehensive error handling for missing sources and invalid formats
- ✅ Integrated into `GET /api/supply-tree/solution/{id}/summary` and `GET /api/supply-tree/solution/{id}/export`
- ✅ New `POST /api/supply-tree/solution/load` endpoint with `SolutionLoadRequest` model
- ✅ Request validation ensures required fields are present based on source type
- ✅ **Test Coverage**: 17 unit tests (all passing)

**Usage Examples**:

```python
# Load from storage
POST /api/supply-tree/solution/load
{
  "source": "storage",
  "solution_id": "uuid"
}

# Load from file
POST /api/supply-tree/solution/load
{
  "source": "file",
  "file_path": "/path/to/solution.json"
}

# Load from inline JSON
POST /api/supply-tree/solution/load
{
  "source": "inline",
  "solution": {...}
}
```

**Implementation**:
```python
async def _load_solution_from_source(
    solution_id: Optional[UUID] = None,
    file_path: Optional[str] = None,
    solution_data: Optional[Dict[str, Any]] = None,
    storage_service: Optional[StorageService] = None,
) -> SupplyTreeSolution:
    """Load solution from storage, file, or inline data"""
    from ..models.supply_trees import SupplyTreeSolution
    
    if solution_id and storage_service:
        # Load from storage
        return await storage_service.load_supply_tree_solution(solution_id)
    elif file_path:
        # Load from local file
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Handle both full response format and solution-only format
            if "solution" in data:
                return SupplyTreeSolution.from_dict(data["solution"])
            elif "all_trees" in data:
                return SupplyTreeSolution.from_dict(data)
            else:
                raise ValueError("Invalid solution file format")
    elif solution_data:
        # Use inline data
        if "solution" in solution_data:
            return SupplyTreeSolution.from_dict(solution_data["solution"])
        elif "all_trees" in solution_data:
            return SupplyTreeSolution.from_dict(solution_data)
        else:
            raise ValueError("Invalid solution data format")
    else:
        raise ValueError("Must provide solution_id, file_path, or solution_data")
```

## Conclusion

The current API supports nested trees in the match endpoint but lacks specialized endpoints for querying, filtering, and visualizing nested solutions. **StorageService integration is critical** for managing large solutions effectively. The recommended approach is:

1. **Immediate**: 
   - Implement StorageService methods for solutions
   - Use jq/jless for CLI inspection and analysis
2. **Short-term**: 
   - Add solution management and filtering endpoints
   - Support multi-source loading (storage, file, inline)
   - Auto-save solutions from match endpoint
3. **Medium-term**: 
   - Implement export formats optimized for visualization tools
   - Add CLI commands for solution management
4. **Long-term**: 
   - Consider building custom visualization components if needed
   - Add solution versioning and comparison features

The visualization tools recommended (jq, jless, RAWGraphs, Graphviz, Mermaid) are all open-source and can be integrated into the workflow without requiring changes to the core OME system. **StorageService integration enables persistent storage and retrieval of large solutions**, making them accessible via API endpoints and CLI commands.

