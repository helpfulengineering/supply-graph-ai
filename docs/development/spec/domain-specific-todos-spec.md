# Domain-Specific TODOs Implementation Specification

## Overview

This specification defines the implementation plan for completing domain-specific functionality TODOs. These are enhancements that improve the manufacturing domain matching, documentation parsing, and BOM processing capabilities.

## Current State Analysis

### Issue 1: Substitution Rules Enhancement

**Location**: `src/core/domains/manufacturing/okh_matcher.py:162`

**Current Implementation:**
```python
def _can_substitute(self, 
                  requirement: OKHRequirement, 
                  capability: Capability) -> bool:
    """Check if a capability can be a substitute for a requirement"""
    # Check if capability is a known substitute
    if 'substitutes_for' in capability.parameters and requirement.name in capability.parameters['substitutes_for']:
        return True
        
    # TODO: Add more sophisticated substitution rules
    return False
```

**Problems:**
- Only checks explicit `substitutes_for` parameter
- No material compatibility checking
- No process similarity checking
- No tool/equipment compatibility checking
- Very limited substitution detection

**Context:**
- Used in matching process to find alternative capabilities
- Important for finding viable alternatives when exact matches aren't available
- Should consider multiple factors: materials, processes, tools, specifications

**Severity**: Low - Enhancement, current functionality works but could be improved

### Issue 2: Documentation Files Parsing

**Location**: `src/core/generation/platforms/local_git.py:366`

**Current Implementation:**
```python
# Create ProjectData
project_data = ProjectData(
    platform=platform,
    url=url,
    metadata=metadata,
    files=files,
    documentation=[],  # TODO: Parse documentation files
    raw_content={"clone_path": str(repo_path)}
)
```

**Problems:**
- Returns empty list for documentation
- Documentation files are not parsed into DocumentInfo objects
- Other extractors (GitLab, GitHub) have basic documentation parsing
- Missing documentation affects OKH manifest generation

**Context:**
- `DocumentInfo` objects are used in OKH manifest generation
- Documentation types include: README, manuals, guides, etc.
- GitLab extractor has `_build_documentation_list()` method
- GitHub extractor has basic README parsing

**Severity**: Medium - Missing feature, affects manifest generation quality

### Issue 3: JSON/YAML BOM Parsing

**Location**: `src/core/generation/bom_models.py:760`

**Current Implementation:**
```python
def _extract_components_from_structured(self, content: str, source: BOMSource) -> List['Component']:
    """Extract components from structured formats (JSON, YAML)"""
    # For now, fallback to markdown parsing
    # TODO: Implement proper JSON/YAML parsing
    return self._extract_components_from_markdown(content, source)
```

**Problems:**
- Falls back to markdown parsing for JSON/YAML files
- Doesn't leverage structured format advantages
- May miss components in structured BOMs
- Less accurate than proper parsing

**Context:**
- BOM files can be in JSON or YAML format
- Structured formats have clear component definitions
- CSV parsing is already implemented
- Should parse structured formats similarly

**Severity**: Medium - Missing feature, affects BOM extraction accuracy

## Requirements

### Functional Requirements

1. **Substitution Rules Enhancement**
   - Material compatibility checking (e.g., steel types, plastic grades)
   - Process similarity checking (e.g., milling vs. turning)
   - Tool/equipment compatibility (e.g., compatible tool sizes)
   - Specification matching (e.g., tolerance ranges)
   - Confidence scoring for substitutions

2. **Documentation Files Parsing**
   - Parse documentation files from repository
   - Identify documentation types (README, manual, guide, etc.)
   - Create DocumentInfo objects
   - Extract titles and content
   - Support common documentation file patterns

3. **JSON/YAML BOM Parsing**
   - Parse JSON format BOM files
   - Parse YAML format BOM files
   - Extract component information (name, quantity, unit, etc.)
   - Handle different BOM JSON/YAML schemas
   - Fallback to markdown parsing on error

### Non-Functional Requirements

