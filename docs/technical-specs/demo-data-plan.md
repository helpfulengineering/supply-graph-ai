# Demo Data Generation Plan

**Version**: 1.0  
**Status**: Planning  
**Date**: 2024  
**Related**: [Nested Supply Tree Generation](./nested-supply-tree-generation.md)

---

## Overview

This document outlines the plan for generating demo data for manual testing of nested supply tree matching. The goal is to create realistic, complex scenarios that demonstrate multi-facility coordination with nested components.

## Objectives

1. **10 Complex OKH Files**: High complexity with nested components (depth 2-4)
2. **Coordinated OKW Facilities**: Facilities that can partially fulfill requests individually but together form valid supply trees
3. **Realistic Scenarios**: Products that require multiple production stages across different facilities
4. **Demo-Ready**: Suitable for conference demonstration

## Demo Scenario Design

### Scenario 1: Medical Ventilator (High Complexity)
**Product**: Emergency medical ventilator for resource-constrained settings

**Components**:
- **Level 0 (Root)**: Complete Ventilator
  - **Level 1**: Control Electronics (PCB + microcontroller)
    - **Level 2**: PCB Board (needs PCB fabrication)
    - **Level 2**: Microcontroller Module (needs electronics assembly)
  - **Level 1**: Mechanical Housing (CNC machined)
    - **Level 2**: Main Frame (needs CNC milling)
    - **Level 2**: Mounting Brackets (needs CNC milling)
  - **Level 1**: Pneumatic System (needs specialized assembly)
    - **Level 2**: Valve Assembly (needs precision machining)
    - **Level 2**: Tubing Connectors (needs injection molding or 3D printing)
  - **Level 1**: Display Module (needs electronics assembly)
  - **Level 1**: Final Assembly (needs clean room assembly)

**Required Facilities**:
- PCB Fabrication Facility (for PCB Board)
- Electronics Assembly Facility (for Microcontroller Module, Display Module)
- CNC Machining Facility (for Main Frame, Mounting Brackets)
- Precision Machining Facility (for Valve Assembly)
- 3D Printing Facility (for Tubing Connectors)
- Clean Room Assembly Facility (for Final Assembly)

### Scenario 2: IoT Sensor Network Hub (Medium-High Complexity)
**Product**: Multi-sensor environmental monitoring hub

**Components**:
- **Level 0**: Sensor Hub
  - **Level 1**: Main Controller Board (PCB + components)
    - **Level 2**: PCB (PCB fabrication)
    - **Level 2**: Sensor Modules (electronics assembly)
  - **Level 1**: Weatherproof Enclosure (sheet metal + assembly)
    - **Level 2**: Enclosure Body (sheet metal fabrication)
    - **Level 2**: Mounting Hardware (CNC machining)
  - **Level 1**: Power System (electronics + mechanical)
    - **Level 2**: Power Board (PCB fabrication)
    - **Level 2**: Battery Holder (3D printing or injection molding)
  - **Level 1**: Final Assembly

**Required Facilities**:
- PCB Fabrication Facility
- Electronics Assembly Facility
- Sheet Metal Fabrication Facility
- CNC Machining Facility
- 3D Printing Facility
- Assembly Facility

### Scenario 3: Open Source Microscope (High Complexity)
**Product**: OpenFlexure-style open source microscope

**Components**:
- **Level 0**: Complete Microscope
  - **Level 1**: Optical System
    - **Level 2**: Lens Mount (3D printing)
    - **Level 2**: Stage Assembly (3D printing + mechanical)
  - **Level 1**: Electronics System
    - **Level 2**: Camera Module (electronics assembly)
    - **Level 2**: Control Board (PCB fabrication + assembly)
  - **Level 1**: Mechanical Base
    - **Level 2**: Base Plate (laser cutting)
    - **Level 2**: Support Structure (3D printing)
  - **Level 1**: Final Assembly

**Required Facilities**:
- 3D Printing Facility (multiple)
- Electronics Assembly Facility
- PCB Fabrication Facility
- Laser Cutting Facility
- Assembly Facility

### Scenario 4-10: Additional Complex Products

**Scenario 4**: Precision Measurement Device
- Requires: PCB, CNC machining, precision assembly

**Scenario 5**: Agricultural Monitoring Station
- Requires: Sheet metal, electronics, 3D printing, assembly

**Scenario 6**: Educational Robot Kit
- Requires: 3D printing, PCB, electronics assembly, CNC (for metal parts)

