# WF-6: No-Match and Error Recovery

**Category**: Resilience
**Priority**: 2 (important for production readiness, depends on WF-1 for context)
**Estimated Duration**: < 10s per scenario

---

## Overview

Validates that the system degrades gracefully when inputs are malformed, incomplete, or unmatchable. The system should:

- Return empty results (not crash) when no facilities match an OKH design.
- Return partial results when only some requirements can be satisfied.
- Raise specific, actionable validation errors for malformed inputs.
- Handle edge cases like empty inputs, missing fields, and type mismatches without unhandled exceptions.

This workflow is the "negative testing" complement to WF-1 (happy path matching) and ensures the system is production-safe.

---

## Prerequisites

### Fixtures

- `matching_service` -- Initialized `MatchingService`.
- `okw_facilities` -- Full pool of 20 OKW facilities.
- `malformed_okh_data(request)` -- Parameterized fixture providing intentionally broken OKH dicts.
- `unmatchable_okh(request)` -- Parameterized fixture providing OKH manifests with unmatchable requirements.

### Test Data

| Input | Role | Category |
|-------|------|----------|
| OKH with `manufacturing_processes: ["quantum_lithography"]` | Exotic process no facility supports | No-match |
| OKH with `manufacturing_processes: ["3DP", "quantum_lithography"]` | One matchable, one unmatchable | Partial match |
| OKH with `manufacturing_processes: []` | Empty process list | Empty input |
| OKH dict with `title: null` | Missing required field | Malformed |
| `{"invalid": "not_an_okh"}` | Completely wrong schema | Malformed |
| `"not valid json"` | Invalid JSON string | Parse error |
| OKH with `manufacturing_processes: [123, true]` | Wrong data types in array | Type error |
| Empty OKW facility list `[]` | No facilities available | Empty pool |

### Services

- `MatchingService` (matching pipeline)
- `OKHService` (manifest parsing)
- `ManufacturingOKHValidator` (validation)

---

## Steps

### Scenario A: No Matching Facilities

#### Step A1: Load unmatchable OKH

**Action**: Create an `OKHManifest` with `manufacturing_processes: ["quantum_lithography"]` (a process no facility offers).

