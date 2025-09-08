# CLAUDE.md - Development Guide for LLM-Driven Agent Framework

This document provides a comprehensive guide for Claude Code instances working with this LLM-driven agent framework codebase.

DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large

## Project Overview

This is a modern, extensible framework for building domain-agnostic LLM-powered agents with persistent, semantically searchable memory. The system supports Retrieval Augmented Generation (RAG), segment-level embeddings, structured knowledge graphs, and robust memory compression.

**Key Capabilities:**
- **Graph Memory System**: Automatic entity extraction and relationship mapping for structured knowledge representation
- **RAG-enabled memory** with semantic search and graph-enhanced context
- **Three-stage memory filtering pipeline** (relevance gate → importance → type)
- **Turn-based memory compression** with importance filtering  
- **Provider-agnostic LLM service** (Ollama/OpenAI)
- **Domain-configurable agents** (no code changes needed)
- **Comprehensive async test suite** with automated agent testing framework
- **Modular, extensible architecture** with seamless graph memory integration

## Architecture Overview

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Agent       │    │   Memory        │    │    LLM          │
│   (Phase-driven)│◄──►│   Manager       │◄──►│   Service       │
│                 │    │(RAG+Graph-enabled)│   │ (Provider-agnostic)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Embeddings      │
                    │     Manager       │
                    └───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Graph Memory    │
                    │     Manager       │
                    └───────────────────┘
```

### Core Components

1. **Agent Layer** (`src/agent/`)
   - Phase-driven conversation orchestrator (INITIALIZATION, LEARNING, INTERACTION)
   - Domain-agnostic and stateless regarding memory
   - Delegates all memory operations to MemoryManager

2. **Memory System** (`src/memory/`)
   - **BaseMemoryManager**: Abstract base with persistence and GUID management
   - **MemoryManager**: Full implementation with RAG, graph memory, compression, and segmentation
   - **SimpleMemoryManager**: Flat memory for testing/simple use cases
   - **DigestGenerator**: Memory relevance gate with importance and type classification
   - **EmbeddingsManager**: Segment-level embedding storage and semantic search
   - **RAGManager**: Context retrieval and prompt enhancement with graph integration
   - **GraphManager**: Structured knowledge representation with entity/relationship extraction

3. **LLM Service** (`src/ai/`)
   - **LLMService**: Abstract base class with response cleaning and debug logging
   - **OllamaService**: Local LLM implementation
   - **OpenAIService**: Cloud LLM implementation
   - Unified interface for both text generation and embeddings

## Development Commands

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
pip install -r requirements.txt
```

### Testing

environment variables: DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large

```bash
# Run all tests
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large pytest tests/ -v -s

# Run specific test categories
pytest tests/memory_manager/ -v -s
pytest tests/agent/ -v -s
pytest tests/ai/ -v -s

# Run integration tests (requires running Ollama)
pytest tests/ -v -s -m integration

# Run automated agent testing framework
python run_automated_tests.py --quick           # Quick test
python run_automated_tests.py                   # Full suite
python run_automated_tests.py --persona curious # Specific persona
python run_automated_tests.py --domain dnd      # Specific domain
```

### Running Examples

environment variables: DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large

```bash
# Canonical RAG example (recommended starting point)
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/rag_enhanced_memory_example_simple.py

# Graph memory standalone example (demonstrates graph-only functionality)
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/graph_memory_example.py

# Interactive agent with domain config (includes automatic graph memory) and interaction passed in via stdin
# Fresh runs can be started by specifying a new guid
# memory files are in <project-root>/agent_memories/standard/[guid]
# graph memory files are in <project-root>/agent_memories/standard/[guid]/agent_memory_graph_data
# logs are in <project-root>/logs/[guid]

echo "Please describe the ruins" | DEV_MODE=true OLLAMA_BASE_URL=http://192.168.0.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/agent_usage_example.py --guid dnd5g16 --config dnd 


# List available memory files
python examples/agent_usage_example.py --list

# Use simple memory manager (no graph memory)
python examples/agent_usage_example.py --type simple
```

## Key Implementation Details

### Memory Structure
Memory is organized as a JSON structure with:
- `static_memory`: Foundational domain knowledge (markdown/text)
- `context`: Compressed, topic-organized summaries
- `conversation_history`: Full interaction record with LLM-rated segments
- `metadata`: System information and versioning

