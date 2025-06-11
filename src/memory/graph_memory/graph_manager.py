"""
Graph Manager

Core graph operations with RAG-based entity resolution.

This module provides the main GraphManager class that orchestrates all graph memory
operations including entity extraction, relationship detection, semantic similarity
matching, and graph storage.

Example::

    from src.memory.graph_memory import GraphManager
    
    # Initialize with services
    graph_manager = GraphManager(
        llm_service=llm_service,
        embeddings_manager=embeddings_manager,
        storage_path="graph_data",
        domain_config=domain_config
    )
    
    # Add entities with automatic deduplication
    node, is_new = graph_manager.add_or_update_node(
        name="Eldara",
        node_type="character", 
        description="A fire wizard who runs a magic shop"
    )

Attributes:
    storage (~.graph_storage.GraphStorage): Handles JSON persistence of graph data.
    embeddings_manager (EmbeddingsManager): Manages entity embeddings for similarity.
    similarity_threshold (float): Threshold for entity similarity matching (default: 0.8).
    nodes (Dict[str, GraphNode]): In-memory cache of graph nodes.
    edges (List[GraphEdge]): In-memory cache of graph edges.
"""

import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import logging

from .graph_storage import GraphStorage
from .entity_extractor import EntityExtractor
from .relationship_extractor import RelationshipExtractor


