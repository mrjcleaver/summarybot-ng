"""
Summary caching logic for performance optimization.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..models.summary import SummaryResult
from ..models.base import BaseModel


class CacheInterface(ABC):
    """Abstract interface for caching backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        pass
    
    @abstractmethod
    async def clear(self, pattern: str = None) -> int:
        """Clear cache entries matching pattern."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if cache backend is healthy."""
        pass


class MemoryCache(CacheInterface):
    """Simple in-memory cache implementation."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.get("expires_at") and datetime.utcnow() > entry["expires_at"]:
            del self._cache[key]
            return None
        
        return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value with optional TTL."""
        # Enforce size limit
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]["created_at"])
            del self._cache[oldest_key]
        
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
        
        self._cache[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self, pattern: str = None) -> int:
        """Clear cache entries matching pattern."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        
        # Simple pattern matching (just prefix for now)
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            del self._cache[key]
        
        return len(keys_to_delete)
    
    async def health_check(self) -> bool:
        """Check if cache backend is healthy."""
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        expired_count = sum(
            1 for entry in self._cache.values()
            if entry.get("expires_at") and now > entry["expires_at"]
        )
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "expired_entries": expired_count,
            "hit_ratio": "N/A",  # Would need tracking
            "backend": "memory"
        }


class SummaryCache:
    """High-level cache interface for summaries."""
    
    def __init__(self, backend: CacheInterface):
        self.backend = backend
    
    async def get_cached_summary(self,
                               channel_id: str,
                               start_time: datetime,
                               end_time: datetime,
                               options_hash: str) -> Optional[SummaryResult]:
        """Get cached summary if available.
        
        Args:
            channel_id: Discord channel ID
            start_time: Start time of message range
            end_time: End time of message range
            options_hash: Hash of summarization options
            
        Returns:
            Cached summary result or None
        """
        cache_key = self._generate_cache_key(
            channel_id, start_time, end_time, options_hash
        )
        
        cached_data = await self.backend.get(cache_key)
        if not cached_data:
            return None
        
        # Deserialize summary result
        try:
            return SummaryResult.from_dict(cached_data)
        except Exception:
            # Invalid cached data, remove it
            await self.backend.delete(cache_key)
            return None
    
    async def cache_summary(self, 
                          summary: SummaryResult, 
                          ttl: int = 3600) -> None:
        """Cache a summary result.
        
        Args:
            summary: Summary result to cache
            ttl: Time to live in seconds
        """
        # Generate cache key from summary properties
        options_hash = self._hash_summary_options(summary)
        cache_key = self._generate_cache_key(
            summary.channel_id,
            summary.start_time,
            summary.end_time,
            options_hash
        )
        
        # Serialize summary
        cached_data = summary.to_dict()
        
        await self.backend.set(cache_key, cached_data, ttl)
    
    async def invalidate_channel(self, channel_id: str) -> int:
        """Invalidate all cached summaries for a channel.
        
        Args:
            channel_id: Channel to invalidate
            
        Returns:
            Number of entries removed
        """
        pattern = f"summary:{channel_id}:"
        return await self.backend.clear(pattern)
    
    async def invalidate_guild(self, guild_id: str) -> int:
        """Invalidate all cached summaries for a guild.
        
        Args:
            guild_id: Guild to invalidate
            
        Returns:
            Number of entries removed
        """
        # This is more complex as we'd need to track guild->channel mappings
        # For now, just clear all (could be optimized with better key structure)
        return await self.backend.clear()
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        # This depends on the backend implementation
        # For memory cache, expired entries are removed on access
        # For Redis, we could use SCAN with TTL checks
        return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        base_stats = {
            "backend_healthy": await self.backend.health_check()
        }
        
        # Add backend-specific stats if available
        if hasattr(self.backend, 'get_stats'):
            base_stats.update(self.backend.get_stats())
        
        return base_stats
    
    async def health_check(self) -> bool:
        """Check if cache is healthy."""
        return await self.backend.health_check()
    
    def _generate_cache_key(self, 
                          channel_id: str,
                          start_time: datetime,
                          end_time: datetime,
                          options_hash: str) -> str:
        """Generate cache key for summary."""
        # Use timestamp ranges rounded to nearest hour for better cache hits
        start_hour = start_time.replace(minute=0, second=0, microsecond=0)
        end_hour = end_time.replace(minute=0, second=0, microsecond=0)
        
        key_parts = [
            "summary",
            channel_id,
            start_hour.strftime("%Y%m%d%H"),
            end_hour.strftime("%Y%m%d%H"),
            options_hash
        ]
        
        return ":".join(key_parts)
    
    def _hash_summary_options(self, summary: SummaryResult) -> str:
        """Generate hash from summary metadata that indicates options used."""
        # Extract relevant options from metadata
        options_data = {
            "model": summary.metadata.get("claude_model", ""),
            "max_tokens": summary.metadata.get("max_tokens", ""),
            # Could add more options here
        }
        
        options_str = json.dumps(options_data, sort_keys=True)
        return hashlib.md5(options_str.encode()).hexdigest()[:8]