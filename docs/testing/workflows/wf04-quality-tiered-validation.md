# WF-4: Quality-Tiered Validation

**Category**: Foundation
**Priority**: 1 (validation is a prerequisite for matching)
**Estimated Duration**: < 5s per parameterized case

---

## Overview

Validates the `ValidationContext` quality-level system. The same OKH manifest should produce different validation results depending on the quality level (`hobby`, `professional`, `medical`), which maps to validation strictness (`relaxed`, `standard`, `strict`).

This workflow tests that:
- Quality levels are correctly mapped to strictness levels.
- Sparse manifests pass relaxed validation but fail strict validation.
- Comprehensive manifests pass at all quality levels.
- The `ValidationEngine` and `ManufacturingOKHValidator` correctly apply domain-specific rules at each strictness level.

Quality context is distinct from validation context: quality context sets a minimum acceptable level of completeness and precision for a given OKH file, while validation context is formal and domain-specific (e.g., ISO 13485 compliance for medical devices).

---

## Prerequisites

### Fixtures

- `validation_engine` -- Initialized `ValidationEngine` with manufacturing domain validators registered.
- `manufacturing_okh_validator` -- Initialized `ManufacturingOKHValidator`.
- `validation_context(request)` -- Parameterized fixture creating `ValidationContext` at each quality level.
- `okh_at_completeness(request)` -- Parameterized fixture loading OKH manifests at different completeness levels.

### Test Data

| File | Completeness Level | Description |
|------|-------------------|-------------|
| *To be created (Issue 1.1.2)* | Minimal | Only required fields (`title`, `version`, `license`); no processes, no parts, no specs |
| `synthetic_data/cnc-machined-aluminum-bracket-2-7-3-okh.json` | Standard | Most fields populated, reasonable detail |
| `synthetic_data/3d-printed-prosthetic-hand-1-5-5-okh.json` | Comprehensive | Full field population including parts, specs, standards, materials |

### Services

- `ValidationEngine` (central validation coordinator)
- `ManufacturingOKHValidator` (domain-specific OKH validation rules)
- `ValidationContext` (quality level configuration)
- `DomainRegistry` (domain registration for context validation)

---

## Steps

### Step 1: Create validation contexts at each quality level

**Action**: Create three `ValidationContext` instances for the manufacturing domain:

```python
hobby_ctx = ValidationContext(name="hobby_test", domain="manufacturing", quality_level="hobby")
professional_ctx = ValidationContext(name="professional_test", domain="manufacturing", quality_level="professional")
medical_ctx = ValidationContext(name="medical_test", domain="manufacturing", quality_level="medical")
```

**Expected result**:
- All three contexts instantiate without error.
- `hobby_ctx.get_validation_strictness()` returns `"relaxed"`.
- `professional_ctx.get_validation_strictness()` returns `"standard"`.
- `medical_ctx.get_validation_strictness()` returns `"strict"`.
- All three pass `is_quality_level_valid()`.

### Step 2: Validate a minimal OKH at each quality level

**Action**: Load a minimal OKH manifest (only required fields) and validate at each quality level using `manufacturing_okh_validator.validate(manifest, context)`.

**Expected result**:
- **Hobby (relaxed)**: `ValidationResult.valid` is `True`, few or no errors. Relaxed validation accepts sparse data.
- **Professional (standard)**: `ValidationResult.valid` is `False` or has warnings. Standard validation expects manufacturing processes, materials, or specifications.
- **Medical (strict)**: `ValidationResult.valid` is `False` with multiple errors. Strict validation requires comprehensive field population, quality standards, and documentation.

### Step 3: Validate a standard OKH at each quality level

**Action**: Load a standard-completeness OKH manifest (e.g., CNC bracket) and validate at each quality level.

**Expected result**:
- **Hobby (relaxed)**: `ValidationResult.valid` is `True`.
- **Professional (standard)**: `ValidationResult.valid` is `True`, may have minor warnings.
- **Medical (strict)**: `ValidationResult.valid` may be `False` -- standard completeness may lack medical-grade requirements like traceability documentation, formal quality standards, or regulatory compliance fields.

### Step 4: Validate a comprehensive OKH at each quality level

**Action**: Load a comprehensive OKH manifest (e.g., prosthetic hand with standards, specs, materials) and validate at each quality level.

