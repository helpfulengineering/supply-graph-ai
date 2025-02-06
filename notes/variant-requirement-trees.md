# Steel blade requirement that works differently in different contexts
blade_req = ProcessRequirement(
    specification=ExactProcessSpec(
        steps=[...],
        tolerances={"hardness": Range(58, 62, unit="HRC")},
        required_equipment=[...],
        quality_metrics={"edge_retention": "...", "corrosion_resistance": "..."}
    ),
    validation_contexts={
        "surgical": ValidationContext(
            domain="medical",
            standards=["ISO 13485", "ASTM F899"],
            acceptance_criteria={
                "sterility": "surgical_grade",
                "traceability": "full_supply_chain",
                "surface_finish": "mirror"
            },
            validation_procedures={...}
        ),
        "hunting": ValidationContext(
            domain="outdoor_equipment",
            standards=["AISI D2"],
            acceptance_criteria={
                "edge_retention": "high",
                "toughness": "medium",
                "corrosion_resistance": "moderate"
            },
            validation_procedures={...}
        )
    },
    failure_responses={
        "surgical": ValidationFailureResponse(
            severity=1.0,  # Maximum severity
            remediation_options=[],  # No remediation allowed
            blocking=True,  # Fails entire supply tree
            reroute_options=None  # No alternatives
        ),
        "hunting": ValidationFailureResponse(
            severity=0.7,
            remediation_options=["heat_treat_adjust", "surface_refinish"],
            blocking=False,
            reroute_options=["alternative_steel_grade"]
        )
    }
)


---

@dataclass
class ValidationContext:
    """
    Defines the context in which requirements are validated
    
    Examples:
    - Medical device manufacturing (ISO 13485)
    - Aerospace components (AS9100)
    - Food preparation (HACCP)
    - Consumer goods
    """
    domain: str
    standards: List[str]  # Applicable standards in this context
    acceptance_criteria: Dict[str, Any]  # Context-specific thresholds
    validation_procedures: Dict[str, Callable]  # How to validate in this context

@dataclass
class ValidationFailureResponse:
    """
    Defines what happens when validation fails
    """
    severity: float  # 0.0 to 1.0 scale of how serious the failure is
    remediation_options: List[str]  # Possible ways to fix/handle failure
    blocking: bool  # Does this failure block the entire supply tree?
    reroute_options: Optional[List[str]]  # Alternative paths to try

@dataclass
class ProcessRequirement:
    """
    Defines what needs to be true about a process/material/component
    """
    specification: Union[ExactProcessSpec, ProcessConstraints]
    validation_contexts: Dict[str, ValidationContext]  # Different contexts to validate in
    failure_responses: Dict[str, ValidationFailureResponse]  # What happens on failure in each context
    
    def validate(self, context_id: str, actual_state: Any) -> ValidationResult:
        """
        Validate this requirement in a specific context
        """
        context = self.validation_contexts[context_id]
        # Perform validation using context-specific procedures
        # Return result with any failures and their consequences

@dataclass
class ExactProcessSpec:
    """Precise specification of required process"""
    steps: List[ProcessStep]
    tolerances: Dict[str, Range]
    required_equipment: List[ResourceURI]
    quality_metrics: Dict[str, Any]

@dataclass
class ProcessConstraints:
    """Flexible specification with start/end requirements"""
    input_state: Dict[str, any]
    output_state: Dict[str, any]
    allowed_methods: List[str]