# Facility Specialization Logic

**Version**: 1.0  
**Status**: Design Document  
**Date**: 2024  
**Related**: [Demo Data Plan](./demo-data-plan.md)

---

## Current Facility Generation Logic

### How It Works Now

The current `OKWGenerator.generate_manufacturing_facility()` method:

1. **Selects a random template** from `facility_templates`:
   ```python
   template = random.choice(self.facility_templates)
   ```

2. **Each template has multiple equipment types**:
   - "Community Makerspace": `["3D printer", "Laser cutter", "CNC router"]`
   - "Professional Machine Shop": `["CNC mill", "CNC lathe", "Surface grinder"]`
   - "Industrial Manufacturing Plant": `["CNC mill", "CNC lathe", "Sheet metal brake", "Welder"]`

3. **Generates equipment for each type**:
   ```python
   for equipment_type in template["equipment_types"]:
       facility.equipment.append(self.generate_equipment(equipment_type))
   ```

4. **Maps equipment to manufacturing processes**:
   ```python
   facility.manufacturing_processes = [
       f"https://en.wikipedia.org/wiki/{process.replace(' ', '_')}" 
       for process in template["equipment_types"]
   ]
   ```

### Problem with Current Approach

**Issue**: Facilities are "jack-of-all-trades" - they have multiple capabilities, which means:
- A single facility might be able to handle an entire simple product
- Doesn't force multi-facility coordination
- Not realistic (real facilities often specialize)

**Example**:
- "Community Makerspace" can do 3D printing, laser cutting, AND CNC routing
- A simple product needing just 3D printing could be fully produced there
- No need for nested matching or multi-facility coordination

---

## Matching Service Logic

### How Matching Works

The matching service matches based on:

1. **OKH Process Requirements**:
   - From `okh_manifest.manufacturing_processes` (list of process names)
   - From component `requirements.process` (component-specific)
   - From component `metadata.tsdc` (component-specific)

2. **Facility Capabilities**:
   - From `facility.manufacturing_processes` (list of Wikipedia URLs)
   - From `equipment.manufacturing_process` (per equipment)

3. **Matching Algorithm**:
   ```python
   # For each process requirement:
   for process_name in process_requirements:
       # Check if facility has matching equipment/process
       for equipment in facility.equipment:
           if process_matches(process_name, equipment.manufacturing_process):
               confidence += 1
   ```

4. **Process Normalization**:
   - Processes are normalized to Wikipedia URLs
   - "3DP" → "https://en.wikipedia.org/wiki/Fused_filament_fabrication"
   - "CNC" → "https://en.wikipedia.org/wiki/Machining"
   - "PCB" → "https://en.wikipedia.org/wiki/Printed_circuit_board"

---

## Specialized Facility Strategy

### Goal

Create facilities that:
1. **Specialize in ONE primary process** (with maybe 1-2 related processes)
2. **Cannot individually fulfill complex products** (forces coordination)
3. **Together can fulfill complete requests** (complementary capabilities)

### Specialization Approach

#### Option 1: Single-Process Specialization (Recommended)

Each facility specializes in ONE primary process:

```python
specialized_templates = [
    {
        "name": "PCB Fabrication Facility Alpha",
        "primary_process": "PCB",
        "equipment_types": ["PCB printer", "Etching tank", "Drilling machine"],
        "related_processes": [],  # Pure specialization
        "batch_size": BatchSize.MEDIUM,
    },
    {
        "name": "Electronics Assembly Facility Beta",
        "primary_process": "Electronics Assembly",
        "equipment_types": ["Pick and place", "Reflow oven", "AOI"],
        "related_processes": ["Testing"],  # Related but distinct
        "batch_size": BatchSize.SMALL,
    },
    {
        "name": "CNC Machining Facility Gamma",
        "primary_process": "CNC",
        "equipment_types": ["CNC mill", "CNC lathe"],
        "related_processes": ["Deburring"],
        "batch_size": BatchSize.MEDIUM,
    },
]
```

**Benefits**:
- Clear specialization
- Forces multi-facility coordination
- Realistic (matches real-world facilities)

**Implementation**:
```python
def generate_specialized_facility(
    self,
    specialization: str,  # "PCB", "CNC", "3DP", etc.
    facility_name: Optional[str] = None
) -> ManufacturingFacility:
    """Generate a facility specialized in a specific process"""
    # Get specialization template
    template = self.get_specialization_template(specialization)
    
    # Generate facility with ONLY that specialization
    facility = ManufacturingFacility(...)
    
    # Add equipment for primary process only
    for equipment_type in template["equipment_types"]:
        facility.equipment.append(self.generate_equipment(equipment_type))
    
    # Set manufacturing processes (primary + related only)
    facility.manufacturing_processes = [
        self.process_to_url(template["primary_process"])
    ]
    for related in template["related_processes"]:
        facility.manufacturing_processes.append(self.process_to_url(related))
    
    return facility
```

#### Option 2: Limited Multi-Process (Alternative)

Facilities have 2-3 related processes (but not everything):

