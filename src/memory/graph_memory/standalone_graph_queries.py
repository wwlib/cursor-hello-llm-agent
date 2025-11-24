"""
Standalone Graph Queries

File-based graph queries that work independently of GraphManager.
Used by the main agent to read graph data without requiring a full GraphManager instance.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .graph_entities import GraphNode, GraphEdge
from .graph_storage import GraphStorage


class StandaloneGraphQueries:
    """Standalone graph queries for reading graph data without GraphManager."""
    
    def __init__(self, storage_path: str, embeddings_manager=None, logger=None):
        """Initialize standalone graph queries.
        
        Args:
            storage_path: Path to graph storage directory
            embeddings_manager: Optional embeddings manager for semantic search
            logger: Optional logger instance
        """
        self.storage_path = storage_path
        self.embeddings_manager = embeddings_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize storage
        self.storage = GraphStorage(storage_path)
        
        # Cache for loaded graph data
        self._nodes_cache = {}
        self._edges_cache = []
        self._cache_timestamp = 0
        self._cache_valid_duration = 5.0  # Cache for 5 seconds
        
        self.logger.debug(f"Initialized StandaloneGraphQueries with storage: {storage_path}")
    
    def _load_graph_data(self, force_refresh: bool = False):
        """Load graph data from files with caching."""
        current_time = datetime.now().timestamp()
        
        # Check if cache is still valid
        if not force_refresh and (current_time - self._cache_timestamp) < self._cache_valid_duration:
            return
        
        try:
            # Load nodes
            nodes_data = self.storage.load_nodes()
            self._nodes_cache = {}
            for node_id, node_data in nodes_data.items():
                self._nodes_cache[node_id] = GraphNode.from_dict(node_data)
            
            # Load edges
            edges_data = self.storage.load_edges()
            self._edges_cache = []
            for edge_data in edges_data:
                self._edges_cache.append(GraphEdge.from_dict(edge_data))
            
            self._cache_timestamp = current_time
            self.logger.debug(f"Loaded {len(self._nodes_cache)} nodes and {len(self._edges_cache)} edges")
            
        except Exception as e:
            self.logger.error(f"Failed to load graph data: {e}")
            # Keep existing cache if load fails
    
    def query_for_context(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Query the graph for relevant context using current data only.
        
        Args:
            query: Query text to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant graph context entries
        """
        self._load_graph_data()
        
        if not self.embeddings_manager:
            # Simple text matching fallback
            return self._text_based_query(query, max_results)
        
        try:
            # Use EmbeddingsManager for semantic search
            search_results = self.embeddings_manager.search(
                query=query,
                k=max_results * 3  # Get more results to account for filtering
            )
            
            # Filter for graph entities only
            graph_results = []
            for result in search_results:
                metadata = result.get('metadata', {})
                if metadata.get('source') == 'graph_entity':
                    # Get the corresponding node for additional data
                    entity_id = metadata.get('entity_id')
                    node = self._nodes_cache.get(entity_id) if entity_id else None
                    
                    if node:
                        graph_results.append({
                            'name': node.name,
                            'type': node.type,
                            'description': node.description,
                            'relevance_score': result.get('score', 0.0),
                            'source': 'semantic_search',
                            'entity_id': entity_id
                        })
                    
                    if len(graph_results) >= max_results:
                        break
            
            # Add metadata about current graph state
            if graph_results:
                graph_results[0]['graph_metadata'] = {
                    'total_nodes': len(self._nodes_cache),
                    'total_edges': len(self._edges_cache),
                    'query_timestamp': datetime.now().isoformat()
                }
            
            return graph_results
            
        except Exception as e:
            self.logger.error(f"Error in semantic graph query: {e}")
            # Fallback to text-based search
            return self._text_based_query(query, max_results)
    
    def _text_based_query(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback text-based search when embeddings are unavailable."""
        results = []
        query_lower = query.lower()
        
        for node in self._nodes_cache.values():
            if (query_lower in node.name.lower() or 
                query_lower in node.description.lower()):
                results.append({
                    'name': node.name,
                    'type': node.type,
                    'description': node.description,
                    'relevance_score': 1.0,
                    'source': 'text_match',
                    'entity_id': node.id
                })
                if len(results) >= max_results:
                    break
        
        return results
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entity by ID."""
        self._load_graph_data()
        
        node = self._nodes_cache.get(entity_id)
        if node:
            return {
                'name': node.name,
                'type': node.type,
                'description': node.description,
                'entity_id': node.id,
                'mention_count': node.mention_count,
                'created_at': node.created_at,
                'updated_at': node.updated_at,
                'attributes': node.attributes
            }
        
        return None
    
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific entity."""
        self._load_graph_data()
        
        relationships = []
        
        for edge in self._edges_cache:
            if edge.from_node_id == entity_id:
                # Outgoing relationship
                target_node = self._nodes_cache.get(edge.to_node_id)
                if target_node:
                    relationships.append({
                        'direction': 'outgoing',
                        'relationship': edge.relationship,
                        'target_entity': {
                            'id': target_node.id,
                            'name': target_node.name,
                            'type': target_node.type
                        },
                        'evidence': edge.evidence,
                        'confidence': edge.confidence
                    })
            
            elif edge.to_node_id == entity_id:
                # Incoming relationship
                source_node = self._nodes_cache.get(edge.from_node_id)
                if source_node:
                    relationships.append({
                        'direction': 'incoming',
                        'relationship': edge.relationship,
                        'source_entity': {
                            'id': source_node.id,
                            'name': source_node.name,
                            'type': source_node.type
                        },
                        'evidence': edge.evidence,
                        'confidence': edge.confidence
                    })
        
        return relationships
    
    def get_entities_by_type(self, entity_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get entities of a specific type."""
        self._load_graph_data()
        
        entities = []
        for node in self._nodes_cache.values():
            if node.type == entity_type:
                entities.append({
                    'name': node.name,
                    'type': node.type,
                    'description': node.description,
                    'entity_id': node.id,
                    'mention_count': node.mention_count
                })
                
                if len(entities) >= limit:
                    break
        
        # Sort by mention count (most mentioned first)
        entities.sort(key=lambda x: x['mention_count'], reverse=True)
        
        return entities
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get current graph statistics."""
        self._load_graph_data()
        
        # Count entities by type
        type_counts = {}
        for node in self._nodes_cache.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
        # Count relationships by type
        rel_counts = {}
        for edge in self._edges_cache:
            rel_counts[edge.relationship] = rel_counts.get(edge.relationship, 0) + 1
        
        return {
            'total_entities': len(self._nodes_cache),
            'total_relationships': len(self._edges_cache),
            'entity_types': type_counts,
            'relationship_types': rel_counts,
            'last_updated': datetime.now().isoformat()
        }
    
    def refresh_cache(self):
        """Force refresh of cached graph data."""
        self._load_graph_data(force_refresh=True)
        self.logger.debug("Forced refresh of graph data cache")
    
    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """Get all nodes (entities) from the graph.
        
        Returns:
            Dictionary mapping entity_id to GraphNode objects
        """
        self._load_graph_data()
        return self._nodes_cache
    
    @property
    def edges(self) -> List[GraphEdge]:
        """Get all edges (relationships) from the graph.
        
        Returns:
            List of GraphEdge objects
        """
        self._load_graph_data()
        return self._edges_cache