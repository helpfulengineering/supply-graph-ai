# Core Functionality TODOs Implementation Specification

## Overview

This specification defines the implementation plan for completing critical core functionality TODOs identified in the pre-publication code review. These items represent incomplete features that need to be implemented to ensure the system functions correctly.

## Current State Analysis

### Issue 1: Validation Endpoint Placeholder

**Location**: `src/core/api/routes/match.py:321`

**Current Implementation:**
```python
# TODO: Implement validation using matching service and new validation framework
# For now, return a placeholder response
logger.debug("Using placeholder validation response")
return ValidationResult(
    is_valid=True,
    score=0.8,
    errors=[],
    warnings=[],
    suggestions=[],
    metadata={...}
)
```

**Problems:**
- Returns hardcoded placeholder response
- Doesn't actually validate the supply tree
- Doesn't use matching service or validation framework
- No actual validation logic

**Context:**
- Endpoint: `POST /v1/api/match/validate`
- Request: `ValidateMatchRequest` with `okh_id`, `supply_tree_id`, `validation_criteria`
- Expected: Domain-aware validation using quality levels (hobby, professional, medical)
- Similar validation exists for OKH manifests (`/v1/api/okh/validate`)

### Issue 2: Processing Time Hardcoded

**Location**: `src/core/api/routes/match.py:495`

**Current Implementation:**
```python
"processing_time": 0.0,  # TODO: Calculate actual processing time
```

**Problems:**
- Processing time always returns 0.0
- No actual timing calculation
- Missing performance metric

**Context:**
- Part of match endpoint response
- Should track time from request start to completion
- Other endpoints use `time.time()` for timing (see decorators.py, middleware.py)

### Issue 3: Scoring Logic Placeholder

**Location**: `src/core/services/matching_service.py:554`

**Current Implementation:**
```python
def _calculate_confidence_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]],
    optimization_criteria: Optional[Dict[str, float]] = None
) -> float:
    """Calculate confidence score for a match"""
    try:
        # TODO: Implement actual scoring logic
        # For now, return a simple score based on requirement coverage
        matched_requirements = sum(
            1 for req in requirements
            if any(req["process_name"] == cap["process_name"] for cap in capabilities)
        )
        return matched_requirements / len(requirements) if requirements else 0.0
```

**Problems:**
- Very simplistic scoring (only checks process name matches)
- Doesn't consider optimization criteria
- Doesn't use multi-layer matching results
- No weighted scoring based on match quality
- Doesn't consider material availability, equipment, etc.

**Context:**
- Used in `_generate_supply_tree()` method
- Should integrate with matching layers (direct, heuristic, NLP, LLM)
- Should consider multiple factors: process match, material match, equipment match, scale, etc.

### Issue 4: Missing OKW Reference Field

**Location**: `src/core/models/supply_trees.py:172`

**Current Implementation:**
```python
@dataclass
class SupplyTree:
    facility_name: str
    okh_reference: str
    # TODO: add okw_reference: str
    confidence_score: float
    ...
```

**Problems:**
- Missing `okw_reference` field
- Comment indicates it should replace `facility_id` (which is already removed)
- SupplyTree should reference both OKH and OKW resources
- Needed for proper resource tracking and validation

**Context:**
- SupplyTree represents a match between OKH requirements and OKW capabilities
- Should reference both the OKH manifest and OKW facility
- Used in validation and matching workflows

## Requirements

### Functional Requirements

1. **Validation Endpoint**
   - Validate supply tree against OKH requirements
   - Validate supply tree against OKW capabilities
   - Use domain-aware validation framework
   - Support quality levels (hobby, professional, medical)
   - Support strict mode
   - Return detailed validation results (errors, warnings, suggestions)
   - Calculate validation score (0.0-1.0)

2. **Processing Time Calculation**
   - Track time from request start to completion
   - Include all matching operations
   - Return time in seconds (float)
   - Consistent with other endpoints

3. **Scoring Logic**
   - Multi-factor scoring algorithm
   - Consider process matching quality
   - Consider material availability
   - Consider equipment/tool availability
   - Consider scale/capacity matching
   - Support optimization criteria weights
   - Integrate with matching layer results
   - Return confidence score (0.0-1.0)

