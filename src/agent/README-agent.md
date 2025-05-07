# LLM-Driven Agent (Phase-Orchestrator)

A modern, domain-agnostic conversational agent that leverages RAG-enabled, segment-based memory for persistent, context-rich interactions.

## Overview

The Agent serves as a thin orchestrator, managing conversation phases and delegating all memory operations to the MemoryManager. It is designed to be:
- **Domain-agnostic**: Behavior is controlled via configuration, not code changes.
- **Extensible**: Easily adapted to new domains or memory strategies.
- **RAG-Enabled**: Works with a memory system that supports segment-level embeddings and semantic search for Retrieval Augmented Generation (RAG).

## Key Features

- **Phase-Driven Conversation**: The agent manages three phases:
  - **INITIALIZATION**: Set up initial domain knowledge.
  - **LEARNING**: Acquire new information and expand memory.
  - **INTERACTION**: Ongoing conversation and Q&A.
- **Delegation to MemoryManager**: All memory creation, update, compression, and retrieval is handled by the memory manager (including RAG and semantic search).
- **Persistent, Contextual Memory**: Memory is automatically compressed and organized for efficient, long-running sessions.
- **Separation of Concerns**: The agent does not manage memory structure or reflection—this is fully encapsulated in the memory layer.

## Architecture

### Components
```
agent/
├── agent.py           # Core agent implementation
├── README-agent.md    # This documentation
```

### Agent Phases
1. **INITIALIZATION**: Load configuration, initialize LLM and memory manager, seed static knowledge.
2. **LEARNING**: Add new domain information to memory.
3. **INTERACTION**: Process user input, generate responses, and update memory.

## Implementation

### Agent Class Structure (Simplified)
```python
class Agent:
    def __init__(self, llm_service, memory_manager, domain_name="general"):
        self.llm = llm_service
        self.memory = memory_manager
        self.domain_name = domain_name
        self.current_phase = AgentPhase.INITIALIZATION

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response (memory/RAG handled automatically)."""
        response = self.memory.query_memory({"query": message})
        if self.current_phase == AgentPhase.INITIALIZATION:
            self.current_phase = AgentPhase.INTERACTION
        return response.get("response", str(response))

    async def learn(self, information: str) -> bool:
        """Learn new information and update memory."""
        if self.current_phase == AgentPhase.INITIALIZATION:
            success = self.memory.create_initial_memory(information)
            if success:
                self.current_phase = AgentPhase.LEARNING
            return success
        else:
            return self.memory.update_memory({"operation": "update", "learning_content": information})
```

## Usage Example

```python
from src.agent.agent import Agent
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

# Initialize LLM and memory manager
llm_service = OllamaService({
    "base_url": "http://localhost:11434",
    "model": "gemma3",
    "temperature": 0.7
})
memory_manager = MemoryManager(llm_service=llm_service)

# Create agent
agent = Agent(llm_service, memory_manager)

# Async usage
import asyncio
async def main():
    await agent.learn("The world is a flat world with a single continent...")
    response = await agent.process_message("Tell me about the campaign world.")
    print(response)

asyncio.run(main())
```

## Best Practices
- **Let the MemoryManager handle all memory logic**: The agent should not manipulate memory structure or perform reflection/compression directly.
- **Use domain configuration for specialization**: Adapt the agent to new domains by providing a new config file.
- **Leverage RAG and semantic search**: The agent automatically benefits from RAG-enabled memory—no special logic required.
- **Keep the agent stateless regarding memory**: All persistent state is managed by the memory manager.

## Extensibility
- **Add new domains** by providing a new config file.
- **Swap LLM providers** by changing the LLM service instantiation.
- **Extend memory or RAG** by subclassing the relevant manager.

## Further Reading
- See the main project README for architectural details and advanced usage.
- See `examples/rag_enhanced_memory_example_simple.py` for a canonical RAG workflow.
