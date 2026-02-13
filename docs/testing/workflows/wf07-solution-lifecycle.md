# WF-7: Solution Lifecycle Management

**Category**: Resilience
**Priority**: 2 (depends on WF-1 or WF-2 to produce a solution)
**Estimated Duration**: < 15s per test case

---

## Overview

Validates the complete lifecycle of a `SupplyTreeSolution` through the storage system: save, load, list, check staleness, extend TTL, and cleanup. The system should correctly persist solutions, manage metadata (timestamps, TTL, tags), detect stale solutions, and clean up expired entries.

This workflow connects to WF-1 or WF-2 (which produce solutions) and tests the storage layer's solution management features in `StorageService`.

---

## Prerequisites

### Fixtures

- `storage_service` -- Initialized `StorageService` configured for local storage (not Azure Blob in tests).
- `sample_solution` -- A pre-built `SupplyTreeSolution` from WF-1 matching (can be created directly from test data to avoid full matching).
- `sample_nested_solution` -- A pre-built nested `SupplyTreeSolution` from WF-2 matching.
- `tmp_storage(tmp_path)` -- Temporary local storage directory for test isolation.

### Test Data

The input is a `SupplyTreeSolution` object, not raw files. The solution can be constructed either by:
1. Running WF-1/WF-2 matching to produce a real solution, OR
2. Building a solution directly using the `SupplyTreeSolution.from_single_tree()` / `from_nested_trees()` factory methods with synthetic data.

### Services

- `StorageService` (solution persistence, metadata management)
  - `save_supply_tree_solution()`
  - `load_supply_tree_solution()`
  - `list_supply_tree_solutions()`
  - `extend_solution_ttl()`
  - `cleanup_stale_solutions()`
  - `load_supply_tree_solution_with_metadata()`
  - `delete_supply_tree_solution()`

---

## Steps

### Step 1: Save a solution

**Action**: Call `storage_service.save_supply_tree_solution(solution, ttl_days=7, tags=["test", "wf07"])`.

**Expected result**:
- Returns a `UUID` (the `solution_id`).
- Solution data file exists at `supply-tree-solutions/{solution_id}.json`.
- Metadata file exists at `supply-tree-solutions/metadata/{solution_id}.json`.
- Metadata contains: `id`, `created_at`, `updated_at`, `expires_at`, `ttl_days=7`, `tags=["test", "wf07"]`, `tree_count`, `score`.

### Step 2: Load the solution back

**Action**: Call `storage_service.load_supply_tree_solution(solution_id)`.

**Expected result**:
- Returns a `SupplyTreeSolution` object.
- `all_trees` matches the original solution's `all_trees` (same count, same facility names).
- `score` matches the original.
- `is_nested` matches the original.
- `metadata` is preserved.

### Step 3: List solutions

**Action**: Call `storage_service.list_supply_tree_solutions()`.

**Expected result**:
- Returns a list containing at least one entry.
- The saved solution appears in the list with correct metadata.
- Filtering by `matching_mode` works correctly.

### Step 4: Load with metadata and freshness check

**Action**: Call `storage_service.load_supply_tree_solution_with_metadata(solution_id, validate_freshness=True)`.

**Expected result**:
- Returns a tuple of `(solution, metadata_dict)`.
- `metadata_dict["is_stale"]` is `False` (solution was just created, TTL=7 days).
- `metadata_dict["age_days"]` is `0`.

### Step 5: Extend TTL

**Action**: Call `storage_service.extend_solution_ttl(solution_id, additional_days=30)`.

**Expected result**:
- Returns `True`.
- Metadata file updated: `expires_at` extended by 30 days, `updated_at` is recent, `ttl_days` increased by 30.

### Step 6: Verify TTL extension

**Action**: Reload metadata and verify the extension took effect.

**Expected result**:
- `expires_at` is now 37 days from original `created_at` (7 original + 30 extended).
- `updated_at` is more recent than `created_at`.

### Step 7: Staleness detection (dry run)

**Action**: Call `storage_service.cleanup_stale_solutions(max_age_days=0, dry_run=True)`.

Note: `max_age_days=0` means "consider everything older than 0 days as stale" -- this should flag our solution since it was created in the past (even if moments ago), depending on implementation. Alternatively, use a very short TTL solution created in a prior step.

**Expected result**:
- Returns `{"dry_run": True, "deleted_count": N, "deleted_ids": [...]}`.
- Our recently-extended solution should NOT be in the stale list (its `expires_at` is 37 days out).
- `dry_run=True` means no actual deletion.

### Step 8: Create and expire a solution

**Action**: Save a second solution with `ttl_days=0` (immediate expiration), then check staleness.

**Expected result**:
- Second solution's `expires_at` is in the past (or at creation time).
- `cleanup_stale_solutions(dry_run=True)` includes the second solution in `deleted_ids`.
- First solution (TTL extended to 37 days) is NOT in `deleted_ids`.

### Step 9: Cleanup stale solutions (real)

**Action**: Call `storage_service.cleanup_stale_solutions(dry_run=False)` to actually delete the expired solution.

**Expected result**:
- Returns `{"dry_run": False, "deleted_count": 1, "freed_space": N}`.
- The expired solution's files are removed from storage.
- The non-expired solution's files remain.

### Step 10: Delete solution

