# CLAUDE.md - Development Guide for LLM-Driven Agent Framework

This document provides a comprehensive guide for Claude Code instances working with this LLM-driven agent framework codebase.

## Project Overview

This is a modern, extensible framework for building domain-agnostic LLM-powered agents with persistent, semantically searchable memory. The system supports Retrieval Augmented Generation (RAG), segment-level embeddings, and robust memory compression.

**Key Capabilities:**
- RAG-enabled memory with semantic search
- Three-stage memory filtering pipeline (relevance gate → importance → type)
- Turn-based memory compression with importance filtering  
- Provider-agnostic LLM service (Ollama/OpenAI)
- Domain-configurable agents (no code changes needed)
- Comprehensive async test suite
- Modular, extensible architecture

## Architecture Overview

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Agent       │    │   Memory        │    │    LLM          │
│   (Phase-driven)│◄──►│   Manager       │◄──►│   Service       │
│                 │    │   (RAG-enabled) │    │ (Provider-agnostic)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌──────▼──────┐
                       │ Embeddings  │
                       │   Manager   │
                       └─────────────┘
```

### Core Components

1. **Agent Layer** (`src/agent/`)
   - Phase-driven conversation orchestrator (INITIALIZATION, LEARNING, INTERACTION)
   - Domain-agnostic and stateless regarding memory
   - Delegates all memory operations to MemoryManager

2. **Memory System** (`src/memory/`)
   - **BaseMemoryManager**: Abstract base with persistence and GUID management
   - **MemoryManager**: Full implementation with RAG, compression, and segmentation
   - **SimpleMemoryManager**: Flat memory for testing/simple use cases
   - **DigestGenerator**: Memory relevance gate with importance and type classification
   - **EmbeddingsManager**: Segment-level embedding storage and semantic search
   - **RAGManager**: Context retrieval and prompt enhancement

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
```bash
# Run all tests
pytest tests/ -v -s

# Run specific test categories
pytest tests/memory_manager/ -v -s
pytest tests/agent/ -v -s
pytest tests/ai/ -v -s

# Run integration tests (requires running Ollama)
pytest tests/ -v -s -m integration
```

### Running Examples
```bash
# Canonical RAG example (recommended starting point)
OLLAMA_BASE_URL=http://localhost:11434 python examples/rag_enhanced_memory_example_simple.py

# Interactive agent with domain config
python examples/agent_usage_example.py --config dnd --guid my-campaign

# List available memory files
python examples/agent_usage_example.py --list

# Use simple memory manager
python examples/agent_usage_example.py --type simple
```

### Development Mode
```bash
# Full debug logging with external Ollama
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/agent_usage_example.py --guid dnd --config dnd
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

### Async Processing
- Digest generation runs asynchronously after conversation entries
- Embedding updates happen in background
- Agent tracks pending operations with `has_pending_operations()`

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
│       ├── memory_manager.py         # Full memory implementation
│       ├── simple_memory_manager.py  # Simplified implementation
│       ├── embeddings_manager.py     # Embedding storage/search
│       ├── rag_manager.py            # RAG context retrieval
│       ├── digest_generator.py       # Segment processing
│       ├── content_segmenter.py      # Content analysis
│       ├── data_preprocessor.py      # Data preparation
│       ├── memory_compressor.py      # Turn-based compression
│       ├── templates/                # LLM prompt templates
│       └── README-memory-manager.md  # Memory system docs
├── examples/
│   ├── agent_usage_example.py        # Main interactive example
│   ├── rag_enhanced_memory_example_simple.py  # Canonical RAG demo
│   ├── domain_configs.py             # Domain configurations
│   └── [other examples]
├── tests/
│   ├── agent/                        # Agent tests
│   ├── ai/                          # LLM service tests
│   └── memory_manager/              # Memory system tests
└── docs/                            # Additional documentation
```

## Configuration System

The system uses domain configs to adapt behavior without code changes:

```python
# Example domain config
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
    }
}
```

Available configs in `examples/domain_configs.py`:
- `dnd`: D&D campaign management
- `user_story`: Software requirements gathering
- `lab_assistant`: Laboratory notebook assistant

## Testing Strategy

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: End-to-end with real LLM services (marked with `@pytest.mark.integration`)
- **Memory Snapshots**: Canonical test data in `tests/memory_manager/memory_snapshots/`
- **Async Testing**: Full async support with pytest-asyncio

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
- **Compression**: Automatic turn-based compression with type filtering keeps memory manageable
- **Caching**: Embedding files use JSONL for efficient append operations
- **Async**: Background processing prevents blocking user interactions

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

The project demonstrates "vibe-coded" development with comprehensive agent-assisted iteration and refinement.

## Quick Start for New Contributors

1. **Read the main README.md** for project overview
2. **Run the canonical example**: `examples/rag_enhanced_memory_example_simple.py`
3. **Explore with interactive agent**: `python examples/agent_usage_example.py --config dnd`
4. **Review component docs**: `src/*/README-*.md` files
5. **Run tests to understand expected behavior**: `pytest tests/ -v -s`

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

This framework provides a solid foundation for building sophisticated LLM agents with persistent, searchable memory. The modular design makes it easy to extend and adapt for new domains and use cases.