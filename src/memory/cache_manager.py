"""
Cache Manager for Memory Operations

Provides intelligent caching for expensive operations like RAG context generation
and graph context queries to improve performance.
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
import logging


class CacheManager:
    """
    Manage caching for expensive memory operations.
    
    Features:
    - TTL-based cache expiration
    - Memory state-aware cache invalidation
    - Size-limited cache with LRU eviction
    - Operation-specific cache strategies
    """
    
    def __init__(self, default_ttl: float = 300.0, max_cache_size: int = 100, logger: Optional[logging.Logger] = None):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
            max_cache_size: Maximum number of cache entries
            logger: Optional logger instance
        """
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache storage: {cache_key: (result, timestamp, access_time)}
        self._rag_cache: Dict[str, Tuple[str, float, float]] = {}
        self._graph_context_cache: Dict[str, Tuple[str, float, float]] = {}
        self._memory_state_cache: Dict[str, Tuple[Any, float, float]] = {}
        
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        
    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate a cache key based on operation and parameters."""
        # Create a hash of the operation and parameters
        key_data = {"operation": operation, **kwargs}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float, ttl: Optional[float] = None) -> bool:
        """Check if a cache entry is still valid."""
        ttl = ttl or self.default_ttl
        return (time.time() - timestamp) < ttl
    
    def _cleanup_cache(self, cache: Dict[str, Tuple[Any, float, float]]):
        """Remove expired entries and enforce size limits."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, (_, timestamp, _) in cache.items()
            if not self._is_cache_valid(timestamp)
        ]
        for key in expired_keys:
            del cache[key]
        
        # Enforce size limits using LRU eviction
        if len(cache) > self.max_cache_size:
            # Sort by access time and remove oldest entries
            sorted_items = sorted(cache.items(), key=lambda x: x[1][2])  # Sort by access_time
            items_to_remove = len(cache) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                del cache[key]
    
    def get_rag_context(self, query: str, memory_state_hash: str, ttl: Optional[float] = None) -> Optional[str]:
        """
        Get cached RAG context if available and fresh.
        
        Args:
            query: The query text
            memory_state_hash: Hash of the current memory state
            ttl: Optional custom TTL for this entry
            
        Returns:
            Cached RAG context if available, None otherwise
        """
        cache_key = self._generate_cache_key("rag_context", query=query, memory_state=memory_state_hash)
        
        if cache_key in self._rag_cache:
            result, timestamp, _ = self._rag_cache[cache_key]
            if self._is_cache_valid(timestamp, ttl):
                # Update access time
                self._rag_cache[cache_key] = (result, timestamp, time.time())
                self._cache_hits += 1
                self.logger.debug(f"RAG cache hit for query: {query[:50]}...")
                return result
            else:
                # Remove expired entry
                del self._rag_cache[cache_key]
        
        self._cache_misses += 1
        self.logger.debug(f"RAG cache miss for query: {query[:50]}...")
        return None
    
    def set_rag_context(self, query: str, memory_state_hash: str, result: str):
        """
        Cache RAG context result.
        
        Args:
            query: The query text
            memory_state_hash: Hash of the current memory state
            result: The RAG context result to cache
        """
        cache_key = self._generate_cache_key("rag_context", query=query, memory_state=memory_state_hash)
        current_time = time.time()
        
        self._rag_cache[cache_key] = (result, current_time, current_time)
        self._cleanup_cache(self._rag_cache)
        
        self.logger.debug(f"Cached RAG context for query: {query[:50]}...")
    
    def get_graph_context(self, query: str, graph_state_hash: str, ttl: Optional[float] = None) -> Optional[str]:
        """
        Get cached graph context if available and fresh.
        
        Args:
            query: The query text
            graph_state_hash: Hash of the current graph state
            ttl: Optional custom TTL for this entry
            
        Returns:
            Cached graph context if available, None otherwise
        """
        cache_key = self._generate_cache_key("graph_context", query=query, graph_state=graph_state_hash)
        
        if cache_key in self._graph_context_cache:
            result, timestamp, _ = self._graph_context_cache[cache_key]
            if self._is_cache_valid(timestamp, ttl):
                # Update access time
                self._graph_context_cache[cache_key] = (result, timestamp, time.time())
                self._cache_hits += 1
                self.logger.debug(f"Graph context cache hit for query: {query[:50]}...")
                return result
            else:
                # Remove expired entry
                del self._graph_context_cache[cache_key]
        
        self._cache_misses += 1
        self.logger.debug(f"Graph context cache miss for query: {query[:50]}...")
        return None
    
    def set_graph_context(self, query: str, graph_state_hash: str, result: str):
        """
        Cache graph context result.
        
        Args:
            query: The query text
            graph_state_hash: Hash of the current graph state
            result: The graph context result to cache
        """
        cache_key = self._generate_cache_key("graph_context", query=query, graph_state=graph_state_hash)
        current_time = time.time()
        
        self._graph_context_cache[cache_key] = (result, current_time, current_time)
        self._cleanup_cache(self._graph_context_cache)
        
        self.logger.debug(f"Cached graph context for query: {query[:50]}...")
    
    def invalidate_memory_caches(self):
        """Invalidate all memory-related caches (call when memory changes significantly)."""
        self._rag_cache.clear()
        self.logger.debug("Invalidated all RAG caches due to memory changes")
    
    def invalidate_graph_caches(self):
        """Invalidate all graph-related caches (call when graph changes significantly)."""
        self._graph_context_cache.clear()
        self.logger.debug("Invalidated all graph context caches due to graph changes")
    
    def get_memory_state_hash(self, memory: Dict[str, Any]) -> str:
        """
        Generate a hash of the current memory state for cache invalidation.
        
        Args:
            memory: The memory dictionary
            
        Returns:
            Hash string representing the memory state
        """
        # Create a hash based on key memory components
        state_data = {
            "conversation_count": len(memory.get("conversation_history", [])),
            "context_count": len(memory.get("context", [])),
            "last_updated": memory.get("metadata", {}).get("updated_at", "")
        }
        
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests) if total_requests > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "rag_cache_size": len(self._rag_cache),
            "graph_cache_size": len(self._graph_context_cache),
            "memory_cache_size": len(self._memory_state_cache)
        }
    
    def clear_all_caches(self):
        """Clear all caches."""
        self._rag_cache.clear()
        self._graph_context_cache.clear()
        self._memory_state_cache.clear()
        self.logger.debug("Cleared all caches")
    
    def print_cache_statistics(self):
        """Print cache statistics to console."""
        stats = self.get_cache_statistics()
        print("\nCache Statistics:")
        print("-" * 30)
        print(f"Cache Hits: {stats['cache_hits']}")
        print(f"Cache Misses: {stats['cache_misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.2%}")
        print(f"RAG Cache Size: {stats['rag_cache_size']}")
        print(f"Graph Cache Size: {stats['graph_cache_size']}")
        print(f"Memory Cache Size: {stats['memory_cache_size']}")


# Global cache manager instance
_global_cache_manager = None

def get_cache_manager(logger: Optional[logging.Logger] = None) -> CacheManager:
    """Get or create the global cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(logger=logger)
    return _global_cache_manager

