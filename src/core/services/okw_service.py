import json
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from ..domains.manufacturing.validation.okw_validator import ManufacturingOKWValidator
from ..validation.context import ValidationContext
from .base import BaseService, ServiceConfig
from .storage_service import StorageService
from ..models.okw import ManufacturingFacility
from ..utils.logging import get_logger
from ..storage.smart_discovery import SmartFileDiscovery
from ..validation.uuid_validator import UUIDValidator

logger = get_logger(__name__)


class OKWService(BaseService["OKWService"]):
    """
    Service for managing OKW manufacturing facilities.

    This service provides functionality for:
    - Creating, reading, updating, and deleting OKW facilities
    - Validating OKW facility data
    - Managing OKW facility storage and retrieval
    - Integration with validation systems
    """

    def __init__(
        self, service_name: str = "OKWService", config: Optional[ServiceConfig] = None
    ):
        """Initialize the OKW service with base service functionality."""
        super().__init__(service_name, config)
        self.storage: Optional[StorageService] = None

    async def _initialize_dependencies(self) -> None:
        """Initialize service dependencies."""
        # Initialize storage service
        self.storage = await StorageService.get_instance()

        # Configure storage service if not already configured
        if not self.storage._configured:
            from ...config.storage_config import get_default_storage_config

            config = get_default_storage_config()
            await self.storage.configure(config)

        self.logger.info("OKW service dependencies initialized")

    async def initialize(self) -> None:
        """Initialize the OKW service with service-specific setup."""
        await self.ensure_initialized()

        # Ensure domains are registered (for fallback mode when server startup doesn't run)
        await self._ensure_domains_registered()

        # Add dependencies to base service
        self.add_dependency("storage", self.storage)

        self.logger.info("OKW service initialized successfully")

    async def create(self, facility_data: Dict[str, Any]) -> ManufacturingFacility:
        """Create a new manufacturing facility"""
        async with self.track_request("create_okw_facility"):
            await self.ensure_initialized()
            self.logger.info("Creating new manufacturing facility")

            # Create facility object - handle both dict and ManufacturingFacility inputs
            if isinstance(facility_data, ManufacturingFacility):
                facility = facility_data
            else:
                facility = ManufacturingFacility.from_dict(facility_data)

            # Store in storage with proper naming convention
            if self.storage:
                # Generate filename based on facility name and ID (similar to synthetic data)
                # Use okw/facilities/ prefix to match SmartFileDiscovery expectations
                safe_name = "".join(
                    c for c in facility.name if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                safe_name = safe_name.replace(" ", "").replace(
                    "'", ""
                )  # Remove spaces and apostrophes for filename
                filename = f"okw/facilities/general/{safe_name}.json"

                # Save to okw/facilities/general/ directory (matching the directory structure used by SmartFileDiscovery)
                facility_json = json.dumps(
                    facility.to_dict(), indent=2, ensure_ascii=False, default=str
                )
                await self.storage.manager.put_object(
                    filename, facility_json.encode("utf-8")
                )
                self.logger.info(f"Saved OKW facility to {filename}")

            return facility

    async def get(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Get a manufacturing facility by ID"""
        async with self.track_request("get_okw_facility"):
            await self.ensure_initialized()
            self.logger.info(f"Getting manufacturing facility with ID {facility_id}")

            if self.storage:
                # Use smart discovery to find OKW files
                discovery = SmartFileDiscovery(self.storage.manager)
                file_infos = await discovery.discover_files("okw")

                self.logger.info(
                    f"Found {len(file_infos)} OKW files using smart discovery"
                )

                # Search through OKW files for the matching ID
                # If multiple files have the same ID, prefer the most recently modified one
                matching_facilities = []
                for file_info in file_infos:
                    try:
                        data = await self.storage.manager.get_object(file_info.key)
                        content = data.decode("utf-8")
                        okw_data = json.loads(content)

                        # Validate and fix UUID issues
                        fixed_okw_data = UUIDValidator.validate_and_fix_okw_data(
                            okw_data
                        )

                        facility = ManufacturingFacility.from_dict(fixed_okw_data)
                        if facility.id == facility_id:
                            # Store with file info for sorting
                            matching_facilities.append((file_info, facility))
                    except Exception as e:
                        self.logger.error(
                            f"Failed to load OKW file {file_info.key}: {e}"
                        )
                        continue

                # If multiple matches, return the most recently modified one
                if matching_facilities:
                    # Sort by last_modified (most recent first)
                    matching_facilities.sort(
                        key=lambda x: (
                            x[0].last_modified if hasattr(x[0], "last_modified") else ""
                        ),
                        reverse=True,
                    )
                    self.logger.info(
                        f"Found {len(matching_facilities)} file(s) with ID {facility_id}, using most recent: {matching_facilities[0][0].key}"
                    )
                    return matching_facilities[0][1]

            return None

    async def get_by_id(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Get a manufacturing facility by ID (CLI compatibility method)"""
        return await self.get(facility_id)

    async def list(
        self,
        page: int = 1,
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ManufacturingFacility], int]:
        """List manufacturing facilities using smart discovery"""
        await self.ensure_initialized()
        logger.info(
            f"Listing manufacturing facilities (page={page}, page_size={page_size})"
        )

        if self.storage:
            # Use smart discovery to find OKW files
            discovery = SmartFileDiscovery(self.storage.manager)
            file_infos = await discovery.discover_files("okw")

            logger.info(f"Found {len(file_infos)} OKW files using smart discovery")

            # Process files and deduplicate by facility ID
            # Use a dict to track unique facilities by ID (keep most recently modified)
            facilities_by_id: Dict[UUID, ManufacturingFacility] = {}
            file_info_by_id: Dict[UUID, Any] = {}

            for file_info in file_infos:
                try:
                    data = await self.storage.manager.get_object(file_info.key)
                    content = data.decode("utf-8")
                    okw_data = json.loads(content)

                    # Validate and fix UUID issues
                    fixed_okw_data = UUIDValidator.validate_and_fix_okw_data(okw_data)

                    facility = ManufacturingFacility.from_dict(fixed_okw_data)
                    facility_id = facility.id

                    # If we haven't seen this ID, or this file is more recent, keep it
                    if facility_id not in facilities_by_id:
                        facilities_by_id[facility_id] = facility
                        file_info_by_id[facility_id] = file_info
                    else:
                        # Compare last_modified dates to keep the most recent
                        existing_modified = (
                            file_info_by_id[facility_id].last_modified
                            if hasattr(file_info_by_id[facility_id], "last_modified")
                            else None
                        )
                        current_modified = (
                            file_info.last_modified
                            if hasattr(file_info, "last_modified")
                            else None
                        )

                        if current_modified and (
                            not existing_modified
                            or current_modified > existing_modified
                        ):
                            facilities_by_id[facility_id] = facility
                            file_info_by_id[facility_id] = file_info
                            logger.debug(
                                f"Replacing facility {facility_id} with more recent version from {file_info.key}"
                            )
                except Exception as e:
                    logger.error(f"Failed to load OKW file {file_info.key}: {e}")
                    continue

            # Convert dict values to list and apply pagination
            unique_facilities = list(facilities_by_id.values())
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_facilities = unique_facilities[start_idx:end_idx]

            logger.info(
                f"Found {len(file_infos)} OKW files, {len(unique_facilities)} unique facilities (page {page}: {len(paginated_facilities)} facilities)"
            )

            return paginated_facilities, len(unique_facilities)

        return [], 0

    async def list_facilities(
        self,
        limit: int = 100,
        offset: int = 0,
        facility_type: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List[ManufacturingFacility]:
        """List manufacturing facilities with limit/offset parameters (CLI compatibility)"""
        # Convert limit/offset to page/page_size
        page_size = limit
        page = (offset // page_size) + 1

        # Build filter parameters
        filter_params = {}
        if facility_type:
            filter_params["facility_type"] = facility_type
        if status:
            filter_params["status"] = status
        if location:
            filter_params["location"] = location

        facilities, total = await self.list(
            page=page, page_size=page_size, filter_params=filter_params
        )
        return facilities

    async def update(
        self, facility_id: UUID, facility_data: Dict[str, Any]
    ) -> ManufacturingFacility:
        """Update a manufacturing facility"""
        await self.ensure_initialized()
        logger.info(f"Updating manufacturing facility with ID {facility_id}")

        # Create facility object
        facility = ManufacturingFacility.from_dict(facility_data)

        # Update in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            await handler.save_object(facility_id, facility.to_dict())

        return facility

    async def delete(self, facility_id: UUID) -> bool:
        """Delete a manufacturing facility"""
        await self.ensure_initialized()
        logger.info(f"Deleting manufacturing facility with ID {facility_id}")

        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            return await handler.delete_object(facility_id)

        return True

    async def validate(
        self,
        content: Dict[str, Any],
        validation_context: Optional[str] = None,
        strict_mode: bool = False,
    ) -> Dict[str, Any]:
        """Validate OKW facility content against canonical ManufacturingFacility dataclass"""
        await self.ensure_initialized()
        logger.info(f"Validating OKW facility content")

        try:
            # Use common validation utility that validates against canonical ManufacturingFacility dataclass
            from ..validation.model_validator import validate_okw_facility

            quality_level = (
                validation_context
                if validation_context in ["hobby", "professional", "medical"]
                else "professional"
            )

            validation_result = validate_okw_facility(
                content=content, quality_level=quality_level, strict_mode=strict_mode
            )

            # Convert to service response format (for backward compatibility)
            return {
                "is_valid": validation_result.valid,
                "valid": validation_result.valid,  # Alias for backward compatibility
                "score": validation_result.details.get("completeness_score", 1.0),
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "suggestions": validation_result.suggestions,
                "completeness_score": validation_result.details.get(
                    "completeness_score", 1.0
                ),
                "issues": [
                    {
                        "severity": "error",
                        "message": error,
                        "path": [],
                        "code": "VALIDATION_ERROR",
                    }
                    for error in validation_result.errors
                ]
                + [
                    {
                        "severity": "warning",
                        "message": warning,
                        "path": [],
                        "code": "VALIDATION_WARNING",
                    }
                    for warning in validation_result.warnings
                ],
            }

        except Exception as e:
            self.logger.error(f"Error validating OKW facility: {str(e)}", exc_info=True)
            raise ValueError(f"Validation failed: {str(e)}")

    # LLM Integration Methods
    async def prepare_llm_integration(self) -> None:
        """Prepare the OKW service for LLM integration."""
        await super().prepare_llm_integration()

        if self.is_llm_enabled():
            self.logger.info(
                "Preparing OKW service for LLM-enhanced facility management"
            )
            # Future: Initialize LLM-specific components for facility operations
            # - LLM validation rules for facility data
            # - LLM-enhanced facility matching and recommendations
            # - LLM-powered facility capability analysis

    async def handle_llm_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LLM requests for OKW facility operations."""
        if not self.is_llm_enabled():
            raise RuntimeError("LLM integration not enabled for OKW service")

        request_type = request_data.get("type")

        if request_type == "validate_facility":
            # Future: Use LLM to validate facility data and capabilities
            return {"status": "llm_validation_not_implemented"}
        elif request_type == "analyze_capabilities":
            # Future: Use LLM to analyze facility capabilities
            return {"status": "llm_analysis_not_implemented"}
        elif request_type == "recommend_facilities":
            # Future: Use LLM to recommend facilities for specific requirements
            return {"status": "llm_recommendation_not_implemented"}
        else:
            return {"error": f"Unknown LLM request type: {request_type}"}

    async def _ensure_domains_registered(self) -> None:
        """Ensure domains are registered (for fallback mode when server startup doesn't run)"""
        from ..registry.domain_registry import (
            DomainRegistry,
            DomainMetadata,
            DomainStatus,
        )

        # Check if all required domains are already registered
        required_domains = {"manufacturing", "cooking"}
        registered_domains = set(DomainRegistry.list_domains())
        if required_domains.issubset(registered_domains):
            logger.info("All required domains already registered")
            return

        logger.info("Registering domains for fallback mode...")

        try:
            # Import domain components
            from ..domains.cooking.extractors import CookingExtractor
            from ..domains.cooking.matchers import CookingMatcher
            from ..domains.cooking.validation.compatibility import (
                CookingValidatorCompat,
            )
            from ..domains.manufacturing.okh_extractor import OKHExtractor
            from ..domains.manufacturing.okh_matcher import OKHMatcher
            from ..domains.manufacturing.validation.compatibility import (
                ManufacturingOKHValidatorCompat,
            )

            # Register Cooking domain
            cooking_metadata = DomainMetadata(
                name="cooking",
                display_name="Cooking & Food Preparation",
                description="Domain for recipe and kitchen capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"recipe", "kitchen"},
                supported_output_types={"cooking_workflow", "meal_plan"},
                documentation_url="https://docs.ome.org/domains/cooking",
                maintainer="OME Cooking Team",
            )

            DomainRegistry.register_domain(
                domain_name="cooking",
                extractor=CookingExtractor(),
                matcher=CookingMatcher(),
                validator=CookingValidatorCompat(),
                metadata=cooking_metadata,
            )

            # Register Manufacturing domain
            manufacturing_metadata = DomainMetadata(
                name="manufacturing",
                display_name="Manufacturing & Hardware Production",
                description="Domain for OKH/OKW manufacturing capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"okh", "okw"},
                supported_output_types={"supply_tree", "manufacturing_plan"},
                documentation_url="https://docs.ome.org/domains/manufacturing",
                maintainer="OME Manufacturing Team",
            )

            DomainRegistry.register_domain(
                domain_name="manufacturing",
                extractor=OKHExtractor(),
                matcher=OKHMatcher(),
                validator=ManufacturingOKHValidatorCompat(),
                metadata=manufacturing_metadata,
            )

            logger.info("Successfully registered domains for fallback mode")

        except Exception as e:
            logger.error(f"Failed to register domains for fallback mode: {e}")
            # Don't raise the exception - let the service continue without domains
