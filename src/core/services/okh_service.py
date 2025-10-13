from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging
import httpx
import yaml
import json

from src.core.services.storage_service import StorageService
from ..models.okh import OKHManifest, ProcessRequirement
from ..utils.logging import get_logger

logger = get_logger(__name__)

class OKHService:
    """Service for managing OKH manifests"""
    
    _instance = None
    
    @classmethod
    async def get_instance(cls, storage_service: Optional[StorageService] = None) -> 'OKHService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize(storage_service)
        return cls._instance
    
    def __init__(self):
        """Initialize the OKH service"""
        self.storage: Optional[StorageService] = None
        self._initialized = False
    
    async def initialize(self, storage_service: Optional[StorageService] = None) -> None:
        """Initialize the service with dependencies"""
        if self._initialized:
            return
            
        self.storage = storage_service or await StorageService.get_instance()
        if self.storage:
            from src.config import settings
            await self.storage.configure(settings.STORAGE_CONFIG)
        self._initialized = True
        logger.info("OKH service initialized")
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("OKH service not initialized")
    
    async def create(self, manifest_data: Dict[str, Any]) -> OKHManifest:
        """Create a new OKH manifest"""
        await self.ensure_initialized()
        logger.info("Creating new OKH manifest")
        
        # Create manifest object
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
            logger.info(f"Saved OKH manifest to {filename}")
        
        return manifest
    
    async def get(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Get an OKH manifest by ID"""
        try:
            await self.ensure_initialized()
            logger.info(f"Getting OKH manifest with ID {manifest_id}")
            
            if not self.storage:
                logger.error("Storage service not available")
                return None
            
            logger.info("Storage service is available, searching for OKH files...")
            
            # Search through all OKH files (they have -okh.json suffix)
            file_count = 0
            okh_file_count = 0
            
            async for obj in self.storage.manager.list_objects():
                file_count += 1
                logger.debug(f"Checking file {file_count}: {obj['key']}")
                
                if obj["key"].endswith("-okh.json"):
                    okh_file_count += 1
                    logger.info(f"Found OKH file {okh_file_count}: {obj['key']}")
                    
                    try:
                        data = await self.storage.manager.get_object(obj["key"])
                        content = data.decode('utf-8')
                        okh_data = json.loads(content)
                        
                        logger.debug(f"Loaded OKH data from {obj['key']}, ID: {okh_data.get('id')}")
                        
                        # Check if this is the manifest we're looking for
                        if okh_data.get("id") == str(manifest_id):
                            logger.info(f"Found matching OKH manifest in {obj['key']}")
                            manifest = OKHManifest.from_dict(okh_data)
                            logger.info(f"Successfully created OKHManifest object for {manifest.title}")
                            return manifest
                        else:
                            logger.debug(f"ID mismatch: looking for {manifest_id}, found {okh_data.get('id')}")
                            
                    except Exception as e:
                        logger.error(f"Failed to load OKH file {obj['key']}: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        continue
            
            logger.warning(f"OKH manifest with ID {manifest_id} not found. Searched {file_count} files, {okh_file_count} OKH files")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in get method: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def fetch_from_url(self, url: str) -> OKHManifest:
        """Fetch an OKH manifest from a remote URL"""
        await self.ensure_initialized()
        logger.info(f"Fetching OKH manifest from URL: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    logger.error(f"Failed to parse manifest content: {e}")
                    raise ValueError(f"Invalid manifest format: {e}")
                
                # Create manifest object
                manifest = OKHManifest.from_dict(data)
                logger.info(f"Successfully fetched OKH manifest: {manifest.id}")
                return manifest
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching manifest from {url}: {e}")
            raise ValueError(f"Failed to fetch manifest from URL: {e}")
        except Exception as e:
            logger.error(f"Error fetching manifest from {url}: {e}")
            raise ValueError(f"Error fetching manifest: {e}")
    
    async def list(
        self, 
        page: int = 1, 
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[OKHManifest], int]:
        """List OKH manifests"""
        await self.ensure_initialized()
        logger.info(f"Listing OKH manifests (page={page}, page_size={page_size})")
        
        if self.storage:
            # For now, load OKH files directly from storage root (they have -okh.json suffix)
            objects = []
            total_count = 0
            
            async for obj in self.storage.manager.list_objects():
                if obj["key"].endswith("-okh.json"):
                    total_count += 1
                    if len(objects) < page_size and len(objects) >= (page - 1) * page_size:
                        try:
                            data = await self.storage.manager.get_object(obj["key"])
                            content = data.decode('utf-8')
                            okh_data = json.loads(content)
                            objects.append(OKHManifest.from_dict(okh_data))
                        except Exception as e:
                            logger.error(f"Failed to load OKH file {obj['key']}: {e}")
                            continue
            
            return objects, total_count
        
        return [], 0
    
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
            # Import the new validation framework
            from ..domains.manufacturing.validation.okh_validator import ManufacturingOKHValidator
            from ..validation.context import ValidationContext
            
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
    
    async def generate_from_url(self, url: str, skip_review: bool = False) -> Dict[str, Any]:
        """Generate OKH manifest from repository URL"""
        try:
            await self.ensure_initialized()
            
            # Import generation modules
            from ..generation.url_router import URLRouter
            from ..generation.engine import GenerationEngine
            from ..generation.review import ReviewInterface
            from ..generation.models import PlatformType
            
            # Validate and route URL
            router = URLRouter()
            if not router.validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            platform = router.detect_platform(url)
            if platform is None:
                raise ValueError(f"Unsupported platform for URL: {url}")
            
            # Get platform-specific generator
            if platform == PlatformType.GITHUB:
                from ..generation.platforms.github import GitHubExtractor
                generator = GitHubExtractor()
            elif platform == PlatformType.GITLAB:
                from ..generation.platforms.gitlab import GitLabExtractor
                generator = GitLabExtractor()
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Generate project data
            project_data = await generator.extract_project(url)
            
            # Generate manifest
            engine = GenerationEngine()
            result = await engine.generate_manifest_async(project_data)
            
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
            logger.error(f"Error generating manifest from URL {url}: {str(e)}")
            raise ValueError(f"Generation failed: {str(e)}")
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("OKH service not initialized")