4. **OKW Reference Field**
   - Add `okw_reference` field to SupplyTree model
   - Store OKW facility identifier/reference
   - Update serialization/deserialization
   - Maintain backward compatibility

### Non-Functional Requirements

1. **Performance**
   - Validation should complete in reasonable time (<5s for typical supply tree)
   - Scoring calculation should be fast (<100ms)
   - Processing time tracking should have minimal overhead

2. **Accuracy**
   - Validation should catch real issues
   - Scoring should reflect actual match quality
   - Processing time should be accurate

3. **Maintainability**
   - Clear separation of concerns
   - Well-documented algorithms
   - Testable components

## Design Decisions

### Validation Strategy

**Use Existing Validation Framework:**
- Leverage domain validators from `DomainRegistry`
- Use quality level validation (hobby, professional, medical)
- Validate both OKH and OKW components
- Check supply tree structure and completeness

**Validation Steps:**
1. Load OKH manifest and OKW facility from storage
2. Validate OKH manifest (using OKH validator)
3. Validate OKW facility (using OKW validator)
4. Validate supply tree structure
5. Validate OKH-OKW compatibility
6. Check for missing requirements/capabilities
7. Calculate validation score

### Processing Time Strategy

**Track at Endpoint Level:**
- Use `time.time()` at start of endpoint
- Calculate difference at end
- Store in response metadata
- Consistent with `track_performance` decorator pattern

### Scoring Strategy

**Multi-Factor Weighted Scoring:**
- Process matching: 40% weight
- Material matching: 25% weight
- Equipment/tool matching: 20% weight
- Scale/capacity matching: 10% weight
- Other factors: 5% weight

**Layer Integration:**
- Direct matches: 1.0 confidence
- Heuristic matches: 0.8 confidence
- NLP matches: 0.6 confidence
- LLM matches: 0.7 confidence (variable based on LLM response)

**Optimization Criteria:**
- Allow custom weights via `optimization_criteria` parameter
- Default weights if not specified

### OKW Reference Strategy

**Add Field with Backward Compatibility:**
- Add `okw_reference: Optional[str] = None`
- Make optional for backward compatibility
- Populate from facility data when available
- Update serialization to include field

## Implementation Specification

### 1. Validation Endpoint Implementation

**File: `src/core/api/routes/match.py`**

**Update `validate_match` function:**

