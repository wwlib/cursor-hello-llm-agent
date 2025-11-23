#!/usr/bin/env python3
"""
Graph Memory Example

Demonstrates the knowledge graph memory system with entity extraction
and RAG-based entity resolution.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.logging_config import LoggingConfig
from src.ai.llm_ollama import OllamaService
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.graph_memory import GraphManager, EntityExtractor, RelationshipExtractor
from examples.domain_configs import DND_CONFIG

# Use a fixed example GUID for this standalone example
EXAMPLE_GUID = "graph_memory_example"

# Configuration - use environment variables with sensible defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")


def find_nodes_by_name(graph_manager, name, exact_match=True):
    """Helper function to find nodes by name (workaround for missing GraphManager method)."""
    matches = []
    name_lower = name.lower()
    
    for node in graph_manager.nodes.values():
        if exact_match:
            if node.name.lower() == name_lower:
                matches.append(node)
        else:
            # Fuzzy match - check name and aliases
            if (name_lower in node.name.lower() or 
                any(name_lower in alias.lower() for alias in node.aliases)):
                matches.append(node)
    
    return matches


def get_connected_nodes(graph_manager, node_id):
    """Helper function to get connected nodes (workaround for missing GraphManager method)."""
    connected = []
    for edge in graph_manager.edges:
        if edge.from_node_id == node_id:
            node = graph_manager.get_node(edge.to_node_id)
            if node:
                connected.append((node, edge))
        elif edge.to_node_id == node_id:
            node = graph_manager.get_node(edge.from_node_id)
            if node:
                connected.append((node, edge))
    return connected


def find_entity_context(graph_manager, entity_name, max_depth=2, max_results=10):
    """Find comprehensive context about an entity."""
    entities = find_nodes_by_name(graph_manager, entity_name, exact_match=False)
    if not entities:
        return {'found': False, 'message': f'Entity "{entity_name}" not found'}
    
    entity = entities[0]
    
    # BFS to find connected entities
    from collections import deque, defaultdict
    queue = deque([(entity.id, 0)])
    visited = {entity.id}
    connected = []
    
    while queue and len(connected) < max_results:
        current_id, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        for connected_node, edge in get_connected_nodes(graph_manager, current_id):
            if connected_node.id not in visited:
                visited.add(connected_node.id)
                connected.append((connected_node, edge, depth + 1))
                queue.append((connected_node.id, depth + 1))
    
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
            'weight': edge.confidence,
            'depth': depth
        })
    
    return {
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
        'context_summary': f"{entity.description}. Connected to {len(connected)} related entities."
    }


def find_entities_by_type(graph_manager, entity_type, limit=20):
    """Find all entities of a specific type."""
    results = []
    type_lower = entity_type.lower()
    
    for node in graph_manager.nodes.values():
        if node.type.lower() == type_lower:
            results.append({
                'name': node.name,
                'type': node.type,
                'description': node.description,
                'mention_count': node.mention_count
            })
            if len(results) >= limit:
                break
    
    return results


def get_context_for_query(graph_manager, query, max_results=5):
    """Get context for a query using semantic search."""
    if not graph_manager.embeddings_manager:
        return {'entities_found': 0, 'context': 'No embeddings manager available'}
    
    try:
        search_results = graph_manager.embeddings_manager.search(query, k=max_results * 2)
        
        # Filter for graph entities
        graph_results = []
        for result in search_results:
            metadata = result.get('metadata', {})
            if metadata.get('source') == 'graph_entity':
                entity_id = metadata.get('entity_id')
                node = graph_manager.get_node(entity_id) if entity_id else None
                if node:
                    graph_results.append(node)
                    if len(graph_results) >= max_results:
                        break
        
        if not graph_results:
            return {'entities_found': 0, 'context': 'No relevant entities found'}
        
        context_parts = [f"{node.name} ({node.type}): {node.description}" for node in graph_results]
        context = ". ".join(context_parts)
        
        return {
            'entities_found': len(graph_results),
            'context': context
        }
    except Exception as e:
        return {'entities_found': 0, 'context': f'Error: {str(e)}'}


def find_path_between_entities(graph_manager, from_entity, to_entity, max_depth=4):
    """Find path between two entities."""
    from collections import deque
    
    from_nodes = find_nodes_by_name(graph_manager, from_entity, exact_match=False)
    to_nodes = find_nodes_by_name(graph_manager, to_entity, exact_match=False)
    
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
            # Build path response
            path_nodes = [graph_manager.get_node(nid) for nid in path]
            path_summary = " -> ".join([node.name for node in path_nodes if node])
            return {'summary': path_summary, 'path': path}
        
        if current_id in visited or len(path) >= max_depth:
            continue
        
        visited.add(current_id)
        
        # Explore connected nodes
        for connected_node, edge in get_connected_nodes(graph_manager, current_id):
            if connected_node.id not in visited:
                new_path = path + [connected_node.id]
                queue.append((connected_node.id, new_path))
    
    return None

def get_graph_stats(graph_manager):
    """Get graph statistics (workaround for missing GraphManager method)."""
    from collections import Counter
    
    node_types = Counter()
    relationship_types = Counter()
    
    for node in graph_manager.nodes.values():
        node_types[node.type] += 1
    
    for edge in graph_manager.edges:
        relationship_types[edge.relationship] += 1
    
    return {
        'total_nodes': len(graph_manager.nodes),
        'total_edges': len(graph_manager.edges),
        'node_types': dict(node_types),
        'relationship_types': dict(relationship_types)
    }

def main():
    """Main example function."""
    print("Graph Memory Example - Knowledge Graph with Entity Extraction")
    print(f"Using Ollama at {OLLAMA_BASE_URL}")
    print(f"Model: {OLLAMA_MODEL}, Embedding Model: {OLLAMA_EMBED_MODEL}\n")
    
    # Set up logging using LoggingConfig
    logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "graph_memory_example",
        log_to_console=False
    )
    llm_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_graph",
        log_to_console=False
    )
    embeddings_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_embeddings",
        log_to_console=False
    )
    
    logger.info("Starting Graph Memory Example")
    
    # Setup LLM service for entity/relationship extraction
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0,  # Lower temperature for more consistent extraction
        "stream": False,
        "logger": llm_logger
    })
    logger.info(f"LLM service initialized with model: {OLLAMA_MODEL}")
    
    # Setup embeddings LLM service
    embeddings_llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "logger": embeddings_logger
    })
    
    # Setup embeddings manager
    storage_path = "examples/graph_memory_data"
    os.makedirs(storage_path, exist_ok=True)
    
    embeddings_file = os.path.join(storage_path, "graph_memory_embeddings.jsonl")
    embeddings_manager = EmbeddingsManager(
        embeddings_file=embeddings_file,
        llm_service=embeddings_llm_service,
        logger=embeddings_logger
    )
    logger.info("Embeddings manager initialized")
    
    # Setup graph manager
    graph_manager = GraphManager(
        storage_path=storage_path,
        embeddings_manager=embeddings_manager,
        similarity_threshold=0.8,
        logger=logger,
        llm_service=llm_service,
        embeddings_llm_service=embeddings_llm_service,
        domain_config=DND_CONFIG,
        memory_guid=EXAMPLE_GUID
    )
    logger.info("Graph manager initialized")
    
    # Setup entity extractor (GraphManager creates its own, but we can also create standalone)
    entity_extractor = EntityExtractor(
        llm_service=llm_service,
        domain_config=DND_CONFIG,
        graph_manager=graph_manager,  # Pass graph_manager for RAG-based matching
        logger=logger
    )
    
    # Setup relationship extractor
    relationship_extractor = RelationshipExtractor(
        llm_service=llm_service,
        domain_config=DND_CONFIG,
        logger=logger
    )
    
    logger.info("Graph memory system initialized")
    print("Graph memory system initialized\n")
    
    # Example conversation segments to process
    # Note: We'll combine these into conversation text for extraction
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
    print(f"Processing {len(example_segments)} conversation segments...\n")
    
    # Combine segments into conversation text for extraction
    conversation_text = "\n\n".join([seg["text"] for seg in example_segments])
    digest_text = "\n".join([
        f"Segment {seg['segment_id']}: {seg['text']} (Importance: {seg['importance']}, Type: {seg['type']})"
        for seg in example_segments
    ])
    
    # Extract entities from conversation
    print("Extracting entities...")
    all_entities = entity_extractor.extract_entities_from_conversation(
        conversation_text=conversation_text,
        digest_text=digest_text
    )
    logger.info(f"Extracted {len(all_entities)} entities")
    print(f"Extracted {len(all_entities)} entities\n")
    
    # Add entities to graph (with RAG-based matching)
    print("Adding entities to graph...")
    added_entities = []
    entity_name_to_node_id = {}  # Map entity names to node IDs
    
    for entity in all_entities:
        node, is_new = graph_manager.add_or_update_node(
            name=entity['name'],
            node_type=entity['type'],
            description=entity['description'],
            source_segment=entity.get('source_segment', ''),
            segment_importance=entity.get('segment_importance', 0)
        )
        added_entities.append((node, is_new))
        # Map entity name to node ID for relationship extraction
        entity_name_to_node_id[entity['name']] = node.id
        
        if is_new:
            logger.info(f"Created new entity: {entity['name']} ({entity['type']})")
            print(f"  ✓ Created new entity: {entity['name']} ({entity['type']})")
        else:
            logger.info(f"Updated existing entity: {entity['name']} (mentions: {node.mention_count})")
            print(f"  ↻ Updated existing entity: {entity['name']} (mentions: {node.mention_count})")
    
    # Prepare entities with resolved_node_id for relationship extraction
    entities_with_ids = []
    for entity in all_entities:
        entity_with_id = entity.copy()
        entity_with_id['resolved_node_id'] = entity_name_to_node_id.get(entity['name'], '')
        entity_with_id['status'] = 'resolved'
        entities_with_ids.append(entity_with_id)
    
    # Extract relationships from conversation
    print("\nExtracting relationships...")
    relationships = relationship_extractor.extract_relationships_from_conversation(
        conversation_text=conversation_text,
        digest_text=digest_text,
        entities=entities_with_ids  # Pass entities with node IDs!
    )
    logger.info(f"Extracted {len(relationships)} relationships")
    print(f"Extracted {len(relationships)} relationships\n")
    
    # Add relationships to graph
    print("Adding relationships to graph...")
    for rel in relationships:
        # Relationships now use node IDs directly
        from_entity_id = rel.get('from_entity_id', '').strip()
        to_entity_id = rel.get('to_entity_id', '').strip()
        
        if from_entity_id and to_entity_id:
            edge = graph_manager.add_edge(
                from_node_id=from_entity_id,
                to_node_id=to_entity_id,
                relationship=rel['relationship'],
                confidence=rel.get('confidence', 1.0)
            )
            if edge:
                # Get entity names for display
                from_node = graph_manager.get_node(from_entity_id)
                to_node = graph_manager.get_node(to_entity_id)
                from_name = from_node.name if from_node else from_entity_id
                to_name = to_node.name if to_node else to_entity_id
                logger.info(f"Added relationship: {from_name} --{rel['relationship']}--> {to_name}")
                print(f"  ✓ {from_name} --{rel['relationship']}--> {to_name}")
            else:
                logger.warning(f"Failed to add relationship: {from_entity_id} --{rel['relationship']}--> {to_entity_id}")
                print(f"  ✗ Failed to add relationship")
        else:
            logger.warning(f"Invalid relationship - missing entity IDs: from={from_entity_id}, to={to_entity_id}")
            print(f"  ✗ Invalid relationship (missing entity IDs)")
    
    # Demonstrate graph queries using helper functions
    print("\n" + "="*80)
    print("GRAPH QUERY DEMONSTRATIONS")
    print("="*80)
    
    # 1. Find entity context
    print("\n1. Finding context for 'Eldara':")
    eldara_context = find_entity_context(graph_manager, "Eldara")
    if eldara_context['found']:
        print(f"   Context: {eldara_context['context_summary']}")
        print(f"   Connections: {eldara_context['total_connections']}")
        for rel_type, rels in eldara_context['relationships'].items():
            entity_names = [r['entity']['name'] for r in rels]
            print(f"   {rel_type}: {', '.join(entity_names)}")
    else:
        print("   Entity not found in graph")
    
    # 2. Find entities by type
    print("\n2. Finding all characters:")
    characters = find_entities_by_type(graph_manager, "character")
    if characters:
        for char in characters:
            desc = char['description'][:50] + "..." if len(char['description']) > 50 else char['description']
            print(f"   {char['name']}: {desc} (mentions: {char['mention_count']})")
    else:
        print("   No characters found")
    
    # 3. Query-based context
    print("\n3. Getting context for query 'What do we know about magic shops?':")
    query_context = get_context_for_query(graph_manager, "What do we know about magic shops?")
    print(f"   Found {query_context['entities_found']} relevant entities")
    if query_context['context']:
        print(f"   Context: {query_context['context'][:200]}...")
    
    # 4. Path between entities
    print("\n4. Finding path between 'Eldara' and 'Riverwatch':")
    path = find_path_between_entities(graph_manager, "Eldara", "Riverwatch")
    if path:
        print(f"   Path found: {path['summary']}")
    else:
        print("   No path found")
    
    # 5. Graph statistics
    print("\n5. Graph Statistics:")
    stats = get_graph_stats(graph_manager)
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"   Node types: {stats.get('node_types', {})}")
    print(f"   Relationship types: {stats.get('relationship_types', {})}")
    
    print("\n" + "="*80)
    print("Graph Memory Example completed successfully!")
    print(f"Logs saved to: {LoggingConfig.get_log_base_dir(EXAMPLE_GUID)}")
    print(f"Graph data saved to: {storage_path}")


if __name__ == "__main__":
    main()