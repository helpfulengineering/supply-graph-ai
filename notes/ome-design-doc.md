# Open Matching Engine (OME) Design Document

## Overview
The Open Matching Engine (OME) is a command-line tool designed to match open hardware designs with manufacturing capabilities. It integrates with two existing standards:
- Open Know-How (OKH): A standard for documenting open hardware designs
- Open Know-Where (OKW): A standard for documenting manufacturing capabilities

The primary function of OME is to generate "Supply Trees" - directed acyclic graphs (DAGs) representing possible manufacturing solutions for a given hardware design.

## Core Components

### 1. Supply Tree
The central data structure representing a manufacturing solution. Implemented using NetworkX's DiGraph with the following characteristics:
- Nodes represent manufacturing steps with their requirements
- Edges represent dependencies between steps
- Each node can have multiple candidate facilities
- Each complete path through the graph represents a possible manufacturing solution

### 2. Core Service Layer
```python
@dataclass 
class SupplyTreeRequest:
    okh_data: dict        # Parsed OKH manifest
    okw_facilities: List[dict]  # List of parsed OKW facility data
    quantity: int         # Required production quantity
    deadline: timedelta  # Production deadline
    constraints: Optional[Dict] = None  # Additional constraints

@dataclass
class SupplyTreeSolution:
    graph: nx.DiGraph    # The solution graph
    score: float         # Solution ranking score
    metadata: Dict       # Metrics like cost, time, distance
```

The SupplyTreeService class handles core business logic:
- Parsing OKH/OKW data
- Building manufacturing graphs
- Finding capable facilities
- Generating and ranking solutions

### 3. Manufacturing Process Representation
```python
@dataclass
class OKWManufacturingProcess:
    wikipedia_url: str           # Using OKW's Wikipedia classification
    equipment_required: List[str]
    duration: timedelta
    materials_worked: List[str]

@dataclass 
class OKWFacility:
    id: str
    name: str
    location: dict              # OKW Location class mapping
    equipment: List[str]        # Equipment types using Wikipedia URLs
    processes: List[str]        # Manufacturing processes
    typical_batch_size: str     # Using OKW's defined ranges
    certifications: List[str]
```

### 4. Graph Generation and Analysis
The system uses NetworkX for:
- Topological sorting to respect dependencies
- Path finding to identify possible manufacturing sequences
- Critical path analysis for timing calculations
- Solution validation and scoring

## Implementation Strategy

### Phase 1: Core Functionality
1. Implement OKH/OKW file parsing and validation
2. Build core Supply Tree generation logic
3. Implement basic CLI interface
4. Develop solution ranking system

### Phase 2: Enhanced Analysis
1. Add detailed cost modeling
2. Implement parallel manufacturing paths
3. Add quality constraints and verification
4. Enhance solution scoring metrics

### Phase 3: API Layer
1. Add FastAPI wrapper around core service
2. Implement serialization for NetworkX graphs
3. Add async support for long-running operations
4. Build API documentation

## Technical Decisions

### 1. Technology Stack
- **Python**: Primary implementation language
- **NetworkX**: Graph operations and analysis
- **Click**: CLI interface
- **FastAPI**: Future API implementation
- **Pydantic**: Data validation (future)

### 2. Architecture Patterns
- Clean separation between core logic and interfaces
- Data Transfer Objects for request/response handling
- Service layer pattern for business logic
- Factory pattern for graph generation

### 3. File Formats
- OKH files: JSON/YAML following OKH schema
- OKW files: JSON/YAML following OKW schema
- Solution output: JSON with serialized graph data

## Integration Points

### 1. OKH Integration
- Parse and validate OKH manifests
- Extract manufacturing requirements
- Analyze design files for dependencies

### 2. OKW Integration
- Parse and validate facility data
- Match capabilities to requirements
- Handle facility classification using Wikipedia URLs

### 3. Future Web Interface
- REST API endpoints for all core functions
- Async operations for long-running processes
- Standardized error handling

## Development Guidelines

### 1. Code Organization
```
ome/
├── core/
│   ├── supply_tree.py
│   ├── parsers/
│   └── analysis/
├── cli/
│   └── main.py
├── api/        # Future
│   └── main.py
└── tests/
```

### 2. Testing Strategy
- Unit tests for core components
- Integration tests for parsers
- Graph validation tests
- Performance benchmarks for large graphs

### 3. Documentation
- API documentation using OpenAPI
- CLI help text
- Code documentation following Google Python style
- Examples and tutorials

## Open Questions
1. How to handle ambiguous assembly instructions?
2. Best practices for NLP analysis of manufacturing requirements?
3. Optimization strategies for large facility databases?
4. Metrics for ranking manufacturing solutions?

## Next Steps
1. Implement core Supply Tree data structures
2. Build basic CLI interface
3. Develop OKH/OKW parsers
4. Create solution generation algorithm
5. Add basic solution ranking