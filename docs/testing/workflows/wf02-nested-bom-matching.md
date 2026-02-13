# WF-2: Nested Multi-Facility BOM Matching

**Category**: Advanced
**Priority**: 1 (core feature, depends on WF-1)
**Estimated Duration**: < 30s per parameterized case

---

## Overview

Validates the nested matching pipeline for complex designs with Bills of Materials (BOMs). Given an OKH manifest with nested parts/sub-parts, the system should explode the BOM into a flat component list, match each component independently to appropriate facilities, build a dependency graph between components, compute a valid production sequence, and return a nested `SupplyTreeSolution`.

This workflow exercises `BOMResolutionService.explode_bom()` and `MatchingService.match_with_nested_components()` -- the most complex code paths in the system.

---

## Prerequisites

### Fixtures

- `matching_service` -- Initialized `MatchingService` with all matching layers ready.
- `bom_resolution_service` -- Initialized `BOMResolutionService`.
- `nested_okh_manifest(request)` -- Parameterized fixture loading OKH manifests that have nested parts.
- `okw_facilities` -- Full pool of 20 OKW facilities from `synthetic_data/`.

### Test Data

| File | Role | Nesting |
|------|------|---------|
| `synthetic_data/3d-printed-prosthetic-hand-1-5-5-okh.json` | 3DP design with parts list | 1-level (parts) |
| `synthetic_data/arduino-based-iot-sensor-node-2-1-0-okh.json` | Electronics with multi-process parts | 1-level (parts) |
| `synthetic_data/3d-printed-prosthetic-hand-3-5-7-okh.json` | Alternate version for comparison | 1-level (parts) |
| `synthetic_data/*-okw.json` (all 20) | Full facility pool | -- |

**Note**: Current synthetic data only has 1-level nesting (parts arrays). See Gap Flags for 2+ level nesting needs.

### Services

- `MatchingService` (full pipeline)
- `BOMResolutionService` (BOM detection, explosion, component resolution)
- `OKHService` (for resolving external OKH references in sub-parts)
- `OKWService` (for facility loading)

---

## Steps

### Step 1: Load OKH manifest with nested components

**Action**: Load an OKH manifest that has a non-empty `parts` list from `synthetic_data/`.

**Expected result**: A valid `OKHManifest` where:
- `parts` is a non-empty list of `PartSpec` objects
- Each part has `name`, `id`, and at least one of `tsdc`, `material`, or `source`

### Step 2: Detect BOM type

**Action**: Call `bom_resolution_service._detect_bom_type(okh_manifest)`.

**Expected result**: Returns `"embedded"` (since parts data is inline in the manifest).

### Step 3: Resolve and explode BOM

**Action**: Resolve the BOM from the manifest and call `bom_resolution_service.explode_bom(bom)`.

**Expected result**: A list of `ComponentMatch` objects where:
- Length equals the total number of parts (recursively, across all nesting levels)
- Each `ComponentMatch` has a valid `component` with `name` and `id`
- `depth` values reflect nesting level (0 for root-level parts)
- `path` tracks lineage from root

### Step 4: Execute nested matching

**Action**: Call `matching_service.match_with_nested_components(okh_manifest, facilities)`.

**Expected result**: A single `SupplyTreeSolution` where:
- `is_nested` is `True`
- `all_trees` contains trees for the root manifest AND for individual components
- `component_mapping` maps component IDs to their matched `SupplyTree` lists
- `root_trees` contains the top-level trees

### Step 5: Validate dependency graph

**Action**: Inspect `solution.dependency_graph`.

**Expected result**:
- Graph is a dict mapping tree IDs to lists of dependent tree IDs
- No circular dependencies exist
- Every tree referenced in the graph exists in `all_trees`

### Step 6: Validate production sequence

**Action**: Inspect `solution.production_sequence`.

**Expected result**:
- Production sequence is a list of tree IDs in topological order
- Components with dependencies appear AFTER their dependencies
- All trees in `all_trees` are represented in the sequence

### Step 7: Validate solution

**Action**: Call `solution.validate_solution()`.

**Expected result**: A `ValidationResult` where:
- `is_valid` is `True`
- `errors` is empty
- `unmatched_components` is empty
- `circular_dependencies` is empty

---

## Assertions

### Functional Assertions

```python
# Step 1: Manifest has parts
assert len(okh_manifest.parts) > 0, "Manifest must have nested parts"

# Step 3: BOM explosion produces components
component_matches = await bom_resolution_service.explode_bom(bom)
assert len(component_matches) > 0, "BOM explosion must produce at least one component"
assert len(component_matches) >= len(okh_manifest.parts), "At least as many components as parts"

# Step 4: Nested matching produces results
solution = await matching_service.match_with_nested_components(okh_manifest, facilities)
assert solution is not None
assert solution.is_nested is True
assert len(solution.all_trees) > 0
```

