# Unified Matching Endpoint Design

**Version**: 1.1  
**Status**: Design Proposal (Updated: Depth-Based Approach)  
**Date**: 2024  
**Related**: 
- [Nested Supply Tree Generation](./nested-supply-tree-generation.md)
- [Depth-Based Matching Analysis](./depth-based-matching-analysis.md)

---

## Overview

This document proposes a unified design for the matching endpoint that supports both single-level and nested matching through a single API endpoint, eliminating the need for separate `/match` and `/match/nested` endpoints.

## Design Goals

1. **Unified Interface**: Single endpoint handles both simple and complex matching scenarios
2. **Backward Compatibility**: Existing single-level matching requests continue to work
3. **Automatic Detection**: System automatically detects when nested matching is needed
4. **Consistent Response Format**: Unified response structure for both matching types
5. **CLI Parity**: CLI commands mirror API functionality

## Current State

### API Endpoints
- `POST /api/match` - Single-level matching (returns list of `SupplyTreeSolution`, one per facility)
- `POST /api/match/nested` - Nested matching (planned, returns single `SupplyTreeSolution` with multiple trees)

### Service Methods
- `find_matches_with_manifest()` - Returns `Set[SupplyTreeSolution]` (one per facility)
- `match_with_nested_components()` - Returns single `SupplyTreeSolution` (with multiple trees)

### Models
- `SupplyTreeSolution` - Unified model supporting both single-tree and nested solutions
  - Single-tree: `all_trees` contains one tree
  - Nested: `all_trees` contains multiple trees with relationships

## Proposed Solution

### 1. Enhanced Request Model

Add unified depth-based parameter to `MatchRequest`:

```python
class MatchRequest(BaseAPIRequest, LLMRequestMixin):
    # ... existing fields ...
    
    # Unified depth-based matching control
    max_depth: Optional[int] = Field(
        0,  # Default: single-level matching (backward compatible)
        ge=0,
        le=10,
        description=(
            "Maximum depth for BOM explosion. "
            "0 = single-level matching (no nesting), "
            "> 0 = nested matching with specified depth. "
            "Default: 0 (single-level matching for backward compatibility)"
        )
    )
    
    # Optional: Auto-detect if nested matching is needed
    auto_detect_depth: Optional[bool] = Field(
        False,
        description=(
            "Auto-detect if nested matching is needed based on OKH structure. "
            "If True and max_depth=0, will use default depth (5) when nested components detected."
        )
    )
    
    include_validation: Optional[bool] = Field(
        True,
        description="Include validation results in response (for nested matching)"
    )
```

### 2. Unified Endpoint Logic

The `POST /api/match` endpoint will:

1. **Determine matching mode from depth**:
   - If `max_depth=0` (default or explicitly set): Use single-level matching
   - If `max_depth > 0`: Use nested matching with specified depth
   - This provides a unified, intuitive control mechanism

2. **Auto-detection** (optional enhancement):
   - If `auto_detect_depth=True` and `max_depth=0`, check if OKH manifest has nested components
   - If nested components detected, automatically use default depth (5)
   - This provides a "smart" default while allowing explicit control

3. **Route to appropriate service method**:
   - Single-level (`max_depth=0`): `find_matches_with_manifest()`
   - Nested (`max_depth > 0`): `match_with_nested_components(max_depth=...)`

### 3. Response Format

#### Single-Level Matching (Backward Compatible)
```json
{
  "success": true,
  "data": {
    "solutions": [
      {
        "tree": { /* SupplyTree */ },
        "facility_id": "uuid",
        "facility_name": "Facility A",
        "match_type": "direct",
        "confidence": 0.9,
        "score": 0.85
      }
    ],
    "total_solutions": 1,
    "matching_mode": "single-level",
    "processing_time": 1.2
  }
}
```

