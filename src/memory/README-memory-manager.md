# Memory Manager for LLM-Driven Agent

A modern, LLM-driven memory system for conversational agents, supporting segment-level embeddings, RAG (Retrieval Augmented Generation), and robust, scalable memory compression.

## Overview

The Memory Manager organizes, compresses, and retrieves conversational memory using LLM prompts and segment-level embeddings. It is designed to:
- Maintain context across long-running sessions
- Support semantic search and RAG
- Adapt to any domain via configuration, not code changes
- Be provider-agnostic (works with any LLM/embedding backend)

## Key Features

- **Segment-Based Memory**: All conversation entries are digested into LLM-rated segments (importance, topics, type).
- **RAG-Enabled**: Segment-level embeddings power semantic search and Retrieval Augmented Generation (RAG).
- **Turn-Based Compression**: Conversation history is compressed in user+agent turns, retaining only the most important segments.
- **Persistent, Traceable Storage**: All memory and conversation history is saved to disk with GUIDs for traceability.
- **Prompt-Driven, Provider-Agnostic**: All memory operations are handled via LLM prompts, and the system is decoupled from any specific LLM provider.

## Memory Structure

Memory is organized as a dictionary with the following main sections:

- `static_memory`: Foundational, unchanging knowledge about the domain (markdown/text, not JSON).
- `context`: Compressed, topic-organized, high-importance information from past conversations (used for efficient retrieval and prompt context).
- `conversation_history`: Full record of all interactions, with each entry digested into LLM-rated segments (importance, topics, type).
- `metadata`: System information (timestamps, version, domain, etc.).

Example (simplified):
```json
{
  "static_memory": "...markdown/text...",
  "context": [
    {"text": "...compressed summary...", "guids": ["..."]}
  ],
  "conversation_history": [
    {
      "guid": "...",
      "role": "user",
      "content": "...",
      "digest": {
        "rated_segments": [
          {"text": "...", "importance": 5, "topics": ["magic"], "type": "information"},
          ...
        ]
      },
      "timestamp": "..."
    },
    ...
  ],
  "metadata": {"created_at": "...", "updated_at": "...", "version": "2.0.0", ...}
}
```

## Embeddings and RAG

- **Segment-Level Embeddings**: Embeddings are generated for each LLM-rated segment (not just full entries).
- **EmbeddingsManager**: Handles embedding generation, storage (JSONL), and semantic search.
- **RAGManager**: Retrieves semantically relevant context for queries, which is injected into LLM prompts for Retrieval Augmented Generation (RAG).

## Turn-Based, Importance-Filtered Compression

- Conversation history is compressed in user+agent turns.
- Only segments rated above a configurable importance threshold are retained.
- Compression is automatic and transparent to the agent.

## Usage Example

```python
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

# Initialize LLM and memory manager
llm_service = OllamaService({
    "base_url": "http://localhost:11434",
    "model": "gemma3",
    "temperature": 0.7
})
memory_manager = MemoryManager(memory_guid, llm_service=llm_service)

# Create initial memory
memory_manager.create_initial_memory("The world is a flat world with a single continent...")

# Add a conversation entry (user message)
user_entry = {
    "role": "user",
    "content": "Tell me about the campaign world."
}
memory_manager.add_conversation_entry(user_entry)

# Query memory (RAG context is used automatically)
response = memory_manager.query_memory({"query": "What are the most important magical artifacts?"})
print(response["response"])
```

## Prompt-Driven, Provider-Agnostic Design

- All memory operations (creation, update, compression, retrieval) are handled via LLM prompts.
- The system is decoupled from any specific LLM provider (Ollama, OpenAI, etc.).
- Per-call options (temperature, model, etc.) are supported.

## Extensibility
- **Add new domains** by providing a new config file—no code changes required.
- **Swap LLM providers** by changing the LLM service instantiation.
- **Extend memory, embeddings, or RAG** by subclassing the relevant manager.
- All components are independently testable and replaceable.

## Best Practices
- Let the MemoryManager handle all memory logic; do not manipulate memory structure directly.
- Use domain configuration for specialization.
- Leverage RAG and semantic search for contextually relevant retrieval.
- Keep the agent stateless regarding memory; all persistent state is managed by the memory manager.

## Further Reading
- See the main project README for architectural details and advanced usage.
- See `examples/rag_enhanced_memory_example_simple.py` for a canonical RAG workflow.
- See `src/memory/memory_manager.py` for implementation details.
