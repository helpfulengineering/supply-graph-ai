# Domain Management in Open Matching Engine

## Overview

Domain Management is a critical aspect of the Open Matching Engine (OME) that ensures the system can correctly operate across different domains (such as manufacturing and cooking) while maintaining consistent behavior. This document outlines the comprehensive approach to Domain Management, including selection, validation, tracking, detection, and enrichment.

## Core Domain Management Components

### 1. Domain Selection

Domain Selection involves explicitly choosing which domain to operate in, which affects component selection and validation rules.

```python
class Pipeline:
    def __init__(self, domain: str):
        self.domain = domain
        self.domain_registry = {
            "cooking": {
                "extractor": RecipeExtractor(),
                "matcher": CookingMatcher(),
                "validator": CookingValidator(),
                "visualizer": CookingVisualizer()
            },
            "manufacturing": {
                "extractor": ManufacturingExtractor(),
                "matcher": ManufacturingMatcher(),
                "validator": ManufacturingValidator(),
                "visualizer": ManufacturingVisualizer()
            }
        }
        
        # Initialize components based on domain
        self.extractor = self.domain_registry[domain]["extractor"]
        self.matcher = self.domain_registry[domain]["matcher"]
        self.validator = self.domain_registry[domain]["validator"]
        self.visualizer = self.domain_registry[domain]["visualizer"]
```

### 2. Domain Validation

Domain Validation ensures that operations only occur within valid domains and that cross-domain operations are properly managed.

```python
@dataclass
class ValidationContext:
    """Context-specific validation rules"""
    domain: str  # e.g., "manufacturing", "cooking"
    standards: List[str]
    acceptance_criteria: Dict[str, Any]
    validation_procedures: Dict[str, Callable]

def validate_domain_consistency(requirements, capabilities):
    """Validate that requirements and capabilities are from same domain"""
    req_domain = getattr(requirements, 'domain', None)
    cap_domain = getattr(capabilities, 'domain', None)
    
    if not req_domain or not cap_domain:
        raise ValidationError("Domain information missing")
        
    if req_domain != cap_domain:
        raise DomainMismatchError(
            f"Cannot match requirements from {req_domain} domain "
            f"with capabilities from {cap_domain} domain"
        )
    
    return req_domain
```

### 3. Domain Tracking

Domain Tracking maintains explicit domain information through all stages of processing.

```python
@dataclass
class SupplyTree:
    id: UUID
    domain: str  # Track which domain this tree belongs to
    workflows: Dict[UUID, Workflow]
    connections: List[WorkflowConnection]
    snapshots: Dict[str, ResourceSnapshot]
    creation_time: datetime
    metadata: Dict
    
    def validate_in_context(self, context_id: str = None) -> bool:
        """
        Validate tree in specific context, defaulting to the tree's domain
        """
        context = context_id if context_id else self.domain
        # Validation logic
```

### 4. Domain Detection

Domain Detection automatically identifies the appropriate domain when not explicitly provided.

```python
class DomainDetector:
    """Handles domain detection for ambiguous inputs"""
    
    @classmethod
    def detect_domain(cls, data: Dict) -> str:
        """Detect domain from data structure"""
        domain_scores = {}
        
        # 1. Schema-based detection
        for domain in DomainRegistry.available_domains():
            schema_matcher = DomainRegistry.get_schema_matcher(domain)
            schema_score = schema_matcher.match_score(data)
            domain_scores[domain] = schema_score
        
        # 2. Keyword-based detection
        keyword_scores = cls._keyword_detection(data)
        for domain, score in keyword_scores.items():
            domain_scores[domain] = domain_scores.get(domain, 0) + score
            
        # 3. Structure-based detection
        structure_scores = cls._structure_detection(data)
        for domain, score in structure_scores.items():
            domain_scores[domain] = domain_scores.get(domain, 0) + score
        
        # Return highest scoring domain
        if not domain_scores:
            raise ValueError("Could not detect domain from input data")
            
        return max(domain_scores.items(), key=lambda x: x[1])[0]
```

### 5. Domain Enrichment

Domain Enrichment explicitly adds domain information to data during normalization.

```python
@dataclass
class NormalizedData:
    """Base class for normalized data with explicit domain tracking"""
    domain: str
    source_format: str
    content: Dict
    confidence: float  # Confidence in domain detection
    metadata: Dict = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate this data against domain-specific schema"""
        validator = DomainRegistry.get_validator(self.domain)
        return validator.validate(self.content)
```

## Domain Management Across System Boundaries

### 1. Edge Processing: Unstructured Data Ingestion

At the edges where OME consumes semi-structured data, domain detection is critical:

