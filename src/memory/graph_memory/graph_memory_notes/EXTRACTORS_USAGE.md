# Extractors Usage Guide

This document explains how to use the new LLM-centric extractors for A/B testing against the baseline extractors.

## Overview

The extractors implement the approach described in `ENTITY_AND_RELATIONSHIP_EXTRACTION_APPROACH.md`:

- **EntityExtractor**: LLM-centric entity extraction with RAG-based duplicate prevention
- **RelationshipExtractor**: Full conversation relationship extraction with entity context
- **GraphManager**: Orchestrates the approach for complete conversation processing

## Key Differences from Baseline

| Aspect | Baseline Approach | Approach |
|--------|------------------|---------------------|
| **Processing Unit** | Conversation segments | Full conversation + digest |
| **Entity Matching** | Algorithmic (name + embedding similarity) | LLM reasoning with RAG context |
| **Relationship Context** | Segment-based entity pairs | Full conversation with all entities |
| **LLM Reliance** | Extraction only | Extraction + reasoning + matching |
| **Prompt Templates** | Hardcoded prompts | Configurable template files |

## Usage Examples

### Basic Usage

```python
from src.memory.graph_memory import GraphManager

# Initialize graph manager
graph_manager = GraphManager(
    storage_path="graph_data",
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    domain_config=domain_config,
    logger=logger
)

# Process a conversation entry
conversation_text = "Elena, the Mayor of Haven, discovered ancient ruins beneath the town square..."
digest_text = "Elena finds ruins and investigates strange magical phenomena in Haven"

results = graph_manager.process_conversation_entry(conversation_text, digest_text)

print(f"Entities: {len(results['entities'])}")
print(f"New entities: {len(results['new_entities'])}")
print(f"Existing entities: {len(results['existing_entities'])}")
print(f"Relationships: {len(results['relationships'])}")
```

### A/B Testing Setup

```python
from src.memory.graph_memory import GraphManager, GraphManager

# Initialize both managers with same configuration
baseline_manager = GraphManager(
    storage_path="baseline_graph",
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    domain_config=domain_config
)

manager = GraphManager(
    storage_path="graph", 
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    domain_config=domain_config
)

# Test with same input
conversation = "Your test conversation text here..."
digest = "Test digest..."

# Run baseline approach
baseline_segments = create_segments(conversation)  # Your segmentation logic
baseline_entities = baseline_manager.extract_entities_from_segments(baseline_segments)
# ... process baseline results

# Run approach  
results = manager.process_conversation_entry(conversation, digest)

# Compare results
print("Baseline entities:", len(baseline_entities))
print("entities:", len(results['entities']))
```

### Individual Extractor Usage

```python
from src.memory.graph_memory import EntityExtractor, RelationshipExtractor

# Entity extraction only
entity_extractor = EntityExtractor(
    llm_service=llm_service,
    domain_config=domain_config,
    graph_manager=graph_manager,  # For RAG functionality
    logger=logger
)

entities = entity_extractor.extract_entities_from_conversation(
    conversation_text="Elena explored the ancient ruins...",
    digest_text="Elena discovers ruins"
)

# Relationship extraction only
rel_extractor = RelationshipExtractor(
    llm_service=llm_service,
    domain_config=domain_config,
    logger=logger
)

relationships = rel_extractor.extract_relationships_from_conversation(
    conversation_text="Elena explored the ancient ruins in Haven...",
    digest_text="Elena discovers ruins",
    entities=entities
)
```

## Configuration

### Prompt Templates

The extractors use configurable prompt templates:

- **Entity Extraction**: `src/memory/graph_memory/templates/entity_extraction.prompt`
- **Relationship Extraction**: `src/memory/graph_memory/templates/relationship_extraction.prompt`

You can customize these templates to:
- Add domain-specific instructions
- Modify output format requirements
- Include additional context or examples

### Domain Configuration

Same domain configuration as baseline extractors:

```python
domain_config = {
    "domain_name": "dnd_campaign",
    "graph_memory_config": {
        "entity_types": ["character", "location", "object", "concept", "event", "organization"],
        "relationship_types": ["located_in", "owns", "member_of", "allies_with", "enemies_with"]
    }
}
```

## Expected Benefits

1. **Better Entity Matching**: LLM reasoning should better identify when "Elena" and "the Mayor" refer to the same entity
2. **Improved Context Understanding**: Full conversation analysis rather than segment-by-segment processing
3. **Enhanced Relationship Detection**: Relationships identified across the entire conversation context
4. **Reduced False Duplicates**: LLM reasoning combined with RAG should prevent more duplicate entities

## Expected Challenges

1. **Higher LLM Token Usage**: Processing full conversations uses more tokens than segments
2. **Increased Latency**: More LLM calls and longer prompts increase processing time
3. **Prompt Engineering Sensitivity**: Results may be more sensitive to prompt wording
4. **Consistency**: LLM reasoning may be less consistent than algorithmic approaches

## Testing Metrics

When comparing approaches, measure:

### Accuracy Metrics
- **Entity Recall**: Percentage of expected entities found
- **Entity Precision**: Percentage of found entities that are correct
- **Duplicate Rate**: Percentage of duplicate entities created
- **Relationship Accuracy**: Correctness of identified relationships

### Performance Metrics
- **Processing Time**: Total time to process conversation
- **Token Usage**: LLM tokens consumed
- **Memory Usage**: Peak memory consumption
- **Throughput**: Conversations processed per minute

### Quality Metrics
- **Entity Description Quality**: Richness and accuracy of entity descriptions
- **Relationship Evidence**: Quality of evidence supporting relationships
- **Graph Connectivity**: How well entities are connected through relationships

## Troubleshooting

### Debug Logging

Enable debug logging to see detailed processing:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Will show:
# - Candidate entities from Stage 1
# - RAG results from existing entity search  
# - Final entity decisions from Stage 2
# - Relationship extraction results
```

## Future Enhancements

1. **Prompt Optimization**: A/B test different prompt formulations
2. **Hybrid Approach**: Combine best aspects of both approaches
3. **Confidence Calibration**: Tune confidence scores based on testing
4. **Cross-Conversation Entity Linking**: Connect entities across multiple conversations
5. **Performance Optimization**: Cache RAG results, batch processing

This approach provides a foundation for testing whether LLM reasoning can improve entity and relationship extraction quality compared to the current algorithmic approach. 