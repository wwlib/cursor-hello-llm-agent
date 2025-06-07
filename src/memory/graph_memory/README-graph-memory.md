# Graph Memory System Documentation

The Graph Memory System provides structured knowledge representation for LLM-driven agents, automatically extracting entities and relationships from conversations to build comprehensive knowledge graphs that enhance agent reasoning and context retrieval.

## Overview

The graph memory system complements the existing RAG-based memory with structured, relationship-aware knowledge representation. It automatically processes conversation segments to extract domain-specific entities and their relationships, creating a knowledge graph that provides rich context for agent responses.

### Key Features

- **Automatic Entity Extraction**: LLM-driven identification of domain-specific entities (characters, locations, objects, events, concepts, organizations)
- **Relationship Detection**: Automatic discovery of relationships between entities (spatial, ownership, social, causal, temporal)
- **Semantic Entity Matching**: RAG-based similarity matching prevents duplicate entities using configurable thresholds
- **Domain Adaptation**: Configurable entity types and relationship types for different domains (D&D, software projects, lab work)
- **Graph-Enhanced Context**: Structured entity context automatically enhances LLM prompts alongside RAG results
- **JSON Persistence**: Memory-efficient storage with incremental updates and backup capabilities

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Entity         │    │  Relationship   │    │  Graph          │
│  Extractor      │    │  Extractor      │    │  Queries        │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Graph Manager        │
                    │  (Main Orchestrator)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Graph Storage        │
                    │  (JSON Persistence)     │
                    └─────────────────────────┘
```

## Core Components

### 1. GraphManager (`graph_manager.py`)
The main orchestrator that coordinates all graph memory operations:

```python
from src.memory.graph_memory import GraphManager

# Initialize with LLM service and embeddings manager
graph_manager = GraphManager(
    llm_service=llm_service,
    embeddings_manager=embeddings_manager,
    storage_path="graph_data",
    domain_config=domain_config
)

# Extract entities from conversation segments
entities = graph_manager.extract_entities_from_segments(segments)

# Add entities with automatic similarity matching
for entity in entities:
    graph_manager.add_or_update_node(
        name=entity["name"],
        node_type=entity["type"],
        description=entity["description"]
    )

# Extract and add relationships
relationships = graph_manager.extract_relationships_from_segments(segments)
for rel in relationships:
    graph_manager.add_edge(
        from_node=rel["from_entity"],
        to_node=rel["to_entity"],
        relationship_type=rel["relationship"]
    )

# Query for context
context = graph_manager.query_for_context("Tell me about the wizard")
```

### 2. EntityExtractor (`entity_extractor.py`)
LLM-driven entity identification with domain-specific configuration:

```python
from src.memory.graph_memory.entity_extractor import EntityExtractor

extractor = EntityExtractor(llm_service, domain_config)

# Extract entities from text segments
segments = [{"text": "Eldara the fire wizard runs a magic shop in Riverwatch"}]
entities = extractor.extract_entities(segments)

# Result:
# [
#   {
#     "name": "Eldara",
#     "type": "character",
#     "description": "A fire wizard who runs a magic shop",
#     "attributes": {"profession": "wizard", "magic_type": "fire"}
#   },
#   {
#     "name": "Riverwatch", 
#     "type": "location",
#     "description": "A settlement where Eldara's magic shop is located"
#   }
# ]
```

### 3. RelationshipExtractor (`relationship_extractor.py`)
Automatic relationship detection between entities:

```python
from src.memory.graph_memory.relationship_extractor import RelationshipExtractor

extractor = RelationshipExtractor(llm_service, domain_config)

# Extract relationships from segments with entities
segments = [{
    "text": "Eldara runs her magic shop in the eastern settlement of Riverwatch",
    "entities": [
        {"name": "Eldara", "type": "character"},
        {"name": "Riverwatch", "type": "location"}
    ]
}]

relationships = extractor.extract_relationships(segments)

# Result:
# [
#   {
#     "from_entity": "Eldara",
#     "to_entity": "Riverwatch",
#     "relationship": "located_in",
#     "confidence": 0.9,
#     "evidence": "Eldara runs her magic shop in the eastern settlement of Riverwatch"
#   }
# ]
```

### 4. GraphQueries (`graph_queries.py`)
Rich query interface for context retrieval and graph navigation:

```python
from src.memory.graph_memory.graph_queries import GraphQueries

queries = GraphQueries(storage)

# Find entity context with relationships
context = queries.get_entity_context("Eldara", max_depth=2)