```python
async def validate_match(
    request: ValidateMatchRequest,
    quality_level: Optional[str] = Query("professional", description="Quality level: hobby, professional, or medical"),
    strict_mode: Optional[bool] = Query(False, description="Enable strict validation mode"),
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    http_request: Request = None
):
    """Enhanced validation endpoint with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        logger.info(
            "Validating supply tree",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "quality_level": quality_level,
                "strict_mode": strict_mode,
                "request_id": request_id
            }
        )
        
        # Load OKH manifest from storage
        okh_handler = await storage_service.get_domain_handler("okh")
        okh_manifest = await okh_handler.load(request.okh_id)
        
        if not okh_manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest {request.okh_id} not found"
            )
        
        # Load supply tree (if stored) or reconstruct from matching service
        # For now, we'll validate based on OKH and matching results
        # TODO: Load actual supply tree from storage if available
        
        # Get domain from OKH manifest or request
        domain = "manufacturing"  # Default, could be detected from manifest
        
        # Get domain validator from registry
        domain_registry = DomainRegistry
        if not domain_registry.is_domain_registered(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain {domain} is not registered"
            )
        
        domain_info = domain_registry.get_domain(domain)
        validator = domain_info.validator
        
        # Validate OKH manifest
        okh_validation = await validator.validate(
            okh_manifest,
            quality_level=quality_level,
            strict_mode=strict_mode
        )
        
        # Validate supply tree structure and compatibility
        supply_tree_errors = []
        supply_tree_warnings = []
        supply_tree_suggestions = []
        
        # Check if supply tree references valid OKW facility
        # (This would require loading the actual supply tree)
        
        # Combine validation results
        all_errors = list(okh_validation.get("errors", [])) + supply_tree_errors
        all_warnings = list(okh_validation.get("warnings", [])) + supply_tree_warnings
        all_suggestions = list(okh_validation.get("suggestions", [])) + supply_tree_suggestions
        
        # Calculate validation score
        # Score based on: OKH validation score, supply tree completeness, compatibility
        okh_score = okh_validation.get("score", 1.0)
        supply_tree_score = 1.0  # Placeholder, would calculate from supply tree validation
        validation_score = (okh_score + supply_tree_score) / 2.0
        
        # Apply strict mode: treat warnings as errors
        if strict_mode:
            all_errors.extend(all_warnings)
            all_warnings = []
            # Reduce score if there were warnings
            if len(all_warnings) > 0:
                validation_score *= 0.9
        
        is_valid = len(all_errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            score=validation_score,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
            metadata={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "validation_criteria": request.validation_criteria,
                "quality_level": quality_level,
                "strict_mode": strict_mode,
                "okh_validation_score": okh_score,
                "supply_tree_validation_score": supply_tree_score
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            "Error validating match",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "error": str(e),
                "request_id": request_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

### 2. Processing Time Calculation

**File: `src/core/api/routes/match.py`**

**Update match endpoint to track processing time:**

```python
@router.post("", ...)
@api_endpoint(...)
async def match_requirements_to_capabilities(
    request: MatchRequest,
    http_request: Request,
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service)
):
    """Enhanced endpoint for matching requirements with capabilities."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = time.time()  # Track start time
    
    try:
        # ... existing matching logic ...
        
        # Find matches
        solutions = await matching_service.find_matches_with_manifest(
            okh_manifest, okw_facilities
        )
        solutions = list(solutions)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Serialize results
        results = []
        for solution in solutions:
            results.append(solution.to_dict())
        
        return create_success_response(
            message="Matching completed successfully",
            data={
                "solutions": results,
                "total_solutions": len(results),
                "processing_time": processing_time,  # Use calculated time
                "matching_metrics": {
                    "direct_matches": len(results),
                    "heuristic_matches": 0,
                    "nlp_matches": 0,
                    "llm_matches": 0
                },
                "validation_results": []
            },
            request_id=request_id
        )
    except Exception as e:
        # ... error handling ...
```

**Also update file upload endpoint:**

```python
async def match_requirements_from_file(...):
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = time.time()  # Track start time
    
    try:
        # ... file processing and matching logic ...
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return create_success_response(
            message="File upload matching completed successfully",
            data={
                "solutions": results,
                "total_solutions": len(results),
                "processing_time": processing_time,  # Use calculated time
                ...
            },
            request_id=request_id
        )
```

**Add import:**
```python
import time
```

### 3. Scoring Logic Implementation

**File: `src/core/services/matching_service.py`**

**Update `_calculate_confidence_score` method:**

```python
def _calculate_confidence_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]],
    optimization_criteria: Optional[Dict[str, float]] = None,
    match_results: Optional[List[Any]] = None  # Matching layer results
) -> float:
    """
    Calculate confidence score for a match using multi-factor weighted scoring.
    
    Args:
        requirements: List of requirement dictionaries
        capabilities: List of capability dictionaries
        optimization_criteria: Optional weights for different factors
        match_results: Optional matching layer results for layer-specific scoring
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    try:
        if not requirements:
            return 0.0
        
        # Default weights
        default_weights = {
            "process": 0.40,
            "material": 0.25,
            "equipment": 0.20,
            "scale": 0.10,
            "other": 0.05
        }
        
        # Use optimization criteria if provided, otherwise use defaults
        weights = optimization_criteria if optimization_criteria else default_weights
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            weights = default_weights
        
        # Calculate process matching score
        process_score = self._calculate_process_score(requirements, capabilities)
        
        # Calculate material matching score
        material_score = self._calculate_material_score(requirements, capabilities)
        
        # Calculate equipment matching score
        equipment_score = self._calculate_equipment_score(requirements, capabilities)
        
        # Calculate scale/capacity matching score
        scale_score = self._calculate_scale_score(requirements, capabilities)
        
        # Calculate other factors score
        other_score = self._calculate_other_score(requirements, capabilities, match_results)
        
        # Weighted combination
        confidence_score = (
            process_score * weights.get("process", 0.40) +
            material_score * weights.get("material", 0.25) +
            equipment_score * weights.get("equipment", 0.20) +
            scale_score * weights.get("scale", 0.10) +
            other_score * weights.get("other", 0.05)
        )
        
        # Ensure score is between 0.0 and 1.0
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        return round(confidence_score, 2)
        
    except Exception as e:
        logger.error(
            "Error calculating confidence score",
            extra={
                "requirement_count": len(requirements),
                "capability_count": len(capabilities),
                "optimization_criteria": optimization_criteria,
                "error": str(e)
            },
            exc_info=True
        )
        # Return a conservative score on error
        return 0.5

