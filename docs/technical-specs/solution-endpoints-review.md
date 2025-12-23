# Solution Endpoints and CLI Commands Review

## Workflow Overview

The intended workflow is:
1. **Run nested matching** → Get 90k line JSON output
2. **Save output to storage** → Store in `supply-tree-solutions/` directory
3. **List/Get/Describe solution** → Use API or CLI to access saved solution

Let's review each endpoint and command to ensure they support this workflow correctly.

---

## 1. Saving Solutions

### 1.1 Auto-Save from Match Endpoint ✅

**Endpoint**: `POST /api/match`

**How it works**:
- When `save_solution: true` is set in the request, the match endpoint automatically saves the solution
- For nested matching: Saves the `SupplyTreeSolution` object directly
- Returns `solution_id` in the response

**Response format**:
```json
{
  "solution": {
    "all_trees": [...],
    "root_trees": [...],
    ...
  },
  "matching_mode": "nested",
  "solution_id": "uuid-here"  // ← Added when save_solution=true
}
```

**Status**: ✅ **Works correctly** - Saves directly to storage during matching

**Questions to verify**:
- [ ] Does the saved solution include all metadata (okh_id, okh_title, etc.)?
- [ ] Is the solution_id returned in the response easy to use?

---

### 1.2 Save via API Endpoint

**Endpoint**: `POST /api/supply-tree/solution/{solution_id}/save`

**How it works**:
- Accepts solution data in request body
- Handles both wrapped format (`{"solution": {...}}`) and direct format (`{"all_trees": [...]}`)
- Saves to storage at `supply-tree-solutions/{solution_id}.json`

**Request format**:
```json
{
  "solution": {
    "all_trees": [...],
    ...
  },
  "ttl_days": 30,  // Optional
  "tags": ["tag1", "tag2"]  // Optional
}
```

**Status**: ✅ **Should work** - Handles the match endpoint response format

**Questions to verify**:
- [ ] Can we save the entire match endpoint response directly?
- [ ] Or do we need to extract just the `solution` part?

---

### 1.3 Save via CLI Command

**Command**: `ome solution save <file> [--id <uuid>] [--ttl-days <days>] [--tags <tags>]`

**How it works**:
- Reads JSON file from filesystem
- Extracts solution from wrapped format if needed (`{"solution": {...}}`)
- Calls the API save endpoint

**Usage**:
```bash
# Save the 90k line output file
ome solution save output-1.json

# Save with specific ID and TTL
ome solution save output-1.json --id abc-123 --ttl-days 60

# Save with tags
ome solution save output-1.json --tags "production,test"
```

**Status**: ✅ **Should work** - Handles wrapped format

**Questions to verify**:
- [ ] Can it handle the full match endpoint response format?
- [ ] Does it correctly extract the solution from `{"solution": {...}, "matching_mode": "nested"}`?

---

## 2. Listing Solutions

### 2.1 List via API Endpoint

**Endpoint**: `GET /api/supply-tree/solutions`

**Query Parameters**:
- `okh_id` - Filter by OKH ID
- `matching_mode` - Filter by nested/single-level
- `sort_by` - Sort field (created_at, updated_at, score, age_days)
- `sort_order` - asc/desc
- `min_age_days`, `max_age_days` - Age filters
- `only_stale`, `include_stale` - Staleness filters
- `limit`, `offset` - Pagination

**Response format**:
```json
{
  "result": [
    {
      "id": "uuid",
      "okh_id": "uuid",
      "okh_title": "Title",
      "matching_mode": "nested",
      "tree_count": 272,
      "score": 0.85,
      "created_at": "2024-01-01T00:00:00",
      "age_days": 5,
      "is_stale": false
    },
    ...
  ]
}
```

**Status**: ✅ **Works correctly** - Returns metadata for all solutions

**Questions to verify**:
- [ ] Does it show solutions saved from match endpoint?
- [ ] Are the metadata fields (okh_title, etc.) populated correctly?

---

### 2.2 List via CLI Command

**Command**: `ome solution list [options]`

**Options**:
- `--okh-id <uuid>` - Filter by OKH ID
- `--matching-mode <mode>` - Filter by mode
- `--sort-by <field>` - Sort field
- `--sort-order <asc|desc>` - Sort order
- `--min-age-days <days>` - Minimum age
- `--max-age-days <days>` - Maximum age
- `--only-stale` - Only stale solutions
- `--include-stale` - Include stale solutions
- `--limit <n>` - Limit results
- `--offset <n>` - Skip results

**Usage**:
```bash
# List all solutions
ome solution list

# List nested solutions only
ome solution list --matching-mode nested

# List stale solutions
ome solution list --only-stale

# List with sorting
ome solution list --sort-by created_at --sort-order desc
```

**Status**: ✅ **Works correctly** - Provides all filtering options

**Questions to verify**:
- [ ] Is the output format readable?
- [ ] Does it show all important fields?

---

## 3. Getting Solutions