1. **Performance**
   - Substitution checking should be fast (<10ms per check)
   - Documentation parsing should be efficient
   - BOM parsing should handle large files

2. **Accuracy**
   - Substitution rules should be conservative (avoid false positives)
   - Documentation parsing should correctly identify types
   - BOM parsing should extract all components

3. **Maintainability**
   - Clear rule definitions
   - Easy to extend substitution rules
   - Well-documented parsing logic

## Design Decisions

### Substitution Rules Strategy

**Multi-Factor Checking:**
- Material compatibility (material type, grade, properties)
- Process compatibility (process type, capabilities)
- Tool compatibility (tool type, size, specifications)
- Specification matching (tolerance, dimensions, etc.)

**Confidence Scoring:**
- Each factor contributes to confidence score
- Higher confidence for multiple matching factors
- Lower confidence for single-factor matches

**Rule-Based Approach:**
- Define substitution rules as data structures
- Easy to extend and maintain
- Can be loaded from configuration files

### Documentation Parsing Strategy

**Pattern-Based Identification:**
- Use file patterns (README*, MANUAL*, GUIDE*, etc.)
- Use directory patterns (docs/, manual/, documentation/)
- Use file extensions (.md, .txt, .rst, .pdf, .docx)

**Type Detection:**
- Infer doc_type from filename and path
- Use heuristics to determine documentation type
- Map to DocumentInfo doc_type field

**Content Extraction:**
- Extract title from filename or first heading
- Use file content (already available in FileInfo)
- Limit content size for very large files

### BOM Parsing Strategy

**Schema-Agnostic Parsing:**
- Support multiple BOM JSON/YAML schemas
- Common patterns: array of components, object with components array
- Flexible field mapping (name, quantity, unit, etc.)

**Error Handling:**
- Try structured parsing first
- Fallback to markdown parsing on error
- Log parsing attempts and failures

**Field Mapping:**
- Map common field names (name, item, component, part)
- Map quantity fields (quantity, qty, amount, count)
- Map unit fields (unit, units, measure)

## Implementation Specification

### 1. Enhanced Substitution Rules

**File: `src/core/domains/manufacturing/okh_matcher.py`**

**Update `_can_substitute` method:**