```python
class OME:
    def process_input(self, input_data: Union[str, Dict], input_type: Optional[str] = None):
        """Process incoming data of unknown domain and format"""
        
        # 1. Determine input format (JSON, YAML, Markdown, etc.)
        if isinstance(input_data, str):
            if input_data.endswith('.json'):
                parsed_data = self._parse_json(input_data)
            elif input_data.endswith('.yaml') or input_data.endswith('.yml'):
                parsed_data = self._parse_yaml(input_data)
            else:
                parsed_data = self._detect_and_parse(input_data)
        else:
            parsed_data = input_data
            
        # 2. Detect domain from content structure
        detected_domain = self._detect_domain(parsed_data)
        
        # 3. Select appropriate extractor based on detected domain
        extractor = self._get_extractor(detected_domain, input_type)
        
        # 4. Extract and normalize to domain-specific objects
        if detected_domain == "manufacturing":
            if input_type == "design":
                return extractor.extract_okh(parsed_data)
            elif input_type == "facility":
                return extractor.extract_okw(parsed_data)
        elif detected_domain == "cooking":
            if input_type == "recipe":
                return extractor.extract_recipe(parsed_data)
            elif input_type == "kitchen":
                return extractor.extract_kitchen(parsed_data)
```

### 2. Core Processing: Domain-Consistent Matching

In the core matching engine, domain consistency is enforced:

```python
class OMEPipeline:
    def process_end_to_end(self, 
                          requirement_data: Union[str, Dict], 
                          capability_data: Union[str, Dict]):
        """Process from raw input through to SupplyTree"""
        
        # 1. Normalize inputs (with domain detection)
        normalized_req = self.process_input(requirement_data)
        normalized_cap = self.process_input(capability_data)
        
        # 2. Ensure domain consistency
        if normalized_req.domain != normalized_cap.domain:
            raise DomainMismatchError(
                f"Cannot match across domains: {normalized_req.domain} vs {normalized_cap.domain}"
            )
        
        domain = normalized_req.domain
        
        # 3. Get domain-specific components for matching
        matcher = DomainRegistry.get_matcher(domain)
        
        # 4. Generate domain-aware SupplyTree
        supply_tree = matcher.generate_supply_tree(
            requirements=normalized_req,
            capabilities=normalized_cap,
            domain=domain  # Explicitly pass domain to all operations
        )
        
        return supply_tree
```

### 3. Domain Registry System

A central registry system for managing domain definitions:

```python
@dataclass
class DomainDefinition:
    """Definition of a domain and its components"""
    name: str
    extractors: Dict[str, Type[BaseExtractor]]
    matchers: Dict[str, Type[BaseMatcher]]
    validators: Dict[str, Type[BaseValidator]]
    standard_contexts: Dict[str, ValidationContext]
    
class DomainRegistry:
    """Central registry for all domain definitions"""
    _domains: Dict[str, DomainDefinition] = {}
    
    @classmethod
    def register_domain(cls, domain_def: DomainDefinition):
        cls._domains[domain_def.name] = domain_def
    
    @classmethod
    def get_domain(cls, name: str) -> DomainDefinition:
        if name not in cls._domains:
            raise ValueError(f"Unknown domain: {name}")
        return cls._domains[name]
    
    @classmethod
    def available_domains(cls) -> List[str]:
        return list(cls._domains.keys())
```

## Domain Detection Methods

### 1. Multi-layered Detection Approach

```python
class DomainDetector:
    @classmethod
    def _keyword_detection(cls, data: Dict) -> Dict[str, float]:
        """Score domains based on domain-specific keywords"""
        manufacturing_keywords = [
            "machining", "tolerance", "material", "equipment", 
            "hardware", "manufacturing", "fabrication"
        ]
        
        cooking_keywords = [
            "recipe", "ingredient", "kitchen", "cooking", 
            "baking", "food", "meal"
        ]
        
        # Count keyword occurrences in data
        text = json.dumps(data).lower()
        manufacturing_score = sum(text.count(kw) for kw in manufacturing_keywords)
        cooking_score = sum(text.count(kw) for kw in cooking_keywords)
        
        return {
            "manufacturing": manufacturing_score,
            "cooking": cooking_score
        }
    
    @classmethod
    def _structure_detection(cls, data: Dict) -> Dict[str, float]:
        """Score domains based on structure patterns"""
        scores = {}
        
        # Manufacturing signatures
        if any(key in data for key in ["materials", "processes", "tools", "equipment"]):
            scores["manufacturing"] = scores.get("manufacturing", 0) + 1
            
        # Cooking signatures    
        if any(key in data for key in ["ingredients", "instructions", "cookTime", "prepTime"]):
            scores["cooking"] = scores.get("cooking", 0) + 1
            
        return scores
```