**Expected result**: Valid `OKHManifest` object (the manifest itself is valid; it just won't match anything).

#### Step A2: Execute matching against full facility pool

**Action**: Call `matching_service.find_matches_with_manifest(unmatchable_okh, facilities)`.

**Expected result**:
- Returns an empty set (no solutions), OR
- Returns solutions with zero trees, OR
- Raises a specific "no matches found" exception (depending on implementation).
- Does NOT raise an unhandled exception or crash.

#### Step A3: Verify no-match response is informative

**Action**: Inspect the result or exception.

**Expected result**: The response should indicate WHY no matches were found (e.g., "No facilities found with process: quantum_lithography").

---

### Scenario B: Partial Matching

#### Step B1: Load partially matchable OKH

**Action**: Create an `OKHManifest` with `manufacturing_processes: ["3DP", "quantum_lithography"]` -- one real, one impossible.

**Expected result**: Valid `OKHManifest` object.

#### Step B2: Execute matching

**Action**: Call `matching_service.find_matches_with_manifest(partial_okh, facilities)`.

**Expected result**:
- May return solutions where `3DP` is matched but `quantum_lithography` is not.
- OR returns empty if the system requires ALL requirements to be satisfied.
- Behaviour is consistent and documented regardless of which path is taken.
- No unhandled exceptions.

---

### Scenario C: Malformed OKH Input

#### Step C1: Parse invalid OKH dict

**Action**: Call `OKHManifest.from_dict({"invalid": "not_an_okh"})`.

**Expected result**:
- Raises a specific exception (e.g., `ValueError`, `KeyError`, or custom parsing error).
- Error message references the missing/invalid fields.
- Does NOT crash with `AttributeError` or `TypeError`.

#### Step C2: Validate malformed OKH

**Action**: Pass malformed data to `manufacturing_okh_validator.validate(malformed_dict, context)`.

**Expected result**:
- Returns `ValidationResult` with `valid=False`.
- `errors` list is non-empty with descriptive messages.
- No unhandled exceptions.

#### Step C3: Feed malformed data to matching

**Action**: Attempt to pass malformed data directly to matching.

**Expected result**:
- Raises a clear validation error before matching begins, OR
- Returns an error response indicating the input is invalid.
- Does NOT attempt matching with invalid data.

---

### Scenario D: Empty Inputs

#### Step D1: Match with empty facility pool

**Action**: Call `matching_service.find_matches_with_manifest(valid_okh, [])`.

**Expected result**:
- Returns empty set (no solutions).
- No unhandled exceptions.

#### Step D2: Match OKH with no processes

**Action**: Create an `OKHManifest` with `manufacturing_processes: []` and `tsdc: []`, then attempt matching.

**Expected result**:
- Returns empty set (nothing to match against), OR
- Raises a clear error indicating "no requirements to match".
- Does NOT match every facility by default.

---

### Scenario E: Type Errors in Data

#### Step E1: OKH with wrong types in fields

**Action**: Attempt `OKHManifest.from_dict({"title": 123, "manufacturing_processes": "not_a_list"})`.

**Expected result**:
- Raises a type-related error or coerces gracefully.
- Error message indicates which field has the wrong type.

---

## Assertions

### No-Crash Assertions (apply to ALL scenarios)

```python
# The system should NEVER raise these for bad input:
# - AttributeError (accessing field on None)
# - TypeError (wrong type passed internally)
# - KeyError (missing dict key without guard)
# - IndexError (accessing empty list)
# - RecursionError (infinite loop)

# Instead, it should raise or return one of:
# - ValueError with descriptive message
# - ValidationResult with valid=False and errors
# - Empty result set
# - Custom exception (DatasheetConversionError, etc.)
```

### No-Match Assertions

```python
# Scenario A: Unmatchable OKH
try:
    solutions = await matching_service.find_matches_with_manifest(
        unmatchable_okh, facilities
    )
    # If it returns normally, should be empty
    assert len(solutions) == 0, "Unmatchable OKH should produce no solutions"
except Exception as e:
    # If it raises, should be a clear, specific exception
    assert "no match" in str(e).lower() or "not found" in str(e).lower(), (
        f"Exception should indicate no matches, got: {e}"
    )
```

### Malformed Input Assertions

```python
# Scenario C: Malformed dict
result = await validator.validate({"invalid": "data"}, professional_ctx)
assert result.valid is False
assert result.error_count > 0
assert any("parse" in e.message.lower() or "required" in e.message.lower()
           for e in result.errors)
```

### Empty Input Assertions

```python
# Scenario D: Empty facility pool
solutions = await matching_service.find_matches_with_manifest(valid_okh, [])
assert len(solutions) == 0, "Empty facility pool should yield no solutions"
```

### Error Quality Assertions

```python
# All error messages should be human-readable
for error in result.errors:
    assert len(error.message) > 10, "Error messages should be descriptive, not just codes"
    assert error.message[0].isupper(), "Error messages should start with uppercase"
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `scenario` | `no_match`, `partial_match`, `malformed`, `empty_input`, `type_error` | All error categories |
| `malformed_variant` | `missing_title`, `wrong_schema`, `invalid_json`, `wrong_types` | Different malformation types |
| `empty_variant` | `empty_facilities`, `empty_processes`, `empty_manifest` | Different empty conditions |

```python
@pytest.mark.parametrize("malformed_data,expected_error_substring", [
    ({"invalid": "schema"}, "parse"),
    ({"title": None, "version": "1.0"}, "title"),
    ({"title": "Test", "manufacturing_processes": "not_a_list"}, "type"),
])
def test_malformed_input_handling(malformed_data, expected_error_substring, ...):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Malformed input rejection | < 100ms | Should fail fast on validation |
| No-match detection | < 5s | Full matching pipeline may run before determining no matches |
| Empty pool detection | < 100ms | Should short-circuit before matching |
| Error response generation | < 50ms | Error formatting is lightweight |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| OKH with `manufacturing_processes: [""]` (empty string in list) | Treated as "no process"; skipped or rejected cleanly |
| OKH with `manufacturing_processes: [null]` (None in list) | Filtered out or rejected with clear error |
| Very long string values (10,000+ chars) | Should not cause memory issues or timeout |
| Deeply nested invalid JSON (100+ levels) | Should not cause stack overflow; rejected at parse time |
| Concurrent error scenarios (multiple bad inputs at once) | Each handled independently; no shared state corruption |
| OKW facility with `equipment: []` (no equipment) | Facility skipped during matching; does not cause error |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] **Critical**: Create intentionally malformed OKH files in `tests/data/okh/invalid/`:
  - `missing_required_fields.json` -- OKH dict missing `title`, `version`
  - `wrong_types.json` -- OKH dict with integer where string expected, string where list expected
  - `wrong_schema.json` -- Valid JSON but not an OKH structure
  - `empty_object.json` -- `{}`
  - `null_values.json` -- Required fields set to `null`
- [ ] **Critical**: Create OKH manifests with unmatchable requirements in `tests/data/okh/edge_cases/`:
  - `exotic_process.json` -- Manufacturing process no facility has
  - `partial_match.json` -- Mix of matchable and unmatchable processes
  - `empty_processes.json` -- `manufacturing_processes: []` and `tsdc: []`
- [ ] Create OKW facility edge cases in `tests/data/okw/edge_cases/`:
  - `no_equipment.json` -- Facility with empty equipment list
  - `minimal_facility.json` -- Only required fields

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf06_error_recovery.py`
- **Fixtures**: `matching_service`, `okw_facilities`, `malformed_okh_data`, `unmatchable_okh`, `manufacturing_okh_validator`
- **Markers**: `@pytest.mark.e2e`
- **Parameterize**: `scenario` (5 categories) x `variant` (2-4 per category) = ~15 test cases
- **Shared conftest**: `tests/e2e/conftest.py`