```python
def _can_substitute(self, 
                  requirement: OKHRequirement, 
                  capability: Capability) -> bool:
    """
    Check if a capability can be a substitute for a requirement.
    
    Uses multiple factors to determine substitution viability:
    - Explicit substitution declarations
    - Material compatibility
    - Process similarity
    - Tool/equipment compatibility
    - Specification matching
    
    Args:
        requirement: The requirement to find substitute for
        capability: The capability to check as substitute
        
    Returns:
        True if capability can substitute for requirement
    """
    # Check explicit substitution declaration (highest priority)
    if 'substitutes_for' in capability.parameters:
        substitutes = capability.parameters['substitutes_for']
        if isinstance(substitutes, list) and requirement.name in substitutes:
            return True
        elif isinstance(substitutes, dict) and requirement.name in substitutes:
            return True
        elif isinstance(substitutes, str) and requirement.name == substitutes:
            return True
    
    # Check material compatibility
    if self._check_material_compatibility(requirement, capability):
        return True
    
    # Check process similarity
    if self._check_process_similarity(requirement, capability):
        return True
    
    # Check tool/equipment compatibility
    if self._check_tool_compatibility(requirement, capability):
        return True
    
    # Check specification matching
    if self._check_specification_match(requirement, capability):
        return True
    
    return False

def _check_material_compatibility(self, requirement: OKHRequirement, capability: Capability) -> bool:
    """
    Check if materials are compatible for substitution.
    
    Args:
        requirement: Requirement with material specifications
        capability: Capability with material capabilities
        
    Returns:
        True if materials are compatible
    """
    # Extract materials from requirement
    req_materials = self._extract_materials(requirement)
    if not req_materials:
        return False
    
    # Extract materials from capability
    cap_materials = self._extract_materials(capability)
    if not cap_materials:
        return False
    
    # Check for compatible material types
    # Material compatibility rules (can be extended)
    material_compatibility = {
        # Steel types
        "steel": {"stainless_steel", "carbon_steel", "alloy_steel"},
        "stainless_steel": {"steel", "stainless_steel_304", "stainless_steel_316"},
        "carbon_steel": {"steel", "mild_steel"},
        
        # Aluminum types
        "aluminum": {"aluminum_6061", "aluminum_7075", "aluminum_alloy"},
        "aluminum_6061": {"aluminum", "aluminum_alloy"},
        
        # Plastic types
        "plastic": {"abs", "pla", "petg", "nylon"},
        "abs": {"plastic", "thermoplastic"},
        "pla": {"plastic", "bioplastic"},
    }
    
    for req_mat in req_materials:
        req_mat_lower = req_mat.lower().replace(" ", "_")
        for cap_mat in cap_materials:
            cap_mat_lower = cap_mat.lower().replace(" ", "_")
            
            # Exact match
            if req_mat_lower == cap_mat_lower:
                return True
            
            # Check compatibility mapping
            if req_mat_lower in material_compatibility:
                if cap_mat_lower in material_compatibility[req_mat_lower]:
                    return True
            
            # Check reverse mapping
            if cap_mat_lower in material_compatibility:
                if req_mat_lower in material_compatibility[cap_mat_lower]:
                    return True
    
    return False

def _check_process_similarity(self, requirement: OKHRequirement, capability: Capability) -> bool:
    """
    Check if processes are similar enough for substitution.
    
    Args:
        requirement: Requirement with process specifications
        capability: Capability with process capabilities
        
    Returns:
        True if processes are similar
    """
    req_process = requirement.process_name.lower() if requirement.process_name else ""
    cap_process = capability.name.lower() if capability.name else ""
    
    if not req_process or not cap_process:
        return False
    
    # Process similarity groups
    process_groups = {
        "machining": {"milling", "turning", "drilling", "cnc_machining", "machining"},
        "milling": {"cnc_milling", "manual_milling", "machining"},
        "turning": {"cnc_turning", "manual_turning", "lathe", "machining"},
        "3d_printing": {"fdm", "sla", "sls", "additive_manufacturing", "3d_printing"},
        "cutting": {"laser_cutting", "waterjet_cutting", "plasma_cutting", "cutting"},
        "welding": {"tig_welding", "mig_welding", "arc_welding", "welding"},
    }
    
    # Check if processes are in same group
    for group, processes in process_groups.items():
        if req_process in processes and cap_process in processes:
            return True
    
    # Check for substring matches (e.g., "cnc_milling" contains "milling")
    if req_process in cap_process or cap_process in req_process:
        return True
    
    return False

def _check_tool_compatibility(self, requirement: OKHRequirement, capability: Capability) -> bool:
    """
    Check if tools/equipment are compatible.
    
    Args:
        requirement: Requirement with tool specifications
        capability: Capability with tool capabilities
        
    Returns:
        True if tools are compatible
    """
    req_tools = requirement.required_tools or []
    if not req_tools:
        return False
    
    # Extract tools from capability
    cap_tools = []
    if 'tools' in capability.parameters:
        cap_tools = capability.parameters['tools']
        if isinstance(cap_tools, str):
            cap_tools = [cap_tools]
    elif 'equipment' in capability.parameters:
        cap_tools = capability.parameters['equipment']
        if isinstance(cap_tools, str):
            cap_tools = [cap_tools]
    
    if not cap_tools:
        return False
    
    # Check for tool matches
    for req_tool in req_tools:
        req_tool_lower = req_tool.lower()
        for cap_tool in cap_tools:
            cap_tool_lower = str(cap_tool).lower()
            
            # Exact or substring match
            if req_tool_lower in cap_tool_lower or cap_tool_lower in req_tool_lower:
                return True
    
    return False

def _check_specification_match(self, requirement: OKHRequirement, capability: Capability) -> bool:
    """
    Check if specifications match closely enough for substitution.
    
    Args:
        requirement: Requirement with specifications
        capability: Capability with specifications
        
    Returns:
        True if specifications match closely
    """
    # Extract specifications from requirement
    req_specs = requirement.parameters or {}
    
    # Extract specifications from capability
    cap_specs = capability.parameters or {}
    
    # Check for tolerance matching
    if 'tolerance' in req_specs and 'tolerance' in cap_specs:
        req_tol = self._parse_tolerance(req_specs['tolerance'])
        cap_tol = self._parse_tolerance(cap_specs['tolerance'])
        
        if req_tol and cap_tol:
            # Capability tolerance should be equal or better (smaller)
            if cap_tol <= req_tol:
                return True
    
    # Check for dimension matching (within reasonable range)
    if 'dimensions' in req_specs and 'dimensions' in cap_specs:
        req_dims = req_specs['dimensions']
        cap_dims = cap_specs['dimensions']
        
        if self._dimensions_compatible(req_dims, cap_dims):
            return True
    
    return False

def _extract_materials(self, obj) -> List[str]:
    """Extract material names from requirement or capability."""
    materials = []
    
    if hasattr(obj, 'materials') and obj.materials:
        if isinstance(obj.materials, list):
            materials.extend(obj.materials)
        elif isinstance(obj.materials, str):
            materials.append(obj.materials)
    
    if hasattr(obj, 'parameters') and obj.parameters:
        if 'materials' in obj.parameters:
            mats = obj.parameters['materials']
            if isinstance(mats, list):
                materials.extend(mats)
            elif isinstance(mats, str):
                materials.append(mats)
    
    return materials

def _parse_tolerance(self, tolerance_str: str) -> Optional[float]:
    """Parse tolerance string to float value."""
    import re
    try:
        # Extract numeric value from tolerance string (e.g., "±0.1mm" -> 0.1)
        match = re.search(r'[\d.]+', str(tolerance_str))
        if match:
            return float(match.group())
    except (ValueError, AttributeError):
        pass
    return None

def _dimensions_compatible(self, req_dims: Any, cap_dims: Any) -> bool:
    """Check if dimensions are compatible (within 10% difference)."""
    try:
        # Simple compatibility check - can be enhanced
        if isinstance(req_dims, dict) and isinstance(cap_dims, dict):
            # Check if key dimensions match
            for key in ['width', 'length', 'height', 'diameter']:
                if key in req_dims and key in cap_dims:
                    req_val = float(req_dims[key])
                    cap_val = float(cap_dims[key])
                    # Within 10% difference
                    if abs(req_val - cap_val) / max(req_val, cap_val) <= 0.1:
                        return True
    except (ValueError, TypeError, KeyError):
        pass
    return False
```