#### Nested Matching
```json
{
  "success": true,
  "data": {
    "solution": {
      "all_trees": [ /* Array of SupplyTree objects */ ],
      "root_trees": [ /* Root-level trees */ ],
      "component_mapping": { /* Component ID -> Trees mapping */ },
      "dependency_graph": { /* Dependency relationships */ },
      "production_sequence": [ /* Production stages */ ],
      "total_estimated_cost": 15000.00,
      "total_estimated_time": "2-3 weeks",
      "validation_result": { /* Validation details */ },
      "is_nested": true
    },
    "matching_mode": "nested",
    "processing_time": 3.5
  }
}
```

**Key Differences**:
- Single-level: `solutions` array (multiple solutions, one per facility)
- Nested: `solution` object (single solution with multiple trees)
- Both include `matching_mode` field for client clarity

### 4. Implementation Details

#### Endpoint Handler Flow

```python
async def match_requirements_to_capabilities(
    request: MatchRequest,
    ...
):
    # 1. Extract requirements (existing logic)
    okh_manifest = await _extract_okh_manifest(...)
    facilities = await _get_filtered_facilities(...)
    
    # 2. Determine depth (default to 0 for single-level matching)
    max_depth = request.max_depth if request.max_depth is not None else 0
    
    # 3. Optional auto-detection
    if request.auto_detect_depth and max_depth == 0:
        if _has_nested_components(okh_manifest):
            max_depth = 5  # Default depth for auto-detection
            logger.info(
                "Auto-detected nested components, using max_depth=5",
                extra={"request_id": request_id}
            )
    
    # 4. Route to appropriate matching method based on depth
    if max_depth > 0:
        # Nested matching
        solution = await matching_service.match_with_nested_components(
            okh_manifest=okh_manifest,
            facilities=facilities,
            max_depth=max_depth,
            domain=domain
        )
        return _format_nested_response(solution, request)
    else:
        # Single-level matching
        solutions = await matching_service.find_matches_with_manifest(
            okh_manifest=okh_manifest,
            facilities=facilities,
            explicit_domain=domain
        )
        return _format_single_level_response(solutions, request)
```

#### Helper Functions

```python
def _has_nested_components(okh_manifest: OKHManifest) -> bool:
    """Check if OKH manifest has nested components"""
    # Check for nested components in sub_parts
    if okh_manifest.sub_parts and len(okh_manifest.sub_parts) > 0:
        # Check if any sub_parts have nested sub_parts
        for sub_part in okh_manifest.sub_parts:
            if isinstance(sub_part, dict) and sub_part.get("sub_parts"):
                return True
        return True
    
    # Check for external BOM with nested structure
    if okh_manifest.bom:
        # Could check BOM file for nested components
        # For now, return False (conservative - requires BOM loading)
        pass
    
    return False

def _format_nested_response(
    solution: SupplyTreeSolution,
    request: MatchRequest
) -> dict:
    """Format nested matching response"""
    response_data = {
        "solution": solution.to_dict(),
        "matching_mode": "nested",
        "processing_time": processing_time,
    }
    
    if request.include_validation and solution.validation_result:
        response_data["validation_result"] = solution.validation_result.to_dict()
    
    return create_success_response(
        message="Nested matching completed successfully",
        data=response_data,
        request_id=request_id
    )

def _format_single_level_response(
    solutions: Set[SupplyTreeSolution],
    request: MatchRequest
) -> dict:
    """Format single-level matching response (existing logic)"""
    # Existing implementation
    ...
```

## CLI Integration

### Enhanced CLI Command

```bash
# Single-level matching (default, max_depth=0)
ome match requirements design.okh.json

# Explicit single-level matching
ome match requirements design.okh.json --max-depth 0

# Nested matching with default depth (5)
ome match requirements design.okh.json --max-depth 5

# Nested matching with custom depth
ome match requirements design.okh.json --max-depth 3

# Auto-detect nested matching (uses depth=5 if nested components found)
ome match requirements design.okh.json --auto-detect-depth
```

### CLI Options

```python
@click.option(
    "--max-depth",
    type=int,
    default=0,
    help=(
        "Maximum depth for BOM explosion. "
        "0 = single-level matching (default), "
        "> 0 = nested matching with specified depth"
    )
)
@click.option(
    "--auto-detect-depth",
    "auto_detect_depth",
    is_flag=True,
    default=False,
    help=(
        "Auto-detect if nested matching is needed based on OKH structure. "
        "If nested components detected and max_depth=0, uses default depth (5)"
    )
)
```