def _calculate_process_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]]
) -> float:
    """Calculate process matching score."""
    if not requirements:
        return 0.0
    
    matched_processes = 0
    total_processes = 0
    
    for req in requirements:
        req_process = req.get("process_name", "").lower()
        if not req_process:
            continue
        
        total_processes += 1
        
        # Check for exact or near-match in capabilities
        for cap in capabilities:
            cap_process = cap.get("process_name", "").lower()
            if not cap_process:
                continue
            
            # Exact match
            if req_process == cap_process:
                matched_processes += 1
                break
            
            # Near-match (Levenshtein distance <= 2)
            if self._levenshtein_distance(req_process, cap_process) <= 2:
                matched_processes += 0.8  # Partial credit for near-match
                break
    
    return matched_processes / total_processes if total_processes > 0 else 0.0

def _calculate_material_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]]
) -> float:
    """Calculate material matching score."""
    req_materials = set()
    for req in requirements:
        materials = req.get("materials", [])
        if isinstance(materials, list):
            req_materials.update(m.lower() for m in materials if m)
        elif isinstance(materials, str):
            req_materials.add(materials.lower())
    
    if not req_materials:
        return 1.0  # No material requirements = perfect score
    
    cap_materials = set()
    for cap in capabilities:
        materials = cap.get("materials", [])
        if isinstance(materials, list):
            cap_materials.update(m.lower() for m in materials if m)
        elif isinstance(materials, str):
            cap_materials.add(materials.lower())
    
    # Calculate overlap
    matched_materials = req_materials.intersection(cap_materials)
    return len(matched_materials) / len(req_materials) if req_materials else 0.0

def _calculate_equipment_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]]
) -> float:
    """Calculate equipment/tool matching score."""
    req_equipment = set()
    for req in requirements:
        equipment = req.get("equipment", []) or req.get("tools", [])
        if isinstance(equipment, list):
            req_equipment.update(e.lower() for e in equipment if e)
        elif isinstance(equipment, str):
            req_equipment.add(equipment.lower())
    
    if not req_equipment:
        return 1.0  # No equipment requirements = perfect score
    
    cap_equipment = set()
    for cap in capabilities:
        equipment = cap.get("equipment", []) or cap.get("tools", [])
        if isinstance(equipment, list):
            cap_equipment.update(e.lower() for e in equipment if e)
        elif isinstance(equipment, str):
            cap_equipment.add(equipment.lower())
    
    matched_equipment = req_equipment.intersection(cap_equipment)
    return len(matched_equipment) / len(req_equipment) if req_equipment else 0.0

def _calculate_scale_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]]
) -> float:
    """Calculate scale/capacity matching score."""
    # Extract scale requirements
    req_scale = None
    for req in requirements:
        scale = req.get("scale") or req.get("quantity") or req.get("volume")
        if scale:
            req_scale = scale
            break
    
    if not req_scale:
        return 1.0  # No scale requirements = perfect score
    
    # Extract capability scale
    cap_scale = None
    for cap in capabilities:
        scale = cap.get("scale") or cap.get("capacity") or cap.get("max_volume")
        if scale:
            cap_scale = scale
            break
    
    if not cap_scale:
        return 0.5  # Unknown capability scale = moderate score
    
    # Compare scales (assuming numeric values)
    try:
        req_val = float(req_scale)
        cap_val = float(cap_scale)
        
        if cap_val >= req_val:
            return 1.0  # Capability can handle requirement
        else:
            # Partial credit based on ratio
            return min(1.0, cap_val / req_val)
    except (ValueError, TypeError):
        # Non-numeric scales, use string comparison
        return 0.5

