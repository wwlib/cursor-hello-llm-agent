"""
Optimized Graph Context Retrieval

High-performance graph context retrieval system optimized for real-time queries.
Provides fast context generation with intelligent caching and fallback mechanisms.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import hashlib
from collections import defaultdict


@dataclass
class ContextCacheEntry:
    """Cache entry for graph context."""
    query_hash: str
    context: str
    timestamp: float
    ttl: float
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class OptimizedGraphContextRetriever:
    """High-performance graph context retrieval with intelligent caching.
    
    Provides fast, cached access to graph context for real-time queries
    with fallback mechanisms and performance optimization.
    """
    
    def __init__(self, 
                 graph_manager,
                 cache_size: int = 100,
                 default_ttl: float = 300.0,  # 5 minutes
                 max_context_length: int = 2000,
                 enable_semantic_caching: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the optimized graph context retriever.
        
        Args:
            graph_manager: GraphManager instance for context retrieval
            cache_size: Maximum number of cached contexts
            default_ttl: Default time-to-live for cached contexts in seconds
            max_context_length: Maximum length of generated context
            enable_semantic_caching: Whether to use semantic similarity for cache hits
            logger: Logger instance for debugging
        """
        self.graph_manager = graph_manager
        self.cache_size = cache_size
        self.default_ttl = default_ttl
        self.max_context_length = max_context_length
        self.enable_semantic_caching = enable_semantic_caching
        self.logger = logger or logging.getLogger(__name__)
        
        # Context cache
        self._context_cache: Dict[str, ContextCacheEntry] = {}
        self._cache_access_order = []  # LRU tracking
        
        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_queries = 0
        self._average_query_time = 0.0
        
        # Semantic cache (if enabled)
        self._semantic_cache = {} if enable_semantic_caching else None
        
        self.logger.info(f"Initialized OptimizedGraphContextRetriever: "
                        f"cache_size={cache_size}, ttl={default_ttl}s, "
                        f"max_length={max_context_length}")
    
    def get_context(self, 
                   query: str, 
                   max_results: int = 5,
                   ttl: Optional[float] = None,
                   use_cache: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Get optimized graph context for a query.
        
        Args:
            query: Query text for context retrieval
            max_results: Maximum number of results to include
            ttl: Time-to-live for caching (overrides default)
            use_cache: Whether to use caching
            
        Returns:
            Tuple of (context_text, metadata)
        """
        start_time = time.time()
        self._total_queries += 1
        
        try:
            # Generate query hash for caching
            query_hash = self._generate_query_hash(query, max_results)
            
            # Check cache first
            if use_cache:
                cached_context = self._get_cached_context(query_hash)
                if cached_context:
                    self._cache_hits += 1
                    self.logger.debug(f"Cache hit for query: {query[:50]}...")
                    
                    metadata = {
                        "source": "cache",
                        "cache_hit": True,
                        "query_time": time.time() - start_time,
                        "cache_entry_age": time.time() - cached_context.timestamp,
                        "hit_count": cached_context.hit_count
                    }
                    
                    return cached_context.context, metadata
            
            # Generate new context
            self._cache_misses += 1
            context = self._generate_context(query, max_results)
            
            # Cache the result
            if use_cache:
                cache_ttl = ttl or self.default_ttl
                self._cache_context(query_hash, context, cache_ttl)
            
            # Update performance metrics
            query_time = time.time() - start_time
            self._update_performance_metrics(query_time)
            
            metadata = {
                "source": "generated",
                "cache_hit": False,
                "query_time": query_time,
                "context_length": len(context),
                "max_results": max_results
            }
            
            self.logger.debug(f"Generated context for query: {query[:50]}... "
                            f"({len(context)} chars, {query_time:.3f}s)")
            
            return context, metadata
            
        except Exception as e:
            self.logger.error(f"Error getting graph context: {e}")
            return "", {"error": str(e), "query_time": time.time() - start_time}
    
    async def get_context_async(self, 
                               query: str, 
                               max_results: int = 5,
                               ttl: Optional[float] = None,
                               use_cache: bool = True) -> Tuple[str, Dict[str, Any]]:
        """Async version of get_context for non-blocking operation."""
        # For now, use synchronous version wrapped in asyncio
        # In the future, this could be enhanced with async graph operations
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_context, 
            query, 
            max_results, 
            ttl, 
            use_cache
        )
    
    def _generate_query_hash(self, query: str, max_results: int) -> str:
        """Generate hash for query caching."""
        # Normalize query for consistent hashing
        normalized_query = query.lower().strip()
        hash_input = f"{normalized_query}:{max_results}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _get_cached_context(self, query_hash: str) -> Optional[ContextCacheEntry]:
        """Get cached context if available and not expired."""
        if query_hash not in self._context_cache:
            return None
        
        entry = self._context_cache[query_hash]
        
        # Check if expired
        if time.time() - entry.timestamp > entry.ttl:
            self._remove_cache_entry(query_hash)
            return None
        
        # Update access tracking
        entry.hit_count += 1
        entry.last_accessed = time.time()
        self._update_cache_access_order(query_hash)
        
        return entry
    
    def _cache_context(self, query_hash: str, context: str, ttl: float) -> None:
        """Cache context with TTL."""
        # Remove oldest entries if cache is full
        while len(self._context_cache) >= self.cache_size:
            self._evict_oldest_cache_entry()
        
        # Add new entry
        entry = ContextCacheEntry(
            query_hash=query_hash,
            context=context,
            timestamp=time.time(),
            ttl=ttl
        )
        
        self._context_cache[query_hash] = entry
        self._cache_access_order.append(query_hash)
        
        self.logger.debug(f"Cached context for hash: {query_hash[:8]}...")
    
    def _evict_oldest_cache_entry(self) -> None:
        """Evict the least recently used cache entry."""
        if not self._cache_access_order:
            return
        
        oldest_hash = self._cache_access_order.pop(0)
        if oldest_hash in self._context_cache:
            del self._context_cache[oldest_hash]
            self.logger.debug(f"Evicted cache entry: {oldest_hash[:8]}...")
    
    def _remove_cache_entry(self, query_hash: str) -> None:
        """Remove specific cache entry."""
        if query_hash in self._context_cache:
            del self._context_cache[query_hash]
            if query_hash in self._cache_access_order:
                self._cache_access_order.remove(query_hash)
    
    def _update_cache_access_order(self, query_hash: str) -> None:
        """Update LRU access order."""
        if query_hash in self._cache_access_order:
            self._cache_access_order.remove(query_hash)
        self._cache_access_order.append(query_hash)
    
    def _generate_context(self, query: str, max_results: int) -> str:
        """Generate graph context for the query."""
        try:
            # Use the graph manager's query method
            results = self.graph_manager.query_for_context(query, max_results=max_results)
            
            if not results:
                return ""
            
            # Format results into context
            context_parts = []
            for i, result in enumerate(results, 1):
                name = result.get('name', 'Unknown')
                entity_type = result.get('type', 'entity')
                description = result.get('description', '')
                relevance_score = result.get('relevance_score', 0.0)
                
                context_part = f"{i}. {name} ({entity_type})"
                if description:
                    context_part += f": {description}"
                if relevance_score > 0:
                    context_part += f" [relevance: {relevance_score:.2f}]"
                
                context_parts.append(context_part)
            
            context = "\n".join(context_parts)
            
            # Truncate if too long
            if len(context) > self.max_context_length:
                context = context[:self.max_context_length - 3] + "..."
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error generating graph context: {e}")
            return ""
    
    def _update_performance_metrics(self, query_time: float) -> None:
        """Update performance metrics."""
        # Simple moving average
        if self._average_query_time == 0:
            self._average_query_time = query_time
        else:
            self._average_query_time = (self._average_query_time * 0.9) + (query_time * 0.1)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_requests, 1)
        
        return {
            "cache_size": len(self._context_cache),
            "max_cache_size": self.cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "total_queries": self._total_queries,
            "average_query_time": self._average_query_time,
            "cache_utilization": len(self._context_cache) / self.cache_size
        }
    
    def get_cache_entries(self) -> List[Dict[str, Any]]:
        """Get information about cached entries."""
        entries = []
        current_time = time.time()
        
        for hash_key, entry in self._context_cache.items():
            entries.append({
                "hash": hash_key[:8] + "...",
                "context_length": len(entry.context),
                "age": current_time - entry.timestamp,
                "ttl": entry.ttl,
                "hit_count": entry.hit_count,
                "last_accessed": current_time - entry.last_accessed,
                "expires_in": entry.ttl - (current_time - entry.timestamp)
            })
        
        return sorted(entries, key=lambda x: x["last_accessed"], reverse=True)
    
    def clear_cache(self) -> int:
        """Clear all cached contexts."""
        cleared_count = len(self._context_cache)
        self._context_cache.clear()
        self._cache_access_order.clear()
        self.logger.info(f"Cleared {cleared_count} cache entries")
        return cleared_count
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching a pattern."""
        if not pattern:
            return self.clear_cache()
        
        invalidated_count = 0
        keys_to_remove = []
        
        for hash_key, entry in self._context_cache.items():
            if pattern.lower() in entry.context.lower():
                keys_to_remove.append(hash_key)
        
        for key in keys_to_remove:
            self._remove_cache_entry(key)
            invalidated_count += 1
        
        self.logger.info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
        return invalidated_count
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache by removing expired entries and reordering."""
        current_time = time.time()
        expired_count = 0
        
        # Remove expired entries
        keys_to_remove = []
        for hash_key, entry in self._context_cache.items():
            if current_time - entry.timestamp > entry.ttl:
                keys_to_remove.append(hash_key)
        
        for key in keys_to_remove:
            self._remove_cache_entry(key)
            expired_count += 1
        
        # Reorder by access frequency
        sorted_entries = sorted(
            self._context_cache.items(),
            key=lambda x: (x[1].hit_count, x[1].last_accessed),
            reverse=True
        )
        
        self._cache_access_order = [entry[0] for entry in sorted_entries]
        
        return {
            "expired_removed": expired_count,
            "remaining_entries": len(self._context_cache),
            "cache_utilization": len(self._context_cache) / self.cache_size
        }
    
    def configure(self, 
                  cache_size: Optional[int] = None,
                  default_ttl: Optional[float] = None,
                  max_context_length: Optional[int] = None) -> None:
        """Update retriever configuration."""
        if cache_size is not None:
            self.cache_size = cache_size
            self.logger.info(f"Updated cache size to {cache_size}")
        
        if default_ttl is not None:
            self.default_ttl = default_ttl
            self.logger.info(f"Updated default TTL to {default_ttl}s")
        
        if max_context_length is not None:
            self.max_context_length = max_context_length
            self.logger.info(f"Updated max context length to {max_context_length}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        cache_stats = self.get_cache_stats()
        
        return {
            "performance": {
                "total_queries": self._total_queries,
                "average_query_time": self._average_query_time,
                "cache_hit_rate": cache_stats["hit_rate"],
                "cache_utilization": cache_stats["cache_utilization"]
            },
            "cache": cache_stats,
            "configuration": {
                "cache_size": self.cache_size,
                "default_ttl": self.default_ttl,
                "max_context_length": self.max_context_length,
                "semantic_caching": self.enable_semantic_caching
            }
        }
