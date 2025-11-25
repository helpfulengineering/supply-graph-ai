"""
Common validation utilities for model dataclasses.

This module provides standardized validation functions that:
1. Parse input data into canonical dataclass instances
2. Validate the dataclass instances
3. Return standardized ValidationResult objects

All validation should reference the canonical dataclass definitions:
- OKHManifest for OKH files
- ManufacturingFacility for OKW files
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import json
from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Standardized validation result for model validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str):
        """Add an error to the validation result"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the validation result"""
        self.warnings.append(warning)
    
    def add_suggestion(self, suggestion: str):
        """Add a suggestion to the validation result"""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "details": self.details
        }
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to API ValidationResult format (from api/models/base.py)"""
        from ..api.models.base import ErrorDetail
        
        # Calculate score based on errors and warnings
        score = 1.0
        if self.errors:
            score = max(0.0, 1.0 - (len(self.errors) * 0.2))
        elif self.warnings:
            score = max(0.5, 1.0 - (len(self.warnings) * 0.1))
        
        error_details = [
            ErrorDetail(
                message=error,
                code="VALIDATION_ERROR",
                field=None
            ) for error in self.errors
        ]
        
        return {
            "is_valid": self.valid,
            "score": score,
            "errors": error_details,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "metadata": self.details
        }


def validate_okh_manifest(
    content: Dict[str, Any],
    quality_level: str = "professional",
    strict_mode: bool = False,
    domain: Optional[str] = None
) -> ValidationResult:
    """
    Validate OKH manifest content against the canonical OKHManifest dataclass.
    
    Args:
        content: Dictionary containing OKH manifest data
        quality_level: Quality level for validation (hobby/professional/medical for manufacturing, home/commercial/professional for cooking)
        strict_mode: Whether to use strict validation mode
        domain: Optional domain override ("manufacturing" or "cooking"). If not provided, will be detected from manifest.
        
    Returns:
        ValidationResult with validation status, errors, warnings, and suggestions
    """
    result = ValidationResult(valid=True)
    result.details["quality_level"] = quality_level
    result.details["strict_mode"] = strict_mode
    result.details["model_type"] = "OKHManifest"
    
    try:
        # Step 1: Parse content into canonical OKHManifest dataclass
        try:
            okh_manifest = OKHManifest.from_dict(content)
            result.details["parsed_successfully"] = True
        except Exception as e:
            result.add_error(f"Failed to parse content as OKHManifest: {str(e)}")
            result.details["parsed_successfully"] = False
            result.details["parse_error"] = str(e)
            return result
        
        # Step 1.5: Detect domain if not provided
        detected_domain = domain or okh_manifest.domain or _detect_okh_domain_from_manifest(okh_manifest)
        result.details["domain"] = detected_domain
        
        # Step 2: Validate using the dataclass's validate() method
        try:
            okh_manifest.validate()
            result.details["dataclass_validation_passed"] = True
        except ValueError as e:
            result.add_error(f"OKHManifest validation failed: {str(e)}")
            result.details["dataclass_validation_passed"] = False
            result.details["validation_error"] = str(e)
        
        # Step 3: Domain-aware quality-level specific validation
        _validate_okh_quality_level(okh_manifest, quality_level, strict_mode, result, detected_domain)
        
        # Step 4: Calculate completeness score
        completeness_score = _calculate_okh_completeness(okh_manifest, quality_level, detected_domain)
        result.details["completeness_score"] = completeness_score
        
        # Step 5: Generate suggestions for improvement
        _generate_okh_suggestions(okh_manifest, quality_level, result, detected_domain)
        
        # Step 6: Validate metadata structure and content
        _validate_okh_metadata(okh_manifest, result)
        
    except Exception as e:
        logger.error(f"Unexpected error during OKH validation: {str(e)}", exc_info=True)
        result.add_error(f"Unexpected validation error: {str(e)}")
        result.details["unexpected_error"] = str(e)
    
    return result


def validate_okw_facility(
    content: Dict[str, Any],
    quality_level: str = "professional",
    strict_mode: bool = False
) -> ValidationResult:
    """
    Validate OKW facility content against the canonical ManufacturingFacility dataclass.
    
    Args:
        content: Dictionary containing OKW facility data
        quality_level: Quality level for validation (hobby, professional, medical)
        strict_mode: Whether to use strict validation mode
        
    Returns:
        ValidationResult with validation status, errors, warnings, and suggestions
    """
    result = ValidationResult(valid=True)
    result.details["quality_level"] = quality_level
    result.details["strict_mode"] = strict_mode
    result.details["model_type"] = "ManufacturingFacility"
    
    try:
        # Step 1: Check for missing required fields before parsing
        if not content.get("location"):
            result.add_error("Required field 'location' is missing")
            result.details["parsed_successfully"] = False
            return result
        
        # Step 2: Parse content into canonical ManufacturingFacility dataclass
        try:
            facility = ManufacturingFacility.from_dict(content)
            result.details["parsed_successfully"] = True
        except Exception as e:
            result.add_error(f"Failed to parse content as ManufacturingFacility: {str(e)}")
            result.details["parsed_successfully"] = False
            result.details["parse_error"] = str(e)
            return result
        
        # Step 3: Validate required fields
        _validate_okw_required_fields(facility, result)
        
        # Step 4: Quality-level specific validation
        _validate_okw_quality_level(facility, quality_level, strict_mode, result)
        
        # Step 5: Calculate completeness score
        completeness_score = _calculate_okw_completeness(facility, quality_level)
        result.details["completeness_score"] = completeness_score
        
        # Step 6: Generate suggestions for improvement
        _generate_okw_suggestions(facility, quality_level, result)
        
    except Exception as e:
        logger.error(f"Unexpected error during OKW validation: {str(e)}", exc_info=True)
        result.add_error(f"Unexpected validation error: {str(e)}")
        result.details["unexpected_error"] = str(e)
    
    return result


def _detect_okh_domain_from_manifest(manifest: OKHManifest) -> str:
    """Detect domain from manifest content"""
    # Check explicit domain field first
    if manifest.domain:
        return manifest.domain
    
    # Check for cooking indicators
    cooking_keywords = ["recipe", "cooking", "baking", "ingredient", "food", "meal", "kitchen", "oven", "stove"]
    content_lower = (manifest.function or "").lower() + " " + (manifest.description or "").lower()
    if any(keyword in content_lower for keyword in cooking_keywords):
        return "cooking"
    
    # Default to manufacturing
    return "manufacturing"


def _validate_okh_quality_level(
    manifest: OKHManifest,
    quality_level: str,
    strict_mode: bool,
    result: ValidationResult,
    domain: str = "manufacturing"
) -> None:
    """Validate OKH manifest against quality-level specific rules"""
    
    # Domain-specific quality level mappings
    if domain == "cooking":
        # Map cooking quality levels to manufacturing equivalents for validation
        quality_level_mapping = {
            "home": "hobby",
            "commercial": "professional",
            "professional": "professional"
        }
        mapped_level = quality_level_mapping.get(quality_level, "hobby")
    else:
        mapped_level = quality_level
    
    # Required fields by quality level (manufacturing-focused)
    quality_requirements = {
        "hobby": {
            "required": ["title", "version", "license", "licensor", "documentation_language", "function"],
            "recommended": ["description", "manufacturing_processes"] if domain == "manufacturing" else ["description", "tool_list"]
        },
        "professional": {
            "required": ["title", "version", "license", "licensor", "documentation_language", "function"] + 
                       (["manufacturing_processes"] if domain == "manufacturing" else ["tool_list"]),
            "recommended": (["description", "manufacturing_specs", "materials", "parts"] if domain == "manufacturing" 
                          else ["description", "materials", "making_instructions"])
        },
        "medical": {
            "required": ["title", "version", "license", "licensor", "documentation_language", "function", 
                        "manufacturing_processes", "manufacturing_specs", "standards_used"],
            "recommended": ["description", "materials", "parts", "attestation", "health_safety_notice"]
        }
    }
    
    requirements = quality_requirements.get(mapped_level, quality_requirements["professional"])
    manifest_dict = manifest.to_dict()
    
    # For cooking domain, be more lenient with license validation
    if domain == "cooking":
        # Cooking recipes may not have hardware license, which is OK
        if "license" in requirements["required"]:
            # Check if at least one license field is present
            license_data = manifest_dict.get("license", {})
            if isinstance(license_data, dict):
                has_any_license = any(license_data.get(k) for k in ["hardware", "documentation", "software"])
                if not has_any_license:
                    result.add_warning("No license information provided (recommended for cooking recipes)")
            elif not license_data:
                result.add_warning("No license information provided (recommended for cooking recipes)")
    
    # Check required fields
    for field_name in requirements["required"]:
        # Skip license check for cooking domain if we already handled it
        if domain == "cooking" and field_name == "license":
            continue
            
        field_value = manifest_dict.get(field_name)
        # Check if field is missing, None, or empty list/string
        if field_value is None or field_value == [] or field_value == "":
            result.add_error(f"Required field '{field_name}' is missing for {quality_level} quality level ({domain} domain)")
    
    # Check recommended fields (warnings only)
    for field_name in requirements["recommended"]:
        if field_name not in manifest_dict or manifest_dict[field_name] is None:
            result.add_warning(f"Recommended field '{field_name}' is missing for {quality_level} quality level ({domain} domain)")
    
    # Strict mode: treat recommended as required
    if strict_mode:
        for field_name in requirements["recommended"]:
            if field_name not in manifest_dict or manifest_dict[field_name] is None:
                result.add_error(f"Required field '{field_name}' is missing (strict mode)")


def _validate_okw_required_fields(
    facility: ManufacturingFacility,
    result: ValidationResult
) -> None:
    """Validate OKW facility required fields"""
    if not facility.name:
        result.add_error("Required field 'name' is missing")
    
    if not facility.location:
        result.add_error("Required field 'location' is missing")
    
    if not facility.facility_status:
        result.add_error("Required field 'facility_status' is missing")


def _validate_okw_quality_level(
    facility: ManufacturingFacility,
    quality_level: str,
    strict_mode: bool,
    result: ValidationResult
) -> None:
    """Validate OKW facility against quality-level specific rules"""
    # Required fields by quality level
    quality_requirements = {
        "hobby": {
            "required": ["name", "location", "facility_status"],
            "recommended": ["equipment", "manufacturing_processes"]
        },
        "professional": {
            "required": ["name", "location", "facility_status", "equipment", "manufacturing_processes"],
            "recommended": ["description", "typical_materials", "certifications", "contact"]
        },
        "medical": {
            "required": ["name", "location", "facility_status", "equipment", "manufacturing_processes", "certifications"],
            "recommended": ["typical_materials", "quality_standards", "regulatory_compliance"]
        }
    }
    
    requirements = quality_requirements.get(quality_level, quality_requirements["professional"])
    facility_dict = facility.to_dict()
    
    # Check required fields
    for field_name in requirements["required"]:
        field_value = facility_dict.get(field_name)
        # Check if field is missing or None
        # Note: Empty lists [] are considered valid (field exists but is empty)
        # Empty strings "" are considered invalid (field exists but has no value)
        if field_name in ["manufacturing_processes", "equipment", "typical_materials", "certifications"]:
            # For array fields, only check if the field is missing or None
            if field_value is None:
                result.add_error(f"Required field '{field_name}' is missing for {quality_level} quality level")
        else:
            # For non-array fields, check if missing, None, or empty string
            if field_value is None or field_value == "":
                result.add_error(f"Required field '{field_name}' is missing for {quality_level} quality level")
    
    # Check recommended fields (warnings only)
    for field_name in requirements["recommended"]:
        if field_name not in facility_dict or facility_dict[field_name] is None:
            result.add_warning(f"Recommended field '{field_name}' is missing for {quality_level} quality level")
    
    # Strict mode: treat recommended as required
    if strict_mode:
        for field_name in requirements["recommended"]:
            if field_name not in facility_dict or facility_dict[field_name] is None:
                result.add_error(f"Required field '{field_name}' is missing (strict mode)")


def _calculate_okh_completeness(manifest: OKHManifest, quality_level: str, domain: str = "manufacturing") -> float:
    """Calculate completeness score for OKH manifest"""
    manifest_dict = manifest.to_dict()
    
    # Base required fields (always required)
    base_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    
    # Domain-specific field mappings
    if domain == "cooking":
        # Map cooking quality levels
        quality_level_mapping = {
            "home": "hobby",
            "commercial": "professional",
            "professional": "professional"
        }
        mapped_level = quality_level_mapping.get(quality_level, "hobby")
        
        # Quality-level specific fields for cooking
        quality_fields = {
            "hobby": base_fields + ["description"],
            "professional": base_fields + ["description", "tool_list", "materials"],
            "medical": base_fields + ["description", "tool_list", "materials", "standards_used", "attestation"]
        }
    else:
        # Manufacturing domain
        quality_fields = {
            "hobby": base_fields + ["description"],
            "professional": base_fields + ["description", "manufacturing_processes", "manufacturing_specs"],
            "medical": base_fields + ["description", "manufacturing_processes", "manufacturing_specs", "standards_used", "attestation"]
        }
        mapped_level = quality_level
    
    expected_fields = quality_fields.get(mapped_level, quality_fields["professional"])
    present_fields = sum(1 for field in expected_fields if field in manifest_dict and manifest_dict[field] is not None)
    
    return present_fields / len(expected_fields) if expected_fields else 1.0


def _calculate_okw_completeness(facility: ManufacturingFacility, quality_level: str) -> float:
    """Calculate completeness score for OKW facility"""
    facility_dict = facility.to_dict()
    
    # Base required fields (always required)
    base_fields = ["name", "location", "facility_status"]
    
    # Quality-level specific fields
    quality_fields = {
        "hobby": base_fields + ["equipment"],
        "professional": base_fields + ["equipment", "manufacturing_processes", "typical_materials"],
        "medical": base_fields + ["equipment", "manufacturing_processes", "certifications", "typical_materials"]
    }
    
    expected_fields = quality_fields.get(quality_level, quality_fields["professional"])
    present_fields = sum(1 for field in expected_fields if field in facility_dict and facility_dict[field] is not None)
    
    return present_fields / len(expected_fields) if expected_fields else 1.0


def _generate_okh_suggestions(manifest: OKHManifest, quality_level: str, result: ValidationResult, domain: str = "manufacturing") -> None:
    """Generate suggestions for improving OKH manifest"""
    manifest_dict = manifest.to_dict()
    
    if not manifest_dict.get("description"):
        result.add_suggestion("Consider adding a description to help users understand the project")
    
    if domain == "cooking":
        if not manifest_dict.get("tool_list"):
            result.add_suggestion("Consider adding tool_list to specify required kitchen equipment")
        if not manifest_dict.get("materials"):
            result.add_suggestion("Consider adding materials to specify required ingredients")
        if not manifest_dict.get("making_instructions"):
            result.add_suggestion("Consider adding making_instructions with step-by-step recipe instructions")
    else:
        if not manifest_dict.get("manufacturing_processes"):
            result.add_suggestion("Consider adding manufacturing_processes to enable better facility matching")
        
        if quality_level in ["professional", "medical"] and not manifest_dict.get("manufacturing_specs"):
            result.add_suggestion("Consider adding manufacturing_specs for detailed process requirements")
        
        if quality_level == "medical" and not manifest_dict.get("standards_used"):
            result.add_suggestion("Consider adding standards_used for medical device compliance")


def _validate_okh_metadata(manifest: OKHManifest, result: ValidationResult) -> None:
    """Validate metadata structure and content for issues"""
    manifest_dict = manifest.to_dict()
    metadata = manifest_dict.get("metadata", {})
    
    if not metadata:
        return  # No metadata to validate
    
    # Check for data that should be in proper fields
    if "original" in metadata:
        original = metadata["original"]
        
        # Check for bom_atoms that should be in materials field
        if "bom_atoms" in original and isinstance(original["bom_atoms"], dict):
            bom_atoms_count = len(original["bom_atoms"])
            materials_count = len(manifest_dict.get("materials", []))
            if bom_atoms_count > 0 and materials_count == 0:
                result.add_warning(
                    f"[METADATA_MISPLACED_DATA] metadata.original.bom_atoms contains {bom_atoms_count} items that should be in the top-level 'materials' field"
                )
            elif bom_atoms_count > 0:
                result.add_warning(
                    f"[METADATA_DUPLICATE_DATA] metadata.original.bom_atoms contains {bom_atoms_count} items that duplicate or should replace data in 'materials' field"
                )
        
        # Check for tool_list_atoms that should be in tool_list field
        if "tool_list_atoms" in original and isinstance(original["tool_list_atoms"], list):
            tool_atoms_count = len(original["tool_list_atoms"])
            tool_list_count = len(manifest_dict.get("tool_list", []))
            if tool_atoms_count > 0 and tool_list_count == 0:
                result.add_warning(
                    f"[METADATA_MISPLACED_DATA] metadata.original.tool_list_atoms contains {tool_atoms_count} items that should be in the top-level 'tool_list' field"
                )
            elif tool_atoms_count > 0:
                result.add_warning(
                    f"[METADATA_DUPLICATE_DATA] metadata.original.tool_list_atoms contains {tool_atoms_count} items that duplicate or should replace data in 'tool_list' field"
                )
        
        # Check for product_atom (unclear purpose, may be misplaced)
        if "product_atom" in original:
            result.add_warning(
                "[METADATA_UNKNOWN_FIELD] metadata.original.product_atom is present but its purpose is unclear. Consider using standard OKH fields instead"
            )
            
            # Check for typos in product_atom
            product_atom = original["product_atom"]
            if isinstance(product_atom, dict):
                if "descroption" in product_atom:
                    result.add_warning(
                        "[METADATA_TYPO] metadata.original.product_atom has typo: 'descroption' should be 'description'"
                    )
                if "Link" in product_atom:
                    result.add_warning(
                        "[METADATA_FORMAT_ERROR] metadata.original.product_atom has wrong case: 'Link' should be 'link' (lowercase)"
                    )
        
        # Check for bom_output_atoms (unclear purpose)
        if "bom_output_atoms" in original:
            result.add_warning(
                "[METADATA_UNKNOWN_FIELD] metadata.original.bom_output_atoms is present but its purpose is unclear. Consider using standard OKH fields instead"
            )
            
            # Check for typos in bom_output_atoms
            bom_output = original["bom_output_atoms"]
            if isinstance(bom_output, dict):
                if "descroption" in bom_output:
                    result.add_warning(
                        "[METADATA_TYPO] metadata.original.bom_output_atoms has typo: 'descroption' should be 'description'"
                    )
                if "Link" in bom_output:
                    result.add_warning(
                        "[METADATA_FORMAT_ERROR] metadata.original.bom_output_atoms has wrong case: 'Link' should be 'link' (lowercase)"
                    )
        
        # Check for maintenance_instructions in metadata (should be top-level)
        if "maintenance_instructions" in original:
            result.add_warning(
                "[METADATA_MISPLACED_DATA] metadata.original.maintenance_instructions should be in the top-level 'operating_instructions' or 'making_instructions' field"
            )
        
        # Check for standards_used_original (should be top-level)
        if "standards_used_original" in original:
            result.add_warning(
                "[METADATA_MISPLACED_DATA] metadata.original.standards_used_original should be in the top-level 'standards_used' field"
            )
    
    # Check for excessive metadata size (may indicate data should be in proper fields)
    metadata_str = json.dumps(metadata)
    if len(metadata_str) > 5000:  # More than 5KB of metadata
        result.add_warning(
            f"[METADATA_EXCESSIVE_SIZE] metadata field is very large ({len(metadata_str)} bytes). Consider moving data to appropriate top-level fields"
        )


def _generate_okw_suggestions(facility: ManufacturingFacility, quality_level: str, result: ValidationResult) -> None:
    """Generate suggestions for improving OKW facility"""
    facility_dict = facility.to_dict()
    
    if not facility_dict.get("description"):
        result.add_suggestion("Consider adding a description to help users understand the facility")
    
    if not facility_dict.get("equipment"):
        result.add_suggestion("Consider adding equipment information for better matching")
    
    if quality_level in ["professional", "medical"] and not facility_dict.get("certifications"):
        result.add_suggestion("Consider adding certifications to demonstrate quality standards")
    
    if not facility_dict.get("contact"):
        result.add_suggestion("Consider adding contact information for facility inquiries")