**Scenario 7**: Water Quality Testing Device
- Requires: Electronics, precision machining, 3D printing, assembly

**Scenario 8**: Solar-Powered IoT Gateway
- Requires: PCB, sheet metal, electronics, assembly

**Scenario 9**: Open Source Spectrometer
- Requires: 3D printing, electronics, precision optics assembly

**Scenario 10**: Modular Lab Equipment
- Requires: Multiple processes, high nesting depth (3-4 levels)

## OKW Facility Strategy

### Facility Specialization Approach

Create facilities that specialize in specific processes, ensuring that:
1. **No single facility can complete the entire product** (forces multi-facility coordination)
2. **Each facility can handle specific component types** (realistic specialization)
3. **Facilities complement each other** (together they can fulfill complete requests)

### Facility Types and Capabilities

#### 1. PCB Fabrication Facility
- **Capabilities**: PCB manufacturing, etching, drilling, soldermask application
- **Equipment**: PCB printer, etching tank, drilling machine
- **Materials**: FR4, copper, solder mask
- **Batch Size**: Medium to Large
- **Can Handle**: PCB boards, circuit boards, electronic substrates

#### 2. Electronics Assembly Facility
- **Capabilities**: Component placement, soldering, testing
- **Equipment**: Pick-and-place machine, reflow oven, soldering station
- **Materials**: Electronic components, solder, flux
- **Batch Size**: Small to Medium
- **Can Handle**: Assembled PCBs, sensor modules, display modules

#### 3. CNC Machining Facility
- **Capabilities**: Precision milling, turning, drilling
- **Equipment**: CNC mill, CNC lathe, precision measuring tools
- **Materials**: Aluminum, steel, plastics
- **Batch Size**: Small to Medium
- **Can Handle**: Frames, brackets, precision mechanical parts

#### 4. 3D Printing Facility
- **Capabilities**: FDM, SLA, SLS printing
- **Equipment**: 3D printers (multiple types), post-processing equipment
- **Materials**: PLA, PETG, TPU, resin
- **Batch Size**: Small
- **Can Handle**: Custom enclosures, brackets, prototypes

#### 5. Sheet Metal Fabrication Facility
- **Capabilities**: Cutting, bending, welding, finishing
- **Equipment**: Laser cutter, sheet metal brake, welder
- **Materials**: Steel, aluminum sheet
- **Batch Size**: Medium to Large
- **Can Handle**: Enclosures, panels, structural components

#### 6. Laser Cutting Facility
- **Capabilities**: Precision cutting, engraving
- **Equipment**: Laser cutter (CO2, fiber)
- **Materials**: Acrylic, wood, thin metals, fabric
- **Batch Size**: Small to Medium
- **Can Handle**: Panels, decorative elements, precise cuts

#### 7. Precision Machining Facility
- **Capabilities**: High-precision machining, tight tolerances
- **Equipment**: Precision CNC, surface grinder, measuring equipment
- **Materials**: Metals, engineering plastics
- **Batch Size**: Small
- **Can Handle**: Valves, precision mechanical components

#### 8. Assembly Facility (General)
- **Capabilities**: Final assembly, quality control, packaging
- **Equipment**: Assembly benches, testing equipment
- **Materials**: Fasteners, adhesives, packaging materials
- **Batch Size**: Small to Medium
- **Can Handle**: Final product assembly

#### 9. Clean Room Assembly Facility
- **Capabilities**: Clean room assembly, medical device assembly
- **Equipment**: Clean room, specialized assembly tools
- **Materials**: Medical-grade materials
- **Batch Size**: Small
- **Can Handle**: Medical devices, sensitive electronics

#### 10. Injection Molding Facility (Optional)
- **Capabilities**: Plastic injection molding
- **Equipment**: Injection molding machine, molds
- **Materials**: Engineering plastics
- **Batch Size**: Large
- **Can Handle**: High-volume plastic components

### Facility Distribution Strategy

For each demo scenario, create:
- **2-3 facilities per process type** (allows for comparison and redundancy)
- **Geographic diversity** (different locations to show multi-location coordination)
- **Varied access types** (public, membership, restricted - shows access control)
- **Different batch sizes** (shows scalability considerations)

