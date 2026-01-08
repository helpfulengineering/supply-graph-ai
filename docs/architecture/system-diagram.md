# System Diagram

```mermaid
flowchart TD
    subgraph inputs[Input Sources]
        I1[Requirements Input\ne.g., OKH, Recipe]
        I2[Capabilities Input\ne.g., OKW, Kitchen]
    end

    subgraph domain_mgmt[Domain Management System]
        DM1[Domain Registry]
        DM2[Domain Detector]
        DM3[Domain Validator]
        DM4[Domain Services]
    end

    subgraph preproc[Pre-processing & Validation]
        V1[Schema Validation]
        V2[Format Checking]
        V3[Required Fields Validation]
        V4[Data Type Validation]
        V5[Domain Detection]
        V6[Domain Validation]
    end

    subgraph extraction[Extraction Pipeline]
        EP1[Initial Parsing]
        EP2[Domain-Specific\nParsing]
        
        subgraph ext_layers[Extraction Layers]
            EL1[Exact Extraction]
            EL2[Heuristic Extraction]
            EL3[NLP Extraction]
            EL4[AI/ML Extraction]
        end
        
        ER1[Extraction Results]
    end

    subgraph storage[Data Storage]
        subgraph permanent[Permanent Storage]
            PS1[Structured Data Store\nValidated OKH Files]
        end
        
        subgraph cache[Cache Layer]
            C1[Confidence Scores]
            C2[Validation Flags]
        end
    end

    subgraph feedback[Feedback System]
        F1[Auto-generated Feedback]
        F2[Human Feedback]
        F3[Feedback API]
    end

    subgraph matching[Matching Pipeline]
        MP1[Requirements\nPreparation]
        MP2[Capabilities\nPreparation]
        
        subgraph match_layers[Matching Layers]
            ML1[Exact Matching]
            ML2[Heuristic Matching]
            ML3[NLP Matching]
            ML4[AI/ML Matching]
        end
        
        MR1[Match Results]
        subgraph match_output[Matching Output]
            MO1[Matches]
            MO2[Confidence Scores]
            MO3[Alternative Suggestions]
            MO4[Required Human Review Flags]
        end
    end

    subgraph actions[Action Layer]
        A1[Automatic Actions]
        A2[Human Review Queue]
        A3[Feedback Loop]
    end

    %% Input to Domain Management flow
    I1 & I2 --> DM2
    DM2 --> DM3
    DM3 --> DM1
    DM1 --> DM4
    
    %% Input to Extraction flow
    I1 & I2 --> V1
    V1 --> V2
    V2 --> V3
    V3 --> V4
    V4 --> V5
    V5 --> V6
    V6 --> EP1
    EP1 --> EP2
    EP2 --> EL1
    EL1 --> EL2
    EL2 --> EL3
    EL3 --> EL4
    EL4 --> ER1
    
    %% Domain Management to Extraction
    DM4 -.->|Domain Services| EP2

    %% Extraction Results to Storage and Feedback
    ER1 --> PS1
    ER1 --> C1
    ER1 --> C2
    ER1 --> F1

    %% Storage to Matching flow
    PS1 --> MP1
    C1 & C2 -.->|Optional| MP1
    DM4 -.->|Domain Services| MP1
    
    %% Matching flow
    MP1 & MP2 --> ML1
    ML1 --> ML2
    ML2 --> ML3
    ML3 --> ML4
    ML4 --> MR1
    MR1 --> MO1 & MO2 & MO3 & MO4
    
    %% Actions and Feedback flow
    MO1 & MO2 & MO3 & MO4 --> A1 & A2
    A2 --> A3
    A3 --> F2
    F1 & F2 --> F3

    
    class inputs,preproc,extraction,matching pipeline
    class ext_layers,match_layers layer
    class permanent storage
    class cache cache
    class feedback feedback
    class match_output output
    class actions action
    class domain_mgmt domain
```