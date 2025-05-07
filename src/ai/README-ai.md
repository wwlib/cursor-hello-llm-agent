# LLM Service Interface

A provider-agnostic interface for interacting with LLMs (OpenAI, Ollama, etc.), supporting both text generation and embedding generation for RAG/semantic search.

## Overview

The LLM service layer provides a unified interface for both text generation and embedding generation, enabling seamless integration with downstream components (agent, memory, RAG) regardless of the underlying provider. This abstraction allows you to swap between local (Ollama) and cloud (OpenAI) models with minimal code changes.

## Key Features
- **Provider Agnostic**: Common interface for all LLM providers
- **Text Generation & Embeddings**: Supports both prompt-based generation and embedding APIs (for RAG/semantic search)
- **Per-Call Options**: Control temperature, max_tokens, streaming, embedding model, etc. on each call
- **Consistent Error Handling**: Standardized error handling across providers
- **Easy Extensibility**: Add new providers by subclassing the base interface

## Architecture

```
ai/
├── llm.py              # Base LLM interface
├── llm_openai.py       # OpenAI implementation
├── llm_ollama.py       # Ollama implementation
└── README-ai.md        # This documentation
```

## Base LLM Interface

```python
from typing import Dict, Any, Optional, List

class LLMService:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None, debug_generate_scope: str = "") -> str:
        """Generate a response from the LLM (supports per-call options)."""
        raise NotImplementedError

    def generate_embedding(self, text: str, options: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate an embedding vector for the given text."""
        raise NotImplementedError
```

## Ollama Implementation Example

```python
from src.ai.llm_ollama import OllamaService

llm = OllamaService({
    "base_url": "http://localhost:11434",
    "model": "gemma3",
    "temperature": 0.7
})

# Text generation
response = llm.generate("Your prompt here", options={"temperature": 0.5, "stream": False})

# Embedding generation
embedding = llm.generate_embedding("Text to embed", options={"model": "mxbai-embed-large"})
```

## OpenAI Implementation Example

```python
from src.ai.llm_openai import OpenAIService

llm = OpenAIService({
    "api_key": "your-api-key",
    "model": "gpt-4",
    "temperature": 0.7
})

# Text generation
response = llm.generate("Your prompt here", options={"temperature": 0.2, "max_tokens": 500})

# Embedding generation
embedding = llm.generate_embedding("Text to embed", options={"model": "text-embedding-ada-002"})
```

## Per-Call Options
- `temperature`: Controls randomness (0.0 to 1.0)
- `max_tokens`: Maximum response length
- `stream`: Enable/disable streaming responses
- `model`: Specify model for generation or embedding
- `debug_generate_scope`: Optional debug scope for logging

## Usage in RAG/Memory Pipeline

The LLM service is used throughout the system for:
- **Text Generation**: Generating agent responses, memory digests, and context summaries.
- **Embedding Generation**: Creating segment-level embeddings for all important memory segments, enabling semantic search and RAG (Retrieval Augmented Generation).
- **Provider-Agnostic RAG**: The memory and RAG layers use the LLM service interface, so you can swap providers (Ollama, OpenAI, etc.) without changing downstream code.

### Example: Segment-Level Embedding for RAG
```python
# Given a list of important segments:
segments = ["The party found a magical sword.", "The dragon guards the mountain pass."]
embeddings = [llm.generate_embedding(seg) for seg in segments]
# These embeddings are used for semantic search and context retrieval in RAG.
```

## Best Practices
- Use environment variables for sensitive data (API keys, etc.)
- Set sensible defaults in your config, but override per-call as needed
- Catch and handle LLMServiceError for robust error handling
- Use the same interface for both text and embedding calls

## Extensibility
- Add new providers by subclassing `LLMService` and implementing the required methods
- The rest of the system (agent, memory, RAG) is decoupled from the LLM provider

## Further Reading
- See the main project README for architectural details and advanced usage
- See `examples/embeddings_manager_example.py` and `examples/rag_enhanced_memory_example_simple.py` for real-world usage