**Update `_create_substitution` to use enhanced confidence:**

```python
def _create_substitution(self, 
                      requirement: OKHRequirement,
                      capability: Capability) -> Any:
    """Create a substitution record with confidence scoring"""
    # Start with base confidence
    confidence = 0.7
    
    # Boost confidence for explicit substitution
    if 'substitutes_for' in capability.parameters:
        confidence = 0.9
    
    # Adjust based on matching factors
    factors_matched = 0
    if self._check_material_compatibility(requirement, capability):
        factors_matched += 1
    if self._check_process_similarity(requirement, capability):
        factors_matched += 1
    if self._check_tool_compatibility(requirement, capability):
        factors_matched += 1
    if self._check_specification_match(requirement, capability):
        factors_matched += 1
    
    # Increase confidence based on number of matching factors
    if factors_matched >= 3:
        confidence = min(0.95, confidence + 0.15)
    elif factors_matched >= 2:
        confidence = min(0.90, confidence + 0.10)
    elif factors_matched >= 1:
        confidence = min(0.85, confidence + 0.05)
    
    # Use explicit confidence if provided
    if 'substitutes_for' in capability.parameters:
        substitutes = capability.parameters['substitutes_for']
        if isinstance(substitutes, dict) and requirement.name in substitutes:
            if 'confidence' in substitutes[requirement.name]:
                confidence = substitutes[requirement.name]['confidence']
    
    return Substitution(
        original=requirement,
        substitute=capability,
        confidence=confidence,
        constraints=capability.limitations,
        notes=f"Substitute {capability.name} for {requirement.name} (matched {factors_matched} factors)"
    )
```