### Memory Filtering Pipeline
The system uses a three-stage filtering pipeline to ensure only valuable information enters memory:

1. **Relevance Gate**: `memory_worthy` field filters out non-memorable content (simple commands, acknowledgments)
2. **Importance Filter**: Only segments with importance ≥ 3 are processed for embeddings and context
3. **Type Filter**: Only `"information"` and `"action"` segments appear in context (excludes old queries/commands)

### Segment-Level Processing
All conversation entries are processed into importance-rated segments:
```json
{
  "text": "The party found a magical sword in the ruins",
  "importance": 4,
  "topics": ["objects", "archaeology"],
  "type": "information",
  "memory_worthy": true
}
```

### RAG Pipeline
1. Query received
2. EmbeddingsManager performs semantic search on filtered segments (importance ≥ 3, types: information/action)
3. RAGManager retrieves relevant context with type filtering
4. Pre-qualified context injected into LLM prompt
5. Enhanced response generated

### Graph Memory System
The graph memory system provides structured knowledge representation alongside RAG:

**Key Features:**
- **Automatic Entity Extraction**: LLM-driven identification of characters, locations, objects, events, concepts, and organizations
- **Relationship Detection**: Automatic discovery of relationships between entities (located_in, owns, allies_with, etc.)
- **Semantic Entity Matching**: RAG-based similarity matching prevents duplicate entities (configurable threshold: 0.8)
- **Domain-Specific Configuration**: Entity types and relationships adapted for D&D, software projects, lab work, etc.
- **Graph-Enhanced Context**: Structured entity context added to LLM prompts alongside RAG results

**Processing Pipeline:**
1. Conversation segments processed for important content (importance ≥ 3)
2. Entities extracted using domain-specific LLM prompts
3. Entity descriptions embedded for similarity matching with existing nodes
4. New entities added or existing entities updated based on similarity
5. Relationships extracted between entities in the same conversation segment
6. Graph context retrieved for queries and added to memory prompts

**Storage Structure:**
```
memory_file_graph_data/
├── graph_nodes.json              # Entity storage with attributes
├── graph_edges.json              # Relationship storage with evidence
├── graph_metadata.json           # Graph statistics and configuration
└── graph_memory_embeddings.jsonl # Entity description embeddings
```

### Async Processing
- Digest generation runs asynchronously after conversation entries
- Embedding updates happen in background
- **Graph memory updates** happen asynchronously (entity/relationship extraction)
- Agent tracks pending operations with `has_pending_operations()` (includes graph updates)

## File Structure Reference

```
├── src/
│   ├── agent/
│   │   ├── agent.py              # Main agent implementation
│   │   └── README-agent.md       # Agent documentation
│   ├── ai/
│   │   ├── llm.py               # Base LLM interface
│   │   ├── llm_ollama.py        # Ollama implementation
│   │   ├── llm_openai.py        # OpenAI implementation
│   │   └── README-ai.md         # LLM service documentation
│   └── memory/
│       ├── base_memory_manager.py    # Abstract base class
│       ├── memory_manager.py         # Full memory implementation with graph integration
│       ├── simple_memory_manager.py  # Simplified implementation
│       ├── embeddings_manager.py     # Embedding storage/search
│       ├── rag_manager.py            # RAG context retrieval with graph integration
│       ├── digest_generator.py       # Segment processing
│       ├── content_segmenter.py      # Content analysis
│       ├── data_preprocessor.py      # Data preparation
│       ├── memory_compressor.py      # Turn-based compression
│       ├── graph_memory/             # Graph memory system
│       │   ├── __init__.py           # Module initialization
│       │   ├── graph_manager.py      # Main graph operations with RAG-based entity resolution
│       │   ├── entity_extractor.py   # LLM-driven entity identification
│       │   ├── relationship_extractor.py # LLM-driven relationship detection
│       │   ├── graph_queries.py      # Context retrieval and graph navigation
│       │   └── graph_storage.py      # JSON persistence layer
│       ├── templates/                # LLM prompt templates
│       └── README-memory-manager.md  # Memory system docs
├── examples/
│   ├── agent_usage_example.py        # Main interactive example (includes graph memory)
│   ├── rag_enhanced_memory_example_simple.py  # Canonical RAG demo
│   ├── graph_memory_example.py       # Standalone graph memory demonstration
│   ├── domain_configs.py             # Domain configurations with graph memory configs
│   ├── temp_data/                    # Temporary example data and example output - excluded via .gitignore
│   └── [other examples]
├── tests/
│   ├── agent/                        # Agent tests
│   ├── ai/                          # LLM service tests
│   ├── memory_manager/              # Memory system tests
│   │   ├── test_graph_memory.py      # Graph memory component tests
│   │   ├── test_graph_memory_integration.py # Graph memory integration tests
│   ├── graph_memory/                # Graph Memory system tests
│   │   ├── logs/                    # Test logs - excluded via .gitignore
│   │   ├── sample_data/             # Sample data for Graph Memory tests
│   ├── test_files/                  # Temporary test data and test output - excluded via .gitignore
│   └── automated_agent_testing/     # Automated testing framework
│       ├── user_simulator.py        # LLM-driven user personas
│       ├── memory_analyzer.py       # Memory evolution analysis
│       ├── log_analyzer.py          # System log analysis
│       └── test_runner.py           # Main test orchestrator
├── run_automated_tests.py           # Simple CLI runner script
└── docs/                            # Additional documentation
```

