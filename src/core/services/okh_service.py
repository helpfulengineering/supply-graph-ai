import httpx
import yaml
import traceback
import json
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from uuid import UUID
            
from src.config import settings
from ..generation.url_router import URLRouter
# Lazy import: GenerationEngine imports heavy dependencies (spacy, numpy, thinc)
# from ..generation.engine import GenerationEngine
from ..generation.models import PlatformType
from .base import BaseService, ServiceConfig
from .storage_service import StorageService
from ..models.okh import OKHManifest, ProcessRequirement
from ..utils.logging import get_logger
from ..generation.platforms.github import GitHubExtractor
from ..generation.platforms.gitlab import GitLabExtractor
from ..domains.manufacturing.validation.okh_validator import ManufacturingOKHValidator
from ..validation.context import ValidationContext
from ..storage.smart_discovery import SmartFileDiscovery
from ..validation.uuid_validator import UUIDValidator

if TYPE_CHECKING:
    from ..generation.engine import GenerationEngine

logger = get_logger(__name__)

class OKHService(BaseService['OKHService']):
    """
    Service for managing OKH manifests.
    
    This service provides functionality for:
    - Creating, reading, updating, and deleting OKH manifests
    - Validating OKH manifest data
    - Generating OKH manifests from project URLs
    - Managing OKH manifest storage and retrieval
    - Integration with generation engine for manifest creation
    """
    
    def __init__(self, service_name: str = "OKHService", config: Optional[ServiceConfig] = None):
        """Initialize the OKH service with base service functionality."""
        super().__init__(service_name, config)
        self.storage: Optional[StorageService] = None
        self.generation_engine: Optional[GenerationEngine] = None
        self.url_router: Optional[URLRouter] = None
    
    async def _initialize_dependencies(self) -> None:
        """Initialize service dependencies."""
        # Initialize storage service
        self.storage = await StorageService.get_instance()
        if self.storage:
            await self.storage.configure(settings.STORAGE_CONFIG)
        
        # Initialize generation engine lazily (only when needed)
        # Lazy import to avoid loading heavy dependencies (spacy, numpy, thinc) at module import time
        from ..generation.engine import GenerationEngine
        self.generation_engine = GenerationEngine()
        
        # Initialize URL router
        self.url_router = URLRouter()
        
        self.logger.info("OKH service dependencies initialized")
    
    async def initialize(self) -> None:
        """Initialize the OKH service with service-specific setup."""
        await self.ensure_initialized()
        
        # Add dependencies to base service
        self.add_dependency("storage", self.storage)
        self.add_dependency("generation_engine", self.generation_engine)
        self.add_dependency("url_router", self.url_router)
        
        self.logger.info("OKH service initialized successfully")
    
    async def create(self, manifest_data: Dict[str, Any]) -> OKHManifest:
        """Create a new OKH manifest"""
        async with self.track_request("create_okh_manifest"):
            await self.ensure_initialized()
            self.logger.info("Creating new OKH manifest")
            
            # Create manifest object - handle both dict and OKHManifest inputs
            if isinstance(manifest_data, OKHManifest):
                manifest = manifest_data
            else:
                manifest = OKHManifest.from_dict(manifest_data)
            
            # Store in storage with -okh.json suffix pattern (consistent with synthetic data)
            if self.storage:
                # Generate filename based on title and ID (similar to synthetic data)
                safe_title = "".join(c for c in manifest.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '-').lower()
                filename = f"{safe_title}-{str(manifest.id)[:8]}-okh.json"
                
                # Save directly to storage root
                manifest_json = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, default=str)
                await self.storage.manager.put_object(filename, manifest_json.encode('utf-8'))
                self.logger.info(f"Saved OKH manifest to {filename}")
            
            return manifest
    
    async def get(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Get an OKH manifest by ID"""
        async with self.track_request("get_okh_manifest"):
            try:
                await self.ensure_initialized()
                self.logger.info(f"Getting OKH manifest with ID {manifest_id}")
                
                if not self.storage:
                    self.logger.error("Storage service not available")
                    return None
                
                self.logger.info("Storage service is available, searching for OKH files...")
                
                # Use smart discovery to find OKH files
                discovery = SmartFileDiscovery(self.storage.manager)
                file_infos = await discovery.discover_files("okh")
                
                self.logger.info(f"Found {len(file_infos)} OKH files using smart discovery")
                
                # Search through OKH files for the matching ID
                for file_info in file_infos:
                    try:
                        data = await self.storage.manager.get_object(file_info.key)
                        content = data.decode('utf-8')
                        okh_data = json.loads(content)
                        
                        self.logger.debug(f"Loaded OKH data from {file_info.key}, ID: {okh_data.get('id')}")
                        
                        # Validate and fix UUID issues
                        fixed_okh_data = UUIDValidator.validate_and_fix_okh_data(okh_data)
                        
                        # Check if this is the manifest we're looking for
                        if fixed_okh_data.get("id") == str(manifest_id):
                            self.logger.info(f"Found matching OKH manifest in {file_info.key}")
                            manifest = OKHManifest.from_dict(fixed_okh_data)
                            self.logger.info(f"Successfully created OKHManifest object for {manifest.title}")
                            return manifest
                        else:
                            self.logger.debug(f"ID mismatch: looking for {manifest_id}, found {fixed_okh_data.get('id')}")
                            
                    except Exception as e:
                        self.logger.error(f"Failed to load OKH file {file_info.key}: {e}")
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        continue
                
                self.logger.warning(f"OKH manifest with ID {manifest_id} not found. Searched {len(file_infos)} OKH files")
                return None
                
            except Exception as e:
                self.logger.error(f"Unexpected error in get method: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise
    
    async def get_by_id(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Get an OKH manifest by ID (CLI compatibility method)"""
        return await self.get(manifest_id)
    
    async def fetch_from_url(self, url: str) -> OKHManifest:
        """Fetch an OKH manifest from a remote URL"""
        async with self.track_request("fetch_okh_from_url"):
            await self.ensure_initialized()
            self.logger.info(f"Fetching OKH manifest from URL: {url}")
            
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # Try to parse as YAML first, then JSON
                    content = response.text
                    try:
                        if url.endswith('.yaml') or url.endswith('.yml') or 'yaml' in response.headers.get('content-type', ''):
                            data = yaml.safe_load(content)
                        else:
                            data = json.loads(content)
                    except (yaml.YAMLError, json.JSONDecodeError) as e:
                        self.logger.error(f"Failed to parse manifest content: {e}")
                        raise ValueError(f"Invalid manifest format: {e}")
                    
                    # Create manifest object
                    manifest = OKHManifest.from_dict(data)
                    self.logger.info(f"Successfully fetched OKH manifest: {manifest.id}")
                    return manifest
                    
            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error fetching manifest from {url}: {e}")
                raise ValueError(f"Failed to fetch manifest from URL: {e}")
            except Exception as e:
                self.logger.error(f"Error fetching manifest from {url}: {e}")
                raise ValueError(f"Error fetching manifest: {e}")
    
    async def list(
        self, 
        page: int = 1, 
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[OKHManifest], int]:
        """List OKH manifests"""
        async with self.track_request("list_okh_manifests"):
            await self.ensure_initialized()
            self.logger.info(f"Listing OKH manifests (page={page}, page_size={page_size})")
            
            if self.storage:
                # Use smart discovery to find OKH files
                discovery = SmartFileDiscovery(self.storage.manager)
                file_infos = await discovery.discover_files("okh")
                
                self.logger.info(f"Found {len(file_infos)} OKH files using smart discovery")
                
                # Process files and apply pagination
                objects = []
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                
                for file_info in file_infos[start_idx:end_idx]:
                    try:
                        data = await self.storage.manager.get_object(file_info.key)
                        content = data.decode('utf-8')
                        okh_data = json.loads(content)
                        
                        # Validate and fix UUID issues
                        fixed_okh_data = UUIDValidator.validate_and_fix_okh_data(okh_data)
                        
                        objects.append(OKHManifest.from_dict(fixed_okh_data))
                    except Exception as e:
                        self.logger.error(f"Failed to load OKH file {file_info.key}: {e}")
                        continue
                
                return objects, len(file_infos)
        
        return [], 0
    
    async def list_manifests(self, limit: int = 100, offset: int = 0) -> List[OKHManifest]:
        """List OKH manifests with limit/offset parameters (CLI compatibility)"""
        # Convert limit/offset to page/page_size
        page_size = limit
        page = (offset // page_size) + 1
        
        manifests, total = await self.list(page=page, page_size=page_size)
        return manifests
    
    async def update(self, manifest_id: UUID, manifest_data: Dict[str, Any]) -> OKHManifest:
        """Update an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Updating OKH manifest with ID {manifest_id}")
        
        # Create manifest object
        manifest = OKHManifest.from_dict(manifest_data)
        
        # Update in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            await handler.save_object(manifest_id, manifest.to_dict())
        
        return manifest
    
    async def delete(self, manifest_id: UUID) -> bool:
        """Delete an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Deleting OKH manifest with ID {manifest_id}")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            return await handler.delete_object(manifest_id)
        
        return True
    
    async def extract_requirements(self, manifest_id: UUID) -> List[ProcessRequirement]:
        """Extract manufacturing requirements from an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Extracting requirements from OKH manifest {manifest_id}")
        
        manifest = await self.get(manifest_id)
        if not manifest:
            return []
            
        return manifest.extract_requirements()
    
    async def validate(self, content: Dict[str, Any], validation_context: Optional[str] = None, strict_mode: bool = False) -> Dict[str, Any]:
        """Validate OKH manifest content using the new validation framework"""
        await self.ensure_initialized()
        logger.info(f"Validating OKH manifest content")
        
        try:
            # Create validator
            validator = ManufacturingOKHValidator()
            
            # Create validation context if provided
            context = None
            if validation_context:
                context = ValidationContext(
                    name=f"okh_validation_{validation_context}",
                    domain="manufacturing",
                    quality_level=validation_context if validation_context in ["hobby", "professional", "medical"] else "professional",
                    strict_mode=strict_mode
                )
            
            # Validate the content
            result = await validator.validate(content, context)
            
            # Convert to API response format
            return {
                "valid": result.valid,
                "normalized_content": content,  # For now, return original content
                "completeness_score": result.metadata.get("completeness_score", 0.0),
                "issues": [
                    {
                        "severity": "error",
                        "message": error.message,
                        "path": [error.field] if error.field else [],
                        "code": error.code
                    } for error in result.errors
                ] + [
                    {
                        "severity": "warning", 
                        "message": warning.message,
                        "path": [warning.field] if warning.field else [],
                        "code": warning.code
                    } for warning in result.warnings
                ]
            }
            
        except Exception as e:
            logger.error(f"Error validating OKH manifest: {str(e)}")
            raise ValueError(f"Validation failed: {str(e)}")
    
    async def generate_from_url(self, url: str, skip_review: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """Generate OKH manifest from repository URL"""
        try:
            await self.ensure_initialized()
            
            # Validate and route URL
            router = URLRouter()
            if not router.validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            platform = router.detect_platform(url)
            if platform is None:
                raise ValueError(f"Unsupported platform for URL: {url}")
            
            # Get platform-specific generator
            if platform == PlatformType.GITHUB:
                generator = GitHubExtractor()
            elif platform == PlatformType.GITLAB:

                generator = GitLabExtractor()
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Generate project data
            project_data = await generator.extract_project(url)
            
            # Generate manifest
            # Lazy import to avoid loading heavy dependencies at module import time
            from ..generation.engine import GenerationEngine
            engine = GenerationEngine()
            result = await engine.generate_manifest_async(project_data, include_file_metadata=verbose)
            
            # Note: Review interface is handled by CLI, not API service
            
            # Convert to response format
            manifest_dict = result.to_dict()
            
            return {
                "success": True,
                "message": "Manifest generated successfully",
                "manifest": manifest_dict,
                "quality_report": {
                    "overall_quality": result.quality_report.overall_quality,
                    "required_fields_complete": result.quality_report.required_fields_complete,
                    "missing_required_fields": result.quality_report.missing_required_fields,
                    "recommendations": result.quality_report.recommendations
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating manifest from URL {url}: {str(e)}")
            raise ValueError(f"Generation failed: {str(e)}")
    
    # LLM Integration Methods
    async def prepare_llm_integration(self) -> None:
        """Prepare the OKH service for LLM integration."""
        await super().prepare_llm_integration()
        
        if self.is_llm_enabled():
            self.logger.info("Preparing OKH service for LLM-enhanced manifest generation")
            # Future: Initialize LLM-specific components for manifest generation
            # - LLM prompt templates for manifest field generation
            # - LLM validation rules for manifest content
            # - LLM-enhanced extraction from project URLs
    
    async def handle_llm_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LLM requests for OKH manifest operations."""
        if not self.is_llm_enabled():
            raise RuntimeError("LLM integration not enabled for OKH service")
        
        request_type = request_data.get("type")
        
        if request_type == "generate_manifest":
            # Future: Use LLM to enhance manifest generation
            return {"status": "llm_generation_not_implemented"}
        elif request_type == "validate_manifest":
            # Future: Use LLM to validate manifest content
            return {"status": "llm_validation_not_implemented"}
        elif request_type == "extract_from_url":
            # Future: Use LLM to extract better information from project URLs
            return {"status": "llm_extraction_not_implemented"}
        else:
            return {"error": f"Unknown LLM request type: {request_type}"}
    
    async def cleanup(self) -> None:
        """Cleanup OKH service resources."""
        await super().cleanup()
        
        # Cleanup generation engine if it has cleanup method
        if self.generation_engine and hasattr(self.generation_engine, 'cleanup'):
            try:
                await self.generation_engine.cleanup()
                self.logger.info("Generation engine cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up generation engine: {e}")
        
        # Cleanup URL router if it has cleanup method
        if self.url_router and hasattr(self.url_router, 'cleanup'):
            try:
                await self.url_router.cleanup()
                self.logger.info("URL router cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up URL router: {e}")
        
        self.logger.info("OKH service cleanup completed")