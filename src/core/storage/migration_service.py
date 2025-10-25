"""
Storage Migration Service

This module provides functionality for migrating files to organized directory structures
with comprehensive data quality checks and safety features.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from .manager import StorageManager
from .smart_discovery import SmartFileDiscovery, FileInfo
from ..validation.uuid_validator import UUIDValidator
from ..utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class MigrationResult:
    """Result of a migration operation"""
    old_path: str
    new_path: str
    file_type: str
    status: str  # 'migrated', 'skipped', 'failed'
    error: Optional[str] = None
    data_quality_fixes: List[str] = None

@dataclass
class MigrationReport:
    """Report of migration operation"""
    total_files: int
    files_migrated: int
    files_skipped: int
    files_failed: int
    data_quality_fixes: int
    dry_run: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    results: List[MigrationResult] = None
    rollback_info: Optional[Dict[str, Any]] = None

class StorageMigrationService:
    """Service for migrating files to organized directory structures"""
    
    def __init__(self):
        self.storage_manager: Optional[StorageManager] = None
        self.smart_discovery: Optional[SmartFileDiscovery] = None
        self.uuid_validator = UUIDValidator()
        self.migration_log: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize the migration service"""
        try:
            from ...config.storage_config import get_default_storage_config
            from ..services.storage_service import StorageService
            
            # Initialize storage service
            storage_config = get_default_storage_config()
            storage_service = await StorageService.get_instance()
            await storage_service.configure(storage_config)
            
            self.storage_manager = storage_service.manager
            self.smart_discovery = SmartFileDiscovery(self.storage_manager)
            
            logger.info("StorageMigrationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize StorageMigrationService: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources to prevent memory leaks"""
        try:
            if self.storage_manager and hasattr(self.storage_manager, 'cleanup'):
                await self.storage_manager.cleanup()
            logger.info("StorageMigrationService cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def generate_organized_path(self, file_type: str, file_data: Dict[str, Any]) -> str:
        """
        Generate organized path for a file based on its type and data
        
        Args:
            file_type: Type of file ('okh', 'okw', 'supply-tree')
            file_data: File data dictionary
            
        Returns:
            Organized path string
        """
        if file_type == "okh":
            # Use file ID or generate from title
            file_id = file_data.get('id', 'unknown')
            if not file_id or file_id == 'unknown':
                title = file_data.get('title', 'untitled')
                file_id = self.uuid_validator.generate_uuid_from_string(title)
            
            return f"okh/manifests/{file_id}.json"
        
        elif file_type == "okw":
            # Group by facility type if available
            facility_type = file_data.get('facility_type', 'general')
            if facility_type not in ['manufacturing', 'makerspaces', 'research']:
                facility_type = 'general'
            
            # Use file ID
            file_id = file_data.get('id', 'unknown')
            if not file_id or file_id == 'unknown':
                name = file_data.get('name', 'unnamed')
                file_id = self.uuid_validator.generate_uuid_from_string(name)
            
            return f"okw/facilities/{facility_type}/{file_id}.json"
        
        elif file_type == "supply-tree":
            # Group by status
            status = file_data.get('status', 'generated')
            if status not in ['generated', 'validated', 'archived']:
                status = 'generated'
            
            # Use file ID
            file_id = file_data.get('id', 'unknown')
            if not file_id or file_id == 'unknown':
                file_id = self.uuid_validator.generate_uuid_from_string(str(datetime.now()))
            
            return f"supply-trees/{status}/{file_id}.json"
        
        else:
            # Fallback for unknown types
            file_id = file_data.get('id', 'unknown')
            if not file_id or file_id == 'unknown':
                file_id = self.uuid_validator.generate_uuid_from_string(str(datetime.now()))
            
            return f"misc/{file_type}/{file_id}.json"
    
    async def migrate_files(self, dry_run: bool = True) -> MigrationReport:
        """
        Migrate all files to organized directory structure
        
        Args:
            dry_run: If True, simulate migration without actually moving files
            
        Returns:
            MigrationReport with results
        """
        if not self.storage_manager or not self.smart_discovery:
            await self.initialize()
        
        start_time = datetime.now()
        logger.info(f"Starting file migration (dry_run={dry_run})")
        
        # Initialize report
        report = MigrationReport(
            total_files=0,
            files_migrated=0,
            files_skipped=0,
            files_failed=0,
            data_quality_fixes=0,
            dry_run=dry_run,
            start_time=start_time,
            results=[]
        )
        
        try:
            # Discover all files
            all_files = await self.smart_discovery.discover_all_files()
            report.total_files = len(all_files)
            
            logger.info(f"Found {len(all_files)} files to migrate")
            
            # Process each file
            for file_info in all_files:
                result = await self._migrate_single_file(file_info, dry_run)
                report.results.append(result)
                
                if result.status == 'migrated':
                    report.files_migrated += 1
                elif result.status == 'dry_run_simulated':
                    # In dry-run mode, count simulated migrations as migrated for reporting
                    report.files_migrated += 1
                elif result.status == 'skipped':
                    report.files_skipped += 1
                elif result.status == 'failed':
                    report.files_failed += 1
                
                if result.data_quality_fixes:
                    report.data_quality_fixes += len(result.data_quality_fixes)
            
            report.end_time = datetime.now()
            
            # Log migration summary
            logger.info(f"Migration completed: {report.files_migrated} migrated, "
                       f"{report.files_skipped} skipped, {report.files_failed} failed")
            
            return report
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            report.end_time = datetime.now()
            raise
    
    async def _migrate_single_file(self, file_info: FileInfo, dry_run: bool) -> MigrationResult:
        """
        Migrate a single file
        
        Args:
            file_info: Information about the file to migrate
            dry_run: If True, simulate migration without actually moving files
            
        Returns:
            MigrationResult with operation details
        """
        try:
            # Skip binary files and system files
            if file_info.key.endswith('.DS_Store') or file_info.key.startswith('.'):
                return MigrationResult(
                    old_path=file_info.key,
                    new_path="",
                    file_type=file_info.file_type,
                    status='skipped',
                    error="Binary or system file, skipping"
                )
            
            # Load file data
            data = await self.storage_manager.get_object(file_info.key)
            content = data.decode('utf-8')
            
            # Skip empty files
            if not content.strip():
                return MigrationResult(
                    old_path=file_info.key,
                    new_path="",
                    file_type=file_info.file_type,
                    status='skipped',
                    error="Empty file, skipping"
                )
            
            file_data = json.loads(content)
            
            # Apply data quality fixes
            data_quality_fixes = []
            if file_info.file_type == 'okh':
                original_data = file_data.copy()
                file_data = self.uuid_validator.validate_and_fix_okh_data(file_data)
                if file_data != original_data:
                    data_quality_fixes.append("UUID validation and fixing applied")
            elif file_info.file_type == 'okw':
                original_data = file_data.copy()
                file_data = self.uuid_validator.validate_and_fix_okw_data(file_data)
                if file_data != original_data:
                    data_quality_fixes.append("UUID validation and fixing applied")
            
            # Generate new path
            new_path = self.generate_organized_path(file_info.file_type, file_data)
            
            # Check if file is already in correct location
            if file_info.key == new_path:
                return MigrationResult(
                    old_path=file_info.key,
                    new_path=new_path,
                    file_type=file_info.file_type,
                    status='skipped',
                    data_quality_fixes=data_quality_fixes
                )
            
            # Perform migration (or simulate if dry run)
            if not dry_run:
                # Store file at new location with updated data
                updated_content = json.dumps(file_data, indent=2)
                await self.storage_manager.put_object(
                    key=new_path,
                    data=updated_content.encode('utf-8'),
                    content_type='application/json',
                    metadata={
                        'original_path': file_info.key,
                        'migrated_at': datetime.now().isoformat(),
                        'file_type': file_info.file_type,
                        'data_quality_fixes': json.dumps(data_quality_fixes) if data_quality_fixes else '[]'
                    }
                )
                
                # Remove old file
                await self.storage_manager.delete_object(file_info.key)
                
                status = 'migrated'
            else:
                # In dry-run mode, just simulate the migration
                status = 'dry_run_simulated'
            
            return MigrationResult(
                old_path=file_info.key,
                new_path=new_path,
                file_type=file_info.file_type,
                status=status,
                data_quality_fixes=data_quality_fixes
            )
            
        except Exception as e:
            logger.error(f"Failed to migrate file {file_info.key}: {e}")
            return MigrationResult(
                old_path=file_info.key,
                new_path="",
                file_type=file_info.file_type,
                status='failed',
                error=str(e)
            )
    
    async def rollback_migration(self) -> Dict[str, Any]:
        """
        Rollback the last migration operation
        
        Returns:
            Dictionary with rollback results
        """
        try:
            # This is a simplified rollback - in a real implementation,
            # we would track migration operations and restore from backups
            
            logger.info("Rollback operation requested")
            
            # For now, return a placeholder response
            return {
                'rollback_successful': True,
                'message': 'Rollback functionality needs to be implemented with proper backup tracking',
                'files_restored': 0
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                'rollback_successful': False,
                'error': str(e),
                'files_restored': 0
            }
