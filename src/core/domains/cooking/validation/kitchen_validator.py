"""
Enhanced kitchen validator for cooking domain.

This module provides an enhanced kitchen validator that integrates with
the new validation framework.
"""

import re
from typing import Any, Dict, List, Optional

from ....models.supply_trees import SupplyTree
from ....validation.context import ValidationContext
from ....validation.engine import Validator
from ....validation.result import ValidationError, ValidationResult, ValidationWarning
from ....validation.rules.cooking import CookingValidationRules


class CookingKitchenValidator(Validator):
    """Enhanced kitchen validator for cooking domain using new validation framework"""

    def __init__(self):
        self.validation_rules = CookingValidationRules()

    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "kitchen"

    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 70  # Medium priority for kitchen validation

    async def validate(
        self, data: Any, context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate kitchen data using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Handle different data types
        if isinstance(data, dict):
            return await self._validate_kitchen_dict(data, context)
        elif isinstance(data, SupplyTree):
            # Extract kitchen data from supply tree
            kitchen_data = self._extract_kitchen_from_supply_tree(data)
            return await self._validate_kitchen_dict(kitchen_data, context)
        else:
            result.add_error(
                f"Unsupported data type for kitchen validation: {type(data)}"
            )
            return result

    async def _validate_kitchen_dict(
        self, kitchen_data: Dict[str, Any], context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate kitchen dictionary using domain-specific rules"""
        result = ValidationResult(valid=True)

        # Get quality level from context or default to home
        quality_level = "home"
        if context:
            quality_level = context.quality_level

        # Validate quality level is supported
        if not CookingValidationRules.validate_quality_level(quality_level):
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result

        # Get validation rules for this quality level
        rules = self.validation_rules.get_kitchen_validation_rules(quality_level)

        # Validate required fields
        required_fields = rules.get("required_fields", [])
        missing_fields = self.validation_rules.get_missing_required_fields(
            kitchen_data, quality_level
        )

        for field in missing_fields:
            result.add_error(
                f"Required field '{field}' is missing for {quality_level} quality level",
                field=field,
                code="required_field_missing",
            )

        # Validate field content based on quality level
        await self._validate_field_content(kitchen_data, quality_level, result)

        # Validate location information
        await self._validate_location(kitchen_data, quality_level, result)

        # Validate equipment
        await self._validate_equipment(kitchen_data, quality_level, result)

        # Validate capacity
        await self._validate_capacity(kitchen_data, quality_level, result)

        # Validate amenities
        await self._validate_amenities(kitchen_data, quality_level, result)

        # Validate certifications
        await self._validate_certifications(kitchen_data, quality_level, result)

        # Validate food safety compliance
        await self._validate_food_safety(kitchen_data, quality_level, result)

        # Calculate kitchen capability score
        capability_score = self._calculate_capability_score(kitchen_data, quality_level)
        result.metadata["capability_score"] = capability_score

        # Add warnings for missing optional fields
        await self._add_optional_field_warnings(kitchen_data, quality_level, result)

        return result

    async def _validate_field_content(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate content of individual fields"""

        # Validate kitchen name
        if "name" in kitchen_data and kitchen_data["name"]:
            name = kitchen_data["name"]
            if len(name.strip()) < 3:
                result.add_warning(
                    "Kitchen name is very short, consider providing a more descriptive name",
                    field="name",
                    code="name_too_short",
                )
            elif len(name.strip()) > 100:
                result.add_warning(
                    "Kitchen name is very long, consider shortening it",
                    field="name",
                    code="name_too_long",
                )

        # Validate description
        if "description" in kitchen_data and kitchen_data["description"]:
            description = kitchen_data["description"]
            if len(description.strip()) < 10:
                result.add_warning(
                    "Description is very brief, consider providing more detail",
                    field="description",
                    code="description_brief",
                )

    async def _validate_location(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate location information"""

        if "location" not in kitchen_data or not kitchen_data["location"]:
            result.add_error(
                "Location information is required",
                field="location",
                code="location_required",
            )
            return

        location = kitchen_data["location"]

        # Validate address
        if isinstance(location, str):
            if len(location.strip()) < 10:
                result.add_warning(
                    "Location address seems incomplete, consider providing full address",
                    field="location",
                    code="location_incomplete",
                )
        elif isinstance(location, dict):
            # Validate structured location
            await self._validate_structured_location(location, quality_level, result)
        else:
            result.add_warning(
                "Location should be a string or dictionary",
                field="location",
                code="location_invalid_format",
            )

    async def _validate_structured_location(
        self, location: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate structured location information"""

        # Validate address
        if "address" in location and location["address"]:
            if len(location["address"].strip()) < 10:
                result.add_warning(
                    "Address seems incomplete, consider providing full address",
                    field="location.address",
                    code="address_incomplete",
                )

        # Validate coordinates
        if "coordinates" in location and location["coordinates"]:
            if not self._validate_coordinates(location["coordinates"]):
                result.add_error(
                    "Invalid coordinates format",
                    field="location.coordinates",
                    code="invalid_coordinates",
                )

        # Validate country code
        if "country_code" in location and location["country_code"]:
            if not self._is_valid_country_code(location["country_code"]):
                result.add_warning(
                    f"Country code '{location['country_code']}' may not be standard ISO format",
                    field="location.country_code",
                    code="non_standard_country_code",
                )

    async def _validate_equipment(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate equipment information"""

        if "equipment" not in kitchen_data or not kitchen_data["equipment"]:
            result.add_error(
                "Equipment information is required",
                field="equipment",
                code="equipment_required",
            )
            return

        equipment = kitchen_data["equipment"]

        # Validate equipment format
        if not isinstance(equipment, list):
            result.add_error(
                "Equipment must be a list", field="equipment", code="equipment_not_list"
            )
            return

        if len(equipment) == 0:
            result.add_error(
                "At least one piece of equipment is required",
                field="equipment",
                code="no_equipment",
            )
            return

        # Validate each piece of equipment
        for i, equipment_item in enumerate(equipment):
            await self._validate_equipment_item(
                equipment_item, i, quality_level, result
            )

    async def _validate_equipment_item(
        self,
        equipment_item: Any,
        index: int,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate individual equipment item"""

        if isinstance(equipment_item, str):
            # Simple string equipment
            if len(equipment_item.strip()) < 2:
                result.add_error(
                    f"Equipment {index}: equipment description is too short",
                    field=f"equipment[{index}]",
                    code="equipment_too_short",
                )
        elif isinstance(equipment_item, dict):
            # Structured equipment
            await self._validate_structured_equipment(
                equipment_item, index, quality_level, result
            )
        else:
            result.add_error(
                f"Equipment {index}: invalid format, must be string or dict",
                field=f"equipment[{index}]",
                code="equipment_invalid_format",
            )

    async def _validate_structured_equipment(
        self,
        equipment: Dict[str, Any],
        index: int,
        quality_level: str,
        result: ValidationResult,
    ):
        """Validate structured equipment"""

        # Check required fields
        if "name" not in equipment or not equipment["name"]:
            result.add_error(
                f"Equipment {index}: name is required",
                field=f"equipment[{index}].name",
                code="equipment_name_required",
            )

        if "type" not in equipment or not equipment["type"]:
            result.add_error(
                f"Equipment {index}: type is required",
                field=f"equipment[{index}].type",
                code="equipment_type_required",
            )

        # Validate equipment type
        if "type" in equipment and equipment["type"]:
            if not self._is_valid_equipment_type(equipment["type"]):
                result.add_warning(
                    f"Equipment {index}: type '{equipment['type']}' may not be standard",
                    field=f"equipment[{index}].type",
                    code="equipment_type_non_standard",
                )

        # Validate specifications
        if "specifications" in equipment and equipment["specifications"]:
            if not self._validate_equipment_specifications(equipment["specifications"]):
                result.add_warning(
                    f"Equipment {index}: specifications format may be invalid",
                    field=f"equipment[{index}].specifications",
                    code="equipment_specifications_invalid",
                )

        # Validate capacity
        if "capacity" in equipment and equipment["capacity"]:
            if not self._is_valid_capacity(equipment["capacity"]):
                result.add_warning(
                    f"Equipment {index}: capacity format may be invalid",
                    field=f"equipment[{index}].capacity",
                    code="equipment_capacity_invalid",
                )

        # Validate features
        if "features" in equipment and equipment["features"]:
            if not self._is_valid_features_list(equipment["features"]):
                result.add_warning(
                    f"Equipment {index}: features format may be invalid",
                    field=f"equipment[{index}].features",
                    code="equipment_features_invalid",
                )

    async def _validate_capacity(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate kitchen capacity"""

        if "capacity" not in kitchen_data or not kitchen_data["capacity"]:
            if quality_level in ["commercial", "professional"]:
                result.add_error(
                    "Capacity information is required for commercial/professional quality levels",
                    field="capacity",
                    code="capacity_required",
                )
            else:
                result.add_warning(
                    "No capacity information provided",
                    field="capacity",
                    code="capacity_missing",
                )
            return

        capacity = kitchen_data["capacity"]

        # Validate capacity format
        if isinstance(capacity, (int, float)):
            if capacity <= 0:
                result.add_error(
                    "Capacity must be greater than 0",
                    field="capacity",
                    code="capacity_invalid",
                )
            elif capacity > 1000:
                result.add_warning(
                    "Capacity seems unusually high",
                    field="capacity",
                    code="capacity_high",
                )
        elif isinstance(capacity, str):
            if not self._is_valid_capacity(capacity):
                result.add_warning(
                    "Capacity format may be invalid",
                    field="capacity",
                    code="capacity_format_invalid",
                )
        else:
            result.add_warning(
                "Capacity should be a number or string",
                field="capacity",
                code="capacity_invalid_type",
            )

    async def _validate_amenities(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate kitchen amenities"""

        if "amenities" not in kitchen_data or not kitchen_data["amenities"]:
            if quality_level in ["commercial", "professional"]:
                result.add_warning(
                    "Amenities information is recommended for commercial/professional quality levels",
                    field="amenities",
                    code="amenities_recommended",
                )
            return

        amenities = kitchen_data["amenities"]

        # Validate amenities format
        if isinstance(amenities, list):
            if len(amenities) == 0:
                result.add_warning(
                    "Amenities list is empty", field="amenities", code="amenities_empty"
                )
            else:
                # Validate each amenity
                for i, amenity in enumerate(amenities):
                    if not isinstance(amenity, str) or len(amenity.strip()) < 2:
                        result.add_warning(
                            f"Amenity {i+1}: description is too short or invalid",
                            field=f"amenities[{i}]",
                            code="amenity_invalid",
                        )
        elif isinstance(amenities, str):
            if len(amenities.strip()) < 5:
                result.add_warning(
                    "Amenities description is very brief",
                    field="amenities",
                    code="amenities_brief",
                )
        else:
            result.add_warning(
                "Amenities should be a list or string",
                field="amenities",
                code="amenities_invalid_format",
            )

    async def _validate_certifications(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate kitchen certifications"""

        if "certifications" not in kitchen_data or not kitchen_data["certifications"]:
            if quality_level in ["commercial", "professional"]:
                result.add_warning(
                    "Certifications are recommended for commercial/professional quality levels",
                    field="certifications",
                    code="certifications_recommended",
                )
            return

        certifications = kitchen_data["certifications"]

        # Validate certifications format
        if isinstance(certifications, list):
            for i, cert in enumerate(certifications):
                if not self._is_valid_certification(cert):
                    result.add_warning(
                        f"Certification {i+1}: '{cert}' may not be a recognized standard",
                        field=f"certifications[{i}]",
                        code="certification_non_standard",
                    )
        elif isinstance(certifications, str):
            if not self._is_valid_certification(certifications):
                result.add_warning(
                    f"Certification '{certifications}' may not be a recognized standard",
                    field="certifications",
                    code="certification_non_standard",
                )
        else:
            result.add_warning(
                "Certifications should be a list or string",
                field="certifications",
                code="certifications_invalid_format",
            )

    async def _validate_food_safety(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate food safety compliance"""

        if (
            "food_safety_compliance" not in kitchen_data
            or not kitchen_data["food_safety_compliance"]
        ):
            if quality_level in ["commercial", "professional"]:
                result.add_warning(
                    "Food safety compliance information is recommended for commercial/professional quality levels",
                    field="food_safety_compliance",
                    code="food_safety_compliance_recommended",
                )
            return

        food_safety = kitchen_data["food_safety_compliance"]

        # Validate food safety format
        if isinstance(food_safety, dict):
            # Validate structured food safety information
            await self._validate_structured_food_safety(
                food_safety, quality_level, result
            )
        elif isinstance(food_safety, str):
            if len(food_safety.strip()) < 10:
                result.add_warning(
                    "Food safety compliance description is very brief",
                    field="food_safety_compliance",
                    code="food_safety_compliance_brief",
                )
        elif isinstance(food_safety, list):
            if len(food_safety) == 0:
                result.add_warning(
                    "Food safety compliance list is empty",
                    field="food_safety_compliance",
                    code="food_safety_compliance_empty",
                )
        else:
            result.add_warning(
                "Food safety compliance should be a dictionary, string, or list",
                field="food_safety_compliance",
                code="food_safety_compliance_invalid_format",
            )

    async def _validate_structured_food_safety(
        self, food_safety: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Validate structured food safety information"""

        # Validate HACCP compliance
        if "haccp" in food_safety:
            if not isinstance(food_safety["haccp"], bool):
                result.add_warning(
                    "HACCP compliance should be a boolean value",
                    field="food_safety_compliance.haccp",
                    code="haccp_invalid_type",
                )

        # Validate temperature control
        if "temperature_control" in food_safety:
            if not isinstance(food_safety["temperature_control"], bool):
                result.add_warning(
                    "Temperature control should be a boolean value",
                    field="food_safety_compliance.temperature_control",
                    code="temperature_control_invalid_type",
                )

        # Validate cleaning procedures
        if "cleaning_procedures" in food_safety:
            if not isinstance(food_safety["cleaning_procedures"], (str, list)):
                result.add_warning(
                    "Cleaning procedures should be a string or list",
                    field="food_safety_compliance.cleaning_procedures",
                    code="cleaning_procedures_invalid_type",
                )

    def _calculate_capability_score(
        self, kitchen_data: Dict[str, Any], quality_level: str
    ) -> float:
        """Calculate kitchen capability score (0.0-1.0)"""

        # Get validation rules for this quality level
        rules = self.validation_rules.get_kitchen_validation_rules(quality_level)
        required_fields = rules.get("required_fields", [])
        optional_fields = rules.get("optional_fields", [])

        # Count present fields
        required_present = sum(
            1
            for field in required_fields
            if field in kitchen_data and kitchen_data[field] is not None
        )
        optional_present = sum(
            1
            for field in optional_fields
            if field in kitchen_data and kitchen_data[field] is not None
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
        if "equipment" in kitchen_data and kitchen_data["equipment"]:
            equipment_count = len(kitchen_data["equipment"])
            bonus_score += min(0.1, equipment_count * 0.02)  # Max 0.1 bonus

        # Amenities bonus
        if "amenities" in kitchen_data and kitchen_data["amenities"]:
            if isinstance(kitchen_data["amenities"], list):
                amenities_count = len(kitchen_data["amenities"])
                bonus_score += min(0.1, amenities_count * 0.02)  # Max 0.1 bonus

        # Certification bonus
        if "certifications" in kitchen_data and kitchen_data["certifications"]:
            if isinstance(kitchen_data["certifications"], list):
                cert_count = len(kitchen_data["certifications"])
                bonus_score += min(0.1, cert_count * 0.05)  # Max 0.1 bonus

        return min(1.0, base_score + bonus_score)

    async def _add_optional_field_warnings(
        self, kitchen_data: Dict[str, Any], quality_level: str, result: ValidationResult
    ):
        """Add warnings for missing optional fields"""

        rules = self.validation_rules.get_kitchen_validation_rules(quality_level)
        optional_fields = rules.get("optional_fields", [])

        missing_optional = [
            field
            for field in optional_fields
            if field not in kitchen_data or kitchen_data[field] is None
        ]

        for field in missing_optional:
            result.add_warning(
                f"Optional field '{field}' is missing, consider adding for better documentation",
                field=field,
                code="optional_field_missing",
            )

    def _extract_kitchen_from_supply_tree(
        self, supply_tree: SupplyTree
    ) -> Dict[str, Any]:
        """Extract kitchen data from supply tree"""
        # This is a simplified extraction - in a real implementation,
        # this would parse the supply tree to extract kitchen information

        kitchen_data = {
            "name": "Extracted Kitchen",
            "location": "Unknown",
            "equipment": [],
        }

        # Extract equipment from supply tree nodes
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]["data"]
                if hasattr(node, "name") and "equipment" in node.name.lower():
                    kitchen_data["equipment"].append(node.name)

        return kitchen_data

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
            "stove",
            "oven",
            "refrigerator",
            "freezer",
            "microwave",
            "dishwasher",
            "sink",
            "counter",
            "island",
            "pantry",
            "storage",
            "prep_station",
            "grill",
            "fryer",
            "steamer",
            "mixer",
            "blender",
            "food_processor",
        ]
        return equipment_type.lower() in valid_types

    def _validate_equipment_specifications(self, specifications: Any) -> bool:
        """Validate equipment specifications format"""
        if not specifications:
            return False

        # Check if specifications is a dict or has common specification fields
        if isinstance(specifications, dict):
            return True

        # Check if it's an object with specification fields
        spec_fields = ["capacity", "power", "dimensions", "features", "brand", "model"]
        return any(hasattr(specifications, field) for field in spec_fields)

    def _is_valid_capacity(self, capacity: Any) -> bool:
        """Check if capacity is valid"""
        if isinstance(capacity, (int, float)):
            return capacity > 0
        elif isinstance(capacity, str):
            # Check for common capacity patterns
            patterns = [
                r"^\d+(\.\d+)?$",  # Simple number
                r"^\d+(\.\d+)?\s*people$",  # Number of people
                r"^\d+(\.\d+)?\s*guests$",  # Number of guests
                r"^\d+(\.\d+)?\s*seats$",  # Number of seats
            ]
            return any(
                re.match(pattern, capacity.strip(), re.IGNORECASE)
                for pattern in patterns
            )
        return False

    def _is_valid_features_list(self, features: Any) -> bool:
        """Check if features list is valid"""
        if isinstance(features, list):
            return all(
                isinstance(feature, str) and len(feature.strip()) > 0
                for feature in features
            )
        elif isinstance(features, str):
            return len(features.strip()) > 0
        return False

    def _is_valid_certification(self, certification: str) -> bool:
        """Check if certification is valid"""
        valid_certifications = [
            "ServSafe",
            "HACCP",
            "Food Safety Manager",
            "Culinary Institute",
            "Health Department Approved",
            "Food Handler",
            "Sanitation",
            "ISO 22000",
            "BRC",
            "SQF",
            "FSSC 22000",
        ]
        return certification in valid_certifications
