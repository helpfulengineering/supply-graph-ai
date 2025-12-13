# Visualization PoC Critical Path

## Goal
Create a minimal proof-of-concept that demonstrates end-to-end visualization of supply tree solutions, from API endpoint to visual output.

## Critical Path Analysis

### Phase 1: Choose Tool & Data Source (30 min)

**Decision Points:**
1. **Which visualization tool?**
   - ✅ **Graphviz** (Recommended for PoC)
     - Pros: Simple, generates static images, DOT format is easy to generate
     - Cons: Static only
     - Input: DOT format (text-based graph description)
   - Alternative: **Mermaid** (documentation-friendly, can embed in markdown)
   - Alternative: **RAWGraphs** (requires CSV conversion, more setup)

2. **Which endpoint to visualize?**
   - ✅ **Hierarchy endpoint** (Recommended for PoC)
     - Shows parent-child relationships clearly
     - Tree structure is intuitive to visualize
     - Works well with Graphviz tree layouts
   - Alternative: Dependencies endpoint (shows dependency graph)
   - Alternative: Production sequence (shows stages/timeline)

3. **Which solution to use?**
   - ✅ **Nested solution** (3 trees) - Simple, clear relationships
   - Alternative: Single-level solution (238 trees) - Tests scalability

### Phase 2: Data Transformation (1-2 hours)

**Required Steps:**
1. **Fetch data from API**
   ```python
   # Fetch hierarchy data
   GET /api/supply-tree/solution/{id}/hierarchy
   ```

2. **Transform to visualization format**
   - For Graphviz (DOT format):
     - Parse hierarchy JSON
     - Generate DOT syntax:
       - Nodes: component names with labels
       - Edges: parent → child relationships
       - Attributes: depth, facility, confidence score

3. **Handle edge cases**
   - Empty solutions
   - Single-node trees
   - Missing relationships

### Phase 3: Visualization Generation (1 hour)

**Required Steps:**
1. **Generate DOT file**
   - Create script: `scripts/viz/generate_graphviz.py`
   - Input: Solution ID or JSON file
   - Output: DOT file

2. **Render visualization**
   - Use Graphviz `dot` command: `dot -Tpng input.dot -o output.png`
   - Or `dot -Tsvg` for scalable vector graphics

3. **Test with nested solution**
   - Use solution ID: `27f40fa8-50bf-4514-ba8d-5807cdb1847c`
   - Verify output shows root → 2 children structure

### Phase 4: Polish & Documentation (1 hour)

**Required Steps:**
1. **Create CLI command or script**
   - `python scripts/viz/viz_hierarchy.py {solution_id}`
   - Or: `ome solution viz {solution_id} --format graphviz`

2. **Add error handling**
   - Invalid solution ID
   - API connection errors
   - Missing Graphviz installation

3. **Document usage**
   - README in `scripts/viz/`
   - Example output images
   - Usage instructions

## Minimal Viable PoC (MVP)

**Success Criteria:**
- ✅ Script fetches hierarchy data from API
- ✅ Transforms to DOT format
- ✅ Generates PNG/SVG image
- ✅ Shows clear parent-child relationships
- ✅ Works with nested solution example

**Time Estimate:** 3-4 hours

## Implementation Steps

### Step 1: Create Python Script (1 hour)
```python
# scripts/viz/generate_hierarchy_graphviz.py
import json
import sys
import httpx
from pathlib import Path

def fetch_hierarchy(solution_id: str, api_base: str = "http://localhost:8001/v1"):
    """Fetch hierarchy data from API"""
    response = httpx.get(f"{api_base}/api/supply-tree/solution/{solution_id}/hierarchy")
    response.raise_for_status()
    return response.json()["data"]

def hierarchy_to_dot(hierarchy_data: dict) -> str:
    """Convert hierarchy JSON to DOT format"""
    # Implementation here
    pass

def main():
    solution_id = sys.argv[1]
    hierarchy = fetch_hierarchy(solution_id)
    dot_content = hierarchy_to_dot(hierarchy)
    
    output_file = f"hierarchy_{solution_id}.dot"
    Path(output_file).write_text(dot_content)
    print(f"Generated {output_file}")
    print(f"Render with: dot -Tpng {output_file} -o {output_file.replace('.dot', '.png')}")

if __name__ == "__main__":
    main()
```

### Step 2: Implement DOT Generation (1 hour)
- Parse hierarchy tree structure
- Generate nodes with labels (component_name, facility_name, confidence)
- Generate edges (parent → child)
- Add styling (colors by depth, node shapes)

### Step 3: Test & Refine (1 hour)
- Test with nested solution
- Test with single-level solution
- Handle edge cases
- Improve visual styling

### Step 4: Create Documentation (30 min)
- Usage instructions
- Example outputs
- Integration with existing workflow

## Alternative Approaches

### Option A: Mermaid Format (Faster, Documentation-Friendly)
- Generate Mermaid syntax instead of DOT
- Can embed directly in markdown
- Use mermaid.live or mermaid CLI to render
- **Time:** 2-3 hours

### Option B: HTML/JavaScript (Interactive, More Complex)
- Generate HTML with D3.js or Cytoscape.js
- Interactive visualization
- Requires web server or file:// access
- **Time:** 4-6 hours

### Option C: CSV for RAWGraphs (Web-Based, Manual)
- Convert to CSV format
- Upload to rawgraphs.io
- Manual process but no code needed
- **Time:** 1 hour (but manual)

## Recommended Path: Graphviz (DOT)

**Why Graphviz?**
1. ✅ Simple text-based format (DOT)
2. ✅ Generates high-quality static images
3. ✅ Works well with tree/hierarchy structures
4. ✅ Easy to integrate into scripts
5. ✅ Can be extended to other graph types later

**Dependencies:**
- Python: `httpx` (or `requests`)
- System: `graphviz` (brew install graphviz / apt-get install graphviz)

**Output:**
- DOT file (text)
- PNG/SVG image (rendered)

## Next Steps After PoC

1. **Extend to other endpoints**
   - Dependencies graph visualization
   - Production sequence timeline

2. **Add more formats**
   - Mermaid export
   - CSV export for RAWGraphs
   - D3.js format export

3. **CLI Integration**
   - Add `ome solution viz` command
   - Support multiple formats
   - Support multiple endpoints

4. **Interactive Visualizations**
   - Web-based viewer
   - D3.js or Cytoscape.js implementation

## Files to Create

```
scripts/viz/
├── generate_hierarchy_graphviz.py  # Main script
├── dot_generator.py                 # DOT format generation
├── README.md                        # Usage instructions
└── examples/
    ├── hierarchy_example.png        # Example output
    └── hierarchy_example.dot        # Example DOT file
```

## Success Metrics

- [ ] Script runs successfully with nested solution
- [ ] Generated image clearly shows hierarchy
- [ ] Documentation is clear and complete
- [ ] Can be extended to other visualization types
- [ ] Takes < 5 minutes to run end-to-end

