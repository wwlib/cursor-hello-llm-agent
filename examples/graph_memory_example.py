#!/usr/bin/env python3
"""
Graph Memory Example

Demonstrates the knowledge graph memory system with entity extraction
and RAG-based entity resolution.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.graph_memory import GraphManager, EntityExtractor, RelationshipExtractor, GraphQueries
from examples.domain_configs import DND_CONFIG


def setup_logging():
    """Setup logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def main():
    """Main example function."""
    logger = setup_logging()
    logger.info("Starting Graph Memory Example")
    
    # Setup LLM service
    llm_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "embedding_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        "debug": True,
        "console_output": True
    }
    
    llm_service = OllamaService(llm_config)
    logger.info(f"LLM service initialized with model: {llm_config['model']}")
    
    # Setup embeddings manager
    embeddings_manager = EmbeddingsManager(
        embeddings_file="examples/graph_memory_data/graph_memory_embeddings.jsonl",
        llm_service=llm_service,
        logger=logger
    )
    
    # Setup graph memory components
    storage_path = "examples/graph_memory_data"
    os.makedirs(storage_path, exist_ok=True)
    
    graph_manager = GraphManager(
        storage_path=storage_path,
        embeddings_manager=embeddings_manager,
        similarity_threshold=0.8,
        logger=logger
    )
    
    entity_extractor = EntityExtractor(
        llm_service=llm_service,
        domain_config=DND_CONFIG,
        logger=logger
    )
    
    relationship_extractor = RelationshipExtractor(
        llm_service=llm_service,
        domain_config=DND_CONFIG,
        logger=logger
    )
    
    graph_queries = GraphQueries(graph_manager, logger=logger)
    
    logger.info("Graph memory system initialized")
    
    # Example conversation segments to process
    example_segments = [
        {
            "segment_id": "seg_001",
            "text": "Eldara is a powerful fire wizard who runs the magic shop in Riverwatch. She has a fiery temper and specializes in flame magic.",
            "importance": 5,
            "type": "information",
            "topics": ["Characters", "Magic"]
        },
        {
            "segment_id": "seg_002", 
            "text": "The party visits Eldara's magic shop to buy healing potions and fire resistance scrolls for their upcoming dungeon expedition.",
            "importance": 4,
            "type": "action",
            "topics": ["Objects", "Actions"]
        },
        {
            "segment_id": "seg_003",
            "text": "Captain Sara of the Riverwatch guard warns the party about increased goblin activity near the Whisperwood forest.",
            "importance": 5,
            "type": "information", 
            "topics": ["Characters", "Threats", "Locations"]
        },
        {
            "segment_id": "seg_004",
            "text": "The fire wizard mentioned that the scrolls were created using rare phoenix feathers from the eastern mountains.",
            "importance": 3,
            "type": "information",
            "topics": ["Magic", "Objects", "Locations"]
        }
    ]
    
    logger.info(f"Processing {len(example_segments)} conversation segments")
    
    # Extract entities from segments
    all_entities = entity_extractor.extract_entities_from_segments(example_segments)
    logger.info(f"Extracted {len(all_entities)} entities")
    
    # Add entities to graph (with RAG-based matching)
    added_entities = []
    for entity in all_entities:
        node, is_new = graph_manager.add_or_update_node(
            name=entity['name'],
            node_type=entity['type'],
            description=entity['description'],
            source_segment=entity.get('source_segment', ''),
            segment_importance=entity.get('segment_importance', 0)
        )
        added_entities.append((node, is_new))
        
        if is_new:
            logger.info(f"Created new entity: {entity['name']} ({entity['type']})")
        else:
            logger.info(f"Updated existing entity: {entity['name']} (mentions: {node.mention_count})")
    
    # Group entities by segment for relationship extraction
    entities_by_segment = {}
    for entity in all_entities:
        segment_id = entity.get('source_segment', '')
        if segment_id not in entities_by_segment:
            entities_by_segment[segment_id] = []
        entities_by_segment[segment_id].append(entity)
    
    # Extract relationships
    relationships = relationship_extractor.extract_relationships_from_segments(
        example_segments, entities_by_segment
    )
    logger.info(f"Extracted {len(relationships)} relationships")
    
    # Add relationships to graph
    for rel in relationships:
        # Find entity nodes by name
        from_nodes = graph_manager.find_nodes_by_name(rel['from_entity'])
        to_nodes = graph_manager.find_nodes_by_name(rel['to_entity'])
        
        if from_nodes and to_nodes:
            edge = graph_manager.add_edge(
                from_node_id=from_nodes[0].id,
                to_node_id=to_nodes[0].id,
                relationship=rel['relationship'],
                weight=rel.get('confidence', 1.0),
                source_segment=rel.get('source_segment', ''),
                evidence=rel.get('evidence', '')
            )
            logger.info(f"Added relationship: {rel['from_entity']} --{rel['relationship']}--> {rel['to_entity']}")
    
    # Demonstrate graph queries
    logger.info("\\n" + "="*50)
    logger.info("GRAPH QUERY DEMONSTRATIONS")
    logger.info("="*50)
    
    # 1. Find entity context
    logger.info("\\n1. Finding context for 'Eldara':")
    eldara_context = graph_queries.find_entity_context("Eldara")
    if eldara_context['found']:
        logger.info(f"Context: {eldara_context['context_summary']}")
        logger.info(f"Connections: {eldara_context['total_connections']}")
        for rel_type, rels in eldara_context['relationships'].items():
            logger.info(f"  {rel_type}: {[r['entity']['name'] for r in rels]}")
    
    # 2. Find entities by type
    logger.info("\\n2. Finding all characters:")
    characters = graph_queries.find_entities_by_type("character")
    for char in characters:
        logger.info(f"  {char['name']}: {char['description'][:50]}... (mentions: {char['mention_count']})")
    
    # 3. Query-based context
    logger.info("\\n3. Getting context for query 'What do we know about magic shops?':")
    query_context = graph_queries.get_context_for_query("What do we know about magic shops?")
    logger.info(f"Found {query_context['entities_found']} relevant entities")
    logger.info(f"Context: {query_context['context']}")
    
    # 4. Path between entities
    logger.info("\\n4. Finding path between 'Eldara' and 'Riverwatch':")
    path = graph_queries.find_path_between_entities("Eldara", "Riverwatch")
    if path:
        logger.info(f"Path found: {path['summary']}")
    else:
        logger.info("No path found")
    
    # 5. Graph statistics
    logger.info("\\n5. Graph Statistics:")
    stats = graph_manager.get_graph_stats()
    logger.info(f"Total nodes: {stats['total_nodes']}")
    logger.info(f"Total edges: {stats['total_edges']}")
    logger.info(f"Node types: {stats['node_types']}")
    logger.info(f"Relationship types: {stats['relationship_types']}")
    
    logger.info("\\nGraph Memory Example completed successfully!")


if __name__ == "__main__":
    main()