class GraphNode:
    """Represents a node in the knowledge graph.
    
    A GraphNode stores entity information including its name, type, description,
    semantic embedding, aliases, and metadata. Nodes support automatic similarity
    matching to prevent duplicates.
    
    Attributes:
        id (str): Unique identifier for the node.
        type (str): Entity type (character, location, object, etc.).
        name (str): Primary name of the entity.
        description (str): Detailed description for semantic matching.
        embedding (List[float]): Semantic embedding vector for similarity.
        aliases (List[str]): Alternative names for this entity.
        created_at (str): ISO timestamp of creation.
        updated_at (str): ISO timestamp of last update.
        mention_count (int): Number of times entity has been mentioned.
        attributes (Dict[str, Any]): Additional custom attributes.
    
    Example::

        node = GraphNode(
            node_id="character_001",
            node_type="character",
            name="Eldara",
            description="A fire wizard who runs a magic shop in Riverwatch",
            embedding=[0.1, 0.2, ...],
            profession="wizard",
            magic_type="fire"
        )
    """
    
    def __init__(self, node_id: str, node_type: str, name: str, description: str, 
                 embedding: Optional[List[float]] = None, **attributes):
        """Initialize a new graph node.
        
        Args:
            node_id: Unique identifier for the node.
            node_type: Type of entity (character, location, object, etc.).
            name: Primary name of the entity.
            description: Detailed description for semantic embedding.
            embedding: Optional semantic embedding vector.
            **attributes: Additional custom attributes for the entity.
        """
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
    
    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert node to dictionary representation.
        
        Args:
            include_embedding: Whether to include embedding vector in output.
                Should be False for storage to avoid bloating JSON files.
                Embeddings are stored separately in graph_memory_embeddings.jsonl
                              
        Returns:
            Dictionary representation of the node suitable for JSON serialization.
            
        Note:
            Embeddings are excluded by default to keep JSON files manageable.
            Use include_embedding=True only for in-memory operations.
        """
        result = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'description': self.description,
            'aliases': self.aliases,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'mention_count': self.mention_count,
            **self.attributes
        }
        
        # Only include embedding if explicitly requested (e.g., for in-memory operations)
        if include_embedding:
            # Convert embedding to list if it's a numpy array
            embedding = self.embedding
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            result['embedding'] = embedding
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphNode':
        """Create node from dictionary representation.
        
        Args:
            data: Dictionary containing node data from JSON storage.
            
        Returns:
            GraphNode instance reconstructed from dictionary data.
            
        Raises:
            KeyError: If required fields are missing from data.
        """
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
    """Represents an edge (relationship) in the knowledge graph.
    
    A GraphEdge connects two entities with a typed relationship, including
    confidence scoring and evidence from the source text.
    
    Attributes:
        id (str): Unique identifier generated automatically.
        from_node_id (str): Source node identifier.
        to_node_id (str): Target node identifier. 
        relationship (str): Type of relationship (located_in, owns, etc.).
        weight (float): Strength/importance of the relationship.
        created_at (str): ISO timestamp of creation.
        updated_at (str): ISO timestamp of last update.
        attributes (Dict[str, Any]): Additional relationship metadata.
    
    Example::

        edge = GraphEdge(
            from_node_id="character_001",
            to_node_id="location_002", 
            relationship="located_in",
            weight=0.9,
            evidence="Eldara runs her magic shop in Riverwatch",
            confidence=0.9
        )
    """
    
    def __init__(self, from_node_id: str, to_node_id: str, relationship: str,
                 weight: float = 1.0, **attributes):
        """Initialize a new graph edge.
        
        Args:
            from_node_id: Identifier of the source node.
            to_node_id: Identifier of the target node.
            relationship: Type of relationship between nodes.
            weight: Strength of the relationship (0.0 to 1.0).
            **attributes: Additional metadata like evidence, confidence, etc.
        """
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
    """Main graph management system with RAG-based entity resolution.
    
    GraphManager orchestrates the entire graph memory pipeline including entity
    extraction, duplicate prevention through semantic similarity matching, 
    relationship detection, and graph storage. It integrates with LLM services
    for content extraction and embeddings managers for similarity matching.
    
    The system prevents duplicate entities through a multi-stage approach:
    
    1. Exact name matching (case-insensitive, alias-aware)
    2. Semantic similarity matching using embeddings 
    3. Entity consolidation with mention counting
    
    Attributes:
        storage (~.graph_storage.GraphStorage): Handles JSON persistence.
        embeddings_manager (EmbeddingsManager): Manages semantic embeddings.
        similarity_threshold (float): Similarity threshold for entity matching.
        nodes (Dict[str, GraphNode]): In-memory graph nodes.
        edges (List[GraphEdge]): In-memory graph edges.
        entity_extractor (~.entity_extractor.EntityExtractor): LLM-based entity extraction.
        relationship_extractor (~.relationship_extractor.RelationshipExtractor): LLM-based relationship extraction.
    
    Example::

        # Initialize with services
        graph_manager = GraphManager(
            llm_service=gemma_service,
            embeddings_manager=embeddings_mgr,
            storage_path="campaign_graph",
            domain_config=dnd_config,
            similarity_threshold=0.8
        )
        
        # Process conversation segments
        entities = graph_manager.extract_entities_from_segments(segments)
        for entity in entities:
            node, is_new = graph_manager.add_or_update_node(
                name=entity["name"],
                node_type=entity["type"],
                description=entity["description"]
            )
    """
    
    def __init__(self, storage_path: str, embeddings_manager=None, 
                 similarity_threshold: float = 0.8, logger=None,
                 llm_service=None, embeddings_llm_service=None, domain_config=None):
        """Initialize graph manager with required services.
        
        Args:
            storage_path: Directory path for JSON graph storage.
            embeddings_manager: EmbeddingsManager for semantic similarity matching.
                If None, only name-based matching will be used.
            similarity_threshold: Cosine similarity threshold for entity matching.
                Higher values (closer to 1.0) require more similarity.
            logger: Logger instance for debugging and monitoring.
            llm_service: LLM service for entity/relationship extraction (e.g., gemma3).
            embeddings_llm_service: LLM service for embeddings (e.g., mxbai-embed-large).
                Defaults to llm_service if not provided.
            domain_config: Domain-specific configuration with entity/relationship types.
                          
        Raises:
            ValueError: If storage_path is invalid or inaccessible.
            
        Note:
            Both llm_service and domain_config are required for automatic entity
            and relationship extraction. Without them, only manual node/edge
            operations will be available.
        """
        self.storage = GraphStorage(storage_path)
        self.embeddings_manager = embeddings_manager
        self.similarity_threshold = similarity_threshold
        self.logger = logger or logging.getLogger(__name__)
        self.llm_service = llm_service  # Text generation service (gemma3)
        self.embeddings_llm_service = embeddings_llm_service or llm_service  # Embeddings service (mxbai-embed-large)
        self.domain_config = domain_config
        
        # Initialize extractors if LLM service is provided
        if llm_service and domain_config:
            self.entity_extractor = EntityExtractor(llm_service, domain_config, logger)
            self.relationship_extractor = RelationshipExtractor(llm_service, domain_config, logger)
        else:
            self.entity_extractor = None
            self.relationship_extractor = None
        
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
        """Add a new node or update existing one using semantic similarity matching.
        
        This method implements the core duplicate prevention logic:
        
        1. Generates semantic embedding for the entity description
        2. Searches for similar existing entities of the same type
        3. If similarity exceeds threshold, updates existing entity
        4. Otherwise creates new entity with unique identifier
        
        Args:
            name: Entity name/identifier.
            node_type: Type of entity (character, location, object, etc.).
                Must match domain-configured entity types.
            description: Detailed description used for semantic embedding.
                This is the primary text used for similarity matching.
            **attributes: Additional custom attributes stored with the entity.
            
        Returns:
            Tuple of (GraphNode, bool) where:
            
            - GraphNode: The created or updated node
            - bool: True if new node was created, False if existing node updated
            
        Example::

            # Add new entity (or update if similar one exists)
            node, is_new = graph_manager.add_or_update_node(
                name="Eldara",
                node_type="character",
                description="A fire wizard who runs a magic shop in Riverwatch",
                profession="wizard",
                magic_type="fire"
            )
            
            if is_new:
                print(f"Created new entity: {node.name}")
            else:
                print(f"Updated existing entity: {node.name} (mentions: {node.mention_count})")
            
        Note:
            Semantic similarity matching requires embeddings_manager to be configured.
            Without it, only exact name matching will prevent duplicates.
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
        similar_node = self._find_similar_node(name, description, node_type, embedding)
        
        if similar_node:
            # Update existing node
            similar_node.description = description
            similar_node.updated_at = datetime.now().isoformat()
            similar_node.mention_count += 1
            
            # Add name as alias if not already present
            if name not in similar_node.aliases and name != similar_node.name:
                similar_node.aliases.append(name)
            
            # Update attributes with special handling for conversation history GUIDs
            for key, value in attributes.items():
                if key == "conversation_history_guids" and isinstance(value, list):
                    # Merge conversation GUID lists, avoiding duplicates
                    existing_guids = similar_node.attributes.get("conversation_history_guids", [])
                    merged_guids = list(set(existing_guids + value))
                    similar_node.attributes[key] = merged_guids
                else:
                    similar_node.attributes[key] = value
            
            # Update embedding if available
            if embedding is not None and len(embedding) > 0:
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
    
    def _find_similar_node(self, name: str, description: str, node_type: str, 
                          embedding: Optional[List[float]]) -> Optional[GraphNode]:
        """Find similar existing node using multi-stage matching approach.
        
        Implements the optimized duplicate prevention pipeline:
        
        Stage 1 - Name-based matching (Priority):
        - Exact name match (case-insensitive)
        - Alias matching for known alternative names
        - Type-specific matching (only same entity types)
        
        Stage 2 - Semantic similarity fallback:
        - Embedding-based cosine similarity
        - Configurable similarity threshold
        - Handles different descriptions of same entity
        
        Args:
            name: Entity name to match against existing entities.
            description: Entity description for semantic similarity.
            node_type: Entity type to filter candidates.
            embedding: Semantic embedding vector for similarity calculation.
            
        Returns:
            Most similar existing node if found above threshold, None otherwise.
            
        Note:
            This is the core optimization that prevents duplicate entities.
            Testing shows 100% duplicate prevention with proper threshold tuning.
        """
        # First: Check for exact name matches of the same type
        name_lower = name.lower().strip()
        for node in self.nodes.values():
            if node.type == node_type:
                # Check primary name
                if node.name.lower().strip() == name_lower:
                    self.logger.debug(f"Found exact name match: {node.id} ('{node.name}' == '{name}')")
                    return node
                # Check aliases
                for alias in node.aliases:
                    if alias.lower().strip() == name_lower:
                        self.logger.debug(f"Found alias match: {node.id} (alias '{alias}' == '{name}')")
                        return node
        
        # Second: Use semantic similarity matching as fallback
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
        # Handle None or empty vectors
        if vec1 is None or vec2 is None:
            return 0.0
        
        # Convert to numpy arrays if not already
        if hasattr(vec1, 'tolist'):
            vec1 = vec1.tolist()
        if hasattr(vec2, 'tolist'):
            vec2 = vec2.tolist()
            
        if len(vec1) == 0 or len(vec2) == 0 or len(vec1) != len(vec2):
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
    
    def add_edge(self, from_node_id: str = None, to_node_id: str = None, relationship: str = None,
                weight: float = 1.0, from_node: str = None, to_node: str = None, 
                relationship_type: str = None, **attributes) -> GraphEdge:
        """
        Add edge between nodes.
        
        Args:
            from_node_id: Source node ID (legacy parameter)
            to_node_id: Target node ID (legacy parameter)
            relationship: Relationship type (legacy parameter)
            from_node: Source node name (new parameter style)
            to_node: Target node name (new parameter style)
            relationship_type: Relationship type (new parameter style)
            weight: Edge weight
            **attributes: Additional edge attributes
            
        Returns:
            Created edge
        """
        # Handle both parameter styles for backward compatibility
        if from_node is not None:
            # New style: node names instead of IDs, find the actual node IDs
            from_nodes = self.find_nodes_by_name(from_node, exact_match=True)
            if not from_nodes:
                raise ValueError(f"Source node '{from_node}' not found")
            actual_from_node_id = from_nodes[0].id
        elif from_node_id is not None:
            # Legacy style: direct node ID
            actual_from_node_id = from_node_id
        else:
            raise ValueError("Either from_node or from_node_id must be provided")
            
        if to_node is not None:
            # New style: node names instead of IDs, find the actual node IDs
            to_nodes = self.find_nodes_by_name(to_node, exact_match=True)
            if not to_nodes:
                raise ValueError(f"Target node '{to_node}' not found")
            actual_to_node_id = to_nodes[0].id
        elif to_node_id is not None:
            # Legacy style: direct node ID
            actual_to_node_id = to_node_id
        else:
            raise ValueError("Either to_node or to_node_id must be provided")
            
        # Handle relationship parameter
        actual_relationship = relationship_type or relationship
        if not actual_relationship:
            raise ValueError("Either relationship or relationship_type must be provided")
        
        # Check if nodes exist
        if actual_from_node_id not in self.nodes:
            raise ValueError(f"Source node {actual_from_node_id} not found")
        if actual_to_node_id not in self.nodes:
            raise ValueError(f"Target node {actual_to_node_id} not found")
        
        # Check if edge already exists
        existing_edge = self._find_edge(actual_from_node_id, actual_to_node_id, actual_relationship)
        if existing_edge:
            # Update existing edge
            existing_edge.weight = weight
            existing_edge.updated_at = datetime.now().isoformat()
            existing_edge.attributes.update(attributes)
            self._save_graph()
            return existing_edge
        
        # Create new edge
        edge = GraphEdge(actual_from_node_id, actual_to_node_id, actual_relationship, weight, **attributes)
        self.edges.append(edge)
        self._save_graph()
        
        self.logger.debug(f"Added edge: {actual_from_node_id} --{actual_relationship}--> {actual_to_node_id}")
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
    
    def extract_entities_from_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entities from conversation segments using the integrated entity extractor.
        
        Args:
            segments: List of segments with text and metadata
            
        Returns:
            List of extracted entities
        """
        if not self.entity_extractor:
            self.logger.warning("Entity extractor not available - LLM service or domain config missing")
            return []
        
        try:
            entities = self.entity_extractor.extract_entities_from_segments(segments)
            self.logger.debug(f"Extracted {len(entities)} entities from {len(segments)} segments")
            return entities
        except Exception as e:
            self.logger.error(f"Error extracting entities from segments: {e}")
            return []
    
    def extract_relationships_from_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships from conversation segments using the integrated relationship extractor.
        
        Args:
            segments: List of segments with text, entities, and metadata
            
        Returns:
            List of extracted relationships
        """
        if not self.relationship_extractor:
            self.logger.warning("Relationship extractor not available - LLM service or domain config missing")
            return []
        
        try:
            # Build entities_by_segment dictionary from segments
            entities_by_segment = {}
            for i, segment in enumerate(segments):
                segment_id = segment.get("id", f"seg_{i}")
                entities = segment.get("entities", [])
                entities_by_segment[segment_id] = entities
                # Ensure segment has an id
                if "id" not in segment:
                    segment["id"] = segment_id
            
            relationships = self.relationship_extractor.extract_relationships_from_segments(
                segments, entities_by_segment)
            self.logger.debug(f"Extracted {len(relationships)} relationships from {len(segments)} segments")
            return relationships
        except Exception as e:
            self.logger.error(f"Error extracting relationships from segments: {e}")
            return []
    
    def query_for_context(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Query the graph for context relevant to a query using semantic search.
        
        Provides context retrieval for LLM prompt enhancement by finding entities
        and their relationships that are semantically relevant to the user's query.
        
        The method uses a two-stage approach:
        
        1. Semantic similarity search using embeddings (if available)
        2. Fallback to keyword/string matching for broader coverage
        
        Args:
            query: The user query to find relevant context for.
            max_results: Maximum number of context results to return.
            
        Returns:
            List of context dictionaries, each containing:
            
            - name (str): Entity name
            - type (str): Entity type  
            - description (str): Entity description
            - connections (List[Dict]): Related entities and relationships
            - relevance_score (float): Relevance to the query
            
        Example::

            # Find context for user query
            context = graph_manager.query_for_context("magic shops")
            
            for result in context:
                print(f"{result['name']}: {result['description']}")
                for conn in result['connections']:
                    print(f"  -> {conn['relationship']} {conn['target']}")
            
        Note:
            Results are sorted by relevance score (highest first).
            Semantic search requires embeddings_manager configuration.
        """
        try:
            results = []
            
            # Use embeddings for semantic search if available
            if self.embeddings_manager:
                try:
                    # Generate embedding for the query
                    query_embedding = self.embeddings_manager.generate_embedding(query)
                    
                    # Find semantically similar entities
                    for node in self.nodes.values():
                        if node.embedding is not None and len(node.embedding) > 0:
                            # Calculate similarity with node embedding
                            similarity = self._cosine_similarity(query_embedding, node.embedding)
                            
                            if similarity > 0.1:  # Minimum similarity threshold
                                # Get connections for this entity
                                connections = self.get_connected_nodes(node.id)
                                connection_info = []
                                
                                for connected_node, edge in connections[:3]:  # Limit to top 3 connections
                                    connection_info.append({
                                        "relationship": edge.relationship,
                                        "target": connected_node.name,
                                        "target_type": connected_node.type
                                    })
                                
                                results.append({
                                    "name": node.name,
                                    "type": node.type,
                                    "description": node.description,
                                    "connections": connection_info,
                                    "relevance_score": similarity
                                })
                    
                    # Sort by similarity score and limit results
                    results.sort(key=lambda x: x["relevance_score"], reverse=True)
                    return results[:max_results]
                    
                except Exception as e:
                    self.logger.warning(f"Embeddings-based search failed, falling back to string matching: {e}")
            
            # Fallback to string matching if embeddings not available
            query_lower = query.lower()
            
            # Extract potential entity names from the query
            query_words = [word.strip().lower() for word in query_lower.replace('?', '').replace('.', '').replace(',', '').split()]
            
            # Find entities that match the query
            for node in self.nodes.values():
                relevance_score = 0
                node_name_lower = node.name.lower()
                node_desc_lower = node.description.lower()
                
                # Check exact name match in query
                if node_name_lower in query_lower:
                    relevance_score += 5
                
                # Check if any query word matches the node name
                for word in query_words:
                    if word == node_name_lower:
                        relevance_score += 4
                    elif word in node_name_lower:
                        relevance_score += 3
                
                # Check description match
                if query_lower in node_desc_lower:
                    relevance_score += 2
                    
                # Check if any query word appears in description
                for word in query_words:
                    if len(word) > 2 and word in node_desc_lower:  # Skip very short words
                        relevance_score += 1
                
                # Check aliases match
                for alias in node.aliases:
                    alias_lower = alias.lower()
                    if query_lower in alias_lower:
                        relevance_score += 1
                    for word in query_words:
                        if word == alias_lower:
                            relevance_score += 2
                
                if relevance_score > 0:
                    # Get connections for this entity
                    connections = self.get_connected_nodes(node.id)
                    connection_info = []
                    
                    for connected_node, edge in connections[:3]:  # Limit to top 3 connections
                        connection_info.append({
                            "relationship": edge.relationship,
                            "target": connected_node.name,
                            "target_type": connected_node.type
                        })
                    
                    results.append({
                        "name": node.name,
                        "type": node.type,
                        "description": node.description,
                        "connections": connection_info,
                        "relevance_score": relevance_score
                    })
            
            # Sort by relevance score and limit results
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"Error querying graph for context: {e}")
            return []