# Find path between entities
path = queries.find_path("Eldara", "Riverwatch")

# Query-based context retrieval
results = queries.query_for_context("magic shops", max_results=5)

# Search entities by type
characters = queries.get_entities_by_type("character")
```

### 5. GraphStorage (`graph_storage.py`)
JSON-based persistence with backup capabilities:

```python
from src.memory.graph_memory.graph_storage import GraphStorage

storage = GraphStorage("graph_data_directory")

# Storage automatically manages:
# - graph_nodes.json: Entity storage with attributes
# - graph_edges.json: Relationship storage with evidence  
# - graph_metadata.json: Graph statistics and configuration
# - Automatic backups with timestamps
```

## Usage Patterns

### Standalone Usage

The graph memory system can be used independently for structured knowledge extraction:

```python
import asyncio
from src.ai.llm_ollama import OllamaService
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.graph_memory import GraphManager

# Initialize services
llm_service = OllamaService({
    "base_url": "http://localhost:11434",
    "model": "gemma3"
})

embeddings_manager = EmbeddingsManager(
    "graph_embeddings.jsonl", 
    llm_service
)

# Configure for D&D domain
domain_config = {
    "graph_memory_config": {
        "entity_types": ["character", "location", "object", "event"],
        "relationship_types": ["located_in", "owns", "allies_with"],
        "similarity_threshold": 0.8
    }
}

# Create graph manager
graph_manager = GraphManager(
    llm_service=llm_service,
    embeddings_manager=embeddings_manager,
    storage_path="dnd_graph_data",
    domain_config=domain_config
)

# Process conversation segments
segments = [
    {"text": "The party meets Eldara, a fire wizard in Riverwatch"},
    {"text": "Eldara owns a magic shop filled with scrolls and potions"},
    {"text": "Riverwatch is the eastern settlement in the Lost Valley"}
]

# Extract and store entities and relationships
entities = graph_manager.extract_entities_from_segments(segments)
for entity in entities:
    graph_manager.add_or_update_node(
        name=entity["name"],
        node_type=entity["type"], 
        description=entity["description"],
        attributes=entity.get("attributes", {})
    )

relationships = graph_manager.extract_relationships_from_segments(segments)
for rel in relationships:
    graph_manager.add_edge(
        from_node=rel["from_entity"],
        to_node=rel["to_entity"],
        relationship_type=rel["relationship"],
        evidence=rel.get("evidence", ""),
        confidence=rel.get("confidence", 0.5)
    )

# Query the graph
context = graph_manager.query_for_context("Tell me about magic shops")
print(f"Found {len(context)} relevant entities")
```

### Integrated with MemoryManager

The graph memory system is automatically integrated with the main MemoryManager:

```python
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

# Graph memory is enabled by default
memory_manager = MemoryManager(
    memory_guid="campaign-guid",
    memory_file="campaign_memory.json",
    domain_config=domain_config,
    llm_service=llm_service,
    enable_graph_memory=True  # Default: True
)

# Graph updates happen automatically during conversation processing
response = memory_manager.query_memory({
    "query": "What do I know about Eldara?"
})

# Response automatically includes both RAG and graph context
# Graph context appears in the LLM prompt as structured entity information
```

### Domain Configuration

Configure the graph memory system for different domains:

```python
# D&D Campaign Configuration
DND_CONFIG = {
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["character", "location", "object", "event", "concept", "organization"],
        "relationship_types": [
            "located_in", "owns", "member_of", "allies_with", "enemies_with",
            "uses", "created_by", "leads_to", "participates_in", "related_to"
        ],
        "entity_extraction_prompt": "Extract entities from this D&D campaign text. Focus on characters, locations, objects, events, concepts, and organizations.",
        "relationship_extraction_prompt": "Identify relationships between entities. Look for spatial relationships (located_in), ownership (owns), and social relationships (allies_with, enemies_with).",
        "similarity_threshold": 0.8
    }
}

# Software Project Configuration  
SOFTWARE_CONFIG = {
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["feature", "stakeholder", "requirement", "technology", "component"],
        "relationship_types": [
            "depends_on", "implements", "used_by", "part_of", "manages",
            "requires", "interacts_with", "supports", "validates"
        ],
        "entity_extraction_prompt": "Extract entities from this software requirements text. Focus on features, stakeholders, requirements, technologies, and components.",
        "relationship_extraction_prompt": "Identify relationships between entities. Look for dependencies (depends_on), implementations (implements), and hierarchical relationships (part_of).",
        "similarity_threshold": 0.8
    }
}

