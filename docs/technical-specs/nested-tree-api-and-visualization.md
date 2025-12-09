# Nested Supply Tree API and Visualization Analysis

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
- ❌ `SupplyTreeSolution` objects are only available via stdout
- ❌ No persistence for nested solutions
- ❌ Solutions must be manually saved/retrieved

### Required StorageService Enhancements

#### 1. Solution Storage Methods

Add to `StorageService` class:

```python
async def save_supply_tree_solution(self, solution: SupplyTreeSolution, solution_id: Optional[UUID] = None) -> UUID:
    """Save a supply tree solution to storage"""
    # Generate ID if not provided (use hash of solution or UUID)
    # Store at: supply-tree-solutions/{solution_id}.json
    # Include metadata: okh_id, matching_mode, tree_count, created_at

async def load_supply_tree_solution(self, solution_id: UUID) -> SupplyTreeSolution:
    """Load a supply tree solution from storage"""
    # Load from: supply-tree-solutions/{solution_id}.json
    # Deserialize to SupplyTreeSolution object

async def list_supply_tree_solutions(
    self, 
    limit: Optional[int] = None, 
    offset: Optional[int] = None,
    okh_id: Optional[UUID] = None,
    matching_mode: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List supply tree solutions with optional filtering"""
    # Return metadata: id, okh_id, matching_mode, tree_count, created_at, score

async def delete_supply_tree_solution(self, solution_id: UUID) -> bool:
    """Delete a supply tree solution from storage"""
    # Delete from: supply-tree-solutions/{solution_id}.json
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
  "created_by": "user/system",
  "tags": ["tag1", "tag2"]
}
```

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
ome solution save solution.json --id {uuid} --tags "production,test"

# Load solution from storage
ome solution load {solution_id} --output solution.json

# List solutions
ome solution list --okh-id {uuid} --matching-mode nested

# Delete solution
ome solution delete {solution_id}
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
- Return summary metadata (tree count, component count, score)

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

### Priority 4: Export and Visualization Formats

#### 4.1 Enhanced Export
```
GET /api/supply-tree/solution/{solution_id}/export
```
- Support additional formats:
  - **GraphML** (enhanced for nested structures)
  - **DOT** (Graphviz format)
  - **Mermaid** (for documentation)
  - **CSV** (flat table of trees with relationships)
  - **Excel** (multi-sheet: trees, components, facilities, dependencies)

#### 4.2 Visualization Data Export
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
2. Add solution summary endpoint (`/api/supply-tree/solution/{id}/summary`)
3. Enhance export endpoint to support GraphML with nested relationships
4. Add query parameters to match endpoint for filtering trees
5. Document jq/jless usage for CLI inspection
6. **Auto-save solutions from match endpoint** (optional flag)

### Phase 2: Core Functionality (1 week)
1. **Implement multi-source loading** (storage, file, inline) for all solution endpoints
2. Implement solution management endpoints (get, list, save, delete)
3. Add tree filtering/querying endpoints
4. Implement dependency graph export (GraphML, DOT, Mermaid)
5. Create CSV export for RAWGraphs integration
6. **Add CLI commands for solution management**

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
async def save_supply_tree_solution(
    self, 
    solution: SupplyTreeSolution, 
    solution_id: Optional[UUID] = None,
    tags: Optional[List[str]] = None
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
        "created_at": datetime.now().isoformat(),
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
                
                solutions.append(metadata)
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
```

### API Endpoint Multi-Source Loading

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

