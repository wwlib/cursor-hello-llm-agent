# Alternative Extractors Usage Guide

This document explains how to use the new alternative LLM-centric extractors for A/B testing against the baseline extractors.

## Overview

The alternative extractors implement the approach described in `ALT_ENTITY_AND_RELATIONSHIP_EXTRACTION_APPROACH.md`:

- **AltEntityExtractor**: LLM-centric entity extraction with RAG-based duplicate prevention
- **AltRelationshipExtractor**: Full conversation relationship extraction with entity context
- **AltGraphManager**: Orchestrates the alternative approach for complete conversation processing

## Key Differences from Baseline

| Aspect | Baseline Approach | Alternative Approach |
|--------|------------------|---------------------|
| **Processing Unit** | Conversation segments | Full conversation + digest |
| **Entity Matching** | Algorithmic (name + embedding similarity) | LLM reasoning with RAG context |
| **Relationship Context** | Segment-based entity pairs | Full conversation with all entities |
| **LLM Reliance** | Extraction only | Extraction + reasoning + matching |
| **Prompt Templates** | Hardcoded prompts | Configurable template files |

## Usage Examples

### Basic Usage

```python
from src.memory.graph_memory import AltGraphManager

# Initialize alternative graph manager
alt_graph_manager = AltGraphManager(
    storage_path="alt_graph_data",
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    domain_config=domain_config,
    logger=logger
)

# Process a conversation entry
conversation_text = "Elena, the Mayor of Haven, discovered ancient ruins beneath the town square..."
digest_text = "Elena finds ruins and investigates strange magical phenomena in Haven"

results = alt_graph_manager.process_conversation_entry(conversation_text, digest_text)

print(f"Entities: {len(results['entities'])}")
print(f"New entities: {len(results['new_entities'])}")
print(f"Existing entities: {len(results['existing_entities'])}")
print(f"Relationships: {len(results['relationships'])}")
```

### A/B Testing Setup

```python
from src.memory.graph_memory import GraphManager, AltGraphManager

# Initialize both managers with same configuration
baseline_manager = GraphManager(
    storage_path="baseline_graph",
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    domain_config=domain_config
)

alt_manager = AltGraphManager(
    storage_path="alt_graph", 
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

# Run alternative approach  
alt_results = alt_manager.process_conversation_entry(conversation, digest)

# Compare results
print("Baseline entities:", len(baseline_entities))
print("Alternative entities:", len(alt_results['entities']))
```

### Individual Extractor Usage

```python
from src.memory.graph_memory import AltEntityExtractor, AltRelationshipExtractor

# Entity extraction only
entity_extractor = AltEntityExtractor(
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
rel_extractor = AltRelationshipExtractor(
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

The alternative extractors use configurable prompt templates:

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

## Sample Test Script

```python
def compare_extractors(conversation_text, digest_text, expected_entities=None):
    """Compare baseline and alternative extractors on the same input."""
    
    results = {
        "baseline": {},
        "alternative": {},
        "comparison": {}
    }
    
    # Time baseline approach
    start_time = time.time()
    # ... run baseline extraction
    baseline_time = time.time() - start_time
    
    # Time alternative approach
    start_time = time.time()
    alt_results = alt_manager.process_conversation_entry(conversation_text, digest_text)
    alt_time = time.time() - start_time
    
    # Calculate metrics
    results["comparison"] = {
        "baseline_time": baseline_time,
        "alternative_time": alt_time,
        "baseline_entities": len(baseline_entities),
        "alternative_entities": len(alt_results['entities']),
        "time_ratio": alt_time / baseline_time if baseline_time > 0 else float('inf')
    }
    
    if expected_entities:
        # Calculate accuracy metrics
        baseline_recall = calculate_recall(baseline_entities, expected_entities)
        alt_recall = calculate_recall(alt_results['entities'], expected_entities)
        results["comparison"]["baseline_recall"] = baseline_recall
        results["comparison"]["alternative_recall"] = alt_recall
    
    return results
```

## Troubleshooting

### Common Issues

1. **Empty Entities List**: Check that conversation_text is not empty and domain_config is properly set
2. **RAG Not Working**: Ensure graph_manager is passed to AltEntityExtractor constructor
3. **Template Not Found**: Verify prompt template files exist in `templates/` directory
4. **JSON Parsing Errors**: Check LLM responses in logs - may need prompt engineering

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

This alternative approach provides a foundation for testing whether LLM reasoning can improve entity and relationship extraction quality compared to the current algorithmic approach. 