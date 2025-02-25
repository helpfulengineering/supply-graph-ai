# Data Flow Diagram

```mermaid
flowchart TD
    %% Input Data Objects
    D1[Raw Input\nUnstructured/Semi-structured\nText, YAML, JSON, etc.]
    D2[Validated Input\nSchema-compliant\nType-checked]
    
    %% Extraction Data Objects
    E1[Basic Structure\nKey-Value Pairs\nHierarchical Relations]
    E2[Domain Objects\nTyped Fields\nNormalized Values]
    
    %% Extraction Layer Results
    EL1[Exact Extraction Result\n- Direct Mappings\n- High Confidence Fields]
    EL2[Heuristic Extraction Result\n- Pattern Matches\n- Field Inferences]
    EL3[NLP Extraction Result\n- Semantic Relations\n- Context Analysis]
    EL4[ML Extraction Result\n- Complex Pattern Recognition\n- Uncertainty Quantification]
    
    %% Composite Extraction Result
    ER1[Composite Extraction Object\n- Merged Layer Results\n- Confidence Scores\n- Validation Status]

    %% Matching Pipeline Data
    M1[Requirements Profile\n- Required Capabilities\n- Constraints\n- Quality Specs]
    M2[Capability Profile\n- Available Resources\n- Capacity\n- Certifications]

    %% Matching Layer Results
    ML1[Exact Match Result\n- Direct Capability Matches\n- Binary Match Flags]
    ML2[Heuristic Match Result\n- Alternative Matches\n- Substitution Options]
    ML3[NLP Match Result\n- Semantic Similarity Scores\n- Context-Based Matches]
    ML4[ML Match Result\n- Probabilistic Matches\n- Complex Compatibility]

    %% Final Results
    R1[Match Results\n- Primary Matches\n- Alternatives\n- Confidence Scores]
    R2[Action Items\n- Required Reviews\n- Automation Tasks\n- Feedback Points]

    %% Data Transformations
    D1 -->|Validation & Type Checking| D2
    D2 -->|Basic Parsing| E1
    E1 -->|Domain-Specific Parsing| E2

    %% Extraction Layer Flow
    E2 -->|Direct Field Mapping| EL1
    E2 -->|Rule-Based Analysis| EL2
    E2 -->|Text Analysis| EL3
    E2 -->|Pattern Learning| EL4

    %% Extraction Results Merge
    EL1 & EL2 & EL3 & EL4 -->|Result Aggregation| ER1

    %% Profile Creation
    ER1 -->|Profile Generation| M1
    ER1 -->|Profile Generation| M2

    %% Matching Layer Flow
    M1 & M2 -->|Direct Comparison| ML1
    M1 & M2 -->|Rule Application| ML2
    M1 & M2 -->|Semantic Analysis| ML3
    M1 & M2 -->|ML Analysis| ML4

    %% Results Aggregation
    ML1 & ML2 & ML3 & ML4 -->|Result Aggregation| R1
    R1 -->|Action Generation| R2

    %% Feedback Loop
    R2 -->|Feedback Integration| D1

    classDef input fill:#e3f2fd,stroke:#1565c0
    classDef extract fill:#fff3e0,stroke:#ef6c00
    classDef match fill:#f3e5f5,stroke:#6a1b9a
    classDef result fill:#e8f5e9,stroke:#2e7d32
    
    class D1,D2 input
    class E1,E2,EL1,EL2,EL3,EL4,ER1 extract
    class M1,M2,ML1,ML2,ML3,ML4 match
    class R1,R2 result
```