**Expected result**:
- **Hobby (relaxed)**: `ValidationResult.valid` is `True`.
- **Professional (standard)**: `ValidationResult.valid` is `True`.
- **Medical (strict)**: `ValidationResult.valid` is `True` (or `True` with warnings if the synthetic data doesn't include every medical-grade field).

### Step 5: Verify strictness monotonicity

**Action**: Compare error counts across quality levels for the same manifest.

**Expected result**: For any given manifest, the error count should be monotonically non-decreasing as strictness increases:
- `errors(hobby) <= errors(professional) <= errors(medical)`

### Step 6: Verify error specificity

**Action**: Inspect validation error messages and field references.

**Expected result**: Each `ValidationError` in the result should:
- Have a non-empty `message` string
- Reference a specific `field` name where applicable (e.g., `"manufacturing_processes"`, `"quality_standards"`)
- Provide actionable guidance (not just "field missing" but context about why it matters at this quality level)

---

## Assertions

### Context Assertions

```python
# Quality levels map correctly to strictness
assert hobby_ctx.get_validation_strictness() == "relaxed"
assert professional_ctx.get_validation_strictness() == "standard"
assert medical_ctx.get_validation_strictness() == "strict"

# All quality levels are valid for manufacturing domain
assert hobby_ctx.is_quality_level_valid() is True
assert professional_ctx.is_quality_level_valid() is True
assert medical_ctx.is_quality_level_valid() is True

# Invalid quality levels are rejected
invalid_ctx = ValidationContext(name="test", domain="manufacturing", quality_level="invalid")
assert invalid_ctx.is_quality_level_valid() is False
```

### Monotonicity Assertions

```python
# For any manifest, errors should not decrease as strictness increases
for manifest in [minimal_okh, standard_okh, comprehensive_okh]:
    hobby_result = await validator.validate(manifest, hobby_ctx)
    professional_result = await validator.validate(manifest, professional_ctx)
    medical_result = await validator.validate(manifest, medical_ctx)

    assert hobby_result.error_count <= professional_result.error_count, (
        f"Hobby errors ({hobby_result.error_count}) should be <= "
        f"professional errors ({professional_result.error_count})"
    )
    assert professional_result.error_count <= medical_result.error_count, (
        f"Professional errors ({professional_result.error_count}) should be <= "
        f"medical errors ({medical_result.error_count})"
    )
```

### Tier-Specific Assertions

```python
# Minimal manifest: hobby passes, medical fails
hobby_result = await validator.validate(minimal_okh, hobby_ctx)
medical_result = await validator.validate(minimal_okh, medical_ctx)
assert hobby_result.valid is True, "Minimal manifest should pass hobby validation"
assert medical_result.valid is False, "Minimal manifest should fail medical validation"

# Comprehensive manifest: all tiers pass
for ctx in [hobby_ctx, professional_ctx, medical_ctx]:
    result = await validator.validate(comprehensive_okh, ctx)
    assert result.valid is True, f"Comprehensive manifest should pass {ctx.quality_level} validation"
```

### Error Quality Assertions

```python
# Errors should reference specific fields
for error in medical_result.errors:
    assert error.message, "Error must have a message"
    # At least some errors should reference specific fields
if medical_result.errors:
    fields_referenced = [e.field for e in medical_result.errors if e.field]
    assert len(fields_referenced) > 0, "At least some errors should reference specific fields"
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `quality_level` | `hobby`, `professional`, `medical` | All three manufacturing quality levels |
| `manifest_completeness` | `minimal`, `standard`, `comprehensive` | Different levels of field population |
| `strict_mode` | `True`, `False` | Test strict_mode override (forces strict regardless of quality_level) |

```python
@pytest.mark.parametrize("quality_level", ["hobby", "professional", "medical"])
@pytest.mark.parametrize("manifest_fixture", ["minimal_okh", "standard_okh", "comprehensive_okh"])
def test_quality_tiered_validation(quality_level, manifest_fixture, request, ...):
    manifest = request.getfixturevalue(manifest_fixture)
    ctx = ValidationContext(
        name=f"test_{quality_level}",
        domain="manufacturing",
        quality_level=quality_level,
    )
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| ValidationContext creation | < 10ms | Dataclass instantiation + domain lookup |
| Validation (single manifest, single context) | < 200ms | In-memory rule checking |
| Full matrix (3 manifests x 3 levels) | < 2s | All 9 combinations |

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| `strict_mode=True` with `quality_level="hobby"` | Overrides to strict validation; behaves like medical |
| Invalid domain name in context | Raises `ValueError` during `ValidationContext.__post_init__()` |
| OKH with only `title` and `version` (no license) | Fails at all levels -- `license` is required by OKH spec itself |
| OKH with `quality_standards: ["ISO 13485"]` | Informational for hobby/professional; potentially used for medical validation |
| Empty OKH dict passed to validator | Returns `valid=False` with parse error, not an unhandled exception |
| Cooking domain quality levels (`home`, `commercial`, `professional`) | Different valid levels; manufacturing levels should be rejected for cooking domain |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] **Critical**: Create a "minimal" OKH manifest with only the bare required fields (`title`, `version`, `license`, `function`) and nothing else. This is needed to test the lower boundary of hobby validation.
- [ ] **Critical**: Create a "comprehensive" OKH manifest with all fields maximally populated: parts with TSDC codes, materials with quantities, `manufacturing_specs` with `process_requirements` and `quality_standards`, `standards_used` with certification status, `making_instructions`, etc.
- [ ] Create an OKH manifest that passes professional but fails medical (has processes and materials but lacks formal quality standards and traceability documentation).
- [ ] Document the specific fields that each quality level requires, as a reference table for the test dataset.

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf04_quality_tiered_validation.py`
- **Fixtures**: `validation_engine`, `manufacturing_okh_validator`, `validation_context`, `minimal_okh`, `standard_okh`, `comprehensive_okh`
- **Markers**: `@pytest.mark.e2e`
- **Parameterize**: `quality_level` (3 levels) x `manifest_completeness` (3 levels) = 9 test cases
- **Shared conftest**: `tests/e2e/conftest.py`