**Total Facilities Needed**: ~25-30 facilities
- 3 PCB facilities
- 3 Electronics assembly facilities
- 3 CNC facilities
- 3 3D printing facilities
- 2 Sheet metal facilities
- 2 Laser cutting facilities
- 2 Precision machining facilities
- 2 Assembly facilities
- 1 Clean room facility
- 1-2 Specialized facilities (injection molding, etc.)

## OKH File Specifications

### Complexity Requirements

Each of the 10 OKH files should have:
- **Nesting Depth**: 2-4 levels
- **Component Count**: 8-20 components total (across all levels)
- **BOM Type**: Mix of embedded and external BOMs
- **Component References**: Some components should reference other OKH files (for reusability)
- **Process Diversity**: Require 3-6 different manufacturing processes

### OKH File Details

| # | Product Name | Depth | Components | Processes | BOM Type | Notes |
|---|--------------|-------|------------|-----------|----------|-------|
| 1 | Medical Ventilator | 3 | 15 | PCB, CNC, 3DP, Assembly | External | High complexity, medical device |
| 2 | IoT Sensor Hub | 2-3 | 12 | PCB, Sheet Metal, 3DP, Assembly | Embedded | Medium-high complexity |
| 3 | Open Source Microscope | 3 | 18 | 3DP, PCB, Laser, Assembly | Mixed | High complexity, optics |
| 4 | Precision Measurement Device | 2-3 | 10 | PCB, CNC, Assembly | Embedded | Precision requirements |
| 5 | Agricultural Monitor | 2-3 | 14 | Sheet Metal, PCB, 3DP, Assembly | External | Weatherproof, outdoor |
| 6 | Educational Robot | 3-4 | 16 | 3DP, PCB, CNC, Assembly | Mixed | Educational, modular |
| 7 | Water Quality Tester | 2-3 | 11 | PCB, Precision Machining, 3DP | Embedded | Precision, chemical resistance |
| 8 | Solar IoT Gateway | 2-3 | 13 | PCB, Sheet Metal, Electronics, Assembly | External | Power management, outdoor |
| 9 | Open Source Spectrometer | 3-4 | 17 | 3DP, Electronics, Precision Optics | Mixed | Optics, precision |
| 10 | Modular Lab Equipment | 4 | 20 | Multiple, high depth | External | Maximum complexity |

### BOM Distribution

- **Embedded BOMs**: 3-4 files (simpler, all-in-one)
- **External BOMs**: 4-5 files (complex, separated)
- **Mixed**: 2-3 files (some embedded, some external references)

## Generation Strategy

### Phase 1: Generate Base OKH Files
1. Generate 10 OKH manifests with nested components
2. Use `generate_okh_manifest_with_nesting()` with varying depths
3. Mix embedded and external BOM formats
4. Include component references where appropriate

### Phase 2: Generate Coordinated OKW Facilities
1. Generate facilities with specific specializations
2. Ensure each facility type has 2-3 instances
3. Vary locations, access types, and capabilities
4. Ensure facilities can collectively fulfill OKH requirements

### Phase 3: Validation
1. Verify each OKH requires multiple facilities
2. Verify facilities can collectively fulfill requirements
3. Test matching to ensure valid supply trees are generated
4. Verify depth > 0 for all scenarios

## Implementation Plan

### Step 1: Create Generation Script
- Extend `generate_synthetic_data.py` with demo-specific functions
- Add facility specialization logic
- Add OKH scenario templates

### Step 2: Generate OKH Files
```bash
python synth/generate_synthetic_data.py \
  --type okh \
  --count 10 \
  --nested \
  --max-depth 4 \
  --complexity complex \
  --output-dir synth/demo-data/okh
```

### Step 3: Generate OKW Facilities
```bash
python synth/generate_synthetic_data.py \
  --type okw \
  --count 30 \
  --specialized \
  --output-dir synth/demo-data/okw
```

### Step 4: Validate and Test
- Run matching tests on each OKH with all facilities
- Verify supply trees have depth > 0
- Verify all components are matched
- Document any issues

## Success Criteria

1. ✅ 10 OKH files generated with depth 2-4
2. ✅ 25-30 OKW facilities generated with specializations
3. ✅ Each OKH requires 3-6 different facilities
4. ✅ All OKH files can generate valid supply trees with depth > 0
5. ✅ Facilities collectively fulfill all component requirements
6. ✅ Demo-ready (suitable for conference presentation)

## Next Steps

1. Review and approve this plan
2. Implement generation script enhancements
3. Generate demo data
4. Validate and test
5. Document demo scenarios