## Configuration System

The system uses domain configs to adapt behavior without code changes:

See: <project-root>/examples/domain_configs.py

```python
# Example domain config with graph memory
DND_CONFIG = {
    "domain_name": "dnd_campaign",
    "domain_specific_prompt_instructions": {
        "query": "You are a DM for a D&D campaign...",
        "update": "You are analyzing input and extracting..."
    },
    "initial_data": "Campaign setting and initial world state...",
    "topic_taxonomy": {
        "world": ["setting", "geography", "location"],
        "characters": ["npc", "player", "personality"]
    },
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["character", "location", "object", "event", "concept", "organization"],
        "relationship_types": ["located_in", "owns", "member_of", "allies_with", "enemies_with", 
                              "uses", "created_by", "leads_to", "participates_in", "related_to"],
        "entity_extraction_prompt": "Extract entities from this D&D campaign text...",
        "relationship_extraction_prompt": "Identify relationships between entities...",
        "similarity_threshold": 0.8
    }
}
```

Available configs in `examples/domain_configs.py`:
- `dnd`: D&D campaign management with characters, locations, objects, events
- `user_story`: Software requirements gathering with features, stakeholders, technologies
- `lab_assistant`: Laboratory notebook assistant with equipment, materials, procedures

**Graph Memory Configuration:**
Each domain config includes `graph_memory_config` with:
- `enabled`: Boolean to enable/disable graph memory
- `entity_types`: Domain-specific entity categories for extraction
- `relationship_types`: Relevant relationship types for the domain
- `entity_extraction_prompt`: Domain-specific instructions for entity identification
- `relationship_extraction_prompt`: Domain-specific instructions for relationship detection
- `similarity_threshold`: Threshold for entity matching (0.0-1.0, default: 0.8)

## Testing Strategy

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: End-to-end with real LLM services (marked with `@pytest.mark.integration`)
- **Graph Memory Tests**: Comprehensive testing of entity extraction, relationship detection, and graph queries
- **Memory Snapshots**: Canonical test data in `tests/memory_manager/memory_snapshots/`
- **Async Testing**: Full async support with pytest-asyncio including graph memory operations
- **Automated Agent Testing**: LLM-driven user simulation for comprehensive system validation

### Automated Testing Framework
The system includes a comprehensive automated testing framework that uses LLMs to simulate realistic user interactions:

**Core Components:**
- **UserSimulator**: 6 different personas (curious beginner, experienced user, testing user, confused user, detailed user, rapid-fire user)
- **MemoryAnalyzer**: Tracks memory evolution, quality, and organization
- **LogAnalyzer**: Monitors system health, errors, and performance
- **TestRunner**: Orchestrates test execution and result analysis

**Quality Metrics:**
- Interaction Quality: Response appropriateness, error rates
- Memory Quality: Organization and usefulness
- System Health: Operational stability
- Overall Quality: Combined weighted score

**Generated Outputs:**
- Memory files: `agent_memories/standard/autotest_*`
- Log files: `logs/autotest_*`
- Test reports: `logs/test_summary_*.json`

## Common Development Patterns

### Adding a New Domain
1. Create config in `examples/domain_configs.py`
2. Define initial data, prompts, and topic taxonomy
3. No code changes needed - system is fully configurable

### Extending Memory Management
1. Subclass `BaseMemoryManager`
2. Implement abstract methods: `create_initial_memory`, `query_memory`, `update_memory`
3. Handle persistence via base class methods