## Migration Strategy

### Phase 1: Add Depth Parameter (Non-Breaking)
- Add `max_depth` parameter to `MatchRequest` with default value `0`
- Default `max_depth=0` maintains backward compatibility (single-level matching)
- Implement nested matching path alongside existing path
- Route based on `max_depth > 0` check

### Phase 2: Auto-Detection (Enhancement)
- Add `auto_detect_depth` parameter (opt-in, default `False`)
- Add auto-detection logic that checks for nested components
- When auto-detection triggers, use default depth (5)
- Monitor usage and feedback

### Phase 3: Default Auto-Detection (Future - Optional)
- Consider making auto-detection default behavior
- Allow explicit override with `--max-depth 0` flag
- This would require careful consideration of performance impact

## Benefits

1. **Simplified API**: Single endpoint instead of two
2. **Unified Parameter Model**: Single `max_depth` parameter controls both mode and depth
3. **Intuitive Semantics**: `depth=0` naturally means "no nesting" (follows common patterns)
4. **Implementation Alignment**: Directly matches existing service method signatures
5. **Backward Compatible**: Default `max_depth=0` maintains existing behavior
6. **Flexible**: Supports both explicit control and auto-detection
7. **Consistent**: Unified response structure
8. **Discoverable**: Clients can easily try nested matching by setting `max_depth > 0`

## Considerations

### Response Format Differences
- **Challenge**: Single-level returns array, nested returns object
- **Solution**: Use `matching_mode` field to indicate format
- **Alternative**: Always return array, but nested has one element with multiple trees

### Performance
- **Concern**: Auto-detection adds overhead
- **Mitigation**: Cache detection results, make it optional initially

### Error Handling
- **Challenge**: Different error scenarios for nested vs single-level
- **Solution**: Unified error response format with context

## Open Questions

1. **Response Format**: Should we always return an array for consistency?
   - Pro: Consistent structure
   - Con: Nested solution is conceptually a single solution
   - **Current Decision**: Keep different formats with `matching_mode` indicator

2. **Auto-Detection**: Should it be default or opt-in?
   - **Current Decision**: Opt-in (`auto_detect_depth=False` by default)
   - **Rationale**: Avoids performance overhead for simple cases
   - **Future Consideration**: Could make default after validating performance impact

3. **Backward Compatibility**: How long to maintain single-level response format?
   - **Decision**: Maintain indefinitely
   - **Rationale**: Not a breaking change, both formats serve different use cases

4. **Depth Validation**: What should happen if `max_depth=0` but OKH has nested components?
   - **Decision**: Match only top-level (ignore nested components)
   - **Rationale**: User explicitly requested single-level matching (`max_depth=0`)
   - **Alternative**: Could warn user, but still match only top-level

## Next Steps

1. ✅ Review and approve design (depth-based approach)
2. Update `MatchRequest` model with `max_depth` parameter
3. Implement unified endpoint logic (route based on `max_depth > 0`)
4. Add CLI options (`--max-depth`, `--auto-detect-depth`)
5. Update documentation
6. Add tests for both modes (single-level and nested)
7. Update API documentation

## Design Rationale

This design uses a **depth-based approach** rather than a boolean flag because:

1. **Unified Parameter**: One parameter (`max_depth`) controls both matching mode and depth, reducing API complexity
2. **Natural Semantics**: `depth=0` naturally means "no nesting" - intuitive and follows common programming patterns
3. **Implementation Alignment**: Directly matches existing service method signatures (`match_with_nested_components(max_depth=5)`)
4. **Simpler Logic**: Clean conditional (`if max_depth > 0`) instead of checking boolean + int combination
5. **Better Defaults**: `max_depth=0` is clearer than `enable_nested_matching=False`

See [Depth-Based Matching Analysis](./depth-based-matching-analysis.md) for detailed comparison and rationale.