def _calculate_other_score(
    self,
    requirements: List[Dict[str, Any]],
    capabilities: List[Dict[str, Any]],
    match_results: Optional[List[Any]] = None
) -> float:
    """Calculate score for other factors (match layer quality, etc.)."""
    if match_results:
        # Use match layer results to inform score
        # Higher confidence from direct matches, lower from NLP/LLM
        layer_scores = []
        for result in match_results:
            layer = getattr(result, 'layer', None)
            confidence = getattr(result, 'confidence', 0.5)
            
            # Weight by layer type
            if layer == "direct":
                layer_scores.append(confidence * 1.0)
            elif layer == "heuristic":
                layer_scores.append(confidence * 0.8)
            elif layer == "nlp":
                layer_scores.append(confidence * 0.6)
            elif layer == "llm":
                layer_scores.append(confidence * 0.7)
            else:
                layer_scores.append(confidence * 0.5)
        
        if layer_scores:
            return sum(layer_scores) / len(layer_scores)
    
    return 0.5  # Default moderate score

def _levenshtein_distance(self, s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return self._levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]
```

**Update method signature in `_generate_supply_tree`:**

```python
def _generate_supply_tree(
    self,
    manifest: OKHManifest,
    facility: ManufacturingFacility,
    domain: str = "manufacturing",
    match_results: Optional[List[Any]] = None  # Add this parameter
) -> SupplyTree:
    # ... existing code ...
    
    # Extract requirements and capabilities
    requirements = self._extract_requirements(manifest)
    capabilities = self._extract_capabilities(facility)
    
    # Calculate confidence score with match results
    confidence_score = self._calculate_confidence_score(
        requirements=requirements,
        capabilities=capabilities,
        optimization_criteria=None,  # Could be passed from request
        match_results=match_results
    )
    
    # ... rest of method ...
