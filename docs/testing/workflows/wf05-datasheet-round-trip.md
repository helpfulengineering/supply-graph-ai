# WF-5: Datasheet Conversion Round-Trip

**Category**: Advanced
**Priority**: 2 (depends on WF-4 for validation of round-tripped manifests)
**Estimated Duration**: < 5s per parameterized case

---

## Overview

Validates the fidelity of bi-directional conversion between OKH manifests and MSF (Maker Space Foundation) datasheets in `.docx` format. The system should:

1. Convert an OKH manifest to a populated MSF datasheet (`.docx`).
2. Parse that datasheet back into an OKH manifest.
3. Compare the original and round-tripped manifests for field preservation.

This workflow exercises the `DatasheetConverter` service, which maps OKH fields to/from the 6-table MSF datasheet structure (Header, Identity, FORM, FIT, FUNCTION, ATTACHMENTS).

Some field loss is expected and acceptable -- the MSF datasheet format does not have slots for every OKH field. The workflow documents exactly which fields must be preserved and which are expected to be lost.

---

## Prerequisites

### Fixtures

- `datasheet_converter` -- Initialized `DatasheetConverter` with the MSF template path.
- `okh_manifest(request)` -- Parameterized fixture loading OKH manifests from `synthetic_data/`.
- `tmp_path` -- pytest built-in fixture for temporary file output.

### Test Data

| File | Role |
|------|------|
| `synthetic_data/3d-printed-prosthetic-hand-1-5-5-okh.json` | Comprehensive manifest with materials, standards, specs |
| `synthetic_data/cnc-machined-aluminum-bracket-2-7-3-okh.json` | Standard manifest with process requirements |
| `synthetic_data/3d-printed-prosthetic-hand-datasheet.docx` | Reference datasheet for comparison |
| `notes/msf/datasheet-template.docx` | Blank MSF template used by the converter |

### Services

- `DatasheetConverter` (bi-directional conversion)

### External Dependencies

- `python-docx` library (for `.docx` manipulation)

---

## Steps

### Step 1: Load source OKH manifest

**Action**: Load an OKH manifest from `synthetic_data/` and parse into `OKHManifest`.

**Expected result**: A valid `OKHManifest` with populated fields including `title`, `version`, `license`, `function`, `materials`, `manufacturing_processes`, and `manufacturing_specs`.

### Step 2: Convert OKH to MSF datasheet

**Action**: Call `converter.okh_to_datasheet(manifest, output_path)` where `output_path` is a temporary `.docx` file.

**Expected result**:
- Returns the absolute path of the written file.
- File exists on disk and is a valid `.docx`.
- File size is greater than 0 bytes.
- No `DatasheetConversionError` raised.

### Step 3: Parse datasheet back to OKH

**Action**: Call `converter.datasheet_to_okh(docx_path)` on the generated file.

**Expected result**:
- Returns a valid `OKHManifest` object.
- No `DatasheetConversionError` raised.

### Step 4: Compare preserved fields

**Action**: Compare the original manifest with the round-tripped manifest on fields that the MSF format can represent.

**Expected preserved fields**:

| Field | Mapping | Notes |
|-------|---------|-------|
| `title` | Table 1: Name | Exact match expected |
| `version` | Table 1: Internal Reference | May include prefix |
| `license.hardware` | Table 2: License | License string representation |
| `function` | Table 4: Description | Text content preserved |
| `materials` | Table 3: Materials | Material names preserved; quantities may be lost |
| `manufacturing_processes` | Table 3: Manufacturing instructions | Process names preserved |
| `manufacturing_specs.outer_dimensions` | Table 2: Dimensions | Length/width/height values |
| `standards_used` | Table 4: Standards | Standard titles preserved |
| `tool_list` | Table 3: Tools (if mapped) | Tool names preserved |

### Step 5: Document expected field loss

**Action**: Identify fields present in the original but absent in the round-tripped manifest.

**Expected acceptable losses**:
- `id` (UUID) -- Not part of the MSF format
- `repo` -- URL not mapped to MSF tables
- `contributors` -- MSF has designed/approved/tested by, which is a different structure
- `keywords` -- No MSF field for keywords
- `software` -- No MSF field for software dependencies
- `metadata` -- Custom metadata not mapped
- `parts` (detailed sub-component data) -- MSF has no nested BOM structure
- `sub_parts` -- Same as parts
- `tsdc` -- OKH-specific classification codes

### Step 6: Validate round-tripped manifest

**Action**: Run the round-tripped manifest through validation (connecting to WF-4).