```python
limited_templates = [
    {
        "name": "Electronics Manufacturing Hub",
        "processes": ["PCB", "Electronics Assembly"],  # Related processes
        "equipment_types": ["PCB printer", "Pick and place", "Reflow oven"],
    },
    {
        "name": "Mechanical Fabrication Shop",
        "processes": ["CNC", "Sheet Metal"],  # Related processes
        "equipment_types": ["CNC mill", "Sheet metal brake"],
    },
]
```

**Benefits**:
- More realistic (some facilities do have related capabilities)
- Still forces coordination for complex products
- Allows some flexibility

---

## Process Mapping Strategy

### Process Name Normalization

We need consistent mapping between:
- **OKH process names**: "3DP", "CNC", "PCB", "LASER", "SHEET"
- **Facility process URLs**: Wikipedia URLs
- **Component requirements**: May use either format

### Process Dictionary

```python
PROCESS_MAPPING = {
    # Short names → Wikipedia URLs
    "3DP": "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
    "3D Printing": "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
    "FDM": "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
    "SLA": "https://en.wikipedia.org/wiki/Stereolithography",
    
    "CNC": "https://en.wikipedia.org/wiki/Machining",
    "CNC Milling": "https://en.wikipedia.org/wiki/Machining",
    "CNC Machining": "https://en.wikipedia.org/wiki/Machining",
    
    "PCB": "https://en.wikipedia.org/wiki/Printed_circuit_board",
    "PCB Fabrication": "https://en.wikipedia.org/wiki/Printed_circuit_board",
    "Circuit Board": "https://en.wikipedia.org/wiki/Printed_circuit_board",
    
    "LASER": "https://en.wikipedia.org/wiki/Laser_cutting",
    "Laser Cutting": "https://en.wikipedia.org/wiki/Laser_cutting",
    
    "SHEET": "https://en.wikipedia.org/wiki/Sheet_metal_forming",
    "Sheet Metal": "https://en.wikipedia.org/wiki/Sheet_metal_forming",
    
    "Electronics Assembly": "https://en.wikipedia.org/wiki/Electronics_manufacturing",
    "Assembly": "https://en.wikipedia.org/wiki/Assembly_line",
    
    # ... more mappings
}
```

### Matching Logic Enhancement

The matching service should:
1. Normalize process names from OKH/components
2. Normalize process URLs from facilities
3. Match using normalized forms
4. Handle partial matches (e.g., "3DP" matches "Fused_filament_fabrication")

---

## Coordination Strategy

### Ensuring Facilities Work Together

To ensure facilities can collectively fulfill requests:

#### 1. Process Coverage Analysis

Before generating facilities, analyze OKH requirements:

```python
def analyze_okh_process_requirements(okh_manifests: List[OKHManifest]) -> Set[str]:
    """Extract all unique process requirements from OKH files"""
    all_processes = set()
    for okh in okh_manifests:
        # From manifest
        all_processes.update(okh.manufacturing_processes or [])
        
        # From components (if BOM is embedded)
        if okh.parts:
            for part in okh.parts:
                if part.tsdc:
                    all_processes.update(part.tsdc)
    
    return all_processes

# Example result: {"PCB", "CNC", "3DP", "LASER", "Assembly", "Sheet Metal"}
```

#### 2. Facility Generation Plan

Generate facilities to cover all required processes:

```python
required_processes = analyze_okh_process_requirements(okh_manifests)
# Result: {"PCB", "CNC", "3DP", "LASER", "Assembly"}

facility_plan = {
    "PCB": 3,  # 3 PCB facilities
    "CNC": 3,  # 3 CNC facilities
    "3DP": 3,  # 3 3D printing facilities
    "LASER": 2,  # 2 Laser cutting facilities
    "Assembly": 2,  # 2 Assembly facilities
}

# Generate facilities according to plan
for process, count in facility_plan.items():
    for i in range(count):
        facility = generator.generate_specialized_facility(process)
        facilities.append(facility)
```

#### 3. Validation

After generation, validate that:
- Each required process has at least 2 facilities (redundancy)
- Complex OKH files require multiple facilities
- All components can be matched to at least one facility

---

## Implementation Plan

### Step 1: Add Specialization Templates

```python
class OKWGenerator:
    def __init__(self, ...):
        # ... existing code ...
        
        # NEW: Specialized facility templates
        self.specialized_templates = {
            "PCB": {
                "name_prefix": "PCB Fabrication Facility",
                "equipment_types": ["PCB printer", "Etching tank", "Drilling machine"],
                "related_processes": [],
                "batch_size": BatchSize.MEDIUM,
            },
            "CNC": {
                "name_prefix": "CNC Machining Facility",
                "equipment_types": ["CNC mill", "CNC lathe"],
                "related_processes": ["Deburring"],
                "batch_size": BatchSize.MEDIUM,
            },
            # ... more specializations
        }
```

### Step 2: Add Specialized Generation Method

