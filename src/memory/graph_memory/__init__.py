"""
Graph Memory Module

Provides knowledge graph functionality for persistent memory with entity resolution
using semantic similarity matching.

Uses LLM-centric extractors as the primary approach.
"""

# Primary LLM-centric classes (renamed from Alt* classes)
from .graph_manager import GraphManager
from .entity_extractor import EntityExtractor
from .relationship_extractor import RelationshipExtractor
from .graph_queries import GraphQueries
from .graph_storage import GraphStorage
from .entity_resolver import EntityResolver

# Legacy classes have been removed - using renamed LLM-centric classes as primary

__all__ = [
    'GraphManager',           # Primary LLM-centric graph manager
    'EntityExtractor',        # Primary LLM-centric entity extractor
    'RelationshipExtractor',  # Primary LLM-centric relationship extractor
    'GraphQueries',
    'GraphStorage',
    'EntityResolver'
]