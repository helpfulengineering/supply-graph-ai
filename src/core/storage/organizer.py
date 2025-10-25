"""
Storage Organization Service

This module provides services for organizing files in storage containers
using a structured directory hierarchy and proper metadata tagging.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from .manager import StorageManager
from .smart_discovery import SmartFileDiscovery, FileInfo
from ..utils.logging import get_logger

logger = get_logger(__name__)

class StorageOrganizer:
    """Service for organizing storage container structure"""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.discovery = SmartFileDiscovery(storage_manager)
    
    async def create_directory_structure(self) -> Dict[str, Any]:
        """Create the organized directory structure in storage"""
        logger.info("Creating organized directory structure")
        
        # Create placeholder files to establish directory structure
        directories = {
            'okh/manifests/01/': 'placeholder-okh-01.json',
            'okh/manifests/02/': 'placeholder-okh-02.json',
            'okw/facilities/manufacturing/': 'placeholder-okw-manufacturing.json',
            'okw/facilities/makerspaces/': 'placeholder-okw-makerspaces.json',
            'okw/facilities/research/': 'placeholder-okw-research.json',
            'supply-trees/generated/': 'placeholder-supply-tree-generated.json',
            'supply-trees/validated/': 'placeholder-supply-tree-validated.json'
        }
        
        created_dirs = []
        
        for directory, placeholder_file in directories.items():
            try:
                # Create a placeholder file to establish the directory
                placeholder_content = {
                    "type": "directory_placeholder",
                    "directory": directory,
                    "created_at": datetime.now().isoformat(),
                    "purpose": "Establishes directory structure in blob storage"
                }
                
                placeholder_key = f"{directory}{placeholder_file}"
                data = json.dumps(placeholder_content).encode('utf-8')
                
                await self.storage_manager.put_object(
                    key=placeholder_key,
                    data=data,
                    content_type="application/json",
                    metadata={
                        "file-type": "directory_placeholder",
                        "directory": directory,
                        "created_at": datetime.now().isoformat()
                    }
                )
                
                created_dirs.append(directory)
                logger.info(f"Created directory: {directory}")
                
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
        
        return {
            "created_directories": created_dirs,
            "total_created": len(created_dirs),
            "timestamp": datetime.now().isoformat()
        }
    
    async def store_okh_manifest(self, manifest_data: Dict[str, Any], manifest_id: Optional[str] = None) -> str:
        """Store an OKH manifest in the organized structure"""
        if not manifest_id:
            manifest_id = manifest_data.get('id', str(uuid4()))
        
        # Determine subdirectory based on manifest data
        subdirectory = self._get_okh_subdirectory(manifest_data)
        
        # Generate organized path
        path = f"okh/manifests/{subdirectory}/{manifest_id}.json"
        
        # Store with metadata
        data = json.dumps(manifest_data).encode('utf-8')
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "okh",
                "domain": "okh",
                "id": manifest_id,
                "title": manifest_data.get('title', 'Unknown'),
                "version": manifest_data.get('version', '1.0.0'),
                "created_at": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Stored OKH manifest at: {path}")
        return path
    
    async def store_okw_facility(self, facility_data: Dict[str, Any], facility_id: Optional[str] = None) -> str:
        """Store an OKW facility in the organized structure"""
        if not facility_id:
            facility_id = facility_data.get('id', str(uuid4()))
        
        # Determine subdirectory based on facility type
        subdirectory = self._get_okw_subdirectory(facility_data)
        
        # Generate organized path
        path = f"okw/facilities/{subdirectory}/{facility_id}.json"
        
        # Store with metadata
        data = json.dumps(facility_data).encode('utf-8')
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "okw",
                "domain": "okw",
                "id": facility_id,
                "name": facility_data.get('name', 'Unknown Facility'),
                "facility_status": facility_data.get('facility_status', 'Unknown'),
                "created_at": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Stored OKW facility at: {path}")
        return path
    
    async def store_supply_tree(self, tree_data: Dict[str, Any], tree_id: Optional[str] = None) -> str:
        """Store a supply tree in the organized structure"""
        if not tree_id:
            tree_id = tree_data.get('id', str(uuid4()))
        
        # Determine subdirectory based on tree status
        subdirectory = self._get_supply_tree_subdirectory(tree_data)
        
        # Generate organized path
        path = f"supply-trees/{subdirectory}/{tree_id}.json"
        
        # Store with metadata
        data = json.dumps(tree_data).encode('utf-8')
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "supply-tree",
                "domain": "supply-tree",
                "id": tree_id,
                "status": subdirectory,
                "created_at": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Stored supply tree at: {path}")
        return path
    
    def _get_okh_subdirectory(self, manifest_data: Dict[str, Any]) -> str:
        """Determine OKH subdirectory based on manifest data"""
        # For now, use simple numbering. Could be enhanced with date-based or category-based logic
        return "01"  # All OKH manifests go to 01 for now
    
    def _get_okw_subdirectory(self, facility_data: Dict[str, Any]) -> str:
        """Determine OKW subdirectory based on facility data"""
        # Check facility type or capabilities to determine subdirectory
        facility_status = facility_data.get('facility_status', '').lower()
        manufacturing_processes = facility_data.get('manufacturing_processes', [])
        
        # Determine facility type based on capabilities
        if any(process in ['3DP', '3D Printing', 'Additive Manufacturing'] for process in manufacturing_processes):
            return "manufacturing"
        elif 'makerspace' in facility_data.get('name', '').lower():
            return "makerspaces"
        elif 'research' in facility_data.get('name', '').lower() or 'university' in facility_data.get('name', '').lower():
            return "research"
        else:
            return "manufacturing"  # Default to manufacturing
    
    def _get_supply_tree_subdirectory(self, tree_data: Dict[str, Any]) -> str:
        """Determine supply tree subdirectory based on tree data"""
        # Check tree status or validation state
        status = tree_data.get('status', 'generated').lower()
        
        if status in ['validated', 'validated', 'approved']:
            return "validated"
        else:
            return "generated"
    
    async def get_storage_structure(self) -> Dict[str, Any]:
        """Get the current storage structure"""
        structure = {
            "okh": {"manifests": {"01": [], "02": []}},
            "okw": {"facilities": {"manufacturing": [], "makerspaces": [], "research": []}},
            "supply-trees": {"generated": [], "validated": []}
        }
        
        try:
            # Get all files and organize them by structure
            all_files = await self.discovery.discover_all_files()
            
            for file_info in all_files:
                path_parts = file_info.key.split('/')
                
                if len(path_parts) >= 3:
                    domain = path_parts[0]
                    category = path_parts[1]
                    subcategory = path_parts[2] if len(path_parts) > 2 else None
                    
                    if domain in structure and category in structure[domain]:
                        if subcategory and subcategory in structure[domain][category]:
                            structure[domain][category][subcategory].append({
                                "key": file_info.key,
                                "file_type": file_info.file_type,
                                "size": file_info.size,
                                "last_modified": file_info.last_modified.isoformat()
                            })
                        else:
                            # Handle files directly in category (no subcategory)
                            if isinstance(structure[domain][category], list):
                                structure[domain][category].append({
                                    "key": file_info.key,
                                    "file_type": file_info.file_type,
                                    "size": file_info.size,
                                    "last_modified": file_info.last_modified.isoformat()
                                })
        
        except Exception as e:
            logger.error(f"Failed to get storage structure: {e}")
        
        return structure
