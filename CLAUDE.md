# CLAUDE.md - Development Guide for LLM-Driven Agent Framework

This document provides a comprehensive guide for Claude Code instances working with this LLM-driven agent framework codebase.

export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; ...

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

### Running Examples

environment variables: 

export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; ...

```bash
# Agent Example
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; python examples/agent_usage_example.py --verbose --guid agent_test_1 --config dnd 


export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; echo "Please describe the ruins" |  python examples/agent_usage_example.py --verbose --guid dnd_test_1 --config dnd 


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
├── graph_memory_embeddings.jsonl # Entity description embeddings
└── graph_verbose.log             # verbose log
```

### Async Processing
- Digest generation runs asynchronously after conversation entries
- Embedding updates happen in background
- **Graph memory updates** happen asynchronously in the background (entity/relationship extraction)
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
- Memory files: agent_memories/standard/{SESSION_GUID}/
- Log files: agent_memories/standard/{SESSION_GUID}/logs

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

## Memory Storage Files

agent_memories/standard/{SESSION_GUID}/agent_memory.json
agent_memories/standard/{SESSION_GUID}/agent_memory_conversations.json
agent_memories/standard/{SESSION_GUID}/agent_memory_graph_data/graph_edges.json
agent_memories/standard/{SESSION_GUID}/agent_memory_graph_data/graph_nodes.json
agent_memories/standard/{SESSION_GUID}/agent_memory_graph_data/graph_metadata.json

## Logs

agent_memories/standard/{SESSION_GUID}/logs
agent_memories/standard/{SESSION_GUID}/agent_memory_graph_data/graph_verbose.log

## Utils

Test Ollama availability
- curl -s http://192.168.10.28:11434/api/tags | head -n 20


## Current Status & Plan

It is time for a change in direction.

### Architecture Plan: Standalone GraphManager Process

**Overview**: Run `GraphManager` as a standalone background process for handling computationally intensive graph operations (entity/relationship extraction, embeddings). Decouple from main CLI agent for responsiveness. Use file-based communication via shared JSON/JSONL files in a common `storage_path` directory. Main agent monitors files for updates; GraphManager processes conversation queue asynchronously.

**Key Components**:
- **GraphManager Process**: Async loop using `asyncio`. Processes conversation entries from `conversation_queue.jsonl`. Uses `OllamaService` for LLM, `EmbeddingsManager` for caching. Batch entries (5-10), throttle with delays. Atomic file updates for `graph_nodes.json`, `graph_edges.json`, `graph_metadata.json`, `graph_memory_embeddings.jsonl`. Track last processed GUID for recovery.
- **Main Agent Integration**: Uses `GraphQueries` to read graph files. Appends new entries to queue. Monitors directory with `watchdog` for event-driven reloads on file changes. Fallback to last known state if process down.
- **Communication Flow**: Agent writes to agent_memory_conversations.json; GraphManager reads, processes, writes updates, keeping track of processed conversation entries; agent detects changes and queries context for prompts.
- **Error Handling**: Logging to `graph_manager.log`. Crash recovery via metadata. Graceful degradation in agent.
- **Performance**: Incremental updates, embedding caching (consider `faiss` for large graphs). Prune low-confidence nodes periodically.
- **Testing/Modularity**: Standalone CLI for GraphManager. Mock LLM/embeddings. Dependency injection. Test crash recovery, file monitoring.
- **Alternatives/Enhancements**: Use SQLite for queue if JSONL bottlenecks. Manage process with `supervisord`. Domain config for entity/relationship types (e.g., D&D: characters, locations).

**Sample Run**:
- Start GraphManager: `python graph_manager_process.py`
- Start Agent: `python main_agent.py`

Implement as per sample code snippets, focusing on isolation and simplicity. Avoid complex IPC; prioritize file-based for now.


### Additional Advice for AI Coding Agent: GraphManager Isolation

**Code Insights**:
- Uses `SimpleGraphProcessor` for internal async task queuing; in separate process, replace with file-based loop to process `conversation_queue.jsonl` directly (read lines, process async via `process_conversation_entry_with_resolver_async`, clear processed lines atomically).
- Init requires `llm_service` (Ollama), `embeddings_manager`, `domain_config`; recreate in process script (e.g., hardcode or load from config file in `storage_path`).
- Async-capable: Use `asyncio` loop for processing; leverage `queue_background_processing` if keeping internal queue, but prefer direct file handling for simplicity.
- Storage/Logging: Shares `storage_path` for JSON files; `_setup_graph_specific_logging` creates per-GUID logs in memory dir—ensure process has write access; use `filelock` for queue to prevent contention.
- Obsolete: Ignore `process_conversation_entry_with_resolver` (sync, marked TODO: REMOVE); use async version only.
- Embeddings: `EmbeddingsManager` loads/saves to `graph_memory_embeddings.jsonl`—shared file, no changes needed.

**Refinements to Plan**:
- In `graph_manager_process.py`: Init full `GraphManager` with services/domain (e.g., `DND_CONFIG`); loop reads queue, calls `process_conversation_entry_with_resolver_async` per entry, uses locking (`filelock`), tracks last GUID in metadata.
- Error Recovery: On start, reload graph via `_load_graph`; resume unfinished queue entries using GUID check.
- Performance: Batch queue reads (e.g., every 1-5s); prune graph periodically via custom method if nodes > threshold.
- Testing: Add standalone mode to process queue file directly; mock LLM for tests.
- Integration: Agent calls write to queue; queries read files directly—no direct GraphManager interaction.

### Standalone Operation

The new GraphManager should be started separately, something like:

export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; python launcher.py --verbose --guid session_guid --config lab_assistant

launcher.py should import the graph manager classes

agent_usage_example.py will no longer need to be aware of the graph manager. The MemoryManager should use part of the graph manager system's code to query the graph for LLM prompt context

NOTE: The agent should work even if the graph manager is not running. Existing graph files can be queried. If there are no graph files, that is fine. If the graph manager is running it will eventually update the graph files.


## Development and Testing Philosopy

- Test subsystems in isolation
- Maintain tests for each subsystem
- When all subsystems work, then test the integrated whole (i.e. agent_usage_example)
- When there are issues, fix the subsystems, first
- Be parsimonious and surgical
- Make as few changes as necessary in each revision
- Remove unused and obsolete code whenever it is detected
- Avoid keeping alternate code, better to prune and keep things clear and simple