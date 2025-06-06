"""
Graph Manager

Core graph operations with RAG-based entity resolution.
"""

import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import logging

from .graph_storage import GraphStorage


class GraphNode:
    """Represents a node in the knowledge graph."""
    
    def __init__(self, node_id: str, node_type: str, name: str, description: str, 
                 embedding: Optional[List[float]] = None, **attributes):
        self.id = node_id
        self.type = node_type
        self.name = name
        self.description = description
        self.embedding = embedding if embedding is not None else []
        self.attributes = attributes
        self.aliases = attributes.get('aliases', [])
        self.created_at = attributes.get('created_at', datetime.now().isoformat())
        self.updated_at = datetime.now().isoformat()
        self.mention_count = attributes.get('mention_count', 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        # Convert embedding to list if it's a numpy array
        embedding = self.embedding
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        
        return {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'description': self.description,
            'embedding': embedding,
            'aliases': self.aliases,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'mention_count': self.mention_count,
            **self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphNode':
        """Create node from dictionary representation."""
        attributes = data.copy()
        # Remove standard fields from attributes
        for field in ['id', 'type', 'name', 'description', 'embedding']:
            attributes.pop(field, None)
        
        return cls(
            node_id=data['id'],
            node_type=data['type'],
            name=data['name'],
            description=data['description'],
            embedding=data.get('embedding', []),
            **attributes
        )


class GraphEdge:
    """Represents an edge in the knowledge graph."""
    
    def __init__(self, from_node_id: str, to_node_id: str, relationship: str,
                 weight: float = 1.0, **attributes):
        self.id = str(uuid.uuid4())
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.relationship = relationship
        self.weight = weight
        self.attributes = attributes
        self.created_at = attributes.get('created_at', datetime.now().isoformat())
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary representation."""
        return {
            'id': self.id,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'relationship': self.relationship,
            'weight': self.weight,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            **self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphEdge':
        """Create edge from dictionary representation."""
        attributes = data.copy()
        # Remove standard fields from attributes
        for field in ['id', 'from_node_id', 'to_node_id', 'relationship', 'weight']:
            attributes.pop(field, None)
        
        edge = cls(
            from_node_id=data['from_node_id'],
            to_node_id=data['to_node_id'],
            relationship=data['relationship'],
            weight=data.get('weight', 1.0),
            **attributes
        )
        edge.id = data.get('id', edge.id)
        return edge


class GraphManager:
    """
    Main graph management system with RAG-based entity resolution.
    """
    
    def __init__(self, storage_path: str, embeddings_manager=None, 
                 similarity_threshold: float = 0.8, logger=None):
        """
        Initialize graph manager.
        
        Args:
            storage_path: Path for graph storage
            embeddings_manager: EmbeddingsManager instance for entity matching
            similarity_threshold: Threshold for entity similarity matching
            logger: Logger instance
        """
        self.storage = GraphStorage(storage_path)
        self.embeddings_manager = embeddings_manager
        self.similarity_threshold = similarity_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Load existing graph data
        self._load_graph()
    
    def _load_graph(self) -> None:
        """Load graph data from storage."""
        nodes_data = self.storage.load_nodes()
        edges_data = self.storage.load_edges()
        
        self.nodes = {
            node_id: GraphNode.from_dict(node_data)
            for node_id, node_data in nodes_data.items()
        }
        
        self.edges = [
            GraphEdge.from_dict(edge_data)
            for edge_data in edges_data
        ]
        
        self.logger.debug(f"Loaded graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
    
    def _save_graph(self) -> None:
        """Save graph data to storage."""
        nodes_data = {
            node_id: node.to_dict()
            for node_id, node in self.nodes.items()
        }
        
        edges_data = [edge.to_dict() for edge in self.edges]
        
        self.storage.save_nodes(nodes_data)
        self.storage.save_edges(edges_data)
        
        self.logger.debug(f"Saved graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
    
    def add_or_update_node(self, name: str, node_type: str, description: str,
                          **attributes) -> Tuple[GraphNode, bool]:
        """
        Add a new node or update existing one using semantic similarity matching.
        
        Args:
            name: Node name
            node_type: Node type (character, location, object, etc.)
            description: Node description for embedding
            **attributes: Additional node attributes
            
        Returns:
            Tuple of (node, is_new) where is_new indicates if node was created
        """
        # Generate embedding for the description and save to embeddings manager
        embedding = None
        if self.embeddings_manager:
            try:
                embedding = self.embeddings_manager.generate_embedding(description)
                # Also save to embeddings manager file for persistence
                entity_metadata = {
                    'entity_name': name,
                    'entity_type': node_type,
                    'text': description,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'graph_entity'
                }
                entity_metadata.update(attributes)
                self.embeddings_manager.add_embedding(description, entity_metadata)
            except Exception as e:
                self.logger.warning(f"Failed to generate/save embedding: {e}")
        
        # Look for similar existing nodes
        similar_node = self._find_similar_node(description, node_type, embedding)
        
        if similar_node:
            # Update existing node
            similar_node.description = description
            similar_node.updated_at = datetime.now().isoformat()
            similar_node.mention_count += 1
            
            # Add name as alias if not already present
            if name not in similar_node.aliases and name != similar_node.name:
                similar_node.aliases.append(name)
            
            # Update attributes
            similar_node.attributes.update(attributes)
            
            # Update embedding if available
            if embedding:
                similar_node.embedding = embedding
            
            self._save_graph()
            self.logger.debug(f"Updated existing node: {similar_node.id}")
            return similar_node, False
        
        else:
            # Create new node
            node_id = f"{node_type}_{str(uuid.uuid4())[:8]}"
            new_node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                name=name,
                description=description,
                embedding=embedding,
                aliases=[],
                **attributes
            )
            
            self.nodes[node_id] = new_node
            self._save_graph()
            self.logger.debug(f"Created new node: {node_id}")
            return new_node, True
    
    def _find_similar_node(self, description: str, node_type: str, 
                          embedding: Optional[List[float]]) -> Optional[GraphNode]:
        """
        Find similar existing node using semantic similarity.
        
        Args:
            description: Description to match
            node_type: Node type to filter by
            embedding: Embedding vector for similarity search
            
        Returns:
            Most similar node if found, None otherwise
        """
        if embedding is None or len(embedding) == 0 or not self.embeddings_manager:
            return None
        
        # Get nodes of the same type with embeddings
        candidate_nodes = [
            node for node in self.nodes.values()
            if node.type == node_type and len(node.embedding) > 0
        ]
        
        if not candidate_nodes:
            return None
        
        best_similarity = 0.0
        best_node = None
        
        for node in candidate_nodes:
            try:
                # Calculate cosine similarity
                similarity = self._cosine_similarity(embedding, node.embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_node = node
            
            except Exception as e:
                self.logger.warning(f"Error calculating similarity for node {node.id}: {e}")
                continue
        
        if best_node:
            self.logger.debug(f"Found similar node {best_node.id} with similarity {best_similarity:.3f}")
        
        return best_node
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def add_edge(self, from_node_id: str, to_node_id: str, relationship: str,
                weight: float = 1.0, **attributes) -> GraphEdge:
        """
        Add edge between nodes.
        
        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            relationship: Relationship type
            weight: Edge weight
            **attributes: Additional edge attributes
            
        Returns:
            Created edge
        """
        # Check if nodes exist
        if from_node_id not in self.nodes:
            raise ValueError(f"Source node {from_node_id} not found")
        if to_node_id not in self.nodes:
            raise ValueError(f"Target node {to_node_id} not found")
        
        # Check if edge already exists
        existing_edge = self._find_edge(from_node_id, to_node_id, relationship)
        if existing_edge:
            # Update existing edge
            existing_edge.weight = weight
            existing_edge.updated_at = datetime.now().isoformat()
            existing_edge.attributes.update(attributes)
            self._save_graph()
            return existing_edge
        
        # Create new edge
        edge = GraphEdge(from_node_id, to_node_id, relationship, weight, **attributes)
        self.edges.append(edge)
        self._save_graph()
        
        self.logger.debug(f"Added edge: {from_node_id} --{relationship}--> {to_node_id}")
        return edge
    
    def _find_edge(self, from_node_id: str, to_node_id: str, 
                   relationship: str) -> Optional[GraphEdge]:
        """Find existing edge with same from/to/relationship."""
        for edge in self.edges:
            if (edge.from_node_id == from_node_id and 
                edge.to_node_id == to_node_id and 
                edge.relationship == relationship):
                return edge
        return None
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)
    
    def find_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Find all nodes of a specific type."""
        return [node for node in self.nodes.values() if node.type == node_type]
    
    def find_nodes_by_name(self, name: str, exact_match: bool = False) -> List[GraphNode]:
        """Find nodes by name or aliases."""
        results = []
        name_lower = name.lower()
        
        for node in self.nodes.values():
            if exact_match:
                if (node.name.lower() == name_lower or 
                    any(alias.lower() == name_lower for alias in node.aliases)):
                    results.append(node)
            else:
                if (name_lower in node.name.lower() or 
                    any(name_lower in alias.lower() for alias in node.aliases)):
                    results.append(node)
        
        return results
    
    def get_connected_nodes(self, node_id: str, relationship: Optional[str] = None) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Get nodes connected to the given node.
        
        Args:
            node_id: Source node ID
            relationship: Optional relationship filter
            
        Returns:
            List of (connected_node, edge) tuples
        """
        results = []
        
        for edge in self.edges:
            if edge.from_node_id == node_id:
                if relationship is None or edge.relationship == relationship:
                    target_node = self.nodes.get(edge.to_node_id)
                    if target_node:
                        results.append((target_node, edge))
        
        return results
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        node_types = {}
        relationship_types = {}
        
        for node in self.nodes.values():
            node_types[node.type] = node_types.get(node.type, 0) + 1
        
        for edge in self.edges:
            relationship_types[edge.relationship] = relationship_types.get(edge.relationship, 0) + 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'node_types': node_types,
            'relationship_types': relationship_types,
            'storage_stats': self.storage.get_storage_stats()
        }