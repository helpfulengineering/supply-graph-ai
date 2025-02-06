# Surgical knife specification
surgical_spec = ProcessConstraints(
    input_state={
        "material": "steel",
        "material_grade": {
            "type": "stainless_steel",
            "acceptable_grades": ["440A", "420HC"]  # Medical grade stainless
        },
        "material_certification": "medical_grade",
        "material_traceability": "full_supply_chain"
    },
    output_state={
        "product": "surgical_knife",
        "type": "scalpel",
        "hardness_range": {
            "min": 54,  # HRC scale - slightly lower for corrosion resistance
            "max": 56
        },
        "surface_finish": "mirror",
        "edge_geometry": {
            "angle": "20_degrees",
            "tolerance": "±1_degree"
        },
        "sterility": "surgical_grade"
    },
    allowed_methods=["precision_grinding"]  # Much more restricted manufacturing method
)

# Surgical validation context
surgical_context = ValidationContext(
    domain="medical_devices",
    standards=[
        "ISO 13485",  # Medical devices QMS
        "ASTM F899",  # Standard for stainless steel surgical instruments
        "ISO 7153-1"  # Surgical instruments materials
    ],
    acceptance_criteria={
        "hardness_test": "rockwell_c",
        "minimum_hardness": 54,
        "maximum_hardness": 56,
        "edge_geometry_tolerance": "±1_degree",
        "surface_roughness": "Ra 0.1 μm",
        "material_certification": "required",
        "sterilization_validation": "required",
        "traceability": "full"
    },
    validation_procedures={
        "material_grade": lambda x: x["material_grade"] in ["440A", "420HC"] 
                                  and x["certification"] == "medical_grade",
        "hardness": lambda x: 54 <= x["hardness"] <= 56,
        "surface_finish": lambda x: x["roughness"] <= 0.1,
        "sterility": lambda x: x["sterility_level"] == "surgical_grade"
    }
)

# Surgical validation failure handling
surgical_failure_response = ValidationFailureResponse(
    severity=1.0,  # Maximum severity - any failure is critical
    remediation_options=[],  # No remediation allowed - must pass all requirements
    blocking=True,  # Completely blocks this path
    reroute_options=None  # No alternative paths allowed
)

# Create surgical requirement
surgical_requirement = ProcessRequirement(
    specification=surgical_spec,
    validation_contexts={
        "surgical": surgical_context
    },
    failure_responses={
        "surgical": surgical_failure_response
    }
)

# Now we can demonstrate the mutually exclusive paths:
def validate_knife_requirements(knife_spec: ProcessRequirement, contexts: List[str]) -> Dict[str, bool]:
    """Test if a knife specification is valid in different contexts"""
    results = {}
    for context in contexts:
        try:
            # This would be part of the actual validation logic in the SupplyTree
            if context in knife_spec.validation_contexts:
                context_valid = all(
                    proc(knife_spec.specification.output_state)
                    for proc in knife_spec.validation_contexts[context].validation_procedures.values()
                )
            else:
                context_valid = False
            results[context] = context_valid
        except Exception:
            results[context] = False
    return results

# Testing mutual exclusivity
test_contexts = ["hobby", "surgical"]

hobby_results = validate_knife_requirements(knife_requirement, test_contexts)
surgical_results = validate_knife_requirements(surgical_requirement, test_contexts)

# These should show that each knife is only valid in its intended context
print("Hobby knife validation:", hobby_results)    # Should be valid in hobby, invalid in surgical
print("Surgical knife validation:", surgical_results)  # Should be valid in surgical, invalid in hobby

# In the SupplyTree, this would manifest as different valid paths:
alternative_paths = {
    "hobby_knife": {
        "valid_facilities": ["maker_spaces", "hobby_workshops", "general_manufacturing"],
        "valid_processes": ["stock_removal", "forging"],
        "valid_materials": ["1075", "1084", "1095"]
    },
    "surgical_knife": {
        "valid_facilities": ["medical_device_manufacturers"],
        "valid_processes": ["precision_grinding"],
        "valid_materials": ["440A", "420HC"]
    }
}