```

### 4. Add OKW Reference Field

**File: `src/core/models/supply_trees.py`**

**Update SupplyTree dataclass:**

```python
@dataclass
class SupplyTree:
    """
    Simplified SupplyTree
    
    This class contains only the essential data needed for matching facilities
    to requirements.
    """
    facility_name: str
    okh_reference: str
    okw_reference: Optional[str] = None  # Add OKW reference field
    confidence_score: float
    id: UUID = field(default_factory=uuid4)
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    match_type: str = "unknown"  # "direct", "heuristic", "nlp", "llm"
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Truncate confidence_score to 2 decimal places
        self.confidence_score = round(self.confidence_score, 2)
    
    def __hash__(self):
        """Enable Set operations by hashing on facility_name and okh_reference"""
        return hash((self.facility_name, self.okh_reference, self.okw_reference))
    
    def __eq__(self, other):
        """Enable Set operations by comparing facility_name and okh_reference"""
        if not isinstance(other, SupplyTree):
            return False
        return (
            self.facility_name == other.facility_name and
            self.okh_reference == other.okh_reference and
            self.okw_reference == other.okw_reference
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            "id": str(self.id),
            "facility_name": self.facility_name,
            "okh_reference": self.okh_reference,
            "okw_reference": self.okw_reference,  # Include in serialization
            "confidence_score": self.confidence_score,
            "estimated_cost": self.estimated_cost,
            "estimated_time": self.estimated_time,
            "materials_required": self.materials_required,
            "capabilities_used": self.capabilities_used,
            "match_type": self.match_type,
            "metadata": self.metadata,
            "creation_time": self.creation_time.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SupplyTree':
        """Create SupplyTree from dictionary"""
        return cls(
            id=UUID(data.get("id", str(uuid4()))),
            facility_name=data["facility_name"],
            okh_reference=data["okh_reference"],
            okw_reference=data.get("okw_reference"),  # Optional, for backward compatibility
            confidence_score=data["confidence_score"],
            estimated_cost=data.get("estimated_cost"),
            estimated_time=data.get("estimated_time"),
            materials_required=data.get("materials_required", []),
            capabilities_used=data.get("capabilities_used", []),
            match_type=data.get("match_type", "unknown"),
            metadata=data.get("metadata", {}),
            creation_time=datetime.fromisoformat(data.get("creation_time", datetime.now().isoformat()))
        )
```

**Update `_generate_supply_tree` to populate okw_reference:**

```python
def _generate_supply_tree(
    self,
    manifest: OKHManifest,
    facility: ManufacturingFacility,
    domain: str = "manufacturing",
    match_results: Optional[List[Any]] = None
) -> SupplyTree:
    # ... existing code ...
    
    # Get OKW reference (facility ID or name)
    okw_reference = str(facility.id) if hasattr(facility, 'id') else facility.name
    
    return SupplyTree(
        facility_name=facility.name,
        okh_reference=str(manifest.id) if hasattr(manifest, 'id') else manifest.title,
        okw_reference=okw_reference,  # Set OKW reference
        confidence_score=confidence_score,
        # ... other fields ...
    )
```

## Integration Points

### 1. Validation Framework

- Use `DomainRegistry` to get domain validators
- Use existing validation methods from domain validators
- Follow same pattern as OKH validation endpoint

### 2. Matching Service

- Integrate scoring with matching layer results
- Use existing matching infrastructure
- Maintain compatibility with existing matching methods

### 3. Storage Service

- Load OKH and OKW data from storage for validation
- Store OKW references in SupplyTree

### 4. Timing Infrastructure

- Use `time.time()` consistent with other endpoints
- Follow `track_performance` decorator pattern

## Testing Considerations

### Unit Tests

1. **Validation Tests:**
   - Test validation with different quality levels
   - Test strict mode behavior
   - Test error/warning/suggestion generation
   - Test score calculation

2. **Scoring Tests:**
   - Test each scoring factor independently
   - Test weighted combination
   - Test edge cases (empty requirements, no matches, etc.)
   - Test optimization criteria weights

3. **Processing Time Tests:**
   - Verify time is calculated correctly
   - Test with different operation durations

4. **OKW Reference Tests:**
   - Test field addition doesn't break existing code
   - Test serialization/deserialization
   - Test backward compatibility

### Integration Tests

1. **End-to-End Validation:**
   - Test validation endpoint with real data
   - Verify validation results are accurate

2. **End-to-End Matching:**
   - Test matching with scoring
   - Verify scores reflect match quality

## Migration Plan

### Phase 1: Implementation (Current)
- Implement validation endpoint
- Implement processing time calculation
- Implement scoring logic
- Add OKW reference field

### Phase 2: Enhancement (Future)
- Improve validation accuracy
- Add more scoring factors
- Add caching for validation results
- Add validation result storage

## Success Criteria

1. ✅ Validation endpoint returns real validation results
2. ✅ Processing time is accurately calculated
3. ✅ Scoring logic considers multiple factors
4. ✅ OKW reference field is added and populated
5. ✅ All TODOs are resolved
6. ✅ Backward compatibility maintained
7. ✅ Tests pass
8. ✅ Performance is acceptable

## Open Questions / Future Enhancements

1. **Validation:**
   - Should validation results be cached?
   - Should validation results be stored?
   - Should validation support incremental validation?

2. **Scoring:**
   - Should scoring be configurable per domain?
   - Should scoring consider historical match success?
   - Should scoring be machine-learned?

3. **OKW Reference:**
   - Should OKW reference be a URI instead of string?
   - Should we support multiple OKW references per SupplyTree?

## Dependencies

### Existing Dependencies

- `time` - Timing (stdlib)
- `DomainRegistry` - Domain validation
- `StorageService` - Data loading
- `MatchingService` - Matching logic

### No New Dependencies

- Uses only existing codebase components

## Implementation Order

1. Add OKW reference field to SupplyTree model
2. Implement processing time calculation
3. Implement scoring logic
4. Implement validation endpoint
5. Update method signatures and calls
6. Write tests
7. Update documentation