### Structural Assertions

```python
# Component mapping covers all parts
for part in okh_manifest.parts:
    part_id = str(part.id) if hasattr(part, 'id') else part.get('id')
    # Component should appear in the mapping (or be matched at root level)
    assert any(
        part_id in cid or part.name.lower() in cid.lower()
        for cid in solution.component_mapping.keys()
    ) or len(solution.root_trees) > 0, f"Part {part.name} should be in component_mapping"

# Parent-child relationships are consistent
for tree in solution.all_trees:
    if tree.parent_tree_id:
        parent_ids = {str(t.id) for t in solution.all_trees}
        assert str(tree.parent_tree_id) in parent_ids, "Parent tree must exist in all_trees"
```

### Dependency Assertions

```python
# No circular dependencies
validation = solution.validate_solution()
assert len(validation.circular_dependencies) == 0, "No circular dependencies allowed"

# Production sequence is a valid topological ordering
if solution.production_sequence:
    seen = set()
    for tree_id in solution.production_sequence:
        # All dependencies should have been seen already
        deps = solution.dependency_graph.get(str(tree_id), [])
        for dep_id in deps:
            assert dep_id in seen, f"Dependency {dep_id} must appear before {tree_id}"
        seen.add(str(tree_id))
```

### Component-Level Matching Assertions

```python
# Components with TSDC codes should match based on THEIR tsdc, not root manifest's
for tree in solution.all_trees:
    if tree.component_id and tree.match_type == "direct":
        # The matched facility should have equipment for the component's process,
        # not necessarily the root manifest's processes
        assert tree.confidence_score > 0.0
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `design_file` | `3d-printed-prosthetic-hand-1-5-5`, `arduino-based-iot-sensor-node-2-1-0` | Designs with parts lists |
| `max_depth` | `1`, `2`, `None` (unlimited) | Test depth limiting |
| `facility_pool_size` | `all` (20), `subset` (5 relevant) | Test with sparse vs. rich facility pools |

```python
@pytest.mark.parametrize("design_file,expected_min_components", [
    ("3d-printed-prosthetic-hand-1-5-5-okh.json", 1),
    ("arduino-based-iot-sensor-node-2-1-0-okh.json", 1),
])
@pytest.mark.parametrize("max_depth", [1, 2, None])
def test_nested_bom_matching(design_file, expected_min_components, max_depth, ...):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| BOM detection | < 10ms | Simple field inspection |
| BOM explosion (1-level, < 10 parts) | < 100ms | In-memory recursion |
| BOM explosion (2-level, < 50 parts) | < 500ms | With external OKH resolution |
| Per-component matching | < 5s | Full matching pipeline per component |
| Total nested matching (10 components) | < 30s | Includes all components + graph building |
| Solution validation | < 100ms | In-memory graph traversal |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| Part with no TSDC code and no manufacturing_processes | Falls back to root manifest's processes for matching |
| Part referencing external OKH manifest (via `source` URL) | `BOMResolutionService` resolves the reference and loads nested manifest |
| Duplicate part IDs in parts list | Each instance matched independently; both appear in `component_mapping` |
| Part with material but no process specified | Material alone should not drive matching; process is required |
| `max_depth=1` with 2-level nesting | Only first level of parts matched; deeper parts ignored |
| Empty parts list but non-empty sub_parts | `sub_parts` should be resolved instead |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] Create OKH manifests with 2+ levels of nesting (parts containing sub_parts that reference external OKH manifests with their own parts). Current synthetic data only has 1-level nesting.
- [ ] Create OKH manifests where different parts require different manufacturing processes (e.g., one part needs 3DP, another needs CNC, another needs PCB fabrication) to test true multi-facility matching.
- [ ] Create OKH manifests with `bom` field pointing to external BOM files (JSON/YAML) to test the external BOM resolution path.
- [ ] Create OKH manifests with parts that have conflicting TSDC codes vs. root manifest TSDC codes to verify component-level TSDC takes precedence.

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf02_nested_bom_matching.py`
- **Fixtures**: `matching_service`, `bom_resolution_service`, `nested_okh_manifest`, `okw_facilities`
- **Markers**: `@pytest.mark.e2e`, `@pytest.mark.slow`
- **Parameterize**: `design_file` (2+ designs), `max_depth` (1, 2, None)
- **Shared conftest**: `tests/e2e/conftest.py`