### 2. Documentation Files Parsing

**File: `src/core/generation/platforms/local_git.py`**

**Add `_build_documentation_list` method:**

```python
def _build_documentation_list(self, files: List[FileInfo]) -> List[DocumentInfo]:
    """
    Build documentation list from files.
    
    Parses documentation files and creates DocumentInfo objects.
    Identifies documentation types based on filename, path, and content.
    
    Args:
        files: List of FileInfo objects from repository
        
    Returns:
        List of DocumentInfo objects
    """
    documentation = []
    documentation_patterns = {
        # README files
        r"(?i)^readme(\.(md|txt|rst))?$": "documentation-home",
        r"(?i)readme": "documentation-home",
        
        # Manual files
        r"(?i)(manual|guide|instructions?)(\.(md|txt|pdf|docx?))?$": "making-instructions",
        r"(?i)^(assembly|build|making|fabrication)(\.(md|txt))?$": "making-instructions",
        
        # Operating instructions
        r"(?i)(user[_\s]?manual|operating[_\s]?guide|usage)(\.(md|txt|pdf))?$": "operating-instructions",
        r"(?i)^(how[_\s]?to[_\s]?use|usage)(\.(md|txt))?$": "operating-instructions",
        
        # Technical specifications
        r"(?i)(spec|specification|technical[_\s]?spec)(\.(md|txt|pdf))?$": "technical-specifications",
        r"(?i)^(dimensions?|tolerances?)(\.(md|txt|csv))?$": "technical-specifications",
        
        # Maintenance
        r"(?i)(maintenance|repair|servicing)(\.(md|txt|pdf))?$": "maintenance-instructions",
        
        # Disposal
        r"(?i)(disposal|recycling|end[_\s]?of[_\s]?life)(\.(md|txt|pdf))?$": "disposal-instructions",
        
        # Risk assessment
        r"(?i)(risk[_\s]?assessment|safety|hazard)(\.(md|txt|pdf))?$": "risk-assessment",
    }
    
    # Documentation directories
    documentation_dirs = {
        "docs/": "documentation-home",
        "documentation/": "documentation-home",
        "manual/": "making-instructions",
        "manuals/": "making-instructions",
        "guides/": "making-instructions",
        "instructions/": "making-instructions",
    }
    
    for file_info in files:
        # Skip non-documentation file types
        if file_info.file_type not in ["markdown", "document", "text"]:
            continue
        
        file_path = Path(file_info.path)
        file_name = file_path.name.lower()
        file_dir = str(file_path.parent).lower() + "/"
        
        # Determine documentation type
        doc_type = None
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        
        # Check directory patterns first
        for dir_pattern, type_name in documentation_dirs.items():
            if dir_pattern in file_dir:
                doc_type = type_name
                break
        
        # Check filename patterns
        if not doc_type:
            for pattern, type_name in documentation_patterns.items():
                if re.match(pattern, file_name):
                    doc_type = type_name
                    break
        
        # Default to making-instructions if in docs directory
        if not doc_type and ("docs/" in file_dir or "documentation/" in file_dir):
            doc_type = "making-instructions"
        
        # Skip if not identified as documentation
        if not doc_type:
            continue
        
        # Extract title from content if available
        if file_info.content:
            # Try to extract title from first heading
            title_match = re.search(r'^#+\s+(.+)$', file_info.content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
            # Or from first line if no heading
            elif file_info.content.strip():
                first_line = file_info.content.strip().split('\n')[0]
                # Remove markdown formatting
                first_line = re.sub(r'^#+\s*', '', first_line)
                first_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', first_line)
                if len(first_line) < 100:  # Reasonable title length
                    title = first_line.strip()
        
        # Limit content size for very large files
        content = file_info.content or ""
        max_content_size = 50000  # 50KB limit
        if len(content) > max_content_size:
            content = content[:max_content_size] + "\n\n... (truncated)"
        
        documentation.append(DocumentInfo(
            title=title,
            path=file_info.path,
            doc_type=doc_type,
            content=content
        ))
    
    return documentation
```

