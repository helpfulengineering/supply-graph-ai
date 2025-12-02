"""
Auto-fix utilities for OKH manifest validation issues.

This module provides functionality to automatically fix warnings and errors
detected by the validation engine.

All fixes are applied through the canonical dataclass models (OKHManifest, ManufacturingFacility)
to ensure consistency and proper validation.
"""

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models.okh import MaterialSpec, OKHManifest
from ..models.okw import ManufacturingFacility
from ..utils.logging import get_logger
from .model_validator import (
    ValidationResult,
    validate_okh_manifest,
    validate_okw_facility,
)

logger = get_logger(__name__)


@dataclass
class Fix:
    """Represents a single fix to be applied"""

    type: str  # "typo", "case_error", "data_movement", "field_removal", etc.
    description: str
    field_path: str
    old_value: Any = None
    new_value: Any = None
    confidence: float = 1.0  # 0.0-1.0
    warning_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert fix to dictionary"""
        return {
            "type": self.type,
            "description": self.description,
            "field_path": self.field_path,
            "confidence": self.confidence,
            "warning_code": self.warning_code,
        }


@dataclass
class FixReport:
    """Report of what was fixed"""

    fixes_applied: List[Fix] = field(default_factory=list)
    fixes_skipped: List[Fix] = field(default_factory=list)
    original_warnings: int = 0
    remaining_warnings: int = 0
    original_errors: int = 0
    remaining_errors: int = 0

    @property
    def status(self) -> str:
        """
        Determine the overall status of the fix operation.

        Returns:
            "complete_success": All issues were fixed (no remaining warnings or errors)
            "partial_success": Some issues were fixed but some remain
            "failure": No fixes were applied or errors remain
        """
        if self.remaining_errors > 0:
            return "failure"
        elif self.remaining_warnings > 0 or len(self.fixes_applied) == 0:
            if len(self.fixes_applied) > 0:
                return "partial_success"
            else:
                return "failure"
        else:
            return "complete_success"

    @property
    def warnings_fixed(self) -> int:
        """Number of warnings that were fixed"""
        return self.original_warnings - self.remaining_warnings

    @property
    def errors_fixed(self) -> int:
        """Number of errors that were fixed"""
        return self.original_errors - self.remaining_errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "fixes_applied": [fix.to_dict() for fix in self.fixes_applied],
            "fixes_skipped": [fix.to_dict() for fix in self.fixes_skipped],
            "original_warnings": self.original_warnings,
            "remaining_warnings": self.remaining_warnings,
            "original_errors": self.original_errors,
            "remaining_errors": self.remaining_errors,
            "warnings_fixed": self.warnings_fixed,
            "errors_fixed": self.errors_fixed,
            "status": self.status,
        }


def auto_fix_okh_manifest(
    content: Dict[str, Any],
    validation_result: ValidationResult,
    quality_level: str = "professional",
    strict_mode: bool = False,
    domain: Optional[str] = None,
    dry_run: bool = False,
    fix_confidence_threshold: float = 0.7,
) -> Tuple[Dict[str, Any], FixReport]:
    """
    Automatically fix issues in OKH manifest based on validation results.

    All fixes are applied through the canonical OKHManifest dataclass to ensure
    consistency and proper validation.

    Args:
        content: Original manifest content (dictionary)
        validation_result: Validation result with warnings/errors
        quality_level: Quality level for re-validation
        strict_mode: Strict mode for re-validation
        domain: Domain for re-validation
        dry_run: If True, don't modify content, just return what would be fixed
        fix_confidence_threshold: Minimum confidence to apply a fix (0.0-1.0)

    Returns:
        Tuple of (fixed_content, fix_report)
    """
    report = FixReport()
    report.original_warnings = len(validation_result.warnings)
    report.original_errors = len(validation_result.errors)

    try:
        # Step 1: Parse content into canonical OKHManifest dataclass
        manifest = OKHManifest.from_dict(content)
    except Exception as e:
        logger.error(f"Failed to parse content as OKHManifest: {str(e)}")
        report.fixes_skipped.append(
            Fix(
                type="parse_error",
                description=f"Failed to parse content as OKHManifest: {str(e)}",
                field_path="",
                confidence=0.0,
                warning_code="PARSE_ERROR",
            )
        )
        # Return original content if parsing fails
        return content, report

    # Step 2: Parse warnings into fix objects
    fixes = _parse_warnings_to_fixes(validation_result.warnings)

    # Step 3: Group fixes by type and sort by confidence (highest first)
    fixes_by_type = _group_fixes_by_type(fixes)

    # Step 4: Apply fixes in order: typos → case → data movement → transformation → removal → field_addition
    # All fixes work on the manifest instance or its metadata dict
    fix_order = [
        "typo",
        "case_error",
        "data_movement",
        "data_transformation",
        "field_removal",
        "field_addition",
    ]

    for fix_type in fix_order:
        if fix_type in fixes_by_type:
            for fix in fixes_by_type[fix_type]:
                if fix.confidence >= fix_confidence_threshold:
                    try:
                        if not dry_run:
                            _apply_fix_to_manifest(manifest, fix)
                        report.fixes_applied.append(fix)
                        logger.debug(f"Applied fix: {fix.description}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply fix {fix.description}: {str(e)}"
                        )
                        report.fixes_skipped.append(fix)
                else:
                    logger.debug(
                        f"Skipped low-confidence fix: {fix.description} (confidence: {fix.confidence})"
                    )
                    report.fixes_skipped.append(fix)

    # Step 5: Convert manifest back to dictionary
    if not dry_run:
        fixed_content = manifest.to_dict()

        # Re-validate after fixes
        detected_domain = domain or manifest.domain
        new_validation = validate_okh_manifest(
            fixed_content,
            quality_level=quality_level,
            strict_mode=strict_mode,
            domain=detected_domain,
        )
        report.remaining_warnings = len(new_validation.warnings)
        report.remaining_errors = len(new_validation.errors)
    else:
        # In dry-run, convert to dict for return but don't validate
        fixed_content = manifest.to_dict()
        report.remaining_warnings = report.original_warnings
        report.remaining_errors = report.original_errors

    return fixed_content, report


def _parse_warnings_to_fixes(
    warnings: List[str], errors: List[str] = None
) -> List[Fix]:
    """Parse warning and error messages into Fix objects"""
    fixes = []
    errors = errors or []

    # Process warnings (metadata issues, typos, etc.)
    for warning in warnings:
        # Extract warning code
        code_match = re.search(r"\[([^\]]+)\]", warning)
        if not code_match:
            # Check if this is a missing recommended field warning (no code)
            missing_field_match = re.search(
                r"Recommended field '([^']+)' is missing", warning
            )
            if missing_field_match:
                field_name = missing_field_match.group(1)
                fix = _create_field_addition_fix(field_name, is_required=False)
                if fix:
                    fixes.append(fix)
            continue

        code = code_match.group(1)

        # Extract field path
        field_match = re.search(r"metadata\.([^\s]+)", warning)
        field_path = field_match.group(0) if field_match else ""

        # Parse based on code type
        if code == "METADATA_TYPO":
            fix = _parse_typo_fix(warning, code, field_path)
            if fix:
                fixes.append(fix)
        elif code == "METADATA_FORMAT_ERROR":
            fix = _parse_case_error_fix(warning, code, field_path)
            if fix:
                fixes.append(fix)
        elif code == "METADATA_MISPLACED_DATA":
            fix = _parse_data_movement_fix(warning, code, field_path)
            if fix:
                fixes.append(fix)
        elif code == "METADATA_DUPLICATE_DATA":
            fix = _parse_data_movement_fix(warning, code, field_path)
            if fix:
                fixes.append(fix)
        elif code == "METADATA_UNKNOWN_FIELD":
            fix = _parse_field_removal_fix(warning, code, field_path)
            if fix:
                fixes.append(fix)

    # Process errors (missing required fields, etc.)
    for error in errors:
        # Check for missing required/recommended fields
        missing_field_match = re.search(
            r"Required field '([^']+)' is missing|Recommended field '([^']+)' is missing",
            error,
        )
        if missing_field_match:
            field_name = missing_field_match.group(1) or missing_field_match.group(2)
            is_required = "Required" in error
            fix = _create_field_addition_fix(field_name, is_required=is_required)
            if fix:
                fixes.append(fix)

    return fixes


def _create_field_addition_fix(field_name: str, is_required: bool) -> Optional[Fix]:
    """Create a field addition fix for a missing field"""
    # For array/list fields, we can add an empty list
    array_fields = {
        "manufacturing_processes": [],
        "equipment": [],
        "typical_materials": [],
        "certifications": [],
        "affiliations": [],
        "tool_list": [],
        "materials": [],
        "parts": [],
    }

    # For complex object fields, we can create minimal placeholder objects
    object_fields = {"contact": {"name": "Contact information needed", "contact": {}}}

    if field_name in array_fields:
        # Low confidence because we're just adding empty arrays
        # User should fill in the actual values
        confidence = 0.3 if is_required else 0.2
        return Fix(
            type="field_addition",
            description=f"Add empty '{field_name}' field ({'required' if is_required else 'recommended'})",
            field_path=field_name,
            old_value=None,
            new_value=array_fields[field_name],
            confidence=confidence,
            warning_code=(
                "MISSING_FIELD" if is_required else "MISSING_RECOMMENDED_FIELD"
            ),
        )
    elif field_name in object_fields:
        # Very low confidence for object fields since they need user input
        confidence = 0.2 if is_required else 0.1
        return Fix(
            type="field_addition",
            description=f"Add placeholder '{field_name}' field ({'required' if is_required else 'recommended'})",
            field_path=field_name,
            old_value=None,
            new_value=object_fields[field_name],
            confidence=confidence,
            warning_code=(
                "MISSING_FIELD" if is_required else "MISSING_RECOMMENDED_FIELD"
            ),
        )

    return None


def _parse_typo_fix(warning: str, code: str, field_path: str) -> Optional[Fix]:
    """Parse a typo fix from warning message"""
    # Extract typo details: 'descroption' should be 'description'
    typo_match = re.search(r"'([^']+)' should be '([^']+)'", warning)
    if not typo_match:
        return None

    typo = typo_match.group(1)
    correct = typo_match.group(2)

    return Fix(
        type="typo",
        description=f"Fix typo: '{typo}' → '{correct}' in {field_path}",
        field_path=field_path,
        old_value=typo,
        new_value=correct,
        confidence=1.0,
        warning_code=code,
    )


def _parse_case_error_fix(warning: str, code: str, field_path: str) -> Optional[Fix]:
    """Parse a case error fix from warning message"""
    # Extract case error: 'Link' should be 'link' (lowercase)
    case_match = re.search(r"'([^']+)' should be '([^']+)'", warning)
    if not case_match:
        return None

    wrong_case = case_match.group(1)
    correct_case = case_match.group(2)

    return Fix(
        type="case_error",
        description=f"Fix case: '{wrong_case}' → '{correct_case}' in {field_path}",
        field_path=field_path,
        old_value=wrong_case,
        new_value=correct_case,
        confidence=1.0,
        warning_code=code,
    )


def _parse_data_movement_fix(warning: str, code: str, field_path: str) -> Optional[Fix]:
    """Parse a data movement fix from warning message"""
    # Extract target field from various warning formats:
    # - "should be in the top-level 'materials' field"
    # - "should be in the top-level 'operating_instructions' or 'making_instructions' field"
    # - "duplicate or should replace data in 'tool_list' field"
    target_match = re.search(r"(?:top-level |data in )'([^']+(?: or [^']+)?)'", warning)
    if not target_match:
        return None

    target_field = target_match.group(1)

    # For fields with "or", use the first one (can be improved later)
    if " or " in target_field:
        target_field = target_field.split(" or ")[0]

    # Determine confidence based on code
    # MISPLACED_DATA: data should be moved (high confidence)
    # DUPLICATE_DATA: data duplicates existing (medium confidence, but still worth fixing)
    confidence = 0.9 if code == "METADATA_MISPLACED_DATA" else 0.75

    return Fix(
        type="data_movement",
        description=f"Move data from {field_path} to top-level '{target_field}' field",
        field_path=field_path,
        old_value=field_path,
        new_value=target_field,
        confidence=confidence,
        warning_code=code,
    )


def _parse_field_removal_fix(warning: str, code: str, field_path: str) -> Optional[Fix]:
    """Parse a field removal fix from warning message"""
    return Fix(
        type="field_removal",
        description=f"Remove unknown/unclear field: {field_path}",
        field_path=field_path,
        confidence=0.5,  # Low confidence - requires user confirmation
        warning_code=code,
    )


def _group_fixes_by_type(fixes: List[Fix]) -> Dict[str, List[Fix]]:
    """Group fixes by type"""
    grouped = {}
    for fix in fixes:
        if fix.type not in grouped:
            grouped[fix.type] = []
        grouped[fix.type].append(fix)

    # Sort each group by confidence (highest first)
    for fix_type in grouped:
        grouped[fix_type].sort(key=lambda f: f.confidence, reverse=True)

    return grouped


def _apply_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """
    Apply a single fix to the OKHManifest instance.

    All fixes are applied through the canonical dataclass to ensure consistency.
    """
    if fix.type == "typo":
        _apply_typo_fix_to_manifest(manifest, fix)
    elif fix.type == "case_error":
        _apply_case_error_fix_to_manifest(manifest, fix)
    elif fix.type == "data_movement":
        _apply_data_movement_fix_to_manifest(manifest, fix)
    elif fix.type == "field_removal":
        _apply_field_removal_fix_to_manifest(manifest, fix)
    elif fix.type == "field_addition":
        _apply_field_addition_fix_to_manifest(manifest, fix)
    else:
        raise ValueError(f"Unknown fix type: {fix.type}")


def _apply_typo_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """Apply a typo fix to the manifest's metadata"""
    # Typo fixes are in metadata, so we work with the metadata dict
    if not manifest.metadata:
        return

    # Navigate to the field in metadata
    field_parts = fix.field_path.split(".")
    if field_parts[0] != "metadata":
        return

    obj = manifest.metadata
    for part in field_parts[1:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            return
        obj = obj[part]

    # Fix the typo in the last field
    last_field = field_parts[-1]
    if last_field in obj and isinstance(obj[last_field], dict):
        if fix.old_value in obj[last_field]:
            obj[last_field][fix.new_value] = obj[last_field].pop(fix.old_value)


def _apply_case_error_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """Apply a case error fix to the manifest's metadata"""
    # Case fixes are in metadata, so we work with the metadata dict
    if not manifest.metadata:
        return

    # Navigate to the field in metadata
    field_parts = fix.field_path.split(".")
    if field_parts[0] != "metadata":
        return

    obj = manifest.metadata
    for part in field_parts[1:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            return
        obj = obj[part]

    # Fix the case in the last field
    last_field = field_parts[-1]
    if last_field in obj and isinstance(obj[last_field], dict):
        if fix.old_value in obj[last_field]:
            obj[last_field][fix.new_value] = obj[last_field].pop(fix.old_value)


def _apply_data_movement_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """
    Apply a data movement fix to the manifest.

    Moves data from metadata to proper top-level fields using the canonical model.
    """
    # Navigate to source field in metadata
    source_parts = fix.field_path.split(".")
    if source_parts[0] != "metadata" or not manifest.metadata:
        return

    source_obj = manifest.metadata
    for part in source_parts[1:-1]:
        if part not in source_obj or not isinstance(source_obj[part], dict):
            return
        source_obj = source_obj[part]

    source_field = source_parts[-1]
    if source_field not in source_obj:
        return

    source_data = source_obj[source_field]

    # Determine target field
    target_field = fix.new_value

    # Transform and move data based on field type
    if source_field == "bom_atoms" and target_field == "materials":
        # Convert bom_atoms dict to MaterialSpec objects
        for name, atom_data in source_data.items():
            material = MaterialSpec(
                material_id=atom_data.get("identifier", ""),
                name=atom_data.get("description", name),
                quantity=None,
                unit=None,
                notes=atom_data.get("link"),
            )
            manifest.materials.append(material)

        # Remove from metadata
        del source_obj[source_field]

    elif source_field == "tool_list_atoms" and target_field == "tool_list":
        # Convert tool_list_atoms list to tool_list list
        tools = []
        for atom in source_data:
            if isinstance(atom, dict):
                tool_name = atom.get("description", atom.get("identifier", ""))
                if tool_name:
                    tools.append(tool_name)

        # Add to manifest's tool_list (only if not already present)
        existing_tools = set(manifest.tool_list)
        for tool in tools:
            if tool not in existing_tools:
                manifest.tool_list.append(tool)

        # Always remove from metadata to eliminate duplication
        del source_obj[source_field]

    elif source_field == "maintenance_instructions" and target_field in [
        "operating_instructions",
        "making_instructions",
    ]:
        # Move maintenance_instructions to appropriate field
        # Since it's null in the example, we just remove it
        if source_data is None:
            del source_obj[source_field]
        else:
            # Would need to convert to DocumentRef objects, but for now just remove
            # This is a simplified approach - could be enhanced
            del source_obj[source_field]

    elif source_field == "standards_used_original" and target_field == "standards_used":
        # Move standards_used_original to standards_used
        # Since it's null in the example, we just remove it
        if source_data is None:
            del source_obj[source_field]
        else:
            # Would need to convert to Standard objects, but for now just remove
            # This is a simplified approach - could be enhanced
            del source_obj[source_field]


def _apply_field_removal_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """
    Apply a field removal fix to the manifest's metadata.

    For unknown/unclear fields (METADATA_UNKNOWN_FIELD), removes them regardless
    of content since their purpose is unclear. For other fields, only removes
    if they are empty or data has been moved.
    """
    # Field removal fixes are in metadata
    if not manifest.metadata:
        return

    # Navigate to the field in metadata
    field_parts = fix.field_path.split(".")
    if field_parts[0] != "metadata":
        return

    obj = manifest.metadata
    for part in field_parts[1:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            return
        obj = obj[part]

    last_field = field_parts[-1]
    if last_field in obj:
        # For unknown fields (METADATA_UNKNOWN_FIELD), always remove
        # since their purpose is unclear and they shouldn't be in the manifest
        if fix.warning_code == "METADATA_UNKNOWN_FIELD":
            del obj[last_field]
            return

        # For other fields, only remove if empty, null, or contains only empty data
        field_value = obj[last_field]
        if field_value is None or field_value == {} or field_value == []:
            del obj[last_field]
        elif isinstance(field_value, dict) and not any(field_value.values()):
            del obj[last_field]


def _apply_field_addition_fix_to_manifest(manifest: OKHManifest, fix: Fix) -> None:
    """Apply a field addition fix to the manifest"""
    field_name = fix.field_path

    # Only handle array/list fields that we can safely initialize as empty
    array_field_mappings = {
        "manufacturing_processes": lambda m: setattr(m, "manufacturing_processes", []),
        "tool_list": lambda m: setattr(m, "tool_list", []),
        "materials": lambda m: setattr(m, "materials", []),
        "parts": lambda m: setattr(m, "parts", []),
        "contributors": lambda m: setattr(m, "contributors", []),
        "manufacturing_files": lambda m: setattr(m, "manufacturing_files", []),
        "design_files": lambda m: setattr(m, "design_files", []),
        "making_instructions": lambda m: setattr(m, "making_instructions", []),
    }

    if field_name in array_field_mappings:
        # Check if field is already set
        current_value = getattr(manifest, field_name, None)
        if current_value is None or (
            isinstance(current_value, list) and len(current_value) == 0
        ):
            array_field_mappings[field_name](manifest)
            logger.debug(f"Added empty '{field_name}' field to manifest")


def auto_fix_okw_facility(
    content: Dict[str, Any],
    validation_result: ValidationResult,
    quality_level: str = "professional",
    strict_mode: bool = False,
    domain: Optional[str] = None,
    dry_run: bool = False,
    fix_confidence_threshold: float = 0.7,
) -> Tuple[Dict[str, Any], FixReport]:
    """
    Automatically fix issues in OKW facility based on validation results.

    All fixes are applied through the canonical ManufacturingFacility dataclass to ensure
    consistency and proper validation.

    Args:
        content: Original facility content (dictionary)
        validation_result: Validation result with warnings/errors
        quality_level: Quality level for re-validation
        strict_mode: Strict mode for re-validation
        domain: Domain for re-validation
        dry_run: If True, don't modify content, just return what would be fixed
        fix_confidence_threshold: Minimum confidence to apply a fix (0.0-1.0)

    Returns:
        Tuple of (fixed_content, fix_report)
    """
    report = FixReport()
    report.original_warnings = len(validation_result.warnings)
    report.original_errors = len(validation_result.errors)

    try:
        # Step 1: Parse content into canonical ManufacturingFacility dataclass
        facility = ManufacturingFacility.from_dict(content)
    except Exception as e:
        logger.error(f"Failed to parse content as ManufacturingFacility: {str(e)}")
        report.fixes_skipped.append(
            Fix(
                type="parse_error",
                description=f"Failed to parse content as ManufacturingFacility: {str(e)}",
                field_path="",
                confidence=0.0,
                warning_code="PARSE_ERROR",
            )
        )
        # Return original content if parsing fails
        return content, report

    # Step 2: Parse warnings and errors into fix objects
    # Reuse the same parsing logic as OKH (typos, case errors, metadata issues)
    fixes = _parse_warnings_to_fixes(
        validation_result.warnings, validation_result.errors
    )

    # Step 3: Group fixes by type and sort by confidence (highest first)
    fixes_by_type = _group_fixes_by_type(fixes)

    # Step 4: Apply fixes in order: typos → case → data movement → transformation → removal → field_addition
    # All fixes work on the facility instance or its metadata dict
    fix_order = [
        "typo",
        "case_error",
        "data_movement",
        "data_transformation",
        "field_removal",
        "field_addition",
    ]

    for fix_type in fix_order:
        if fix_type in fixes_by_type:
            for fix in fixes_by_type[fix_type]:
                if fix.confidence >= fix_confidence_threshold:
                    try:
                        if not dry_run:
                            _apply_fix_to_facility(facility, fix)
                        report.fixes_applied.append(fix)
                        logger.debug(f"Applied fix: {fix.description}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply fix {fix.description}: {str(e)}"
                        )
                        report.fixes_skipped.append(fix)
                else:
                    logger.debug(
                        f"Skipped low-confidence fix: {fix.description} (confidence: {fix.confidence})"
                    )
                    report.fixes_skipped.append(fix)

    # Step 5: Convert facility back to dictionary
    if not dry_run:
        fixed_content = facility.to_dict()

        # Re-validate after fixes
        detected_domain = domain or facility.domain
        new_validation = validate_okw_facility(
            fixed_content, quality_level=quality_level, strict_mode=strict_mode
        )
        report.remaining_warnings = len(new_validation.warnings)
        report.remaining_errors = len(new_validation.errors)
    else:
        # In dry-run, convert to dict for return but don't validate
        fixed_content = facility.to_dict()
        report.remaining_warnings = report.original_warnings
        report.remaining_errors = report.original_errors

    return fixed_content, report


def _apply_fix_to_facility(facility: ManufacturingFacility, fix: Fix) -> None:
    """
    Apply a single fix to the ManufacturingFacility instance.

    All fixes are applied through the canonical dataclass to ensure consistency.
    """
    if fix.type == "typo":
        _apply_typo_fix_to_facility(facility, fix)
    elif fix.type == "case_error":
        _apply_case_error_fix_to_facility(facility, fix)
    elif fix.type == "data_movement":
        _apply_data_movement_fix_to_facility(facility, fix)
    elif fix.type == "field_removal":
        _apply_field_removal_fix_to_facility(facility, fix)
    elif fix.type == "field_addition":
        _apply_field_addition_fix_to_facility(facility, fix)
    else:
        raise ValueError(f"Unknown fix type: {fix.type}")


def _apply_typo_fix_to_facility(facility: ManufacturingFacility, fix: Fix) -> None:
    """Apply a typo fix to the facility's metadata"""
    # Typo fixes are in metadata, so we work with the metadata dict
    # OKW facilities may not have metadata, so check first
    if not hasattr(facility, "record_data") or not facility.record_data:
        return

    # For now, OKW facilities don't have a metadata dict like OKH
    # Most fixes will be in record_data or other nested structures
    # This is a placeholder for future OKW-specific metadata fixes
    pass


def _apply_case_error_fix_to_facility(
    facility: ManufacturingFacility, fix: Fix
) -> None:
    """Apply a case error fix to the facility's metadata"""
    # Similar to typo fixes, OKW may not have metadata structure
    # Placeholder for future OKW-specific case fixes
    pass


def _apply_data_movement_fix_to_facility(
    facility: ManufacturingFacility, fix: Fix
) -> None:
    """Apply a data movement fix to the facility"""
    # OKW facilities may have data movement fixes in the future
    # Placeholder for future OKW-specific data movement fixes
    pass


def _apply_field_removal_fix_to_facility(
    facility: ManufacturingFacility, fix: Fix
) -> None:
    """Apply a field removal fix to the facility's metadata"""
    # OKW facilities may have field removal fixes in the future
    # Placeholder for future OKW-specific field removal fixes
    pass


def _apply_field_addition_fix_to_facility(
    facility: ManufacturingFacility, fix: Fix
) -> None:
    """Apply a field addition fix to the facility"""
    field_name = fix.field_path

    # Only handle array/list fields that we can safely initialize as empty
    array_field_mappings = {
        "manufacturing_processes": lambda f: setattr(f, "manufacturing_processes", []),
        "equipment": lambda f: setattr(f, "equipment", []),
        "typical_materials": lambda f: setattr(f, "typical_materials", []),
        "certifications": lambda f: setattr(f, "certifications", []),
        "affiliations": lambda f: setattr(f, "affiliations", []),
    }

    # Handle complex object fields
    if field_name == "contact":
        # Check if contact is already set
        current_value = getattr(facility, "contact", None)
        if current_value is None:
            # Create a minimal Agent object for contact
            from ..models.okw import Agent

            contact_agent = Agent(name="Contact information needed")
            setattr(facility, "contact", contact_agent)
            logger.debug(f"Added placeholder '{field_name}' field to facility")
        return

    if field_name in array_field_mappings:
        # Check if field is already set
        current_value = getattr(facility, field_name, None)
        if current_value is None or (
            isinstance(current_value, list) and len(current_value) == 0
        ):
            array_field_mappings[field_name](facility)
            logger.debug(f"Added empty '{field_name}' field to facility")


def _get_nested_value(content: Dict[str, Any], path: str) -> Any:
    """Get a nested value from content using dot notation path"""
    parts = path.split(".")
    obj = content
    for part in parts:
        if part not in obj:
            return None
        obj = obj[part]
    return obj


def _set_nested_value(content: Dict[str, Any], path: str, value: Any) -> None:
    """Set a nested value in content using dot notation path"""
    parts = path.split(".")
    obj = content
    for part in parts[:-1]:
        if part not in obj:
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value
