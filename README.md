# LLM-Driven Agent with Session Memory

(overview written by Cursor Agent using claude-3.7-sonnet)

(This project has been vibe-coded using Cursor)

(The most recent vibe-coding history is in the .specstory directory. Earlier history is in the cursor-notes directory)

(The following is a Summary of Phase 1 - see README-phase-2.md for Phase 2 details)

This is a sophisticated framework for building domain-agnostic LLM-powered agents with persistent memory capabilities. The system is designed to maintain context across multiple sessions, organize complex information dynamically, and adapt to different domains through configuration rather than code changes.

## Core Architecture

The project is structured around three main components:

### 1. Memory Management System

At the heart of the system is a flexible, LLM-driven memory manager that uses a structured approach to organize and persist information:

- **BaseMemoryManager**: An abstract base class that defines core persistence functionality and the interface for all memory operations.

- **MemoryManager**: The primary implementation that uses LLM to dynamically organize information with a sophisticated memory structure:
  - **Static Memory**: Read-only foundational knowledge about the domain
  - **Working Memory**: Dynamic information learned during interactions
  - **Knowledge Graph**: Explicit relationships between entities
  - **Conversation History**: Complete record of all interactions
  - **Metadata**: System information like timestamps and version

- **SimpleMemoryManager**: A straightforward implementation for testing and simpler use cases that maintains a flat memory structure.

The memory manager uses prompt templates to instruct the LLM on how to structure, query, and update memory. Rather than hard-coding schemas, it allows the LLM to determine the most appropriate way to organize information based on the context.

### 2. LLM Service Layer

The system abstracts interactions with language models through a service layer:

- **OllamaService**: Connects to local LLM deployments via Ollama
- Supports both streaming and non-streaming responses
- Includes configurable debug logging for troubleshooting

### 3. Agent Layer

The agent orchestrates the interaction flow, manages conversation phases, and coordinates between the user and memory:

- **Agent**: Manages the conversation flow through distinct phases:
  - **INITIALIZATION**: Setting up initial domain knowledge
  - **LEARNING**: Acquiring new domain information
  - **INTERACTION**: Regular conversation
- Automatically triggers memory reflection after a configurable number of messages
- Maintains phase-specific handling of user inputs

## Key Features

1. **Domain Agnosticism**: The system can be adapted to different domains through configuration files rather than code changes.

2. **Persistent Memory**: All interactions are saved to disk, allowing conversations to continue across multiple sessions.

3. **Memory Reflection**: The system periodically reviews conversation history to identify and extract important information into the structured working memory.

4. **Flexible Knowledge Representation**: The memory structure is adaptable, allowing the LLM to determine the optimal organization for different domains.

5. **Robust Error Handling**: The system includes mechanisms for graceful error handling, including memory backups and recovery.

6. **Debug Logging**: Comprehensive logging of all LLM interactions with scoped outputs for easier debugging.

## Implementation Details

- **Prompt Engineering**: The system uses carefully crafted prompt templates to instruct the LLM on how to structure, query, and update memory.

- **JSON Persistence**: Memory is stored in JSON format with automatic backups created on each save operation.

- **Domain Configurations**: Different domains (like D&D campaigns or user story generation) are defined through configuration objects that include schema suggestions and domain-specific prompts.

- **Conversation History Management**: All interactions are tracked and used for both direct responses and periodic memory reflection.

## Example Use Cases

The repository includes examples demonstrating the system's versatility:

1. **D&D Campaign Management**: Creating and managing a virtual D&D campaign world, including locations, characters, and plot elements.

2. **User Story Generation**: Assisting in requirements gathering and feature planning for software projects.

3. **Basic Memory Operations**: Demonstrating direct memory creation, querying, and reflection processes.

The framework is set up to be easily extended to new domains by providing appropriate domain configurations, without needing to modify the core code.

## Technical Implementation

The project uses modern Python patterns including abstract base classes, typed interfaces, and modular design. It has a proper package structure with pyproject.toml for installation and dependencies. The code leverages asyncio for efficient handling of LLM operations and includes comprehensive error handling throughout.

The memory system demonstrates a sophisticated approach to knowledge management, using the LLM itself to determine the best way to structure and organize information rather than hard-coding schemas, which makes it highly adaptable to different domains and use cases.


## Setup and Usage

Development and testing has been done using ollama running either on a local machine or on the local LAN. The usage examples instantiate the OllamaService like:

```python
    llm_service = OllamaService({
        "base_url": "http://localhost:11434",
        "model": "llama3", // gemma3
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "agent_debug.log",
        "debug_scope": "agent_example",
        "console_output": False
    })
```


## Usage

Start ollama and have it serve a `llama3` model (or similar)

Python setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
pip install -r requirements.txt
```

Note: `The project is set up with a modern Python packaging structure using pyproject.toml, but there are a couple of things we need to do to install it correctly:`

```
First, we need to install the build dependencies
Then we can install the project in editable mode
Let me help you with the correct installation steps. I'll propose the commands to run:
pip install --upgrade pip setuptools wheel
wheel
```

Note: `Now that we have the build dependencies installed, let's install the project in editable mode:`
`pip install -e .`

If necessary...

```bash
python3 -m pip install --upgrade pip
```

Example usage:

```bash
# D&D Campaign Example - usinf the default, LLM-driven "standard" MemoryManager
python examples/agent_usage_example.py
OLLAMA_BASE_URL=http://ollama-ip-address:11434 python examples/call_ollama_to_generate_embeddings.py
OLLAMA_BASE_URL=http://192.168.1.173:11434 python examples/call_ollama_to_generate_embeddings.py

# Test Ollama
OLLAMA_BASE_URL=http://ollama-ip-address:11434 python examples/call_ollama.py
OLLAMA_BASE_URL=http://192.168.1.173:11434 python examples/call_ollama.py

# Test Ollama Embeddings
OLLAMA_BASE_URL=http://ollama-ip-address:11434 python examples/call_ollama_to_generate_embeddings.py
OLLAMA_BASE_URL=http://192.168.1.173:11434 python examples/call_ollama_to_generate_embeddings.py

# Test MemoryManager
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_LLM_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large pytest tests/memory_manager/test_memory_manager_integration.py -v -s

# Test Data Preprocessor
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_LLM_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large pytest tests/memory_manager/test_data_preprocessor_integration.py -v -s

# D&D Campaign Example - using the simple memory manager
python examples/agent_usage_example.py --type simple

# User Story Generation Example
python examples/user_story_example.py

# Memory Manager Example
python examples/memory_manager_usage_example.py

# Embedding Manager Example
OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large  python examples/embeddings_manager_example.py

# RAG Manager Example
OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/rag_enhanced_memory_example.py
```