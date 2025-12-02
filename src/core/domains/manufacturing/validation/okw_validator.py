"""
OKW validator for manufacturing domain.

This module provides a new OKW validator for the manufacturing domain
that integrates with the new validation framework.
"""

from typing import Dict, Any, Optional, List
from ....validation.engine import Validator
from ....validation.context import ValidationContext
from ....validation.result import ValidationResult, ValidationError, ValidationWarning
from ....validation.rules.manufacturing import ManufacturingValidationRules
from ....models.okw import ManufacturingFacility
from ....models.base.base_types import Requirement, Capability
import re


class ManufacturingOKWValidator(Validator):
    """OKW validator for manufacturing domain using new validation framework"""

    def __init__(self):
        self.validation_rules = ManufacturingValidationRules()

    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "okw_facility"

    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 90  # High priority for OKW validation

    async def validate(
        self, data: Any, context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate OKW facility data using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Handle different data types
        if isinstance(data, ManufacturingFacility):
            return await self._validate_manufacturing_facility(data, context)
        elif isinstance(data, dict):
            # Validate raw dictionary data without requiring full object parsing
            return await self._validate_okw_dict(data, context)
        else:
            result.add_error(f"Unsupported data type for OKW validation: {type(data)}")
            return result

    async def _validate_okw_dict(
        self, data: Dict[str, Any], context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate OKW facility data as dictionary"""
        result = ValidationResult(valid=True)

        # Get quality level from context or default to professional
        quality_level = "professional"
        if context:
            quality_level = context.quality_level

        # Validate quality level is supported
        if quality_level not in self.validation_rules.get_supported_quality_levels():
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result

        rules = self.validation_rules.get_okw_validation_rules(quality_level)

        # 1. Required fields validation
        required_fields = self.validation_rules.get_okw_required_fields(quality_level)
        missing_required_fields = [
            field
            for field in required_fields
            if field not in data or data[field] is None
        ]
        for field in missing_required_fields:
            result.add_error(
                f"Missing required field: '{field}'",
                field=field,
                code="missing_required_field",
            )

        # 2. Basic type and format validation
        if "name" in data:
            if not isinstance(data["name"], str):
                result.add_error(
                    "Name must be a string", field="name", code="invalid_type"
                )
            elif not data["name"].strip():
                result.add_error(
                    "Name cannot be empty", field="name", code="empty_field"
                )
        if "location" in data and not isinstance(data["location"], (str, dict)):
            result.add_error(
                "Location must be a string or dictionary",
                field="location",
                code="invalid_type",
            )
        if "facility_status" in data:
            if not isinstance(data["facility_status"], str):
                result.add_error(
                    "Facility status must be a string",
                    field="facility_status",
                    code="invalid_type",
                )
            elif not data["facility_status"].strip():
                result.add_error(
                    "Facility status cannot be empty",
                    field="facility_status",
                    code="empty_field",
                )

        # 3. Equipment validation (if present)
        if "equipment" in data and isinstance(data["equipment"], list):
            for i, equipment_item in enumerate(data["equipment"]):
                if not isinstance(equipment_item, dict):
                    result.add_error(
                        f"Equipment item at index {i} must be a dictionary",
                        field=f"equipment.{i}",
                        code="invalid_type",
                    )
                    continue
                # Check required fields for equipment
                eq_required = rules.get("equipment_validation", {}).get(
                    "required_fields", []
                )
                for field in eq_required:
                    if field not in equipment_item or equipment_item[field] is None:
                        result.add_error(
                            f"Equipment item at index {i} is missing required field: '{field}'",
                            field=f"equipment.{i}.{field}",
                            code="missing_required_equipment_field",
                        )

        # 4. Manufacturing processes validation (if present)
        if "manufacturing_processes" in data and isinstance(
            data["manufacturing_processes"], list
        ):
            valid_processes = rules.get("process_validation", {}).get(
                "valid_processes", []
            )
            for i, process_url in enumerate(data["manufacturing_processes"]):
                if not isinstance(process_url, str) or not re.match(
                    r"^https?://[^\s]+$", process_url
                ):
                    result.add_error(
                        f"Manufacturing process at index {i} is not a valid URL",
                        field=f"manufacturing_processes.{i}",
                        code="invalid_url_format",
                    )
                elif valid_processes and process_url not in valid_processes:
                    result.add_warning(
                        f"Manufacturing process '{process_url}' is not in the list of known valid processes",
                        field=f"manufacturing_processes.{i}",
                        code="unknown_process",
                    )

        # Add warnings for recommended fields if strict_mode is off
        if not (context and context.strict_mode):
            optional_fields = self.validation_rules.get_okw_optional_fields(
                quality_level
            )
            for field in optional_fields:
                if field not in data or data[field] is None:
                    result.add_warning(
                        f"Recommended field '{field}' is missing",
                        field=field,
                        code="missing_recommended_field",
                    )

        return result

    async def _validate_manufacturing_facility(
        self,
        facility: ManufacturingFacility,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        """Validate manufacturing facility using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Get quality level from context or default to professional
        quality_level = "professional"
        if context:
            quality_level = context.quality_level

        # Validate quality level is supported
        if not ManufacturingValidationRules.validate_quality_level(quality_level):
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result

        # Get validation rules for this quality level
        rules = self.validation_rules.get_okw_validation_rules(quality_level)

        # Validate required fields
        required_fields = rules.get("required_fields", [])
        missing_fields = self.validation_rules.get_missing_required_fields(
            facility.to_dict(), quality_level
        )

        for field in missing_fields:
            result.add_error(
                f"Required field '{field}' is missing for {quality_level} quality level",
                field=field,
                code="required_field_missing",
            )

        # Validate field content based on quality level
        await self._validate_field_content(facility, quality_level, result)

        # Validate facility status
        await self._validate_facility_status(facility, quality_level, result)

        # Validate location information
        await self._validate_location(facility, quality_level, result)

        # Validate equipment
        await self._validate_equipment(facility, quality_level, result)

        # Validate manufacturing processes
        await self._validate_manufacturing_processes(facility, quality_level, result)

        # Validate materials
        await self._validate_materials(facility, quality_level, result)

        # Validate certifications and quality standards
        await self._validate_certifications(facility, quality_level, result)

        # Calculate capability score
        capability_score = self._calculate_capability_score(facility, quality_level)
        result.metadata["capability_score"] = capability_score

        # Add warnings for missing optional fields
        await self._add_optional_field_warnings(facility, quality_level, result)

        return result

    async def _validate_field_content(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate content of individual fields"""

        # Validate facility name
        if hasattr(facility, "name") and facility.name:
            if len(facility.name.strip()) < 3:
                result.add_warning(
                    "Facility name is very short, consider providing a more descriptive name",
                    field="name",
                    code="name_too_short",
                )

        # Validate facility type
        if hasattr(facility, "facility_type") and facility.facility_type:
            if not self._is_valid_facility_type(facility.facility_type):
                result.add_warning(
                    f"Facility type '{facility.facility_type}' may not be standard",
                    field="facility_type",
                    code="non_standard_facility_type",
                )

    async def _validate_facility_status(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate facility status"""

        if not hasattr(facility, "facility_status") or not facility.facility_status:
            result.add_error(
                "Facility status is required",
                field="facility_status",
                code="facility_status_required",
            )
            return

        valid_statuses = ["operational", "maintenance", "closed", "planning"]
        if facility.facility_status not in valid_statuses:
            result.add_error(
                f"Invalid facility status '{facility.facility_status}'. Valid statuses: {', '.join(valid_statuses)}",
                field="facility_status",
                code="invalid_facility_status",
            )

        # Add warnings based on status
        if facility.facility_status == "maintenance":
            result.add_warning(
                "Facility is under maintenance, availability may be limited",
                field="facility_status",
                code="facility_under_maintenance",
            )
        elif facility.facility_status == "closed":
            result.add_warning(
                "Facility is closed, not available for manufacturing",
                field="facility_status",
                code="facility_closed",
            )
        elif facility.facility_status == "planning":
            result.add_warning(
                "Facility is in planning phase, not yet operational",
                field="facility_status",
                code="facility_planning",
            )

    async def _validate_location(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate location information"""

        if not hasattr(facility, "location") or not facility.location:
            result.add_error(
                "Location information is required",
                field="location",
                code="location_required",
            )
            return

        location = facility.location

        # Validate address
        if hasattr(location, "address") and location.address:
            if len(location.address.strip()) < 10:
                result.add_warning(
                    "Address seems incomplete, consider providing full address",
                    field="location.address",
                    code="address_incomplete",
                )

        # Validate coordinates
        if hasattr(location, "coordinates"):
            if not self._validate_coordinates(location.coordinates):
                result.add_error(
                    "Invalid coordinates format",
                    field="location.coordinates",
                    code="invalid_coordinates",
                )

        # Validate country code
        if hasattr(location, "country_code") and location.country_code:
            if not self._is_valid_country_code(location.country_code):
                result.add_warning(
                    f"Country code '{location.country_code}' may not be standard ISO format",
                    field="location.country_code",
                    code="non_standard_country_code",
                )

    async def _validate_equipment(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate equipment information"""

        if not hasattr(facility, "equipment") or not facility.equipment:
            if quality_level in ["professional", "medical"]:
                result.add_error(
                    "Equipment information is required for professional/medical quality levels",
                    field="equipment",
                    code="equipment_required",
                )
            else:
                result.add_warning(
                    "No equipment information provided",
                    field="equipment",
                    code="equipment_missing",
                )
            return

        # Validate each piece of equipment
        for i, equipment in enumerate(facility.equipment):
            await self._validate_equipment_item(equipment, i, quality_level, result)

    async def _validate_equipment_item(
        self, equipment: Any, index: int, quality_level: str, result: ValidationResult
    ):
        """Validate individual equipment item"""

        # Check required equipment fields
        if not hasattr(equipment, "name") or not equipment.name:
            result.add_error(
                f"Equipment {index}: name is required",
                field=f"equipment[{index}].name",
                code="equipment_name_required",
            )

        if not hasattr(equipment, "type") or not equipment.type:
            result.add_error(
                f"Equipment {index}: type is required",
                field=f"equipment[{index}].type",
                code="equipment_type_required",
            )

        # Validate equipment type
        if hasattr(equipment, "type") and equipment.type:
            if not self._is_valid_equipment_type(equipment.type):
                result.add_warning(
                    f"Equipment {index}: type '{equipment.type}' may not be standard",
                    field=f"equipment[{index}].type",
                    code="non_standard_equipment_type",
                )

        # Validate specifications
        if hasattr(equipment, "specifications") and equipment.specifications:
            if not self._validate_equipment_specifications(equipment.specifications):
                result.add_warning(
                    f"Equipment {index}: specifications format may be invalid",
                    field=f"equipment[{index}].specifications",
                    code="invalid_equipment_specifications",
                )

    async def _validate_manufacturing_processes(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate manufacturing processes"""

        if (
            not hasattr(facility, "manufacturing_processes")
            or not facility.manufacturing_processes
        ):
            if quality_level in ["professional", "medical"]:
                result.add_error(
                    "Manufacturing processes are required for professional/medical quality levels",
                    field="manufacturing_processes",
                    code="manufacturing_processes_required",
                )
            else:
                result.add_warning(
                    "No manufacturing processes specified",
                    field="manufacturing_processes",
                    code="manufacturing_processes_missing",
                )
            return

        # Validate each manufacturing process
        for i, process in enumerate(facility.manufacturing_processes):
            if not self._is_valid_manufacturing_process(process):
                result.add_error(
                    f"Invalid manufacturing process: {process}",
                    field=f"manufacturing_processes[{i}]",
                    code="invalid_manufacturing_process",
                )

    async def _validate_materials(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate materials information"""

        if not hasattr(facility, "typical_materials") or not facility.typical_materials:
            if quality_level in ["professional", "medical"]:
                result.add_warning(
                    "Typical materials information is recommended for professional/medical quality levels",
                    field="typical_materials",
                    code="typical_materials_recommended",
                )
            return

        # Validate each material
        for i, material in enumerate(facility.typical_materials):
            await self._validate_material_item(material, i, quality_level, result)

    async def _validate_material_item(
        self, material: Any, index: int, quality_level: str, result: ValidationResult
    ):
        """Validate individual material item"""

        # Check required material fields
        if not hasattr(material, "material_type") or not material.material_type:
            result.add_error(
                f"Material {index}: material_type is required",
                field=f"typical_materials[{index}].material_type",
                code="material_type_required",
            )

        # Validate material type format
        if hasattr(material, "material_type") and material.material_type:
            if not self._is_valid_material_type(material.material_type):
                result.add_warning(
                    f"Material {index}: material_type '{material.material_type}' may not be standard",
                    field=f"typical_materials[{index}].material_type",
                    code="non_standard_material_type",
                )

    async def _validate_certifications(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate certifications and quality standards"""

        # Validate certifications
        if hasattr(facility, "certifications") and facility.certifications:
            for i, cert in enumerate(facility.certifications):
                if not self._is_valid_certification(cert):
                    result.add_warning(
                        f"Certification {i}: '{cert}' may not be a recognized standard",
                        field=f"certifications[{i}]",
                        code="non_standard_certification",
                    )

        # Validate quality standards
        if hasattr(facility, "quality_standards") and facility.quality_standards:
            for i, standard in enumerate(facility.quality_standards):
                if not self._is_valid_quality_standard(standard):
                    result.add_warning(
                        f"Quality standard {i}: '{standard}' may not be a recognized standard",
                        field=f"quality_standards[{i}]",
                        code="non_standard_quality_standard",
                    )

        # Check for required certifications based on quality level
        if quality_level == "medical":
            required_certifications = ["ISO 13485", "FDA", "CE"]
            if not hasattr(facility, "certifications") or not facility.certifications:
                result.add_warning(
                    "Medical quality level typically requires certifications like ISO 13485, FDA, or CE",
                    field="certifications",
                    code="medical_certifications_recommended",
                )

    def _calculate_capability_score(
        self, facility: ManufacturingFacility, quality_level: str
    ) -> float:
        """Calculate capability score (0.0-1.0)"""

        # Get validation rules for this quality level
        rules = self.validation_rules.get_okw_validation_rules(quality_level)
        required_fields = rules.get("required_fields", [])
        optional_fields = rules.get("optional_fields", [])

        # Count present fields
        facility_dict = facility.to_dict()
        required_present = sum(
            1
            for field in required_fields
            if field in facility_dict and facility_dict[field] is not None
        )
        optional_present = sum(
            1
            for field in optional_fields
            if field in facility_dict and facility_dict[field] is not None
        )

        # Calculate score (required fields weighted more heavily)
        if not required_fields:
            return 0.0

        required_score = required_present / len(required_fields)
        optional_score = (
            optional_present / len(optional_fields) if optional_fields else 1.0
        )

        # Weight: 70% required fields, 30% optional fields
        base_score = 0.7 * required_score + 0.3 * optional_score

        # Bonus points for additional capabilities
        bonus_score = 0.0

        # Equipment bonus
        if hasattr(facility, "equipment") and facility.equipment:
            equipment_count = len(facility.equipment)
            bonus_score += min(0.1, equipment_count * 0.02)  # Max 0.1 bonus

        # Process bonus
        if (
            hasattr(facility, "manufacturing_processes")
            and facility.manufacturing_processes
        ):
            process_count = len(facility.manufacturing_processes)
            bonus_score += min(0.1, process_count * 0.02)  # Max 0.1 bonus

        # Certification bonus
        if hasattr(facility, "certifications") and facility.certifications:
            cert_count = len(facility.certifications)
            bonus_score += min(0.1, cert_count * 0.05)  # Max 0.1 bonus

        return min(1.0, base_score + bonus_score)

    async def _add_optional_field_warnings(
        self,
        facility: ManufacturingFacility,
        quality_level: str,
        result: ValidationResult,
    ):
        """Add warnings for missing optional fields"""

        rules = self.validation_rules.get_okw_validation_rules(quality_level)
        optional_fields = rules.get("optional_fields", [])

        facility_dict = facility.to_dict()
        missing_optional = [
            field
            for field in optional_fields
            if field not in facility_dict or facility_dict[field] is None
        ]

        for field in missing_optional:
            result.add_warning(
                f"Optional field '{field}' is missing, consider adding for better documentation",
                field=field,
                code="optional_field_missing",
            )

    def _is_valid_facility_type(self, facility_type: str) -> bool:
        """Check if facility type is valid"""
        valid_types = [
            "machine_shop",
            "fab_lab",
            "makerspace",
            "manufacturing_plant",
            "prototype_lab",
            "assembly_facility",
            "research_lab",
            "production_facility",
        ]
        return facility_type in valid_types

    def _validate_coordinates(self, coordinates: Any) -> bool:
        """Validate coordinate format"""
        if not coordinates:
            return False

        # Check if coordinates have lat/lng
        if hasattr(coordinates, "latitude") and hasattr(coordinates, "longitude"):
            try:
                lat = float(coordinates.latitude)
                lng = float(coordinates.longitude)
                return -90 <= lat <= 90 and -180 <= lng <= 180
            except (ValueError, TypeError):
                return False

        return False

    def _is_valid_country_code(self, country_code: str) -> bool:
        """Check if country code is valid ISO format"""
        # Basic ISO country code validation (2 or 3 characters)
        return len(country_code) in [2, 3] and country_code.isalpha()

    def _is_valid_equipment_type(self, equipment_type: str) -> bool:
        """Check if equipment type is valid"""
        valid_types = [
            "cnc_mill",
            "cnc_lathe",
            "3d_printer",
            "laser_cutter",
            "water_jet",
            "injection_molding",
            "press_brake",
            "welder",
            "assembly_station",
            "quality_control",
            "packaging",
            "material_handling",
        ]
        return equipment_type in valid_types

    def _validate_equipment_specifications(self, specifications: Any) -> bool:
        """Validate equipment specifications format"""
        if not specifications:
            return False

        # Check if specifications is a dict or has common specification fields
        if isinstance(specifications, dict):
            return True

        # Check if it's an object with specification fields
        spec_fields = ["capacity", "precision", "speed", "power", "dimensions"]
        return any(hasattr(specifications, field) for field in spec_fields)

    def _is_valid_manufacturing_process(self, process: str) -> bool:
        """Check if manufacturing process is valid"""
        valid_processes = [
            "https://en.wikipedia.org/wiki/CNC_mill",
            "https://en.wikipedia.org/wiki/3D_printing",
            "https://en.wikipedia.org/wiki/CNC_lathe",
            "https://en.wikipedia.org/wiki/Laser_cutting",
            "https://en.wikipedia.org/wiki/Water_jet_cutting",
            "https://en.wikipedia.org/wiki/Injection_molding",
            "https://en.wikipedia.org/wiki/Sheet_metal_forming",
            "https://en.wikipedia.org/wiki/Welding",
            "https://en.wikipedia.org/wiki/Assembly",
        ]
        return process in valid_processes

    def _is_valid_material_type(self, material_type: str) -> bool:
        """Check if material type is valid"""
        # Check if it's a Wikipedia URL or standard material name
        if material_type.startswith("https://en.wikipedia.org/wiki/"):
            return True

        valid_materials = [
            "aluminum",
            "steel",
            "plastic",
            "wood",
            "ceramic",
            "composite",
            "titanium",
            "brass",
            "copper",
            "stainless_steel",
            "carbon_fiber",
        ]
        return material_type.lower() in valid_materials

    def _is_valid_certification(self, certification: str) -> bool:
        """Check if certification is valid"""
        valid_certifications = [
            "ISO 9001",
            "ISO 14001",
            "ISO 13485",
            "AS9100",
            "IATF 16949",
            "FDA",
            "CE",
            "UL",
            "CSA",
            "TUV",
            "DNV",
            "ABS",
        ]
        return certification in valid_certifications

    def _is_valid_quality_standard(self, standard: str) -> bool:
        """Check if quality standard is valid"""
        valid_standards = [
            "ISO 9001",
            "ISO 14001",
            "ISO 13485",
            "AS9100",
            "IATF 16949",
            "Six Sigma",
            "Lean Manufacturing",
            "Total Quality Management",
        ]
        return standard in valid_standards
