# WF-1: Single-Level Design-to-Manufacturing Match

**Category**: Foundation
**Priority**: 1 (must pass before advanced workflows)
**Estimated Duration**: < 10s per parameterized case

---

## Overview

Validates the core matching pipeline for simple (non-nested) designs. Given a single OKH manifest and a pool of OKW facilities, the system should extract manufacturing requirements, run multi-layer matching (Direct, Heuristic, NLP), generate SupplyTrees for matching facilities, and return a valid `SupplyTreeSolution`.

This is the most fundamental workflow -- if single-level matching is broken, all downstream workflows (nested matching, solution lifecycle, etc.) are invalid.

---

## Prerequisites

### Fixtures

- `matching_service` -- Initialized `MatchingService` instance with capability rules loaded and NLP matchers pre-warmed.
- `okh_manifest(request)` -- Parameterized fixture that loads an `OKHManifest` from `synthetic_data/` by name.
- `okw_facilities` -- Fixture that loads all 20 OKW facilities from `synthetic_data/`.
- `single_facility_pool(request)` -- Parameterized fixture that loads a subset of facilities by type.

### Test Data

| File | Role |
|------|------|
| `synthetic_data/cnc-machined-aluminum-bracket-2-7-3-okh.json` | CNC design (simple, single process) |
| `synthetic_data/laser-cut-acrylic-display-case-2-3-3-okh.json` | Laser cutting design |
| `synthetic_data/sheet-metal-enclosure-2-9-1-okh.json` | Sheet metal design |
| `synthetic_data/3d-printed-prosthetic-hand-1-5-5-okh.json` | 3DP design with parts |
| `synthetic_data/arduino-based-iot-sensor-node-2-1-0-okh.json` | Electronics/PCB design |
| `synthetic_data/*-okw.json` (all 20) | Full facility pool |

### Services

- `MatchingService` (with `MfgDirectMatcher`, `CapabilityMatcher`, `NLPMatcher` initialized)
- `OKHService` (for manifest loading only -- no LLM dependency)
- `OKWService` (for facility loading)

---

## Steps

### Step 1: Load OKH manifest

**Action**: Load an OKH manifest from `synthetic_data/` and parse into `OKHManifest` via `OKHManifest.from_dict()`.

**Expected result**: A valid `OKHManifest` object with:
- Non-empty `id` (UUID)
- Non-empty `manufacturing_processes` list
- Non-empty `tsdc` list
- At least one of: `materials`, `parts`, or `manufacturing_specs`

### Step 2: Load OKW facility pool

**Action**: Load all 20 OKW facility JSON files from `synthetic_data/` and parse into `ManufacturingFacility` objects.

**Expected result**: List of 20 `ManufacturingFacility` objects, each with:
- Non-empty `id`
- Non-empty `equipment` list
- At least one equipment item with a `manufacturing_process` URI

### Step 3: Extract requirements from OKH

**Action**: Call `okh_manifest.extract_requirements()` to get the list of manufacturing requirements.

**Expected result**: A non-empty list of process requirement strings (e.g., `"3DP"`, `"CNC"`, `"PCB"`).

### Step 4: Execute matching

**Action**: Call `matching_service.find_matches_with_manifest(okh_manifest, facilities)`.

**Expected result**: A non-empty `Set[SupplyTreeSolution]` containing at least one solution.

### Step 5: Validate solution structure

**Action**: Inspect each `SupplyTreeSolution` in the result set.

**Expected result**: Each solution has:
- `all_trees` is non-empty
- `root_trees` is non-empty
- `score` is a float in range `[0.0, 1.0]`
- `is_nested` is `False`
- Each `SupplyTree` in `all_trees` has:
  - `facility_name` is non-empty string
  - `confidence_score` in range `[0.0, 1.0]`
  - `match_type` is one of `"direct"`, `"heuristic"`, `"nlp"`, `"unknown"`
  - `okh_reference` is non-empty
  - `okw_reference` is non-empty

### Step 6: Verify match correctness

**Action**: For each matched facility in the solution, verify that the facility's capabilities actually overlap with the OKH's requirements.

**Expected result**: For every `SupplyTree` in the solution, the referenced OKW facility has at least one `equipment` entry whose `manufacturing_process` URI relates to one of the OKH's `manufacturing_processes` or `tsdc` codes.