### Adding LLM Providers
1. Subclass `LLMService`
2. Implement `_generate_impl` and `_generate_embedding_impl`
3. Provider automatically works with entire system

## Debugging and Logging

The system includes comprehensive debug logging:

```python
# Enable debug logging
llm_service = OllamaService({
    "debug": True,
    "debug_file": "debug.log",
    "debug_scope": "my_scope",
    "console_output": True
})
```

Logs are organized by:
- GUID-specific directories for session isolation
- Component-specific files (general, digest, embeddings)
- Scoped logging with clear operation tracking

## Performance Considerations

- **Memory Filtering**: Three-stage pipeline prevents non-valuable content from entering system
- **Embeddings**: Only high-importance (≥3) information/action segments are embedded
- **Graph Memory**: Entity extraction and relationship detection only on important, memory-worthy segments
- **Semantic Entity Matching**: Prevents duplicate graph nodes through embedding similarity (configurable threshold)
- **Compression**: Automatic turn-based compression with type filtering keeps memory manageable
- **Caching**: Embedding files use JSONL for efficient append operations
- **Async Processing**: Background processing for digests, embeddings, and graph updates prevents blocking
- **JSON Storage**: Memory-efficient graph storage with incremental updates

## Integration Points

### With Ollama
```bash
# Start Ollama with required models
ollama pull gemma3
ollama pull mxbai-embed-large
```

### With OpenAI
```python
openai_service = OpenAIService({
    "api_key": "your-key",
    "model": "gpt-4"
})
```

## Development History

This codebase was developed using Cursor AI assistance and maintains detailed development records in:
- `cursor-notes/`: Original Cursor interactions and design decisions
- `README-phase-*.md`: Phase-specific development documentation
- `.specstory/`: Continued development history (going forward)
- `claude-code-notes/`: Development using Claude Code

The project demonstrates "vibe-coded" development with comprehensive agent-assisted iteration and refinement.

## Quick Start for New Contributors

1. **Read the main README.md** for project overview
2. **Run the canonical example**: `examples/rag_enhanced_memory_example_simple.py`
3. **Try graph memory**: `python examples/graph_memory_example.py` (requires Ollama)
4. **Explore with interactive agent**: `python examples/agent_usage_example.py --config dnd` (includes graph memory)
5. **Review component docs**: `src/*/README-*.md` files
6. **Run tests to understand expected behavior**: `pytest tests/ -v -s`

## Common Debugging Scenarios

### Memory Not Persisting
- Check file permissions in memory directory
- Verify GUID consistency between sessions
- Check backup files created during saves

### RAG Not Working
- Ensure embedding model is available
- Check embeddings file creation in logs
- Verify segment importance scores meet threshold (≥3)
- Confirm segments have appropriate types (information/action) for embedding
- Check memory_worthy filtering isn't excluding too much content

### LLM Connection Issues
- Confirm Ollama is running: `ollama list`
- Check base URL configuration
- Review debug logs for connection errors

### Test Failures
- Integration tests require running Ollama service
- Check model availability: `ollama list`
- Verify network connectivity for external Ollama instances

### Memory Filtering Issues
- Check digest generation logs for memory_worthy classification
- Verify importance threshold settings across components (default: 3)
- Review segment type distribution in generated digests
- Test with simple vs complex content to validate filtering effectiveness

### Graph Memory Issues
- **Graph Not Updating**: Check that `enable_graph_memory=True` in MemoryManager initialization
- **No Entities Extracted**: Verify segment importance scores meet threshold (≥3) and are memory_worthy
- **Duplicate Entities**: Adjust similarity threshold in domain config (default: 0.8)
- **Missing Graph Files**: Check graph storage directory creation and permissions
- **Graph Context Empty**: Verify entity extraction is working and entities exist in graph storage
- **Relationship Extraction Failing**: Check that multiple entities exist in conversation segments

### Automated Testing Issues
- Ensure automated testing framework has access to running Ollama service
- Check memory analyzer for context data structure handling (should be array format)
- Verify user simulator personas are generating appropriate interactions
- Review test summary files for detailed failure analysis

## Recent Enhancements (Phase 4)

### Enhanced Digest System
The digest system has been significantly improved with a comprehensive filtering pipeline:

**Memory Relevance Gate:**
- Added `memory_worthy` field to segment classification
- Filters out non-memorable content (simple commands, acknowledgments, conversational niceties)
- Prevents memory bloat by excluding content that doesn't need to be remembered

**Standardized Thresholds:**
- Unified importance threshold of 3 across all memory components
- Previously inconsistent: compression (3), RAG (2), embeddings (none)
- Now consistent: all components use importance ≥ 3 for processing

**Type-Based Filtering:**
- Only `"information"` and `"action"` segments included in context
- `"query"` and `"command"` segments filtered out to prevent noise
- Applied consistently across compression, RAG retrieval, and embeddings

**Test Coverage:**
- Comprehensive test suite with 8.2-8.8/10 LLM evaluation scores
- 100% effective memory worthy filtering (0/3 non-memorable segments preserved)
- Accurate type classification and topic normalization validation

This creates a highly efficient pipeline ensuring only valuable information influences agent responses, significantly improving both performance and response quality.

### Automated Testing Framework (Phase 4)
A comprehensive automated testing system was implemented that uses LLMs to simulate realistic user interactions:

**Framework Architecture:**
- **UserSimulator**: 6 personas simulating different user types and interaction patterns
- **MemoryAnalyzer**: Comprehensive analysis of memory evolution, quality, and organization
- **LogAnalyzer**: System health monitoring, error detection, and performance analysis
- **TestRunner**: Orchestrates test execution with configurable scenarios and success criteria

**Key Features:**
- Realistic user simulation with authentic interaction patterns
- Comprehensive monitoring of memory evolution and system health
- Automated analysis with quality scoring and success evaluation
- Flexible configuration for custom scenarios and success criteria
- Rich reporting with detailed analysis and actionable insights

**Quality Metrics:**
Each test generates comprehensive scores (0-100):
- Interaction Quality: Response appropriateness and error rates
- Memory Quality: Organization effectiveness and information usefulness
- System Health: Operational stability and performance
- Overall Quality: Combined weighted score

**Bug Fixes:**
- Fixed memory analyzer bug with context data format handling (array vs dictionary)
- Standardized context data structure handling across memory analyzer
- Eliminated unreachable code and simplified logic
- Verified automated testing framework is fully operational with 100% success rate

The framework automatically validates agent performance across different user types, memory development patterns, and system health metrics, providing deep insights into agent capabilities and identifying areas for improvement.

## Recent Enhancements (Phase 5)

### Graph Memory System Integration
A comprehensive graph memory system has been fully integrated with the main memory manager:

**Core Integration:**
- **Seamless MemoryManager Integration**: Graph memory automatically enabled by default in all memory managers
- **Async Processing Pipeline**: Entity extraction and relationship detection happen asynchronously with digests and embeddings
- **RAG + Graph Context**: Memory queries now receive both semantic (RAG) and structural (graph) context
- **Domain-Specific Configuration**: Graph memory adapts to D&D campaigns, software projects, lab work, etc.

**Automatic Processing:**
- **Entity Extraction**: LLM-driven identification of domain-specific entities from conversation segments
- **Relationship Detection**: Automatic discovery of relationships between entities within conversations
- **Semantic Entity Matching**: RAG-based similarity matching prevents duplicate entities (configurable threshold)
- **Graph Context Enhancement**: Structured entity context automatically added to all memory queries

**Technical Implementation:**
- **Modular Architecture**: Complete graph memory system in `src/memory/graph_memory/` with clean separation
- **JSON Persistence**: Memory-efficient storage with incremental updates and backup capabilities
- **Error Handling**: Robust error handling with graceful degradation when graph operations fail
- **Comprehensive Testing**: Full test suite including integration tests and mock LLM services

**Impact:**
- **Enhanced Memory**: Conversations automatically build structured knowledge graphs alongside flat memory
- **Improved Context**: Queries benefit from both semantic search and relationship-based context
- **No Breaking Changes**: All existing examples and code work with enhanced capabilities
- **Foundation for Advanced Features**: Enables future graph-based reasoning and visualization

This represents a major advancement in the agent framework's memory capabilities, providing structured knowledge representation that significantly enhances the system's ability to understand and reason about conversational context.

## Summary

This framework provides a solid foundation for building sophisticated LLM agents with persistent, searchable memory enhanced by structured knowledge graphs. The modular design makes it easy to extend and adapt for new domains and use cases, while the graph memory system adds powerful relationship-aware context to improve agent reasoning and response quality.