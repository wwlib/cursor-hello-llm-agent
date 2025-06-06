"""
Graph Queries

Query interface for retrieving context from the knowledge graph.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import logging
from collections import defaultdict, deque


class GraphQueries:
    """Provides query interface for knowledge graph."""
    
    def __init__(self, graph_manager, logger=None):
        """
        Initialize graph queries.
        
        Args:
            graph_manager: GraphManager instance
            logger: Logger instance
        """
        self.graph_manager = graph_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def find_entity_context(self, entity_name: str, max_depth: int = 2, 
                           max_results: int = 10) -> Dict[str, Any]:
        """
        Find comprehensive context about an entity.
        
        Args:
            entity_name: Name of entity to find context for
            max_depth: Maximum relationship depth to explore
            max_results: Maximum number of related entities to return
            
        Returns:
            Dictionary with entity information and related context
        """
        # Find the entity
        entities = self.graph_manager.find_nodes_by_name(entity_name, exact_match=False)
        if not entities:
            return {'found': False, 'message': f'Entity "{entity_name}" not found'}
        
        # Use the first/best match
        entity = entities[0]
        
        # Get connected entities with BFS
        connected = self._get_connected_entities_bfs(entity.id, max_depth, max_results)
        
        # Organize by relationship type
        relationships_by_type = defaultdict(list)
        for related_entity, edge, depth in connected:
            relationships_by_type[edge.relationship].append({
                'entity': {
                    'name': related_entity.name,
                    'type': related_entity.type,
                    'description': related_entity.description
                },
                'relationship': edge.relationship,
                'weight': edge.weight,
                'depth': depth
            })
        
        context = {
            'found': True,
            'entity': {
                'name': entity.name,
                'type': entity.type,
                'description': entity.description,
                'aliases': entity.aliases,
                'mention_count': entity.mention_count
            },
            'direct_connections': len([r for r in connected if r[2] == 1]),
            'total_connections': len(connected),
            'relationships': dict(relationships_by_type),
            'context_summary': self._generate_context_summary(entity, connected)
        }
        
        return context
    
    def _get_connected_entities_bfs(self, start_node_id: str, max_depth: int, 
                                   max_results: int) -> List[Tuple[Any, Any, int]]:
        """Get connected entities using breadth-first search."""
        visited = set()
        queue = deque([(start_node_id, 0)])  # (node_id, depth)
        results = []
        
        while queue and len(results) < max_results:
            current_id, depth = queue.popleft()
            
            if current_id in visited or depth >= max_depth:
                continue
            
            visited.add(current_id)
            
            # Get all connected nodes
            connected_nodes = self.graph_manager.get_connected_nodes(current_id)
            
            for connected_node, edge in connected_nodes:
                if connected_node.id not in visited and len(results) < max_results:
                    results.append((connected_node, edge, depth + 1))
                    
                    # Add to queue for further exploration
                    if depth + 1 < max_depth:
                        queue.append((connected_node.id, depth + 1))
        
        return results
    
    def _generate_context_summary(self, entity, connected_entities) -> str:
        """Generate a natural language summary of entity context."""
        if not connected_entities:
            return f"{entity.name} is a {entity.type}. {entity.description}"
        
        # Group relationships
        locations = []
        possessions = []
        associations = []
        
        for related_entity, edge, depth in connected_entities[:5]:  # Top 5 most relevant
            if edge.relationship == 'located_in':
                locations.append(related_entity.name)
            elif edge.relationship in ['owns', 'uses']:
                possessions.append(related_entity.name)
            else:
                associations.append(f"{edge.relationship} {related_entity.name}")
        
        summary_parts = [f"{entity.name} is a {entity.type}. {entity.description}"]
        
        if locations:
            summary_parts.append(f"Located in: {', '.join(locations)}.")
        
        if possessions:
            summary_parts.append(f"Associated with: {', '.join(possessions)}.")
        
        if associations:
            summary_parts.append(f"Also: {', '.join(associations[:3])}.")
        
        return " ".join(summary_parts)
    
    def find_entities_by_type(self, entity_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Find all entities of a specific type."""
        nodes = self.graph_manager.find_nodes_by_type(entity_type)
        
        results = []
        for node in nodes[:limit]:
            # Get connection count
            connections = self.graph_manager.get_connected_nodes(node.id)
            
            results.append({
                'name': node.name,
                'type': node.type,
                'description': node.description,
                'mention_count': node.mention_count,
                'connection_count': len(connections),
                'aliases': node.aliases
            })
        
        # Sort by relevance (mention count * connection count)
        results.sort(key=lambda x: x['mention_count'] * x['connection_count'], reverse=True)
        
        return results
    
    def find_path_between_entities(self, from_entity: str, to_entity: str, 
                                  max_depth: int = 4) -> Optional[Dict[str, Any]]:
        """
        Find relationship path between two entities.
        
        Args:
            from_entity: Starting entity name
            to_entity: Target entity name
            max_depth: Maximum path length to search
            
        Returns:
            Dictionary with path information or None if no path found
        """
        # Find entity nodes
        from_nodes = self.graph_manager.find_nodes_by_name(from_entity, exact_match=False)
        to_nodes = self.graph_manager.find_nodes_by_name(to_entity, exact_match=False)
        
        if not from_nodes or not to_nodes:
            return None
        
        from_node = from_nodes[0]
        to_node = to_nodes[0]
        
        # BFS to find shortest path
        queue = deque([(from_node.id, [from_node.id])])
        visited = set()
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == to_node.id:
                # Found path - build response
                return self._build_path_response(path)
            
            if current_id in visited or len(path) >= max_depth:
                continue
            
            visited.add(current_id)
            
            # Explore connected nodes
            connected_nodes = self.graph_manager.get_connected_nodes(current_id)
            for connected_node, edge in connected_nodes:
                if connected_node.id not in visited:
                    new_path = path + [connected_node.id]
                    queue.append((connected_node.id, new_path))
        
        return None  # No path found
    
    def _build_path_response(self, node_ids: List[str]) -> Dict[str, Any]:
        """Build response for entity path."""
        if len(node_ids) < 2:
            return None
        
        path_info = []
        
        for i in range(len(node_ids) - 1):
            from_id = node_ids[i]
            to_id = node_ids[i + 1]
            
            from_node = self.graph_manager.get_node(from_id)
            to_node = self.graph_manager.get_node(to_id)
            
            # Find the edge between these nodes
            edge = None
            for e in self.graph_manager.edges:
                if e.from_node_id == from_id and e.to_node_id == to_id:
                    edge = e
                    break
            
            if from_node and to_node and edge:
                path_info.append({
                    'from': from_node.name,
                    'to': to_node.name,
                    'relationship': edge.relationship,
                    'weight': edge.weight
                })
        
        return {
            'path_found': True,
            'path_length': len(node_ids) - 1,
            'path': path_info,
            'summary': self._generate_path_summary(path_info)
        }
    
    def _generate_path_summary(self, path_info: List[Dict[str, Any]]) -> str:
        """Generate natural language summary of entity path."""
        if not path_info:
            return "No connection found."
        
        if len(path_info) == 1:
            step = path_info[0]
            return f"{step['from']} {step['relationship']} {step['to']}"
        
        summary = f"{path_info[0]['from']}"
        for step in path_info:
            summary += f" {step['relationship']} {step['to']}"
        
        return summary
    
    def get_recent_entities(self, limit: int = 10, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recently mentioned entities."""
        nodes = list(self.graph_manager.nodes.values())
        
        # Filter by type if specified
        if entity_type:
            nodes = [n for n in nodes if n.type == entity_type]
        
        # Sort by updated_at (most recent first)
        nodes.sort(key=lambda x: x.updated_at, reverse=True)
        
        results = []
        for node in nodes[:limit]:
            connections = self.graph_manager.get_connected_nodes(node.id)
            results.append({
                'name': node.name,
                'type': node.type,
                'description': node.description,
                'last_mentioned': node.updated_at,
                'mention_count': node.mention_count,
                'connection_count': len(connections)
            })
        
        return results
    
    def get_context_for_query(self, query_text: str, max_entities: int = 5) -> Dict[str, Any]:
        """
        Get relevant graph context for a user query.
        
        Args:
            query_text: User query text
            max_entities: Maximum entities to include in context
            
        Returns:
            Relevant graph context for the query
        """
        # Simple keyword matching for entity relevance
        # In a more sophisticated version, this could use embeddings
        query_lower = query_text.lower()
        relevant_entities = []
        
        for node in self.graph_manager.nodes.values():
            # Check if entity name or aliases appear in query
            relevance_score = 0
            
            if node.name.lower() in query_lower:
                relevance_score += 10
            
            for alias in node.aliases:
                if alias.lower() in query_lower:
                    relevance_score += 5
            
            # Check description for partial matches
            for word in query_lower.split():
                if len(word) > 3 and word in node.description.lower():
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_entities.append((node, relevance_score))
        
        # Sort by relevance and get top entities
        relevant_entities.sort(key=lambda x: x[1], reverse=True)
        top_entities = relevant_entities[:max_entities]
        
        if not top_entities:
            return {'entities_found': 0, 'context': ''}
        
        # Build context summary
        context_parts = []
        for entity, score in top_entities:
            entity_context = self.find_entity_context(entity.name, max_depth=1, max_results=3)
            if entity_context.get('found'):
                context_parts.append(entity_context['context_summary'])
        
        return {
            'entities_found': len(top_entities),
            'relevant_entities': [e.name for e, s in top_entities],
            'context': ' '.join(context_parts),
            'entity_details': [
                {
                    'name': e.name,
                    'type': e.type,
                    'relevance_score': s
                } for e, s in top_entities
            ]
        }