**Action**: Call `storage_service.delete_supply_tree_solution(solution_id)` for the remaining solution.

**Expected result**:
- Returns `True`.
- Solution data file no longer exists.
- Metadata file no longer exists.
- `load_supply_tree_solution(solution_id)` raises an exception.

---

## Assertions

### Save/Load Round-Trip Assertions

```python
# Step 1: Save returns valid UUID
solution_id = await storage_service.save_supply_tree_solution(
    solution, ttl_days=7, tags=["test", "wf07"]
)
assert isinstance(solution_id, UUID)

# Step 2: Load returns equivalent solution
loaded = await storage_service.load_supply_tree_solution(solution_id)
assert isinstance(loaded, SupplyTreeSolution)
assert len(loaded.all_trees) == len(solution.all_trees)
assert loaded.score == pytest.approx(solution.score, abs=0.01)
assert loaded.is_nested == solution.is_nested

# Tree contents preserved
original_facilities = sorted(t.facility_name for t in solution.all_trees)
loaded_facilities = sorted(t.facility_name for t in loaded.all_trees)
assert original_facilities == loaded_facilities
```

### Metadata Assertions

```python
# Step 4: Metadata is correct
solution_obj, metadata = await storage_service.load_supply_tree_solution_with_metadata(
    solution_id, validate_freshness=True
)
assert metadata["is_stale"] is False
assert "created_at" in metadata
assert "expires_at" in metadata
assert metadata.get("age_days", 0) <= 1  # Just created
```

### TTL Extension Assertions

```python
# Step 5: TTL extension succeeds
result = await storage_service.extend_solution_ttl(solution_id, additional_days=30)
assert result is True

# Step 6: Verify extended metadata
_, metadata_after = await storage_service.load_supply_tree_solution_with_metadata(
    solution_id, validate_freshness=True
)
assert metadata_after["is_stale"] is False
# TTL should be original 7 + extended 30 = 37
assert metadata_after.get("ttl_days", 0) >= 37
```

### Staleness and Cleanup Assertions

```python
# Step 7: Dry run does not delete
dry_result = await storage_service.cleanup_stale_solutions(dry_run=True)
assert dry_result["dry_run"] is True

# Step 9: Real cleanup deletes expired solution
cleanup_result = await storage_service.cleanup_stale_solutions(dry_run=False)
assert cleanup_result["dry_run"] is False
assert str(expired_solution_id) in cleanup_result["deleted_ids"]
assert str(solution_id) not in cleanup_result["deleted_ids"]  # Not expired
```

### Deletion Assertions

```python
# Step 10: Delete succeeds
delete_result = await storage_service.delete_supply_tree_solution(solution_id)
assert delete_result is True

# Load after delete should fail
with pytest.raises(Exception):
    await storage_service.load_supply_tree_solution(solution_id)
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `solution_type` | `single_tree`, `nested_trees` | Both solution types should persist correctly |
| `ttl_days` | `0`, `7`, `30`, `365` | Various TTL values including edge cases |
| `storage_backend` | `local` | Local storage for tests; cloud backends tested in integration |

```python
@pytest.mark.parametrize("solution_type", ["single_tree", "nested_trees"])
@pytest.mark.parametrize("ttl_days", [0, 7, 30])
def test_solution_lifecycle(solution_type, ttl_days, storage_service, ...):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Save solution | < 500ms | JSON serialization + file write |
| Load solution | < 500ms | File read + JSON deserialization |
| List solutions (< 100 solutions) | < 1s | Directory listing + metadata reads |
| TTL extension | < 200ms | Metadata read + update + write |
| Staleness check (< 100 solutions) | < 2s | Iterate metadata files |
| Cleanup (dry run) | < 2s | Same as staleness check |
| Cleanup (real, 10 solutions) | < 5s | Delete files + metadata |
| Delete single solution | < 200ms | Delete 2 files (data + metadata) |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| Save solution with `ttl_days=0` | Solution expires immediately; appears in stale list |
| Save two solutions with same content | Each gets a unique UUID; both persist independently |
| Load non-existent solution_id | Raises exception with descriptive message |
| Extend TTL on non-existent solution | Returns `False`; no side effects |
| Extend TTL with `additional_days=0` | No-op; expiration unchanged |
| Cleanup with no stale solutions | Returns `{"deleted_count": 0}` |
| Delete already-deleted solution | Returns `False` or raises; no crash |
| Save solution with very large tree count (1000+) | Succeeds; may be slow but should not fail |
| List with filtering that matches nothing | Returns empty list, not error |
| Concurrent save/load on same solution_id | Last write wins; no corruption |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] Create factory functions in `tests/e2e/conftest.py` that build `SupplyTreeSolution` objects directly from synthetic data (without running matching) for fast test setup.
- [ ] Create a `SupplyTreeSolution` fixture with known field values for deterministic round-trip comparison.
- [ ] Ensure local storage backend is easily configurable for test isolation (tmp directories).

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf07_solution_lifecycle.py`
- **Fixtures**: `storage_service`, `sample_solution`, `sample_nested_solution`, `tmp_storage`
- **Markers**: `@pytest.mark.e2e`
- **Parameterize**: `solution_type` (single/nested) x `ttl_days` (0, 7, 30)
- **Shared conftest**: `tests/e2e/conftest.py`