**Update `extract_project` method:**

```python
# In extract_project method, replace:
documentation=[],  # TODO: Parse documentation files

# With:
documentation=self._build_documentation_list(files),
```

**Add import:**

```python
import re
from pathlib import Path
```

### 3. JSON/YAML BOM Parsing

**File: `src/core/generation/bom_models.py`**

**Update `_extract_components_from_structured` method:**

```python
def _extract_components_from_structured(self, content: str, source: BOMSource) -> List['Component']:
    """
    Extract components from structured formats (JSON, YAML).
    
    Supports multiple BOM schemas:
    - Array of component objects: [{"name": "...", "quantity": ...}, ...]
    - Object with components array: {"components": [...], ...}
    - Object with parts array: {"parts": [...], ...}
    - Object with items array: {"items": [...], ...}
    
    Args:
        content: File content as string
        source: BOMSource object with file metadata
        
    Returns:
        List of Component objects
    """
    file_path = source.file_path.lower()
    components = []
    
    try:
        # Parse JSON or YAML
        if file_path.endswith('.json'):
            import json
            data = json.loads(content)
        elif file_path.endswith(('.yaml', '.yml')):
            import yaml
            data = yaml.safe_load(content)
        else:
            # Unknown format, fallback to markdown
            return self._extract_components_from_markdown(content, source)
        
        if not data:
            return []
        
        # Extract components array from different schema formats
        components_data = None
        
        if isinstance(data, list):
            # Array of components
            components_data = data
        elif isinstance(data, dict):
            # Object with components array
            for key in ['components', 'parts', 'items', 'materials', 'bom']:
                if key in data and isinstance(data[key], list):
                    components_data = data[key]
                    break
            
            # If no array found, try to extract from dict values
            if not components_data:
                # Check if dict values are component objects
                if all(isinstance(v, dict) for v in data.values()):
                    components_data = list(data.values())
        
        if not components_data:
            # Couldn't find components, fallback to markdown
            logger.warning(f"Could not find components array in structured BOM: {source.file_path}")
            return self._extract_components_from_markdown(content, source)
        
        # Parse each component
        for comp_data in components_data:
            if not isinstance(comp_data, dict):
                continue
            
            component = self._parse_component_from_dict(comp_data, source)
            if component:
                components.append(component)
        
        return components
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON BOM {source.file_path}: {e}")
        return self._extract_components_from_markdown(content, source)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML BOM {source.file_path}: {e}")
        return self._extract_components_from_markdown(content, source)
    except Exception as e:
        logger.warning(f"Error parsing structured BOM {source.file_path}: {e}", exc_info=True)
        return self._extract_components_from_markdown(content, source)

def _parse_component_from_dict(self, comp_data: Dict[str, Any], source: BOMSource) -> Optional['Component']:
    """
    Parse a single component from dictionary data.
    
    Supports various field name variations:
    - Name: name, item, component, part, id, title
    - Quantity: quantity, qty, amount, count, number
    - Unit: unit, units, measure, uom
    - Description: description, desc, notes, comment
    
    Args:
        comp_data: Dictionary with component data
        source: BOMSource object
        
    Returns:
        Component object or None if parsing fails
    """
    from ...models.bom import Component
    
    # Extract name
    name = None
    for key in ['name', 'item', 'component', 'part', 'id', 'title']:
        if key in comp_data and comp_data[key]:
            name = str(comp_data[key]).strip()
            break
    
    if not name:
        return None
    
    # Extract quantity
    quantity = 1.0
    for key in ['quantity', 'qty', 'amount', 'count', 'number']:
        if key in comp_data:
            try:
                quantity = float(comp_data[key])
                break
            except (ValueError, TypeError):
                continue
    
    # Extract unit
    unit = "pcs"
    for key in ['unit', 'units', 'measure', 'uom']:
        if key in comp_data and comp_data[key]:
            unit = str(comp_data[key]).strip()
            break
    
    # Extract description/notes
    description = None
    for key in ['description', 'desc', 'notes', 'comment', 'note']:
        if key in comp_data and comp_data[key]:
            description = str(comp_data[key]).strip()
            break
    
    # Extract metadata (all other fields)
    metadata = {k: v for k, v in comp_data.items() 
                if k not in ['name', 'item', 'component', 'part', 'id', 'title',
                            'quantity', 'qty', 'amount', 'count', 'number',
                            'unit', 'units', 'measure', 'uom',
                            'description', 'desc', 'notes', 'comment', 'note']}
    
    # Generate component ID
    component_id = self._generate_component_id(name)
    
    # Create component
    return Component(
        id=component_id,
        name=name,
        quantity=quantity,
        unit=unit,
        description=description,
        source=source.file_path,
        metadata=metadata
    )
```

