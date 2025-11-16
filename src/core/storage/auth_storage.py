"""
Authentication storage layer.

This module provides storage operations for API keys using the StorageService.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from ..models.auth import APIKey
from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


class AuthStorage:
    """Storage layer for API key persistence."""
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize AuthStorage.
        
        Args:
            storage_service: StorageService instance for persistence
        """
        self.storage_service = storage_service
        self._storage_prefix = "auth/api-keys"
    
    async def save_key(self, key: APIKey) -> None:
        """
        Save API key to storage.
        
        Args:
            key: APIKey instance to save
        """
        # Serialize key to JSON
        key_data = key.model_dump(mode='json')
        # Convert datetime objects to ISO format strings
        if key_data.get('created_at'):
            key_data['created_at'] = key.created_at.isoformat()
        if key_data.get('last_used_at'):
            key_data['last_used_at'] = key.last_used_at.isoformat()
        if key_data.get('expires_at'):
            key_data['expires_at'] = key.expires_at.isoformat()
        # Convert UUID to string
        key_data['key_id'] = str(key.key_id)
        
        data = json.dumps(key_data).encode('utf-8')
        
        # Generate storage key
        storage_key = self._get_storage_key(key.key_id)
        
        # Save with metadata
        await self.storage_service.manager.put_object(
            key=storage_key,
            data=data,
            content_type="application/json",
            metadata={
                "type": "api_key",
                "key_id": str(key.key_id),
                "name": key.name
            }
        )
    
    async def load_key(self, key_id: UUID) -> Optional[APIKey]:
        """
        Load API key from storage.
        
        Args:
            key_id: UUID of the key to load
            
        Returns:
            APIKey instance if found, None otherwise
        """
        storage_key = self._get_storage_key(key_id)
        
        try:
            data = await self.storage_service.manager.get_object(storage_key)
            key_data = json.loads(data.decode('utf-8'))
            
            # Convert ISO format strings back to datetime objects
            from datetime import datetime
            if key_data.get('created_at'):
                key_data['created_at'] = datetime.fromisoformat(key_data['created_at'])
            if key_data.get('last_used_at'):
                key_data['last_used_at'] = datetime.fromisoformat(key_data['last_used_at'])
            if key_data.get('expires_at'):
                key_data['expires_at'] = datetime.fromisoformat(key_data['expires_at'])
            
            # Convert string UUID back to UUID object
            key_data['key_id'] = UUID(key_data['key_id'])
            
            return APIKey(**key_data)
        except Exception as e:
            logger.debug(f"Failed to load API key {key_id}: {e}")
            return None
    
    async def list_keys(self) -> List[APIKey]:
        """
        List all API keys from storage.
        
        Returns:
            List of APIKey instances
        """
        keys = []
        prefix = f"{self._storage_prefix}/"
        
        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                if 'data' in obj:
                    # If data is already loaded
                    data = obj['data']
                else:
                    # Load the object data
                    data = await self.storage_service.manager.get_object(obj['key'])
                
                try:
                    key_data = json.loads(data.decode('utf-8'))
                    
                    # Convert ISO format strings back to datetime objects
                    from datetime import datetime
                    if key_data.get('created_at'):
                        key_data['created_at'] = datetime.fromisoformat(key_data['created_at'])
                    if key_data.get('last_used_at'):
                        key_data['last_used_at'] = datetime.fromisoformat(key_data['last_used_at'])
                    if key_data.get('expires_at'):
                        key_data['expires_at'] = datetime.fromisoformat(key_data['expires_at'])
                    
                    # Convert string UUID back to UUID object
                    key_data['key_id'] = UUID(key_data['key_id'])
                    
                    keys.append(APIKey(**key_data))
                except Exception as e:
                    logger.warning(f"Failed to parse API key from {obj.get('key', 'unknown')}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            raise
        
        return keys
    
    async def delete_key(self, key_id: UUID) -> None:
        """
        Delete API key from storage.
        
        Args:
            key_id: UUID of the key to delete
        """
        storage_key = self._get_storage_key(key_id)
        await self.storage_service.manager.delete_object(storage_key)
    
    def _get_storage_key(self, key_id: UUID) -> str:
        """
        Get storage path for key.
        
        Args:
            key_id: UUID of the key
            
        Returns:
            Storage key path
        """
        return f"{self._storage_prefix}/{key_id}.json"