### 2. Handling Detection Uncertainty

```python
class DomainDetectionResult:
    """Results of domain detection with confidence"""
    domain: str
    confidence: float
    alternative_domains: Dict[str, float]  # Other possible domains with scores
    
    def is_confident(self, threshold: float = 0.8) -> bool:
        """Check if detection meets confidence threshold"""
        return self.confidence >= threshold
    
    def get_alternatives(self, min_score: float = 0.4) -> List[str]:
        """Get alternative domains above minimum confidence score"""
        return [
            domain for domain, score in self.alternative_domains.items() 
            if score >= min_score
        ]

class OME:
    def process_with_fallback(self, data, domain_hint: Optional[str] = None):
        """Process data with domain fallback mechanisms"""
        
        # Try using hint first if provided
        if domain_hint:
            try:
                return self.process_in_domain(data, domain_hint)
            except ValidationError:
                # Hint was incorrect, fall back to detection
                pass
        
        # Detect domain
        detection = DomainDetector.detect_domain_with_confidence(data)
        
        # If confident, process with detected domain
        if detection.is_confident():
            return self.process_in_domain(data, detection.domain)
            
        # If uncertain, try alternatives in order
        errors = []
        for alt_domain in detection.get_alternatives():
            try:
                return self.process_in_domain(data, alt_domain)
            except Exception as e:
                errors.append((alt_domain, str(e)))
        
        # If all attempts fail
        raise DomainDetectionError(
            f"Could not confidently determine domain. Best guess: {detection.domain} "
            f"with confidence {detection.confidence}. Errors: {errors}"
        )
```

## Cross-Domain Operations

### 1. Domain Conversion

For cases where cross-domain operations might be needed:

```python
class DomainConverter:
    """Handles conversions between domains when possible"""
    
    @classmethod
    def convert(cls, data: NormalizedData, target_domain: str) -> NormalizedData:
        """Convert data to target domain if possible"""
        source_domain = data.domain
        
        # Check if conversion is supported
        converter_key = f"{source_domain}_to_{target_domain}"
        if converter_key not in cls._converters:
            raise UnsupportedConversionError(
                f"Cannot convert from {source_domain} to {target_domain}"
            )
            
        # Perform conversion
        converter = cls._converters[converter_key]
        return converter(data)
    
    # Register standard converters
    _converters = {
        "cooking_to_manufacturing": lambda data: cls._cooking_to_manufacturing(data),
        "manufacturing_to_cooking": lambda data: cls._manufacturing_to_cooking(data),
    }
```

### 2. Domain Translation Layer

```python
class DomainTranslator:
    """Handles translation between domains for similar concepts"""
    
    @classmethod
    def translate_requirement(cls, req: BaseRequirement, 
                             source_domain: str, target_domain: str) -> BaseRequirement:
        """Translate a requirement from one domain to another"""
        # Implementation
        
    @classmethod
    def translate_supply_tree(cls, tree: SupplyTree, target_domain: str) -> SupplyTree:
        """Translate an entire supply tree to a new domain"""
        # Implementation
```

## Domain Configuration

Domain definitions can be configured through YAML:

```yaml
domains:
  - name: cooking
    extractors:
      - RecipeExtractor
      - KitchenExtractor
    matchers:
      - ExactMatcher
      - HeuristicMatcher
    validators:
      - IngredientValidator
      - ProcessValidator
    contexts:
      - home_cooking
      - professional_kitchen
      
  - name: manufacturing
    extractors:
      - OKHExtractor
      - OKWExtractor
    matchers:
      - ExactMatcher
      - HeuristicMatcher
      - NLPMatcher
    validators:
      - MaterialValidator
      - ProcessValidator
      - QualityValidator
    contexts:
      - hobby
      - professional
      - medical
```

## Best Practices for Domain Management

1. **Explicit Domain Propagation**: Ensure domain information is explicit in all data structures and passed through all pipeline stages.

2. **Multi-stage Detection**: Use progressively more complex detection methods based on need:
   - First: Check for explicit domain information
   - Second: Apply schema validation to determine domain
   - Third: Use content analysis (keywords, structure)
   - Fourth: Try processing with multiple domains and select the one that succeeds

3. **Domain Verification at Boundaries**: Verify domain consistency at system boundaries:

   ```python
   def match(self, requirements, capabilities):
       # Ensure consistent domain at matching boundaries
       req_domain = getattr(requirements, 'domain', None)
       cap_domain = getattr(capabilities, 'domain', None)
       
       if req_domain and cap_domain and req_domain != cap_domain:
           # Handle domain mismatch
           if self.can_convert(cap_domain,