# Laboratory Configuration
LAB_CONFIG = {
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["equipment", "material", "procedure", "result", "project", "person"],
        "relationship_types": [
            "uses", "produces", "requires", "part_of", "leads_to",
            "tested_with", "works_with", "owned_by", "located_in"
        ],
        "entity_extraction_prompt": "Extract entities from this laboratory text. Focus on equipment, materials, procedures, results, projects, and people.",
        "relationship_extraction_prompt": "Identify relationships between entities. Look for usage patterns (uses), production relationships (produces), and experimental connections.",
        "similarity_threshold": 0.8
    }
}
```

## Storage Structure

The graph memory system creates the following file structure:

```
storage_path/
├── graph_nodes.json              # Entity storage
│   └── {
│         "node_id": {
│           "id": "character_eldara_001",
│           "name": "Eldara", 
│           "type": "character",
│           "description": "A fire wizard who runs a magic shop",
│           "attributes": {"profession": "wizard", "magic_type": "fire"},
│           "embedding": [0.1, 0.2, ...],
│           "aliases": ["the wizard", "fire mage"],
│           "mention_count": 3,
│           "created_at": "2024-01-01T10:00:00",
│           "updated_at": "2024-01-01T12:00:00"
│         }
│       }
├── graph_edges.json              # Relationship storage
│   └── {
│         "edge_id": {
│           "id": "edge_001",
│           "from_node": "character_eldara_001",
│           "to_node": "location_riverwatch_001", 
│           "relationship_type": "located_in",
│           "evidence": "Eldara runs her shop in Riverwatch",
│           "confidence": 0.9,
│           "created_at": "2024-01-01T10:00:00"
│         }
│       }
├── graph_metadata.json           # Graph statistics
│   └── {
│         "total_nodes": 15,
│         "total_edges": 8,
│         "entity_type_counts": {"character": 5, "location": 3},
│         "relationship_type_counts": {"located_in": 3, "owns": 2},
│         "last_updated": "2024-01-01T12:00:00"
│       }
└── graph_memory_embeddings.jsonl # Entity embeddings (JSONL format)
    └── {"text": "Eldara: A fire wizard...", "embedding": [...], "metadata": {...}}
```

## Advanced Features

### Semantic Entity Matching

The system uses RAG-based similarity matching to prevent duplicate entities:

```python
# When adding a new entity, the system:
# 1. Generates an embedding for the entity description
# 2. Searches existing entities for similar embeddings
# 3. If similarity > threshold (default: 0.8), merges with existing entity
# 4. Otherwise, creates a new entity

# Configure similarity threshold
domain_config["graph_memory_config"]["similarity_threshold"] = 0.85  # More strict
domain_config["graph_memory_config"]["similarity_threshold"] = 0.7   # More permissive
```

### Graph Context Enhancement

Graph context is automatically added to LLM prompts in the MemoryManager:

```
GRAPH_CONTEXT (Structured relationships and entities):

Relevant entities and relationships:
• Eldara (character): A fire wizard who runs a magic shop in Riverwatch
  - located_in Riverwatch
  - owns Magic Shop
  - uses Fire Magic

• Riverwatch (location): Eastern settlement in the Lost Valley  
  - part_of Lost Valley
  - contains Magic Shop
```

### Async Processing Integration

When integrated with MemoryManager, graph updates happen asynchronously:

```python
# In AsyncMemoryManager, graph updates are tracked as pending operations
async def _update_graph_memory_async(self, entry):
    """Update graph memory with entities and relationships from a conversation entry."""
    # 1. Extract important segments (importance ≥ 3, memory_worthy=True)
    # 2. Extract entities from segments using domain-specific prompts
    # 3. Add/update entities with semantic similarity matching
    # 4. Extract relationships between entities in same segments
    # 5. Add relationships to graph with evidence and confidence scores

# Check for pending graph operations
if memory_manager.has_pending_operations():
    await memory_manager.wait_for_pending_operations()
```

### Query Interface

Rich query capabilities for different use cases:

```python
# Entity context with relationship traversal
context = graph_queries.get_entity_context("Eldara", max_depth=2)
# Returns: Entity info + all directly connected entities + their connections

# Path finding between entities  
path = graph_queries.find_path("Player", "Ancient Artifact")
# Returns: Shortest path through relationships with natural language summary

# Query-based context retrieval
results = graph_queries.query_for_context("magic items", max_results=5)
# Returns: Entities and relationships relevant to the query

