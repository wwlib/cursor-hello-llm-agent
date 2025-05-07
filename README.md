# LLM-Driven Agent with RAG-Enabled Session Memory


This project is a modern, extensible framework for building domain-agnostic LLM-powered agents with persistent, semantically searchable memory. The system supports Retrieval Augmented Generation (RAG), segment-level embeddings, and robust memory compression, making it suitable for complex, long-running conversational applications.

Important: This project has been "vibe-coded" using Cursor as a way to get familiar with agent-assisted development. All of the agent interactions have been preserved in `/cursor-notes` (intially) and now going forward in `/.specstory` as markdown transcripts.

This README contains a description of the current state of the project. For historical details, see:
- cursor-notes (contains the original cursor instructions and .specstory files)
- [README-phase-2.md](README-phase-2.md) (phase 2 development notes)
- [README-phase-3.md](README-phase-3.md) (phase 3 development notes - this is the current phase)

---

## Project Highlights

- **RAG-Enabled Memory**: Memory is searchable using segment-level embeddings and semantic similarity (RAG). Relevant context is automatically retrieved and injected into LLM prompts for grounded, context-aware responses.
- **Turn-Based, Importance-Filtered Compression**: Conversation history is compressed in user+agent turns, retaining only the most important segments (rated by the LLM) for efficient, scalable memory.
- **Provider-Agnostic LLM Service**: Supports both local (Ollama) and cloud (OpenAI) LLMs, with per-call options for temperature, streaming, and embedding generation.
- **Modular, Domain-Agnostic Agent**: The agent is phase-driven (INITIALIZATION, LEARNING, INTERACTION) and can be configured for any domain via external config files—no code changes required.
- **Robust, Modern Test Suite**: Comprehensive tests for memory, agent, embeddings, RAG, and segmentation. Canonical, minimal RAG example included.
- **Extensible and Maintainable**: All major components (memory, embeddings, RAG, agent) are modular and easily extended or replaced.

---

## Core Architecture

### 1. Memory Management System

- **BaseMemoryManager**: Abstract base class for all memory managers (handles persistence, interface, and GUIDs).
- **MemoryManager**: Main implementation. Features:
  - **Static Memory**: Foundational, read-only knowledge (seeded at initialization).
  - **Context**: Compressed, topic-organized, high-importance information from past conversations.
  - **Conversation History**: Full record of all interactions, with each entry digested into LLM-rated segments (importance, topics, type).
  - **Segment-Level Embeddings**: Only the most meaningful segments are embedded and indexed for semantic search.
  - **Automatic, Turn-Based Compression**: After a configurable number of turns, memory is compressed to retain only important segments, preserving dialogue flow and traceability.
- **SimpleMemoryManager**: Flat, non-transforming memory for testing and simple use cases.

### 2. Embeddings and RAG Layer

- **EmbeddingsManager**: Handles all embedding generation, storage (JSONL), and semantic search. Embeddings are generated for each LLM-rated segment, not just full entries.
- **RAGManager**: Retrieves semantically relevant context for queries using the EmbeddingsManager. Injects this context into LLM prompts for Retrieval Augmented Generation (RAG).
- **Canonical Example**: See `examples/rag_enhanced_memory_example_simple.py` for a minimal, end-to-end RAG workflow.

### 3. LLM Service Layer

- **Provider-Agnostic**: Supports Ollama (local) and OpenAI (cloud) via a common interface.
- **Configurable**: Per-call options for temperature, streaming, and embedding model.
- **Debug Logging**: Optional, with scoped output and file/console support.

### 4. Agent Layer

- **Phase-Driven**: The agent manages conversation flow through INITIALIZATION, LEARNING, and INTERACTION phases.
- **Delegation**: All memory operations (creation, update, compression, retrieval) are handled by the memory manager. The agent is domain-agnostic and stateless regarding memory.
- **Domain Configuration**: Behavior is controlled via external config files (see `examples/domain_configs.py`).

---

## Key Features

- **RAG-Enhanced Memory Search**: Retrieve contextually relevant information from any point in conversation history using semantic similarity.
- **Segment-Only Embeddings**: Only the most important, LLM-rated segments are embedded and indexed, improving retrieval quality and efficiency.
- **Automatic, Turn-Based Memory Compression**: Keeps memory size manageable while preserving important context and dialogue flow.
- **Separation of Concerns**: Agent, memory, embeddings, and RAG are fully decoupled and independently testable.
- **Persistent, Traceable Storage**: All memory and conversation history is saved to disk with GUIDs for traceability.
- **Robust Error Handling**: Defensive programming throughout, with automatic backups and recovery.
- **Modern Test Suite**: Tests for all major components, including integration with real LLM endpoints.

---

## Example Use Cases

- **D&D Campaign Management**: Create and manage a virtual campaign world, with persistent memory and semantic search.
- **User Story Generation**: Assist in requirements gathering and feature planning for software projects.
- **RAG-Enhanced Q&A**: Retrieve and use relevant historical context for any domain.
- **Basic Memory Operations**: Demonstrate direct memory creation, querying, and compression.

---

## Setup and Usage

### Prerequisites
- Python 3.8+
- Ollama (for local LLM/embedding models) or OpenAI API key

### Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
pip install -r requirements.txt
```

### LLM Service Configuration
Example Ollama setup:
```python
from src.ai.llm_ollama import OllamaService
llm_service = OllamaService({
    "base_url": "http://localhost:11434",
    "model": "gemma3",  # or llama3, etc.
    "temperature": 0.7,
    "stream": False,
    "debug": True,
    "debug_file": "agent_debug.log",
    "debug_scope": "agent_example",
    "console_output": False
})
```

### Running Examples
```bash
# Canonical RAG Example (recommended starting point)
OLLAMA_BASE_URL=http://localhost:11434 python examples/rag_enhanced_memory_example_simple.py

# D&D Campaign Example (standard memory manager)
python examples/agent_usage_example.py

# D&D Campaign Example (simple memory manager)
python examples/agent_usage_example.py --type simple

# User Story Generation Example
python examples/user_story_example.py

# Embeddings Manager Example
OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/embeddings_manager_example.py

# Memory Manager Example
python examples/memory_manager_usage_example.py
```

### Running Tests
```bash
pytest tests/ -v -s
```

---

## Extensibility & Modularity
- **Add new domains** by providing a new config file—no code changes required.
- **Swap LLM providers** by changing the LLM service instantiation.
- **Extend memory, embeddings, or RAG** by subclassing the relevant manager.
- **All components are independently testable and replaceable.**

---

## Further Reading & Development History


## Component Documentation
- [Agent Service](src/agent/README-agent.md): Phase-driven conversational agent design
- [LLM Service](src/ai/README-ai.md): Provider-agnostic LLM interface
- [Memory Manager](src/memory/README-memory-manager.md): RAG-enabled memory system

- [README-phase-3.md](README-phase-3.md): Notes about the current phase of development.
- [README-phase-2.md](README-phase-2.md): Detailed development notes and architectural evolution.
- `cursor-notes/`, `.specstory/`: Historical design and implementation records.

---

## Acknowledgements
- Built with Cursor, Ollama, and OpenAI.
- Inspired by best practices in LLM agent and RAG system design.