```python
def generate_specialized_facility(
    self,
    specialization: str,
    facility_index: int = 1
) -> ManufacturingFacility:
    """Generate a facility specialized in a specific process"""
    if specialization not in self.specialized_templates:
        raise ValueError(f"Unknown specialization: {specialization}")
    
    template = self.specialized_templates[specialization]
    
    # Generate facility name
    facility_name = f"{template['name_prefix']} {facility_index}"
    
    # Generate facility with specialization
    facility = ManufacturingFacility(
        name=facility_name,
        location=self.generate_location(),
        facility_status=FacilityStatus.ACTIVE,
        access_type=random.choice([AccessType.PUBLIC, AccessType.MEMBERSHIP, AccessType.RESTRICTED]),
        description=f"Specialized {specialization} manufacturing facility"
    )
    
    # Add equipment for primary process
    for equipment_type in template["equipment_types"]:
        facility.equipment.append(self.generate_equipment(equipment_type))
    
    # Set manufacturing processes
    facility.manufacturing_processes = [
        self._process_to_url(specialization)
    ]
    for related in template["related_processes"]:
        facility.manufacturing_processes.append(self._process_to_url(related))
    
    # Set batch size
    facility.typical_batch_size = template["batch_size"]
    
    # ... add other fields ...
    
    return facility

def _process_to_url(self, process: str) -> str:
    """Convert process name to Wikipedia URL"""
    process_mapping = {
        "PCB": "Printed_circuit_board",
        "CNC": "Machining",
        "3DP": "Fused_filament_fabrication",
        "LASER": "Laser_cutting",
        "SHEET": "Sheet_metal_forming",
        "Assembly": "Assembly_line",
        "Electronics Assembly": "Electronics_manufacturing",
    }
    process_key = process_mapping.get(process, process.replace(" ", "_"))
    return f"https://en.wikipedia.org/wiki/{process_key}"
```

### Step 3: Add Coordinated Generation

```python
def generate_coordinated_facilities(
    self,
    required_processes: Dict[str, int],  # {"PCB": 3, "CNC": 3, ...}
    output_dir: str
) -> List[ManufacturingFacility]:
    """Generate a coordinated set of specialized facilities"""
    facilities = []
    
    for process, count in required_processes.items():
        for i in range(1, count + 1):
            facility = self.generate_specialized_facility(process, facility_index=i)
            facilities.append(facility)
    
    return facilities
```

### Step 4: Update Main Generation Logic

```python
# In main() function
if args.type == "okw" and args.specialized:
    # Generate coordinated specialized facilities
    required_processes = {
        "PCB": 3,
        "CNC": 3,
        "3DP": 3,
        "LASER": 2,
        "SHEET": 2,
        "Assembly": 2,
        "Electronics Assembly": 3,
        "Precision Machining": 2,
        "Clean Room Assembly": 1,
    }
    
    facilities = generator.generate_coordinated_facilities(
        required_processes,
        args.output_dir
    )
else:
    # Use existing random generation
    facilities = [generator.generate_manufacturing_facility() for _ in range(args.count)]
```

---

## Example: Medical Ventilator Scenario

### OKH Requirements
- **Processes needed**: PCB, CNC, 3DP, Assembly, Precision Machining

### Generated Facilities
1. **PCB Fabrication Facility 1** (can handle: PCB Board)
2. **PCB Fabrication Facility 2** (can handle: PCB Board - redundancy)
3. **Electronics Assembly Facility 1** (can handle: Microcontroller Module, Display Module)
4. **CNC Machining Facility 1** (can handle: Main Frame, Mounting Brackets)
5. **Precision Machining Facility 1** (can handle: Valve Assembly)
6. **3D Printing Facility 1** (can handle: Tubing Connectors)
7. **Clean Room Assembly Facility 1** (can handle: Final Assembly)

### Matching Result
- **No single facility** can produce the entire ventilator
- **Multiple facilities** are required (forces nested matching)
- **Valid supply tree** with depth > 0 is generated
- **Production sequence** shows dependencies (components before assembly)

---

## Benefits of Specialization

1. **Forces Multi-Facility Coordination**: No single facility can complete complex products
2. **Realistic**: Matches real-world facility specialization
3. **Demonstrates Value**: Shows why nested matching is needed
4. **Clear Dependencies**: Makes production sequences obvious
5. **Better Demo**: More compelling demonstration of system capabilities

---

## Questions to Consider

1. **Should facilities have ANY secondary capabilities?**
   - Option A: Pure specialization (one process only)
   - Option B: Primary + 1-2 related processes
   - **Recommendation**: Option B (more realistic)

2. **How many facilities per process type?**
   - Option A: Fixed count (e.g., always 3)
   - Option B: Based on OKH requirements (dynamic)
   - **Recommendation**: Option B (ensures coverage)

3. **Should we validate coverage?**
   - Check that all OKH process requirements have matching facilities
   - **Recommendation**: Yes, add validation step

4. **Geographic distribution?**
   - Should facilities be in different locations?
   - **Recommendation**: Yes, adds realism and shows location filtering

---

## Next Steps

1. Review and approve specialization approach
2. Implement `generate_specialized_facility()` method
3. Implement `generate_coordinated_facilities()` method
4. Add process mapping/normalization
5. Add validation logic
6. Generate demo facilities
7. Test matching with demo OKH files