# Type-based filtering
all_characters = graph_queries.get_entities_by_type("character")
all_locations = graph_queries.get_entities_by_type("location")

# Relationship analysis
incoming_rels = graph_queries.get_incoming_relationships("Riverwatch")
outgoing_rels = graph_queries.get_outgoing_relationships("Eldara")
```

## Performance Considerations

### Memory Efficiency
- **Filtered Processing**: Only processes important segments (importance ≥ 3, memory_worthy=True)
- **Incremental Updates**: JSON files are updated incrementally, not rewritten entirely
- **JSONL Embeddings**: Embeddings stored in append-only JSONL format for efficiency
- **Lazy Loading**: Graph data loaded on-demand, not kept in memory permanently

### Semantic Matching Optimization
- **Embedding Caching**: Entity embeddings cached and reused for similarity matching
- **Configurable Thresholds**: Similarity thresholds tunable per domain
- **Batch Processing**: Multiple entities processed together for efficiency

### Async Processing
- **Non-blocking**: Graph updates happen in background without blocking user interactions
- **Error Isolation**: Graph processing errors don't affect main conversation flow
- **Graceful Degradation**: System continues working even if graph operations fail

## Error Handling

The graph memory system includes robust error handling:

```python
# GraphManager handles common error scenarios:

try:
    entities = graph_manager.extract_entities_from_segments(segments)
except LLMServiceError:
    # LLM service unavailable - skip graph update, log warning
    logger.warning("LLM service unavailable, skipping entity extraction")
    return []

try:
    graph_manager.add_or_update_node(name, node_type, description)
except StorageError:
    # Storage issue - attempt backup recovery
    logger.error("Storage error, attempting backup recovery")
    storage.restore_from_backup()

try:
    context = graph_manager.query_for_context(query)
except Exception as e:
    # Any query error - return empty context, don't break main flow
    logger.warning(f"Graph query failed: {e}")
    return ""
```

### Common Error Scenarios

1. **LLM Service Unavailable**: Graph updates are skipped, system continues without graph context
2. **Storage Permission Issues**: Automatic backup/recovery attempts, fallback to read-only mode
3. **Malformed Entity Data**: Individual entities skipped, processing continues with remaining entities
4. **Similarity Matching Errors**: Falls back to creating new entities without deduplication
5. **Query Processing Failures**: Returns empty context, doesn't affect main conversation flow

## Testing

Comprehensive test suite covers all major functionality:

```bash
# Run graph memory tests
pytest tests/memory_manager/test_graph_memory.py -v

# Run integration tests  
pytest tests/memory_manager/test_graph_memory_integration.py -v

# Test with real LLM (requires Ollama)
pytest tests/memory_manager/test_graph_memory.py -v -m integration
```

### Test Coverage

- **Unit Tests**: Individual component testing with mock LLM services
- **Integration Tests**: End-to-end testing with real LLM services
- **Entity Extraction Tests**: Validates domain-specific entity identification
- **Relationship Detection Tests**: Validates relationship extraction accuracy
- **Similarity Matching Tests**: Validates entity deduplication logic
- **Storage Tests**: Validates JSON persistence and backup/recovery
- **Query Tests**: Validates all query interface methods
- **Error Handling Tests**: Validates graceful degradation scenarios

## Examples

### Complete Example: D&D Campaign

```python
#!/usr/bin/env python3

import asyncio
from src.ai.llm_ollama import OllamaService
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.graph_memory import GraphManager
from examples.domain_configs import DND_CONFIG