---

## Assertions

### Functional Assertions

```python
# Step 1: Manifest loads correctly
assert isinstance(okh_manifest, OKHManifest)
assert okh_manifest.id is not None
assert len(okh_manifest.manufacturing_processes) > 0

# Step 4: Matching produces results
solutions = await matching_service.find_matches_with_manifest(okh_manifest, facilities)
assert len(solutions) > 0, "Expected at least one matching solution"

# Step 5: Solution structure is valid
for solution in solutions:
    assert len(solution.all_trees) > 0
    assert len(solution.root_trees) > 0
    assert solution.is_nested is False
    assert 0.0 <= solution.score <= 1.0
```

### Structural Assertions

```python
# Each tree has required fields populated
for solution in solutions:
    for tree in solution.all_trees:
        assert tree.facility_name, "facility_name must be non-empty"
        assert tree.okh_reference, "okh_reference must be non-empty"
        assert tree.okw_reference, "okw_reference must be non-empty"
        assert 0.0 <= tree.confidence_score <= 1.0
        assert tree.match_type in ("direct", "heuristic", "nlp", "unknown")
```

### Scoring Assertions

```python
# Solutions should be distinguishable by score
scores = [s.score for s in solutions]
assert max(scores) > 0.0, "At least one solution should have a non-zero score"

# Direct matches should score higher than NLP matches (when both exist)
direct_scores = [t.confidence_score for s in solutions for t in s.all_trees if t.match_type == "direct"]
nlp_scores = [t.confidence_score for s in solutions for t in s.all_trees if t.match_type == "nlp"]
if direct_scores and nlp_scores:
    assert max(direct_scores) >= max(nlp_scores), "Direct matches should score >= NLP matches"
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `design_type` | `cnc-bracket`, `laser-case`, `sheet-metal`, `3dp-prosthetic`, `iot-sensor` | Cover all 5 design domains |
| `facility_pool` | `all` (20 facilities), `matching-only` (facilities relevant to design), `non-matching` (no overlap) | Test match/no-match scenarios |

```python
@pytest.mark.parametrize("design_file", [
    "cnc-machined-aluminum-bracket-2-7-3-okh.json",
    "laser-cut-acrylic-display-case-2-3-3-okh.json",
    "sheet-metal-enclosure-2-9-1-okh.json",
    "3d-printed-prosthetic-hand-1-5-5-okh.json",
    "arduino-based-iot-sensor-node-2-1-0-okh.json",
])
def test_single_level_matching(design_file, okw_facilities, matching_service):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Manifest load + parse | < 100ms | JSON parse only, no I/O |
| Facility pool load (20 facilities) | < 500ms | JSON parse only |
| Requirement extraction | < 50ms | In-memory operation |
| Matching (full pipeline, 20 facilities) | < 5s | Includes Direct + Heuristic + NLP layers |
| Total workflow (steps 1-6) | < 10s | End-to-end per design type |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| OKH with single manufacturing process | Should match facilities with that specific capability |
| OKH with multiple processes (e.g., 3DP + Assembly) | Should only match facilities supporting ALL required processes |
| OKH with TSDC codes only (no `manufacturing_processes` strings) | TSDC codes should be resolved to process URIs for matching |
| Facility pool with duplicate capabilities | Each unique facility should appear at most once per solution |
| OKH with `manufacturing_specs.process_requirements` | Process parameters should not block matching (informational only at this stage) |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] Add a synthetic OKH manifest with only TSDC codes and no `manufacturing_processes` strings to test TSDC-driven matching in isolation.
- [ ] Add a synthetic OKH manifest requiring multiple disparate processes (e.g., CNC + PCB + assembly) to test multi-requirement matching.
- [ ] Add a "non-matching" OKW facility pool fixture (facilities with no overlap to a given design) for testing the no-match path as part of WF-6.

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf01_single_level_matching.py`
- **Fixtures**: `matching_service`, `okh_manifest`, `okw_facilities`
- **Markers**: `@pytest.mark.e2e`
- **Parameterize**: `design_file` (5 design types)
- **Shared conftest**: `tests/e2e/conftest.py` (service initialization, data loading helpers)