**Add imports:**

```python
import json
import yaml
from typing import Dict, Any, Optional
```

## Integration Points

### 1. Substitution Rules

- Integrates with existing matching logic
- Uses existing Requirement and Capability models
- Works with existing substitution creation

### 2. Documentation Parsing

- Uses existing DocumentInfo model
- Follows same pattern as GitLab/GitHub extractors
- Integrates with ProjectData structure

### 3. BOM Parsing

- Uses existing Component model
- Integrates with existing BOM processing pipeline
- Falls back to markdown parsing on error

## Testing Considerations

### Unit Tests

1. **Substitution Rules Tests:**
   - Test material compatibility
   - Test process similarity
   - Test tool compatibility
   - Test specification matching
   - Test confidence scoring

2. **Documentation Parsing Tests:**
   - Test README identification
   - Test manual/guide identification
   - Test directory-based identification
   - Test title extraction
   - Test content truncation

3. **BOM Parsing Tests:**
   - Test JSON array format
   - Test JSON object with components array
   - Test YAML formats
   - Test field name variations
   - Test error handling and fallback

### Integration Tests

1. **End-to-End Substitution:**
   - Test substitution in matching workflow
   - Test confidence scores in results

2. **End-to-End Documentation:**
   - Test documentation parsing in project extraction
   - Test documentation in OKH manifest generation

3. **End-to-End BOM:**
   - Test structured BOM parsing in BOM collection
   - Test component extraction accuracy

## Migration Plan

### Phase 1: Implementation (Current)
- Implement enhanced substitution rules
- Implement documentation parsing
- Implement JSON/YAML BOM parsing

### Phase 2: Enhancement (Future)
- Add more substitution rules
- Add substitution rule configuration files
- Add more BOM schema support
- Add documentation type detection improvements

## Success Criteria

1. ✅ Substitution rules check multiple factors
2. ✅ Documentation files are parsed into DocumentInfo objects
3. ✅ JSON/YAML BOM files are properly parsed
4. ✅ All TODOs are resolved
5. ✅ Tests pass
6. ✅ Backward compatibility maintained

## Open Questions / Future Enhancements

1. **Substitution Rules:**
   - Should rules be configurable via files?
   - Should we support user-defined substitution rules?
   - Should we use ML for substitution detection?

2. **Documentation Parsing:**
   - Should we use LLM for better type detection?
   - Should we support more documentation formats?
   - Should we extract structured metadata from docs?

3. **BOM Parsing:**
   - Should we support more BOM schemas?
   - Should we validate BOM structure?
   - Should we support BOM templates?

## Dependencies

### Existing Dependencies

- `json` - JSON parsing (stdlib)
- `yaml` - YAML parsing (PyYAML already in requirements)
- `re` - Regular expressions (stdlib)
- `pathlib` - Path handling (stdlib)

### No New Dependencies

- Uses only existing libraries

## Implementation Order

1. Implement enhanced substitution rules
2. Implement documentation parsing
3. Implement JSON/YAML BOM parsing
4. Write unit tests
5. Write integration tests
6. Update documentation