async def main():
    # Initialize services
    llm_service = OllamaService({
        "base_url": "http://localhost:11434",
        "model": "gemma3"
    })
    
    embeddings_manager = EmbeddingsManager(
        "dnd_graph_embeddings.jsonl",
        llm_service
    )
    
    # Create graph manager
    graph_manager = GraphManager(
        llm_service=llm_service,
        embeddings_manager=embeddings_manager,
        storage_path="dnd_campaign_graph",
        domain_config=DND_CONFIG
    )
    
    # Sample campaign conversation
    segments = [
        {"text": "The party arrives in Riverwatch, the eastern settlement of the Lost Valley"},
        {"text": "Eldara the fire wizard greets them at her magic shop"},
        {"text": "She offers to sell them healing potions and fire resistance scrolls"},
        {"text": "The ancient ruins north of town are said to contain powerful artifacts"}
    ]
    
    print("Processing campaign segments...")
    
    # Extract entities
    entities = graph_manager.extract_entities_from_segments(segments)
    print(f"Extracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity['name']} ({entity['type']}): {entity['description']}")
        
        # Add to graph
        graph_manager.add_or_update_node(
            name=entity["name"],
            node_type=entity["type"],
            description=entity["description"],
            attributes=entity.get("attributes", {})
        )
    
    # Extract relationships
    relationships = graph_manager.extract_relationships_from_segments(segments)
    print(f"\nExtracted {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel['from_entity']} {rel['relationship']} {rel['to_entity']}")
        
        # Add to graph
        graph_manager.add_edge(
            from_node=rel["from_entity"],
            to_node=rel["to_entity"],
            relationship_type=rel["relationship"],
            evidence=rel.get("evidence", ""),
            confidence=rel.get("confidence", 0.5)
        )
    
    # Query for context
    print("\nQuerying graph for context...")
    
    # Query about characters
    context = graph_manager.query_for_context("Tell me about the wizard")
    print(f"Wizard context: {len(context)} results")
    for result in context:
        print(f"  - {result['name']}: {result['description']}")
    
    # Query about locations
    context = graph_manager.query_for_context("What locations are available?")
    print(f"Location context: {len(context)} results")
    for result in context:
        print(f"  - {result['name']}: {result['description']}")
    
    print("\nGraph memory processing complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

### Integration Example: Enhanced Memory Manager

```python
from src.memory.memory_manager import AsyncMemoryManager
from src.ai.llm_ollama import OllamaService
from examples.domain_configs import DND_CONFIG

# Create enhanced memory manager with graph memory
memory_manager = AsyncMemoryManager(
    memory_guid="enhanced-campaign",
    memory_file="enhanced_campaign.json", 
    domain_config=DND_CONFIG,
    llm_service=llm_service,
    enable_graph_memory=True
)

# Initialize with campaign data
memory_manager.create_initial_memory("""
Campaign: The Lost Valley Adventure

The party has been hired to investigate strange occurrences in the Lost Valley,
a hidden region surrounded by impassable mountains. The main settlements are:
- Haven: Central hub and starting point
- Riverwatch: Eastern settlement with trading post
- Mountainkeep: Western fortress guarding the passes

Key NPCs:
- Eldara: Fire wizard who runs Riverwatch's magic shop
- Captain Sara: Leader of Riverwatch's guard
- Elder Theron: Scholar studying the ancient ruins
""")

# Have a conversation - graph memory updates automatically
async def conversation_example():
    # User input
    await memory_manager.add_conversation_entry({
        "role": "user",
        "content": "I want to visit Eldara's magic shop in Riverwatch"
    })
    
    # Query memory - gets both RAG and graph context
    response = memory_manager.query_memory({
        "query": "What can I find at Eldara's shop?"
    })
    
    # Agent response
    await memory_manager.add_conversation_entry({
        "role": "agent", 
        "content": response["response"]
    })
    
    # Wait for all async processing (including graph updates)
    await memory_manager.wait_for_pending_operations()
    
    # Check graph context
    graph_context = memory_manager.get_graph_context("magic shops")
    print("Graph context:", graph_context)

# Run the conversation
asyncio.run(conversation_example())
```

## Future Enhancements

The graph memory system provides a foundation for advanced features:

### Planned Features
- **Multi-hop Graph Queries**: Chain multiple relationship traversals for complex reasoning
- **Temporal Graph Analysis**: Track how entities and relationships evolve over time
- **Graph Visualization**: Visual representation of knowledge graphs for debugging and analysis
- **Advanced Entity Resolution**: More sophisticated matching using multiple similarity metrics
- **Graph-based Reasoning**: Use graph structure for logical inference and consistency checking

### Extension Points
- **Custom Entity Types**: Add domain-specific entity types beyond the standard set
- **Custom Relationship Types**: Define specialized relationships for unique domains
- **Custom Query Patterns**: Implement domain-specific graph query patterns
- **External Graph Databases**: Integrate with Neo4j, Amazon Neptune, or other graph databases
- **Graph Analytics**: Compute centrality, clustering, and other graph metrics

## Conclusion

The Graph Memory System provides a powerful complement to RAG-based memory, offering structured knowledge representation that enhances agent reasoning capabilities. Its modular design allows for both standalone usage and seamless integration with the existing memory management system, while domain-specific configuration enables adaptation to diverse use cases.

The system's automatic processing pipeline ensures that knowledge graphs are built transparently during normal agent interactions, requiring no additional user effort while providing significant improvements in context quality and reasoning capabilities.