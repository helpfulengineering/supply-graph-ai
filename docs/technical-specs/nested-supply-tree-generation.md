# Technical Specification: Nested Supply Tree Generation

**Version**: 1.0  
**Status**: Draft  
**Date**: 2024  
**Authors**: OHM Development Team  
**Related**: [Demo Readiness Plan](../../notes/demo-readiness-plan.md), [Supply Tree Models](../models/supply-tree.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Architecture](#architecture)
4. [Data Models](#data-models)
5. [API Specifications](#api-specifications)
6. [Algorithms](#algorithms)
7. [Error Handling](#error-handling)
8. [Testing Strategy](#testing-strategy)
9. [Implementation Plan](#implementation-plan)
10. [Dependencies](#dependencies)
11. [Risks and Mitigations](#risks-and-mitigations)

---

## 1. Overview

### 1.1 Purpose

This specification defines the design and implementation of nested supply tree generation, enabling OHM to handle complex OKH designs with nested sub-components that require multi-facility production coordination.

### 1.2 Scope

**In Scope**:
- BOM (Bill of Materials) resolution and parsing
- Recursive component matching across multiple facilities
- Hierarchical supply tree generation with parent-child relationships
- Multi-facility production coordination
- Dependency tracking and production sequence calculation

**Out of Scope** (Future Enhancements):
- Real-time facility availability updates
- Cost optimization algorithms
- Shipping cost calculation
- Just-in-time scheduling
- Batch production optimization

### 1.3 Background

Currently, OHM matches single OKH manifests to single facilities, generating one SupplyTree per facility. This works for simple designs but cannot handle complex products with nested components that require production across multiple facilities.

**Example**: A medical ventilator requires:
- Housing (needs milling facility)
- Electronics (needs PCB fabrication facility)
- Final assembly (needs assembly facility)

This specification enables OHM to match each component to appropriate facilities and coordinate the complete production solution.

### 1.4 Key Concepts

- **BOM Explosion**: Recursive breakdown of a product into all its components and sub-components
- **Component Resolution**: Loading and parsing component references (including external OKH manifests)
- **Multi-Facility Matching**: Matching each component to the best available facilities
- **Hierarchical Supply Trees**: SupplyTrees linked via parent-child relationships
- **Production Sequence**: Ordered stages of production based on dependencies

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: BOM Resolution
- **FR-1.1**: System MUST support both embedded BOMs (within OKH manifest) and external BOM files (separate JSON/YAML files linked from OKH)
- **FR-1.2**: System MUST parse BOM from OKH manifest in embedded format (when BOM data is directly in manifest)
- **FR-1.3**: System MUST load and parse external BOM files when OKH manifest references them via `bom` field (file path)
- **FR-1.4**: System MUST support BOM files in JSON, YAML, and Markdown formats
- **FR-1.5**: System MUST resolve component references to external OKH manifests
- **FR-1.6**: System MUST build complete component hierarchy with depth tracking
- **FR-1.7**: System MUST support recursive component nesting up to configurable max depth (default: 5)

#### FR-2: Recursive Matching
- **FR-2.1**: System MUST match each component to available facilities
- **FR-2.2**: System MUST recurse into sub-components when component cannot be matched directly
- **FR-2.3**: System MUST match components in dependency order (deepest first)
- **FR-2.4**: System MUST generate SupplyTree for each component-facility match

#### FR-3: Hierarchical Relationships
- **FR-3.1**: System MUST link parent SupplyTrees to child SupplyTrees
- **FR-3.2**: System MUST track which component each SupplyTree represents
- **FR-3.3**: System MUST maintain backward compatibility (existing SupplyTrees remain valid)

#### FR-4: Dependency Tracking
- **FR-4.1**: System MUST build dependency graph showing component dependencies
- **FR-4.2**: System MUST calculate production sequence (what can be done in parallel, what must be sequential)
- **FR-4.3**: System MUST detect circular dependencies and report errors

#### FR-5: Solution Validation
- **FR-5.1**: System MUST validate that all components have matches before returning solution
- **FR-5.2**: System MUST report which components could not be matched
- **FR-5.3**: System MUST validate dependency satisfaction (all dependencies have matches)

#### FR-6: API Integration
- **FR-6.1**: System MUST provide API endpoint for nested matching
- **FR-6.2**: System MUST return hierarchical supply tree solution
- **FR-6.3**: System MUST support existing single-level matching (backward compatible)

### 2.2 Non-Functional Requirements

#### NFR-1: Performance
- **NFR-1.1**: Matching MUST complete in < 10 seconds for 3-level nesting with 50 facilities
- **NFR-1.2**: System MUST support up to 100 components per OKH
- **NFR-1.3**: System MUST support up to 50 facilities per matching operation

#### NFR-2: Reliability
- **NFR-2.1**: System MUST handle missing component references gracefully
- **NFR-2.2**: System MUST handle invalid BOM formats gracefully
- **NFR-2.3**: System MUST prevent infinite recursion (max depth enforcement)

#### NFR-3: Compatibility
- **NFR-3.1**: System MUST maintain backward compatibility with existing SupplyTree model
- **NFR-3.2**: System MUST support existing API endpoints without breaking changes
- **NFR-3.3**: System MUST work with existing OKH and OKW data models

#### NFR-4: Usability
- **NFR-4.1**: Error messages MUST clearly indicate which components failed to match
- **NFR-4.2**: API responses MUST include clear dependency information
- **NFR-4.3**: Documentation MUST include examples of nested component matching

---

## 3. Architecture

### 3.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Matching Service                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     match_with_nested_components()                    │   │
│  │  - Orchestrates nested matching process              │   │
│  │  - Coordinates BOM resolution and matching           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BOM Resolution Service                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - detect_bom_type() (embedded vs external)          │   │
│  │  - resolve_bom() (handles both types)                │   │
│  │  - load_embedded_bom() (from OKH manifest)           │   │
│  │  - load_external_bom() (from file path)              │   │
│  │  - resolve_component_references()                     │   │
│  │  - explode_bom()                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Enhanced Matching Service                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - match_component()                                  │   │
│  │  - generate_supply_tree() (enhanced)                  │   │
│  │  - link_parent_child()                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Dependency Resolution Service                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - build_dependency_graph()                           │   │
│  │  - calculate_production_sequence()                    │   │
│  │  - validate_solution()                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
1. User Request (OKH + Facilities)
   │
   ▼
2. BOM Resolution
   ├─ Detect BOM type (embedded vs external)
   ├─ If embedded: Parse BOM from OKH manifest fields
   ├─ If external: Load BOM file from path
   ├─ Resolve component references
   └─ Build component hierarchy
   │
   ▼
3. Component Matching (recursive, deepest first)
   ├─ For each component:
   │  ├─ Try direct match
   │  ├─ If has sub-components: recurse
   │  └─ Generate SupplyTree
   │
   ▼
4. Relationship Linking
   ├─ Link parent-child relationships
   ├─ Track dependencies
   └─ Build dependency graph
   │
   ▼
5. Solution Building
   ├─ Calculate production sequence
   ├─ Validate solution
   └─ Aggregate costs/times
   │
   ▼
6. Response (NestedSupplyTreeSolution)
```

### 3.3 Key Design Decisions

#### DD-1: Backward Compatibility
**Decision**: All new fields in SupplyTree are optional.

**Rationale**: 
- Existing code continues to work without modification
- Gradual migration path
- Supports both simple and nested matching

**Implementation**: Use `Optional` types and default values.

#### DD-2: Depth Limiting
**Decision**: Add `max_depth` parameter (default: 5, configurable).

**Rationale**:
- Prevents infinite recursion
- Allows control over complexity
- Real-world BOMs rarely exceed 5 levels

**Implementation**: Track depth during BOM explosion, enforce limit.

#### DD-3: Component Reference Resolution
**Decision**: Support both inline sub-components and external OKH references.

**Rationale**:
- Flexibility (can embed or reference)
- Reusability (same OKH can be used in multiple places)
- Matches real-world patterns

**Implementation**: Check `component.reference` field, load OKH if present.

#### DD-5: BOM Storage Strategy
**Decision**: Support both embedded BOMs (within OKH manifest) and external BOM files (separate files linked via path).

**Rationale**:
- **Embedded BOMs**: Simpler for small BOMs, everything in one file, easier to manage
- **External BOMs**: Better for large BOMs, keeps OKH manifest readable, allows BOM reuse across multiple OKH files
- Matches OKH specification design goals (decoupling large BOMs from manifests)

**Implementation**:
- Check if OKH manifest has embedded BOM data (in `parts`, `sub_parts`, or BOM-related fields)
- If `okh_manifest.bom` field is present (non-empty string), treat as path to external BOM file
- Load external BOM file from same location as OKH manifest (relative path resolution)
- Support both approaches in BOMResolutionService with automatic detection

#### DD-4: Dependency Tracking
**Decision**: Track dependencies at SupplyTree level, not just parent-child.

**Rationale**:
- Supports complex dependencies (A needs B and C)
- Enables parallel production optimization
- Supports future features (just-in-time scheduling)

**Implementation**: Add `depends_on` and `required_by` fields to SupplyTree.

---

## 4. Data Models

### 4.1 Enhanced SupplyTree Model

```python
@dataclass
class SupplyTree:
    """Enhanced SupplyTree with hierarchical relationships"""
    
    # Existing fields (unchanged)
    id: UUID = field(default_factory=uuid4)
    facility_name: str
    okh_reference: str
    okw_reference: Optional[str] = None
    confidence_score: float
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    match_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    # NEW: Hierarchical relationships
    parent_tree_id: Optional[UUID] = None
    """ID of parent SupplyTree (if this represents a component of a larger product)"""
    
    child_tree_ids: List[UUID] = field(default_factory=list)
    """IDs of child SupplyTrees (components that this tree depends on)"""
    
    # NEW: Component tracking
    component_id: Optional[str] = None
    """ID of the component this SupplyTree represents (from BOM)"""
    
    component_name: Optional[str] = None
    """Human-readable name of the component"""
    
    component_quantity: Optional[float] = None
    """Quantity of this component needed"""
    
    component_unit: Optional[str] = None
    """Unit for component quantity (e.g., 'pieces', 'kg')"""
    
    # NEW: Dependency tracking
    depends_on: List[UUID] = field(default_factory=list)
    """SupplyTree IDs that must be completed before this one"""
    
    required_by: List[UUID] = field(default_factory=list)
    """SupplyTree IDs that depend on this one"""
    
    # NEW: Multi-facility coordination
    production_stage: str = "final"
    """Stage of production: 'component', 'sub-assembly', 'final'"""
    
    assembly_location: Optional[UUID] = None
    """Facility ID where final assembly happens (for final stage only)"""
    
    depth: int = 0
    """Depth in component hierarchy (0 = top level)"""
    
    component_path: List[str] = field(default_factory=list)
    """Path from root component (e.g., ['Device', 'Housing', 'Frame'])"""
```

**Serialization**:
- All new fields MUST be included in `to_dict()` output
- All new fields MUST be optional in `from_dict()` (for backward compatibility)
- Missing fields in deserialization MUST default to `None` or empty lists

### 4.2 ComponentMatch Model

```python
@dataclass
class ComponentMatch:
    """Represents a component in the matching process"""
    
    component: Component
    """The component being matched"""
    
    depth: int
    """Depth in hierarchy (0 = top level)"""
    
    parent_component_id: Optional[str] = None
    """ID of parent component (None for root)"""
    
    okh_manifest: Optional[OKHManifest] = None
    """Resolved OKH manifest if component references one"""
    
    path: List[str] = field(default_factory=list)
    """Path from root (e.g., ['Device', 'Housing', 'Frame'])"""
    
    matched: bool = False
    """Whether this component has been matched to facilities"""
    
    supply_trees: List[SupplyTree] = field(default_factory=list)
    """SupplyTrees generated for this component"""
```

### 4.3 NestedSupplyTreeSolution Model

```python
@dataclass
class NestedSupplyTreeSolution:
    """Complete solution for nested component matching"""
    
    root_trees: List[SupplyTree]
    """Top-level SupplyTrees (final products)"""
    
    all_trees: List[SupplyTree]
    """All SupplyTrees (flat list for easy iteration)"""
    
    component_mapping: Dict[str, List[SupplyTree]]
    """Component ID → List of SupplyTrees for that component"""
    
    dependency_graph: Dict[UUID, List[UUID]] = field(default_factory=dict)
    """Dependency graph: tree_id → [dependent_tree_ids]"""
    
    production_sequence: List[List[UUID]] = field(default_factory=list)
    """Production stages: each inner list can be done in parallel"""
    
    validation_result: Optional[ValidationResult] = None
    """Validation result for this solution"""
    
    total_estimated_cost: Optional[float] = None
    """Sum of all SupplyTree costs"""
    
    total_estimated_time: Optional[str] = None
    """Critical path time (longest dependency chain)"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata (matching parameters, etc.)"""
    
    def get_dependency_graph(self) -> Dict[UUID, List[UUID]]:
        """Build dependency graph from SupplyTrees"""
        graph = {}
        for tree in self.all_trees:
            dependencies = []
            if tree.parent_tree_id:
                dependencies.append(tree.parent_tree_id)
            if tree.depends_on:
                dependencies.extend(tree.depends_on)
            graph[tree.id] = dependencies
        return graph
    
    def validate_solution(self) -> ValidationResult:
        """Validate that all components have matches and dependencies are satisfied"""
        # Implementation details in Algorithms section
    
    def get_assembly_sequence(self) -> List[List[SupplyTree]]:
        """Get production sequence with SupplyTree objects"""
        sequence = []
        for stage in self.production_sequence:
            trees = [t for t in self.all_trees if t.id in stage]
            sequence.append(trees)
        return sequence
    
    def calculate_total_cost(self) -> float:
        """Sum costs across all trees"""
        return sum(
            tree.estimated_cost 
            for tree in self.all_trees 
            if tree.estimated_cost is not None
        )
    
    def calculate_critical_path_time(self) -> str:
        """Calculate critical path time (longest dependency chain)"""
        # Implementation details in Algorithms section
```

### 4.4 ValidationResult Model

```python
@dataclass
class ValidationResult:
    """Result of solution validation"""
    
    is_valid: bool
    """Whether the solution is valid"""
    
    errors: List[str] = field(default_factory=list)
    """List of error messages"""
    
    warnings: List[str] = field(default_factory=list)
    """List of warning messages"""
    
    unmatched_components: List[str] = field(default_factory=list)
    """Component IDs that could not be matched"""
    
    circular_dependencies: List[List[UUID]] = field(default_factory=list)
    """Detected circular dependencies"""
    
    missing_dependencies: List[UUID] = field(default_factory=list)
    """SupplyTree IDs with missing dependencies"""
```

---

## 5. API Specifications

### 5.1 New Endpoint: Nested Matching

**Endpoint**: `POST /api/match/nested`

**Request Body**:
```json
{
  "okh_id": "uuid",
  "okh_manifest": { /* OKHManifest object */ },
  "okh_url": "string",
  "facility_ids": ["uuid1", "uuid2"],
  "max_depth": 5,
  "domain": "manufacturing",
  "optimization_criteria": {
    "priority": "cost|time|quality",
    "weights": {
      "cost": 0.4,
      "time": 0.3,
      "quality": 0.3
    }
  },
  "include_validation": true
}
```

**Response** (Success - 200):
```json
{
  "success": true,
  "data": {
    "solution": {
      "root_trees": [ /* SupplyTree objects */ ],
      "all_trees": [ /* SupplyTree objects */ ],
      "component_mapping": {
        "component-id-1": [ /* SupplyTree objects */ ]
      },
      "dependency_graph": {
        "tree-uuid-1": ["tree-uuid-2", "tree-uuid-3"]
      },
      "production_sequence": [
        ["tree-uuid-1", "tree-uuid-2"],
        ["tree-uuid-3"]
      ],
      "total_estimated_cost": 15000.00,
      "total_estimated_time": "2-3 weeks",
      "validation_result": {
        "is_valid": true,
        "errors": [],
        "warnings": []
      }
    }
  },
  "request_id": "uuid",
  "processing_time": 2.5
}
```

**Response** (Error - 400/404/500):
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": {
      "unmatched_components": ["component-id-1"],
      "circular_dependencies": [["tree-uuid-1", "tree-uuid-2"]]
    }
  },
  "request_id": "uuid"
}
```

### 5.2 Enhanced Existing Endpoint

**Endpoint**: `POST /api/match` (existing)

**Enhancement**: Add optional parameter to enable nested matching:

```json
{
  "okh_id": "uuid",
  "enable_nested_matching": true,
  "max_depth": 5,
  /* ... other existing fields ... */
}
```

**Behavior**:
- If `enable_nested_matching` is `false` or omitted: Use existing single-level matching
- If `enable_nested_matching` is `true`: Use nested matching and return `NestedSupplyTreeSolution`

### 5.3 Query Parameters

**Common Parameters**:
- `max_depth` (int, default: 5): Maximum depth for BOM explosion
- `include_validation` (bool, default: true): Include validation results in response
- `include_dependency_graph` (bool, default: true): Include dependency graph in response
- `include_production_sequence` (bool, default: true): Include production sequence in response

---

## 6. Algorithms

### 6.1 BOM Resolution Algorithm

```python
class BOMResolutionService:
    """Service for resolving BOMs from OKH manifests"""
    
    async def resolve_bom(
        self, 
        okh_manifest: OKHManifest,
        okh_service: OKHService
    ) -> BillOfMaterials:
        """
        Resolve BOM from OKH manifest, handling both embedded and external BOMs.
        
        Algorithm:
        1. Detect BOM type (embedded vs external)
        2. If embedded: Extract BOM from OKH manifest fields
        3. If external: Load BOM file from path
        4. Parse BOM into BillOfMaterials structure
        5. Return BillOfMaterials
        """
        bom_type = self._detect_bom_type(okh_manifest)
        
        if bom_type == "embedded":
            return await self._load_embedded_bom(okh_manifest)
        elif bom_type == "external":
            return await self._load_external_bom(okh_manifest, okh_service)
        else:
            # No BOM found - create empty BOM
            return BillOfMaterials(
                name=okh_manifest.title or "Unknown",
                components=[]
            )
    
    def _detect_bom_type(self, okh_manifest: OKHManifest) -> str:
        """
        Detect whether BOM is embedded or external.
        
        Detection logic:
        - If okh_manifest.bom is a non-empty string: external BOM file
        - If okh_manifest.parts or okh_manifest.sub_parts have data: embedded BOM
        - Otherwise: no BOM
        """
        # Check for external BOM file reference
        if okh_manifest.bom and okh_manifest.bom.strip():
            return "external"
        
        # Check for embedded BOM data
        if (okh_manifest.parts and len(okh_manifest.parts) > 0) or \
           (okh_manifest.sub_parts and len(okh_manifest.sub_parts) > 0):
            return "embedded"
        
        return "none"
    
    async def _load_embedded_bom(
        self, 
        okh_manifest: OKHManifest
    ) -> BillOfMaterials:
        """
        Load BOM from embedded OKH manifest fields.
        
        Handles:
        - parts: List[PartSpec] - direct parts/components
        - sub_parts: List[Dict] - nested sub-parts (may need conversion)
        
        Algorithm:
        1. Convert parts to Component objects
        2. Convert sub_parts to Component objects with sub_components
        3. Build BillOfMaterials structure
        """
        components = []
        
        # Convert parts to components
        if okh_manifest.parts:
            for part in okh_manifest.parts:
                component = self._part_to_component(part)
                components.append(component)
        
        # Convert sub_parts to components (may be nested)
        if okh_manifest.sub_parts:
            for sub_part in okh_manifest.sub_parts:
                component = self._sub_part_to_component(sub_part)
                components.append(component)
        
        return BillOfMaterials(
            name=okh_manifest.title or "Unknown",
            components=components
        )
    
    async def _load_external_bom(
        self,
        okh_manifest: OKHManifest,
        okh_service: OKHService
    ) -> BillOfMaterials:
        """
        Load BOM from external file referenced by okh_manifest.bom.
        
        Algorithm:
        1. Resolve BOM file path (relative to OKH manifest location)
        2. Load file content (JSON, YAML, or Markdown)
        3. Parse using BOMProcessor (existing service)
        4. Return BillOfMaterials
        """
        bom_path = okh_manifest.bom
        
        # Resolve path relative to OKH manifest location
        # (Implementation depends on how OKH files are stored/accessed)
        resolved_path = await self._resolve_bom_path(
            bom_path,
            okh_manifest,
            okh_service
        )
        
        # Load file content
        file_content = await okh_service.load_file(resolved_path)
        
        # Parse using existing BOMProcessor
        from ..generation.bom_models import BOMProcessor
        
        processor = BOMProcessor()
        bom_source = BOMSource(
            file_path=resolved_path,
            content=file_content
        )
        
        components = processor.process_bom(bom_source)
        
        return BillOfMaterials(
            name=okh_manifest.title or "Unknown",
            components=components
        )
    
    def _part_to_component(self, part: PartSpec) -> Component:
        """Convert PartSpec to Component"""
        # Implementation: convert PartSpec fields to Component fields
        return Component(
            id=part.id or str(uuid4()),
            name=part.name,
            quantity=part.quantity or 1.0,
            unit=part.unit or "pieces",
            requirements=part.requirements or {},
            metadata=part.metadata or {}
        )
    
    def _sub_part_to_component(self, sub_part: Dict) -> Component:
        """Convert sub_part Dict to Component (may be nested)"""
        # Implementation: convert Dict structure to Component
        # Handle nested sub_parts recursively
        sub_components = []
        if "sub_parts" in sub_part:
            for nested_sub_part in sub_part["sub_parts"]:
                sub_components.append(
                    self._sub_part_to_component(nested_sub_part)
                )
        
        return Component(
            id=sub_part.get("id", str(uuid4())),
            name=sub_part.get("name", "Unknown"),
            quantity=sub_part.get("quantity", 1.0),
            unit=sub_part.get("unit", "pieces"),
            sub_components=sub_components,
            reference=sub_part.get("reference"),
            requirements=sub_part.get("requirements", {}),
            metadata=sub_part.get("metadata", {})
        )
    
    async def _resolve_bom_path(
        self,
        bom_path: str,
        okh_manifest: OKHManifest,
        okh_service: OKHService
    ) -> str:
        """
        Resolve BOM file path relative to OKH manifest location.
        
        Handles:
        - Relative paths (e.g., "bom.json", "data/bom.yaml")
        - Absolute paths (if OKH service supports them)
        - URL paths (if OKH was loaded from URL)
        """
        # Implementation depends on OKHService file resolution logic
        # This should leverage existing path resolution in OKHService
        return await okh_service.resolve_file_path(bom_path, okh_manifest)
```

### 6.2 BOM Explosion Algorithm

```python
async def explode_bom(
    bom: BillOfMaterials,
    okh_service: OKHService,
    max_depth: int = 5,
    current_depth: int = 0,
    parent_id: Optional[str] = None,
    path: List[str] = None
) -> List[ComponentMatch]:
    """
    Recursively explode BOM into flat list with depth tracking.
    
    Algorithm:
    1. For each component in BOM:
       a. Create ComponentMatch with current depth and path
       b. If component has reference to external OKH:
          - Load OKH manifest
          - If OKH has BOM, recursively explode it
       c. If component has sub-components:
          - Recursively explode sub-components (depth + 1)
       d. Add ComponentMatch to result list
    2. Return flat list of ComponentMatches
    """
    if path is None:
        path = []
    
    if current_depth >= max_depth:
        raise ValueError(f"Max depth {max_depth} exceeded")
    
    component_matches = []
    
    for component in bom.components:
        # Build component path
        component_path = path + [component.name]
        
        # Create ComponentMatch
        component_match = ComponentMatch(
            component=component,
            depth=current_depth,
            parent_component_id=parent_id,
            path=component_path
        )
        
        # Resolve external OKH reference if present
        if component.reference:
            okh_manifest = await resolve_component_reference(
                component.reference,
                okh_service
            )
            if okh_manifest:
                component_match.okh_manifest = okh_manifest
                
                # If referenced OKH has BOM (embedded or external), explode it
                bom_resolver = BOMResolutionService(okh_service)
                nested_bom = await bom_resolver.resolve_bom(okh_manifest, okh_service)
                if nested_bom.components:
                    nested_matches = await explode_bom(
                        nested_bom,
                        okh_service,
                        max_depth,
                        current_depth + 1,
                        component.id,
                        component_path
                    )
                    component_matches.extend(nested_matches)
        
        # Explode sub-components if present
        if component.sub_components:
            for sub_component in component.sub_components:
                # Create temporary BOM for sub-components
                sub_bom = BillOfMaterials(
                    name=f"{component.name} Sub-components",
                    components=[sub_component]
                )
                sub_matches = await explode_bom(
                    sub_bom,
                    okh_service,
                    max_depth,
                    current_depth + 1,
                    component.id,
                    component_path
                )
                component_matches.extend(sub_matches)
        
        component_matches.append(component_match)
    
    return component_matches
```

### 6.2 Recursive Matching Algorithm

```python
async def match_with_nested_components(
    okh_manifest: OKHManifest,
    facilities: List[ManufacturingFacility],
    max_depth: int = 5,
    domain: str = "manufacturing"
) -> NestedSupplyTreeSolution:
    """
    Match OKH with nested components across multiple facilities.
    
    Algorithm:
    1. Resolve BOM and explode into component matches
    2. Sort components by depth (deepest first)
    3. For each component (in dependency order):
       a. Match component to facilities
       b. Generate SupplyTrees for each match
       c. Link parent-child relationships
    4. Build dependency graph
    5. Calculate production sequence
    6. Validate solution
    7. Return NestedSupplyTreeSolution
    """
    # Step 1: Resolve BOM
    bom_resolver = BOMResolutionService(okh_service)
    bom = await bom_resolver.resolve_bom(okh_manifest)
    component_matches = await bom_resolver.explode_bom(bom, max_depth)
    
    # Step 2: Sort by depth (deepest first)
    component_matches.sort(key=lambda x: -x.depth)
    
    # Step 3: Match each component
    component_supply_trees: Dict[str, List[SupplyTree]] = {}
    
    for component_match in component_matches:
        component = component_match.component
        
        # Determine which OKH to use for matching
        manifest = component_match.okh_manifest or okh_manifest
        
        # Match component to facilities
        component_trees = []
        for facility in facilities:
            tree = await generate_supply_tree(
                manifest,
                facility,
                domain
            )
            
            # Enhance tree with component information
            tree.component_id = component.id
            tree.component_name = component.name
            tree.component_quantity = component.quantity
            tree.component_unit = component.unit
            tree.depth = component_match.depth
            tree.component_path = component_match.path
            tree.production_stage = (
                "component" if component_match.depth > 0 
                else "final"
            )
            
            component_trees.append(tree)
        
        component_supply_trees[component.id] = component_trees
        component_match.supply_trees = component_trees
        component_match.matched = len(component_trees) > 0
        
        # Link to parent if exists
        if component_match.parent_component_id:
            parent_trees = component_supply_trees.get(
                component_match.parent_component_id,
                []
            )
            for parent_tree in parent_trees:
                for child_tree in component_trees:
                    child_tree.parent_tree_id = parent_tree.id
                    parent_tree.child_tree_ids.append(child_tree.id)
                    parent_tree.depends_on.append(child_tree.id)
                    child_tree.required_by.append(parent_tree.id)
    
    # Step 4: Build solution
    all_trees = sum(component_supply_trees.values(), [])
    root_trees = [
        tree for tree in all_trees 
        if tree.depth == 0
    ]
    
    solution = NestedSupplyTreeSolution(
        root_trees=root_trees,
        all_trees=all_trees,
        component_mapping=component_supply_trees
    )
    
    # Step 5: Build dependency graph and production sequence
    solution.dependency_graph = solution.get_dependency_graph()
    solution.production_sequence = calculate_production_sequence(
        solution.dependency_graph
    )
    
    # Step 6: Validate solution
    solution.validation_result = solution.validate_solution()
    
    # Step 7: Calculate aggregates
    solution.total_estimated_cost = solution.calculate_total_cost()
    solution.total_estimated_time = solution.calculate_critical_path_time()
    
    return solution
```

### 6.3 Production Sequence Calculation (Topological Sort)

```python
def calculate_production_sequence(
    dependency_graph: Dict[UUID, List[UUID]]
) -> List[List[UUID]]:
    """
    Calculate production sequence using topological sort.
    
    Returns list of stages, where each stage can be produced in parallel.
    
    Algorithm:
    1. Build in-degree map (how many dependencies each node has)
    2. Initialize queue with nodes that have no dependencies
    3. While queue is not empty:
       a. Process all nodes in current queue (parallel stage)
       b. For each processed node, decrement in-degree of dependents
       c. Add nodes with in-degree 0 to next stage queue
    4. Return list of stages
    """
    # Build in-degree map
    in_degree = {node: 0 for node in dependency_graph.keys()}
    for node, deps in dependency_graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1
    
    # Initialize queue with nodes that have no dependencies
    queue = [node for node, degree in in_degree.items() if degree == 0]
    stages = []
    
    while queue:
        # Current stage (can be done in parallel)
        current_stage = queue.copy()
        stages.append(current_stage)
        queue = []
        
        # Process nodes in current stage
        for node in current_stage:
            # Decrement in-degree of dependents
            for dependent in dependency_graph.get(node, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
    
    # Check for circular dependencies
    if len(stages) < len(dependency_graph):
        remaining = [
            node for node in dependency_graph.keys()
            if node not in sum(stages, [])
        ]
        raise ValueError(f"Circular dependencies detected: {remaining}")
    
    return stages
```

### 6.4 Solution Validation Algorithm

```python
def validate_solution(
    solution: NestedSupplyTreeSolution
) -> ValidationResult:
    """
    Validate that solution is complete and dependencies are satisfied.
    
    Checks:
    1. All components have at least one match
    2. No circular dependencies
    3. All dependencies have matches
    4. All parent-child relationships are valid
    """
    errors = []
    warnings = []
    unmatched_components = []
    circular_dependencies = []
    missing_dependencies = []
    
    # Check 1: All components have matches
    for component_id, trees in solution.component_mapping.items():
        if not trees:
            unmatched_components.append(component_id)
            errors.append(f"Component {component_id} has no matches")
    
    # Check 2: Circular dependencies
    try:
        calculate_production_sequence(solution.dependency_graph)
    except ValueError as e:
        if "Circular dependencies" in str(e):
            circular_dependencies.append(extract_circular_deps(solution.dependency_graph))
            errors.append("Circular dependencies detected")
    
    # Check 3: All dependencies have matches
    for tree in solution.all_trees:
        for dep_id in tree.depends_on:
            if dep_id not in [t.id for t in solution.all_trees]:
                missing_dependencies.append(dep_id)
                errors.append(
                    f"Tree {tree.id} depends on {dep_id} which is not in solution"
                )
    
    # Check 4: Parent-child relationships are valid
    for tree in solution.all_trees:
        if tree.parent_tree_id:
            parent = next(
                (t for t in solution.all_trees if t.id == tree.parent_tree_id),
                None
            )
            if not parent:
                errors.append(
                    f"Tree {tree.id} has invalid parent {tree.parent_tree_id}"
                )
            elif tree.id not in parent.child_tree_ids:
                warnings.append(
                    f"Tree {tree.id} parent-child relationship is inconsistent"
                )
    
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        unmatched_components=unmatched_components,
        circular_dependencies=circular_dependencies,
        missing_dependencies=missing_dependencies
    )
```

---

## 7. Error Handling

### 7.1 Error Types

#### E-1: BOM Parsing Errors
- **Error Code**: `BOM_PARSE_ERROR`
- **HTTP Status**: 400
- **Handling**: Return error with details about which BOM (embedded or external) failed and why
- **Recovery**: User must fix BOM format

#### E-1a: External BOM File Not Found
- **Error Code**: `BOM_FILE_NOT_FOUND`
- **HTTP Status**: 404
- **Handling**: Return error with BOM file path, OKH manifest ID, and resolution attempt details
- **Recovery**: User must provide valid BOM file or fix path reference in OKH manifest

#### E-2: Component Reference Resolution Errors
- **Error Code**: `COMPONENT_REFERENCE_ERROR`
- **HTTP Status**: 404
- **Handling**: Return error with component ID and reference that failed
- **Recovery**: User must provide valid OKH reference or remove reference

#### E-3: Max Depth Exceeded
- **Error Code**: `MAX_DEPTH_EXCEEDED`
- **HTTP Status**: 400
- **Handling**: Return error with current depth and max depth
- **Recovery**: User can increase max_depth parameter

#### E-4: Circular Dependencies
- **Error Code**: `CIRCULAR_DEPENDENCY`
- **HTTP Status**: 400
- **Handling**: Return error with detected circular dependency path
- **Recovery**: User must fix component dependencies

#### E-5: Unmatched Components
- **Error Code**: `UNMATCHED_COMPONENTS`
- **HTTP Status**: 200 (partial success)
- **Handling**: Return solution with validation errors indicating unmatched components
- **Recovery**: User can add more facilities or modify component requirements

#### E-6: Missing Dependencies
- **Error Code**: `MISSING_DEPENDENCIES`
- **HTTP Status**: 400
- **Handling**: Return error with list of missing dependencies
- **Recovery**: User must ensure all dependencies are matched

### 7.2 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "component_id": "component-123",
      "depth": 3,
      "max_depth": 5,
      "circular_path": ["tree-1", "tree-2", "tree-1"]
    },
    "suggestion": "How to fix this error"
  },
  "request_id": "uuid"
}
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

#### UT-1: BOM Resolution Service
- Test BOM type detection (embedded vs external vs none)
- Test embedded BOM loading from OKH manifest fields
- Test external BOM file loading (JSON, YAML, Markdown)
- Test BOM path resolution (relative and absolute paths)
- Test component reference resolution
- Test BOM explosion with various depths
- Test max depth enforcement
- Test circular reference detection
- Test error handling for missing external BOM files

#### UT-2: Enhanced SupplyTree Model
- Test serialization/deserialization with new fields
- Test backward compatibility (missing new fields)
- Test parent-child relationship linking
- Test dependency tracking

#### UT-3: Matching Algorithms
- Test recursive matching with 2-level nesting
- Test component matching logic
- Test production sequence calculation
- Test solution validation

### 8.2 Integration Tests

#### IT-1: End-to-End Nested Matching
- Test complete flow: OKH → BOM → Matching → Solution
- Test with real OKH manifests (from test data)
- Test with multiple facilities
- Test error scenarios

#### IT-2: API Endpoints
- Test new nested matching endpoint
- Test enhanced existing endpoint
- Test error responses
- Test response format validation

### 8.3 Performance Tests

#### PT-1: Matching Performance
- Test with 3-level nesting, 50 facilities (target: < 10 seconds)
- Test with 100 components (target: completes successfully)
- Test with max depth 5 (target: no infinite loops)

### 8.4 Test Data Requirements

- OKH manifests with embedded BOMs (parts and sub_parts fields)
- OKH manifests with external BOM files (JSON, YAML, Markdown formats)
- OKH manifests with 2-level nested components (both embedded and external)
- OKH manifests with external component references
- OKH manifests with mixed BOM types (some components embedded, some external)
- Facilities with diverse capabilities
- Test scenarios for error cases (missing BOM files, invalid paths, etc.)

---

## 9. Implementation Plan

### 9.1 Phase 1: Foundation (Week 1-2)

**Tasks**:
1. ✅ Enhance SupplyTree model with hierarchical fields
2. ✅ Create BOMResolutionService
3. ✅ Implement BOM type detection (embedded vs external)
4. ✅ Implement embedded BOM loading from OKH manifest fields
5. ✅ Implement external BOM file loading (leverage existing BOMProcessor)
6. ✅ Implement BOM path resolution (relative to OKH manifest location)
7. ✅ Add component reference resolution
8. ✅ Unit tests for new models and services

**Deliverables**:
- ✅ Enhanced SupplyTree model (backward compatible)
- ✅ BOMResolutionService with support for both embedded and external BOMs
- ✅ BOM type detection logic
- ✅ BOM path resolution logic
- ✅ Unit tests (24 tests passing, covering all BOM resolution functionality including component reference resolution)

**Acceptance Criteria**:
- ✅ Can detect BOM type (embedded, external, or none)
- ✅ Can parse embedded BOM from OKH manifest fields (parts, sub_parts)
- ✅ Can load and parse external BOM files (JSON, YAML)
- ✅ Can resolve BOM file paths relative to OKH manifest location
- ✅ Can resolve component references to OKH manifests (by ID and by path)
- ⏳ Can explode BOM into component matches (Phase 2)
- ✅ All new fields are optional and backward compatible

**Progress Notes**:
- **Completed (2024-12-08)**:
  - Enhanced SupplyTree model with all hierarchical fields (parent_tree_id, child_tree_ids, component tracking, dependency tracking, production_stage, depth, component_path)
  - All new fields are optional and backward compatible
  - Created BOMResolutionService with BOM type detection
  - Implemented embedded BOM loading from parts and sub_parts fields
  - Supports nested sub_parts recursively
  - Enhanced BOM type detection to handle both string paths and object with external_file property
  - Added `_get_external_bom_path()` method to extract BOM path from both formats
  - Implemented external BOM file loading with support for JSON and YAML formats
  - Implemented BOM path resolution (relative to OKH manifest location, handles both relative and absolute paths)
  - Added `_load_external_bom()` method to load and parse external BOM files
  - Added `_resolve_bom_path()` method for path resolution
  - Added `_load_file_content()` method for file loading (filesystem and storage support)
  - Implemented component reference resolution with support for:
    - Resolving by OKH ID (using OKHService.get())
    - Resolving by file path (relative and absolute)
    - Graceful error handling for missing/invalid references
  - Added `resolve_component_reference()` method for resolving component references
  - Added `_load_manifest_from_path()` method for loading OKH manifests from file paths
  - All 24 unit tests passing (18 original + 6 new for component reference resolution)
  - Verified backward compatibility with existing tests

- **BOM Explosion Algorithm** (Phase 2, Task 2):
  - Created `ComponentMatch` data model to track components during matching process
  - Implemented `explode_bom()` method in `BOMResolutionService`:
    - Recursively explodes BOM into flat list of ComponentMatch objects
    - Tracks depth, parent relationships, and component paths
    - Handles component references to external OKH manifests
    - Recursively explodes nested sub-components
    - Enforces depth limiting with clear error messages
  - All 6 unit tests passing for BOM explosion:
    - Simple BOM explosion (no nesting)
    - Nested BOM explosion (2 levels)
    - Path tracking (3 levels)
    - Depth limiting (error handling)
    - Component references (external OKH resolution)
    - Complex nesting (multiple branches and levels)
  - Verified backward compatibility with existing BOM resolution tests

- **Nested Component Matching** (Phase 2, Task 3):
  - Created `NestedSupplyTreeSolution` data model to represent complete nested matching solutions
  - Created `ValidationResult` data model for solution validation
  - Implemented `match_with_nested_components()` method in `MatchingService`:
    - Resolves BOM and explodes into component matches using `BOMResolutionService`
    - Sorts components by depth (deepest first) for dependency order
    - Matches each component to facilities using existing `_generate_supply_tree()` method
    - Enhances SupplyTrees with component information (id, name, quantity, unit, depth, path, production_stage)
    - Links parent-child relationships between SupplyTrees
    - Builds dependency graph from SupplyTree relationships
    - Calculates production sequence using topological sort
    - Validates solution (checks for unmatched components, missing dependencies, circular dependencies)
    - Calculates aggregate metrics (total cost, critical path time)
  - Implemented `_calculate_production_sequence()` method for topological sorting
  - Enhanced `explode_bom()` to respect depth limits before recursing (prevents unnecessary recursion)
  - All 4 unit tests passing for nested component matching:
    - Simple nested BOM matching
    - Multiple facilities matching
    - Parent-child linking verification
    - Depth limiting verification
  - Verified backward compatibility with existing matching service tests

- **Component-Level Matching Logic** (Phase 2, Task 4):
  - Created `_match_component_to_facilities()` method for component-specific matching
  - Enhanced matching to filter facilities based on component requirements
  - Added confidence threshold support (min_confidence parameter)
  - Extracts component requirements from component.requirements and component.metadata
  - Adds component-specific metadata to SupplyTrees
  - Improved logging for component-level matching decisions

- **Parent-Child Linking** (Phase 2, Task 5):
  - Created `_link_parent_child_relationships()` method for enhanced linking
  - Handles cases where parent components have no trees (graceful degradation)
  - Prevents duplicate links (checks before adding to lists)
  - Updates both parent and child relationships bidirectionally:
    - Parent's `child_tree_ids` and `depends_on` lists
    - Child's `parent_tree_id` and `required_by` lists
  - Enhanced logging for relationship linking

- **Depth Limiting and Cycle Detection** (Phase 2, Task 6):
  - Depth limiting already implemented in `explode_bom()` (checks before recursing)
  - Enhanced `_detect_circular_dependencies()` in SupplyTreeSolution:
    - Improved cycle detection algorithm with duplicate prevention
    - Normalizes cycles to avoid reporting the same cycle multiple times
    - Returns detailed cycle paths for better error messages
  - All depth checks happen before recursion to prevent unnecessary work

- **Integration Tests** (Phase 2, Task 7):
  - Created comprehensive integration test suite (`test_nested_matching_integration.py`)
  - 4 integration tests covering:
    - End-to-end nested matching with 2-level nesting
    - Handling unmatched components
    - Depth limiting in integration context
    - Parent-child linking verification
  - All integration tests passing
  - Tests verify complete flow from OKH → BOM → Matching → Solution
  
- **External BOM Structure** (from test-data/open-flexure):
  - When `bom` field is an object: `{"external_file": "bom/bom.json", "id": "...", "name": "...", ...}`
  - When `bom` field is a string: `"bom/bom.json"` (direct path)
  - External BOM files are in BillOfMaterials format (id, name, components array)
  - BOM files can be JSON, YAML, or Markdown format
  - Paths are relative to OKH manifest location

### 9.2 Phase 2: Recursive Matching (Week 2-3)

**Tasks**:
1. ✅ Update synthetic data generator to create nested components for testing
2. ✅ Implement BOM explosion algorithm
3. ✅ Implement `match_with_nested_components` method
4. ✅ Add component-level matching logic
5. ✅ Implement parent-child linking
6. ✅ Add depth limiting and cycle detection
7. ✅ Integration tests

**Deliverables**:
- Enhanced synthetic data generator with nested component support
- Enhanced MatchingService with nested component support
- Integration tests for 2-level nesting
- Documentation for new methods

**Acceptance Criteria**:
- Synthetic data generator can create OKH manifests with nested components (2-3 levels deep)
- Can match OKH with 2-level nested components
- Can generate SupplyTrees for each component
- Can link parent-child relationships
- Depth limiting works correctly

### 9.3 Phase 3: Multi-Facility Coordination (Week 3-4)

**Tasks**:
1. ✅ Implement dependency graph building
2. ✅ Add production sequence calculation (topological sort)
3. ✅ Implement solution validation
4. ✅ Add cost/time aggregation
5. ✅ End-to-end tests

**Deliverables**:
- NestedSupplyTreeSolution model
- Dependency resolution algorithms
- Solution validation logic
- End-to-end tests with multi-facility scenarios

**Acceptance Criteria**:
- ✅ Can build dependency graph from SupplyTrees
- ✅ Can calculate production sequence
- ✅ Can validate complete solutions
- ✅ Can aggregate costs and times

**Progress Notes**:
- **Dependency Graph Building** (Phase 3, Task 1):
  - Enhanced `get_dependency_graph()` method in `SupplyTreeSolution`:
    - Builds graph from parent_tree_id and depends_on relationships
    - Removes duplicate dependencies while preserving order
    - Returns dictionary mapping tree_id -> list of dependent tree_ids
  - Graph includes both parent-child relationships and explicit dependencies
  - All trees in solution are included in the graph

- **Production Sequence Calculation** (Phase 3, Task 2):
  - Implemented `_calculate_production_sequence()` static method using topological sort
  - Algorithm correctly identifies parallel execution stages
  - Returns list of stages, where each stage can be produced in parallel
  - Handles complex dependency graphs correctly
  - Called automatically in `from_nested_trees()` factory method

- **Solution Validation** (Phase 3, Task 3):
  - Enhanced `validate_solution()` method:
    - Checks that all components have matches
    - Validates dependency satisfaction (all dependencies have matches)
    - Detects circular dependencies using enhanced DFS algorithm
    - Validates parent-child relationships
    - Returns comprehensive `ValidationResult` with errors, warnings, and details
  - Validation runs automatically when creating nested solutions

- **Cost/Time Aggregation** (Phase 3, Task 4):
  - Enhanced `calculate_total_cost()` method:
    - Sums estimated_cost from all trees
    - Logs when some trees don't have cost estimates
    - Returns 0.0 if no trees have cost estimates
  - Enhanced `calculate_critical_path_time()` method:
    - Calculates time based on production sequence stages
    - Detects when trees have time estimates and includes that information
    - Returns meaningful time estimates or stage counts
  - Both methods called automatically in `from_nested_trees()` factory method

- **End-to-End Tests** (Phase 3, Task 5):
  - Created comprehensive test suite (`test_phase3_multi_facility.py`)
  - 5 integration tests covering:
    - Dependency graph building verification
    - Production sequence calculation verification
    - Solution validation verification
    - Cost/time aggregation verification
    - Complete multi-facility coordination scenario
  - All Phase 3 tests passing
  - Tests verify all Phase 3 functionality works correctly

**Deliverables**:
- ✅ Unified SupplyTreeSolution model (merged from NestedSupplyTreeSolution)
- ✅ Dependency graph building algorithm
- ✅ Production sequence calculation (topological sort)
- ✅ Solution validation logic with comprehensive error reporting
- ✅ Cost/time aggregation methods
- ✅ Comprehensive end-to-end tests (9 tests total: 5 Phase 3 + 4 nested matching)

### 9.4 Phase 4: API Integration (Week 4)

**Tasks**:
1. ✅ Design unified matching endpoint (see [Unified Matching Endpoint Design](./unified-matching-endpoint-design.md))
2. ✅ Update `MatchRequest` model with nested matching parameters
3. ✅ Implement unified endpoint logic (single-level and nested)
4. ✅ Update response models to handle both modes
5. ✅ Add CLI commands for nested matching
6. ⏳ Add demo data with nested components
7. ⏳ Documentation and examples
8. ⏳ Performance testing

**Deliverables**:
- Unified API endpoint: `POST /api/match` (supports both single-level and nested)
- Enhanced `MatchRequest` model with nested matching parameters
- Updated response models for both matching modes
- CLI commands for nested matching (`ome match requirements --nested`)
- Updated API documentation
- Demo-ready nested component examples
- Performance test results

**Acceptance Criteria**:
- ✅ Unified endpoint handles both single-level and nested matching
- ✅ Backward compatibility maintained (existing single-level requests work)
- ✅ Response format clearly indicates matching mode
- ✅ CLI commands work for both modes
- ⏳ Demo data includes 2-level nested components
- ⏳ Performance meets requirements (< 10 seconds for nested matching)

**Progress Notes**:
- **API Integration** (Phase 4, Tasks 1-4):
  - ✅ Designed unified matching endpoint using depth-based approach
  - ✅ Updated `MatchRequest` model with `max_depth`, `auto_detect_depth`, and `include_validation` parameters
  - ✅ Implemented unified endpoint logic that routes based on `max_depth > 0`
  - ✅ Added `_has_nested_components()` helper for auto-detection
  - ✅ Added `_format_nested_response()` helper for nested response formatting
  - ✅ Updated single-level response to include `matching_mode: "single-level"` field
  - ✅ Added `MAX_DEPTH` configuration setting to central config (default: 5, configurable via environment variable)
  - ✅ All services now use `MAX_DEPTH` from config instead of hardcoded values

- **CLI Integration** (Phase 4, Task 5):
  - ✅ Added `--max-depth` CLI option (default: 0 for single-level matching)
  - ✅ Added `--auto-detect-depth` CLI option (flag for auto-detection)
  - ✅ Updated CLI help text and examples to show nested matching usage
  - ✅ Updated `requirements()` command to accept and pass nested matching parameters
  - ✅ Updated `fallback_match()` function to support nested matching when `max_depth > 0`
  - ✅ Auto-detection logic works in CLI fallback mode
  - ✅ CLI response format matches API response format (includes `matching_mode` field)

---

## 10. Dependencies

### 10.1 Internal Dependencies

- **OKHService**: For loading OKH manifests and resolving component references
- **OKWService**: For loading facilities
- **MatchingService**: Existing matching logic (to be enhanced)
- **BOMProcessor**: Existing BOM parsing logic (to be leveraged)
- **StorageService**: For saving/loading SupplyTrees

### 10.2 External Dependencies

- **FastAPI**: For API endpoints (already in use)
- **Pydantic**: For data validation (already in use)
- **Python 3.9+**: For type hints and dataclasses

### 10.3 Data Dependencies

- OKH manifests with BOM files
- OKH manifests with component references
- Facilities with diverse capabilities
- Test data for various scenarios

---

## 11. Risks and Mitigations

### 11.1 Technical Risks

#### R-1: Performance Degradation
**Risk**: Recursive matching may be slow with deep nesting.

**Mitigation**:
- Implement depth limiting (max_depth parameter)
- Optimize BOM resolution (cache resolved OKH manifests)
- Add performance monitoring
- Set clear performance targets and test early

#### R-2: Circular Dependency Detection
**Risk**: May miss circular dependencies or false positives.

**Mitigation**:
- Use proven topological sort algorithm
- Add comprehensive tests for circular dependency scenarios
- Provide clear error messages with dependency paths

#### R-3: Backward Compatibility Issues
**Risk**: Changes may break existing code.

**Mitigation**:
- All new fields are optional
- Comprehensive backward compatibility tests
- Gradual migration path
- Clear documentation of changes

### 11.2 Data Risks

#### R-4: Invalid BOM Formats
**Risk**: BOM files (embedded or external) may be in unexpected formats or malformed.

**Mitigation**:
- Support multiple formats (JSON, YAML, Markdown)
- Robust error handling and validation for both embedded and external BOMs
- Clear error messages indicating BOM type (embedded vs external)
- Fallback to basic parsing if advanced parsing fails
- Separate validation logic for embedded vs external BOMs

#### R-4a: External BOM File Access Issues
**Risk**: External BOM files may be inaccessible, missing, or have incorrect paths.

**Mitigation**:
- Robust path resolution (relative to OKH manifest location)
- Clear error messages with attempted path and resolution details
- Support for both relative and absolute paths
- Validation of file existence before parsing
- Graceful fallback if external BOM cannot be loaded (with warning)

#### R-5: Missing Component References
**Risk**: Component references may point to non-existent OKH manifests.

**Mitigation**:
- Validate references before matching
- Provide clear error messages
- Support optional references (skip if not found, with warning)

### 11.3 Integration Risks

#### R-6: API Breaking Changes
**Risk**: New API may conflict with existing endpoints.

**Mitigation**:
- New endpoint (`/api/match/nested`) instead of modifying existing
- Optional parameter on existing endpoint
- Comprehensive API versioning strategy
- Clear migration documentation

---

## 12. Appendices

### 12.1 Example: Medical Ventilator Scenario

See [Nested Supply Tree Analysis](../../notes/nested-supply-tree-analysis.md#part-5-example-scenario) for detailed example.

### 12.2 Glossary

- **BOM**: Bill of Materials - list of components needed to build a product
- **BOM Explosion**: Recursive breakdown of a product into all its components
- **Component**: A part or sub-assembly in a BOM
- **Dependency Graph**: Graph showing what components depend on what
- **Production Sequence**: Ordered stages of production based on dependencies
- **Supply Tree**: Data structure representing a manufacturing solution
- **Topological Sort**: Algorithm for ordering nodes in a DAG based on dependencies

### 12.3 References

- [Supply Tree Models](../models/supply-tree.md)
- [BOM Models](../models/bom.md)
- [Matching Architecture](../architecture/matching.md)
- [Demo Readiness Plan](../../notes/demo-readiness-plan.md)
- [Nested Supply Tree Analysis](../../notes/nested-supply-tree-analysis.md)

---

**Document Status**: Draft - Ready for Review  
**Next Steps**: Review, approve, and begin Phase 1 implementation

