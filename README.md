# llm-driven-agent-with-session-memory

This is a simple example of a LLM-driven agent with session memory.

All of the code in this repo was written by cursor using instructions from the `README-initial-cursor-instructions.md` file.

A complete history of the cursor sessions is in the `cursor-notes/` directory.

The process - so far - is documented in the `cursor-notes/` directory:

- NOTES-initial-readmes.md
- NOTES-composer-memory-manager.md
- NOTES-composer-agent.md

Complete transcripts of the cursor chat and composer sessions are in the `cursor-notes/cursor-chat-and-composer-transcripts/` directory. These transcripts were exported using the [SpecStory](https://specstory.com/) extension for cursor:

- Chat - Designing a Memory Manager for Campaign Data.md
- Chat - Fixing AssertionError in Python Test.md
- Chat - Resolving Skipped Asyncio Tests.md

- Composer - MemoryManager Code and Testing Implementation.md
- Composer - Fixing ModuleNotFoundError in pytest.md
- Composer - Creating Detailed README for Agent.md

Cursor wrote the subsystem readmes and then wrote the code for the `LLMService`, `MemoryManager` and `Agent` classes:

- src/agent/README-agent.md
- src/memory/README-memory-manager.md
- src/ai/README-ai.md

Development and testing has been done using ollama running either on a local machine or on the local LAN. The usage examples instantiate the OllamaService like:

```python
    llm_service = OllamaService({
        "base_url": "http://localhost:11434",
        "model": "llama3",
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
pip install -r requirements.txt
```
If necessary...

```bash
python3 -m pip install --upgrade pip
```

Example usage

```bash
python scripts/agent_usage_example.py
```

See: `cursor-notes/data/agent-usage-example/agent_interaction_transcript_jan3.txt` for a transcript of an example interaction.


## Architecture Overview

The project implements a LLM-driven agent with persistent memory, designed around three main components:

### 1. LLM Service Layer (`src/ai/`)
- Base `LLMService` class defining the interface for LLM interactions
- `OllamaService` implementation for local LLM deployment
- Supports both streaming and non-streaming responses
- Configurable debug logging with scoped output
- Error handling and response validation

### 2. Memory Management (`src/memory/`)
- `MemoryManager` class handling persistent memory in JSON format
- Memory structure includes:
  - `structured_data`: Organized facts about the world/campaign
  - `knowledge_graph`: Relationships between entities
  - `conversation_history`: Complete interaction history
  - `metadata`: Phase tracking and timestamps
- Automatic memory reflection after every 10 messages
- Memory backups created on each save operation

### 3. Agent Layer (`src/agent/`)
- Main `Agent` class orchestrating interactions
- Manages conversation phases:
  - INITIALIZATION: Setting up the world/campaign
  - LEARNING: Acquiring new information
  - INTERACTION: Regular conversation
- Delegates memory operations to MemoryManager
- Handles phase transitions and message processing

### Key Features
- Persistent memory across sessions
- Automatic memory consolidation through reflection
- Graceful error handling and recovery
- Detailed debug logging with operation scopes
- Memory backups for troubleshooting
- Efficient LLM usage (combined query/update operations)

### Example Implementation
The repository includes a D&D campaign example that demonstrates:
- Campaign world initialization
- NPC and quest management
- Interactive storytelling
- Memory persistence and reflection
- Natural conversation handling

The system is designed to be extensible for other use cases beyond D&D campaigns, with the core components providing a general framework for LLM-driven agents with memory.
