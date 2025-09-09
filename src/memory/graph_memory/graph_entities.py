"""
Graph Entity Classes

Core data structures for graph nodes and edges.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class GraphNode:
    """Represents a node in the knowledge graph.
    
    A node encapsulates an entity (character, location, object, etc.) with its metadata
    and relationship tracking. Embeddings for semantic similarity are handled separately
    by the EmbeddingsManager.
    
    Attributes:
        id (str): Unique identifier for the node.
        name (str): Human-readable name of the entity.
        type (str): Entity type (character, location, object, etc.).
        description (str): Detailed description for semantic matching.
        attributes (Dict[str, Any]): Additional domain-specific attributes.
        aliases (List[str]): Alternative names for this entity.
        mention_count (int): Number of times this entity has been mentioned.
        created_at (str): ISO timestamp of creation.
        updated_at (str): ISO timestamp of last update.
    """
    
    def __init__(self, node_id: str, name: str, node_type: str, description: str,
                 attributes: Optional[Dict[str, Any]] = None,
                 aliases: Optional[List[str]] = None, mention_count: int = 1,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        """Initialize a graph node."""
        self.id = node_id
        self.name = name
        self.type = node_type
        self.description = description
        self.attributes = attributes or {}
        self.aliases = aliases or []
        self.mention_count = mention_count
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "attributes": self.attributes,
            "aliases": self.aliases,
            "mention_count": self.mention_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphNode':
        """Create node from dictionary (deserialization)."""
        return cls(
            node_id=data["id"],
            name=data["name"],
            node_type=data["type"],
            description=data["description"],
            attributes=data.get("attributes", {}),
            aliases=data.get("aliases", []),
            mention_count=data.get("mention_count", 1),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def add_alias(self, alias: str):
        """Add an alternative name for this entity."""
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = datetime.now().isoformat()
    
    def increment_mentions(self):
        """Increment the mention count."""
        self.mention_count += 1
        self.updated_at = datetime.now().isoformat()


class GraphEdge:
    """Represents an edge (relationship) in the knowledge graph.
    
    An edge connects two nodes with a typed relationship, includes evidence
    for the relationship, and tracks confidence scores.
    
    Attributes:
        id (str): Unique identifier for the edge.
        from_node_id (str): ID of the source node.
        to_node_id (str): ID of the target node.
        relationship (str): Type of relationship (located_in, owns, etc.).
        evidence (str): Text evidence supporting this relationship.
        confidence (float): Confidence score for this relationship (0.0-1.0).
        created_at (str): ISO timestamp of creation.
        updated_at (str): ISO timestamp of last update.
    """
    
    def __init__(self, edge_id: str, from_node_id: str, to_node_id: str,
                 relationship: str, evidence: str = "", confidence: float = 1.0,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        """Initialize a graph edge."""
        self.id = edge_id
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.relationship = relationship
        self.evidence = evidence
        self.confidence = confidence
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "relationship": self.relationship,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphEdge':
        """Create edge from dictionary (deserialization)."""
        return cls(
            edge_id=data["id"],
            from_node_id=data["from_node_id"],
            to_node_id=data["to_node_id"],
            relationship=data["relationship"],
            evidence=data.get("evidence", ""),
            confidence=data.get("confidence", 1.0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def update_confidence(self, new_confidence: float):
        """Update the confidence score for this relationship."""
        self.confidence = new_confidence
        self.updated_at = datetime.now().isoformat()
    
    def update_evidence(self, new_evidence: str):
        """Update the evidence for this relationship."""
        self.evidence = new_evidence
        self.updated_at = datetime.now().isoformat()