**Expected result**: The round-tripped manifest should pass hobby-level validation at minimum. If significant fields were preserved, it should pass professional-level validation.

---

## Assertions

### Conversion Assertions

```python
# Step 2: OKH to datasheet succeeds
output_path = str(tmp_path / "test_output.docx")
result_path = converter.okh_to_datasheet(original_manifest, output_path)
assert os.path.exists(result_path)
assert os.path.getsize(result_path) > 0

# Step 3: Datasheet to OKH succeeds
round_tripped = converter.datasheet_to_okh(result_path)
assert isinstance(round_tripped, OKHManifest)
```

### Field Preservation Assertions

```python
# Core identity fields preserved
assert round_tripped.title == original_manifest.title, "Title must survive round-trip"
assert round_tripped.function == original_manifest.function, "Function must survive round-trip"

# License preserved (may be string representation)
if original_manifest.license:
    assert round_tripped.license is not None, "License must survive round-trip"

# Dimensions preserved
if original_manifest.manufacturing_specs and original_manifest.manufacturing_specs.outer_dimensions:
    assert round_tripped.manufacturing_specs is not None
    assert round_tripped.manufacturing_specs.outer_dimensions is not None
    orig_dims = original_manifest.manufacturing_specs.outer_dimensions
    rt_dims = round_tripped.manufacturing_specs.outer_dimensions
    for key in ("length", "width", "height"):
        if orig_dims.get(key):
            assert rt_dims.get(key) == pytest.approx(orig_dims[key], abs=0.1), (
                f"Dimension {key} must be preserved within tolerance"
            )

# Materials preserved (at least names)
if original_manifest.materials:
    assert len(round_tripped.materials) > 0, "At least some materials should survive"
    original_names = {m.name.lower() for m in original_manifest.materials if m.name}
    rt_names = {m.name.lower() for m in round_tripped.materials if m.name}
    assert original_names & rt_names, "At least one material name should match"
```

### No-Crash Assertions

```python
# Round-trip should not introduce invalid data
assert round_tripped.title is not None, "Round-tripped manifest must have a title"
# Should not have empty strings where None is expected
if round_tripped.version:
    assert round_tripped.version.strip(), "Version should not be whitespace-only"
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `design_file` | `3d-printed-prosthetic-hand-1-5-5`, `cnc-machined-aluminum-bracket-2-7-3` | Different field populations |
| `direction` | `okh_to_datasheet`, `datasheet_to_okh`, `round_trip` | Test each direction independently + combined |

```python
@pytest.mark.parametrize("design_file", [
    "3d-printed-prosthetic-hand-1-5-5-okh.json",
    "cnc-machined-aluminum-bracket-2-7-3-okh.json",
])
def test_datasheet_round_trip(design_file, datasheet_converter, tmp_path, ...):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| OKH to datasheet conversion | < 2s | Docx template population |
| Datasheet to OKH parsing | < 2s | Docx table parsing |
| Full round-trip (convert + parse + compare) | < 5s | End-to-end |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| OKH with empty `function` field | Datasheet cell left blank; round-trip returns empty/None |
| OKH with very long `function` text (1000+ chars) | Text truncated to fit MSF cell; round-trip gets truncated version |
| OKH with unicode characters in fields | Unicode preserved through `.docx` round-trip |
| OKH with no `manufacturing_specs` | Related MSF cells left blank; round-trip returns None for `manufacturing_specs` |
| OKH with multiple materials | All materials concatenated in MSF cell; parsing back may lose structure |
| Datasheet template not found on disk | `DatasheetConversionError` raised with descriptive path message |
| Corrupted `.docx` file passed to `datasheet_to_okh` | `DatasheetConversionError` raised, not an unhandled exception |
| OKH with `standards_used` containing certifications | Standard titles preserved; certification details may be lost |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] Create a "maximally populated" OKH manifest where every MSF-mappable field is filled, to measure maximum fidelity.
- [ ] Create a "MSF-minimal" OKH manifest with only the fields that the MSF format supports, to test the clean round-trip path.
- [ ] Document the exact field mapping table between OKH and MSF formats as a reference.
- [ ] Create pre-populated MSF datasheets (not generated by our converter) to test `datasheet_to_okh` with real-world input.

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf05_datasheet_round_trip.py`
- **Fixtures**: `datasheet_converter`, `okh_manifest`, `tmp_path`
- **Markers**: `@pytest.mark.e2e`
- **Parameterize**: `design_file` (2-3 manifests)
- **Shared conftest**: `tests/e2e/conftest.py`
