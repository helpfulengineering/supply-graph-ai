"""
UUID Validation Utilities

This module provides utilities for validating and fixing UUID-related issues
in OKH and OKW files.
"""

import logging
import re
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class UUIDValidator:
    """Utility class for UUID validation and generation"""

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """
        Check if a string is a valid UUID format.

        Args:
            uuid_string: String to validate

        Returns:
            True if valid UUID format, False otherwise
        """
        if not isinstance(uuid_string, str):
            return False

        try:
            UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def generate_uuid_from_string(input_string: str) -> str:
        """
        Generate a deterministic UUID from a string using a simple hash-based approach.

        Args:
            input_string: String to convert to UUID

        Returns:
            Valid UUID string
        """
        import hashlib

        # Create a hash of the input string
        hash_obj = hashlib.md5(input_string.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        # Format as UUID
        uuid_str = f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"

        # Validate the generated UUID
        if UUIDValidator.is_valid_uuid(uuid_str):
            return uuid_str
        else:
            # Fallback to random UUID if hash-based approach fails
            return str(uuid4())

    @staticmethod
    def fix_invalid_uuid(uuid_string: str, fallback_to_random: bool = False) -> str:
        """
        Attempt to fix an invalid UUID string.

        Args:
            uuid_string: Invalid UUID string to fix
            fallback_to_random: If True, generate random UUID if fixing fails

        Returns:
            Valid UUID string
        """
        if UUIDValidator.is_valid_uuid(uuid_string):
            return uuid_string

        # Try to clean up common issues
        cleaned = uuid_string.strip().lower()

        # Remove common prefixes/suffixes
        cleaned = re.sub(r"^(id|uuid|guid)[-_]?", "", cleaned)
        cleaned = re.sub(r"[-_]?(id|uuid|guid)$", "", cleaned)

        # Try to fix common formatting issues
        # Remove spaces and convert to hyphens
        cleaned = re.sub(r"[_\s]+", "-", cleaned)

        # If it looks like it might be a UUID with wrong separators
        if re.match(
            r"^[0-9a-f]{8}[0-9a-f]{4}[0-9a-f]{4}[0-9a-f]{4}[0-9a-f]{12}$",
            cleaned.replace("-", ""),
        ):
            # Try to add proper UUID formatting
            hex_only = cleaned.replace("-", "")
            if len(hex_only) == 32:
                uuid_str = f"{hex_only[:8]}-{hex_only[8:12]}-{hex_only[12:16]}-{hex_only[16:20]}-{hex_only[20:32]}"
                if UUIDValidator.is_valid_uuid(uuid_str):
                    return uuid_str

        # If it's a meaningful string, generate deterministic UUID
        if len(uuid_string) > 3 and not re.match(r"^[0-9]+$", uuid_string):
            return UUIDValidator.generate_uuid_from_string(uuid_string)

        # Fallback to random UUID
        if fallback_to_random:
            return str(uuid4())

        # If no fallback, return the original (will cause validation to fail)
        return uuid_string

    @staticmethod
    def validate_and_fix_okw_data(okw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix UUID issues in OKW data.

        Args:
            okw_data: OKW data dictionary

        Returns:
            Fixed OKW data dictionary
        """
        fixed_data = okw_data.copy()

        # Check and fix ID field
        if "id" in fixed_data:
            original_id = fixed_data["id"]
            if not UUIDValidator.is_valid_uuid(original_id):
                logger.warning(f"Invalid UUID in OKW data: {original_id}")
                fixed_id = UUIDValidator.fix_invalid_uuid(
                    original_id, fallback_to_random=True
                )
                fixed_data["id"] = fixed_id
                logger.info(f"Fixed UUID: {original_id} -> {fixed_id}")

        return fixed_data

    @staticmethod
    def validate_and_fix_okh_data(okh_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix UUID issues in OKH data.

        Args:
            okh_data: OKH data dictionary

        Returns:
            Fixed OKH data dictionary
        """
        fixed_data = okh_data.copy()

        # Check and fix ID field
        if "id" in fixed_data:
            original_id = fixed_data["id"]
            if not UUIDValidator.is_valid_uuid(original_id):
                logger.warning(f"Invalid UUID in OKH data: {original_id}")
                fixed_id = UUIDValidator.fix_invalid_uuid(
                    original_id, fallback_to_random=True
                )
                fixed_data["id"] = fixed_id
                logger.info(f"Fixed UUID: {original_id} -> {fixed_id}")

        return fixed_data
