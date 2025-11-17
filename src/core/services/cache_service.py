"""
Cache service for API response caching.

Provides in-memory caching with TTL support and automatic cleanup.
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import Lock

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CacheEntry:
    """Single cache entry with value and expiry time"""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() >= self.expires_at


class CacheService:
    """
    In-memory cache service with TTL support and automatic cleanup.
    
    Thread-safe cache implementation suitable for single-instance deployments.
    For multi-instance deployments, use Redis-based cache (Phase 2).
    """
    
    def __init__(self, max_size: int = 1000, cleanup_interval_seconds: int = 60):
        """
        Initialize cache service.
        
        Args:
            max_size: Maximum number of cache entries (LRU eviction)
            cleanup_interval_seconds: How often to clean expired entries
        """
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = datetime.now()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed()
            
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        with self._lock:
            # Periodic cleanup
            self._cleanup_if_needed()
            
            # Evict if at max size (remove oldest)
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)  # Remove oldest
            
            # Store entry
            entry = CacheEntry(value, ttl_seconds)
            self._cache[key] = entry
            self._cache.move_to_end(key)  # Move to end (most recently used)
    
    def delete(self, key: str) -> None:
        """Delete entry from cache"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def _cleanup_if_needed(self) -> None:
        """Clean up expired entries if cleanup interval has passed"""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = now
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "entries": [
                    {
                        "key": key,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat(),
                        "is_expired": entry.is_expired()
                    }
                    for key, entry in self._cache.items()
                ]
            }


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