### 3.1 Get Full Solution via API

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}`

**How it works**:
- Loads solution from storage
- Returns full `SupplyTreeSolution` object

**Response format**:
```json
{
  "id": "uuid",
  "all_trees": [...],
  "root_trees": [...],
  "score": 0.85,
  "metadata": {...},
  ...
}
```

**Status**: ✅ **Works correctly** - Returns full solution

**Questions to verify**:
- [ ] Is this the same format as the match endpoint response?
- [ ] Can we use this to get the 90k line solution back?

---

### 3.2 Get Solution Summary via API

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/summary`

**How it works**:
- Loads solution from storage
- Calculates aggregated statistics
- Returns summary without full tree data

**Response format**:
```json
{
  "id": "uuid",
  "okh_id": "uuid",
  "okh_title": "Title",
  "matching_mode": "nested",
  "total_trees": 272,
  "total_components": 8,
  "total_facilities": 34,
  "average_confidence": 0.85,
  "score": 0.85,
  "component_distribution": [...],
  "facility_distribution": [...],
  "cost_estimate": 1234.56,
  "time_estimate": "5 days",
  "is_nested": true
}
```

**Status**: ✅ **Works correctly** - Provides summary without full data

**Questions to verify**:
- [ ] Is this useful for quick inspection?
- [ ] Does it provide enough information?

---

### 3.3 Load via CLI Command

**Command**: `ome solution load <solution_id> [--output <file>]`

**How it works**:
- Calls API to get full solution
- Writes to file if `--output` specified, otherwise stdout

**Usage**:
```bash
# Load to stdout
ome solution load abc-123

# Load to file
ome solution load abc-123 --output solution.json

# Load as JSON
ome solution load abc-123 --json
```

**Status**: ✅ **Works correctly** - Can retrieve full solution

**Questions to verify**:
- [ ] Can it handle large solutions (90k lines)?
- [ ] Is the output format correct?

---

## 4. Tree Filtering and Querying

### 4.1 Get Trees with Filters

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/trees`

**Query Parameters**:
- `component_id`, `component_name` - Filter by component
- `facility_name`, `okw_reference` - Filter by facility
- `depth`, `min_depth`, `max_depth` - Filter by depth
- `min_confidence` - Filter by confidence
- `production_stage` - Filter by stage
- `sort_by`, `sort_order` - Sorting
- `limit`, `offset` - Pagination

**Response format**:
```json
{
  "trees": [...],
  "total_count": 272,
  "returned_count": 10,
  "filters_applied": {...}
}
```

**Status**: ✅ **Works correctly** - Provides filtered tree access

**Questions to verify**:
- [ ] Is this useful for exploring large solutions?
- [ ] Does pagination work well for 90k line solutions?

---

### 4.2 Get Component Trees

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/component/{component_id}`

**How it works**:
- Returns all trees for a specific component

**Status**: ✅ **Works correctly**

**Questions to verify**:
- [ ] Is component_id easy to find/use?

---

### 4.3 Get Facility Trees

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/facility/{facility_id}`

**How it works**:
- Returns all trees for a specific facility
- Can match by `okw_reference` or `facility_name`

**Status**: ✅ **Works correctly**

**Questions to verify**:
- [ ] Is facility_id easy to find/use?

---

## 5. Staleness Management

### 5.1 Check Staleness

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/staleness`

**Command**: `ome solution check <solution_id> [--max-age-days <days>]`

**Status**: ✅ **Works correctly**

---

### 5.2 Extend TTL

**Endpoint**: `POST /api/supply-tree/solution/{solution_id}/extend`

**Command**: `ome solution extend <solution_id> [--days <days>]`

**Status**: ✅ **Works correctly**

---

### 5.3 Cleanup Stale Solutions

**Endpoint**: `POST /api/supply-tree/solutions/cleanup`

**Command**: `ome solution cleanup [--max-age-days <days>] [--before-date <date>] [--dry-run] [--archive]`

**Status**: ✅ **Works correctly**

---

## 6. Export

### 6.1 Export Solution

**Endpoint**: `GET /api/supply-tree/solution/{solution_id}/export?format=<format>`

**Formats**: json, xml, graphml

**Status**: ✅ **GraphML works**, other formats pending

---

## Key Questions for Review

1. **Format Compatibility**:
   - [ ] Can we save the full match endpoint response directly?
   - [ ] Or do we need to extract just the `solution` part?
   - [ ] Does the CLI save command handle the match response format correctly?

2. **Metadata Preservation**:
   - [ ] Are all metadata fields (okh_id, okh_title, etc.) preserved when saving?
   - [ ] Are they accessible when listing/getting solutions?

3. **Large Solution Handling**:
   - [ ] Can we save 90k line solutions without issues?
   - [ ] Can we list/get them efficiently?
   - [ ] Does pagination work well?

4. **Workflow Completeness**:
   - [ ] Can we complete the full workflow: match → save → list → get?
   - [ ] Are there any missing pieces?

5. **CLI vs API**:
   - [ ] Are CLI commands equivalent to API endpoints?
   - [ ] Is there feature parity?

