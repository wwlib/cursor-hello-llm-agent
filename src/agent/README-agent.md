# LLM-Driven Agent with Session Memory

A flexible, conversational agent that maintains context across multiple interactions using LLM-driven memory management.

## Overview

The Agent serves as the core orchestrator, managing conversations with users while leveraging the Memory Manager to maintain context and the LLM Service for generating responses. It's designed to be domain-agnostic but includes specialized capabilities for running tabletop RPG campaigns.

### Key Features

- **Contextual Conversations**: Maintains conversation history and context
- **Memory-Augmented Responses**: Uses structured data and knowledge graphs to inform responses
- **Multi-Phase Interactions**: Supports different interaction phases (e.g., setup, execution)
- **Domain Adaptation**: Adapts to different use cases through LLM-driven memory structuring
- **Persistent State**: Maintains conversation state across sessions

## Architecture

### Components

```
agent/
├── agent.py           # Core agent implementation
├── README.md         # This documentation
└── prompts/         # Agent prompt templates
    ├── respond.txt  # Response generation prompt
    └── reflect.txt  # Memory update reflection prompt
```

### Agent States

1. **Initialization**
   - Load configuration
   - Initialize LLM service
   - Initialize Memory Manager

2. **Learning Phase**
   - Gather domain information
   - Structure initial memory
   - Establish baseline knowledge

3. **Interaction Phase**
   - Process user input
   - Generate contextual responses
   - Update memory with new information

## Implementation

### Agent Class Structure

```python
class Agent:
    def __init__(self, llm_service, memory_manager):
        """Initialize the agent with required services"""
        self.llm = llm_service
        self.memory = memory_manager
        self.current_phase = "initialization"

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response"""
        # 1. Query memory for context
        # 2. Generate response using LLM
        # 3. Update memory with new information
        # 4. Return response

    async def learn(self, information: str) -> bool:
        """Learn new information and update memory"""
        # Process and store new information

    async def reflect(self) -> None:
        """Periodic reflection to optimize memory"""
        # Analyze and restructure memory if needed
```

## Usage

### Initialization

```python
from agent.agent import Agent
from memory.memory_manager import MemoryManager
from ai.llm import LLMService

# Initialize services
llm_service = LLMService()
memory_manager = MemoryManager(llm_service)

# Create agent
agent = Agent(llm_service, memory_manager)
```

### Basic Interaction

```python
# Process a user message
response = await agent.process_message("Tell me about the campaign world.")

# Learn new information
success = await agent.learn("The world has a new magical artifact...")

# Trigger reflection
await agent.reflect()
```

## Example: D&D Campaign Management

### Phase 1: Learning Campaign Details

```python
# Initialize with campaign setting
await agent.learn("""
The world is a simple, flat world with a single continent...
[Campaign details from README]
""")
```

### Phase 2: Character Integration

```python
# Add player characters
await agent.learn("""
The party consists of 4 players...
[Character details from README]
""")
```

### Phase 3: Campaign Execution

```python
# Start an encounter
response = await agent.process_message("The party enters the mountain cave...")
```

## LLM Prompts

### Response Generation

```text
Context:
{MEMORY_CONTEXT}

Current Phase: {PHASE}
Previous Messages: {CONVERSATION_HISTORY}

User Message: {USER_INPUT}

Generate a response that:
1. Uses relevant information from memory
2. Maintains consistency with previous interactions
3. Advances the current phase appropriately
4. Identifies any new information to be stored

Response should be in-character and appropriate for the current phase.
```

### Memory Reflection

```text
Current Memory State:
{MEMORY_JSON}

Recent Interactions:
{RECENT_MESSAGES}

Analyze the current memory state and recent interactions to:
1. Identify important patterns or relationships
2. Suggest memory structure optimizations
3. Highlight key information for future reference

Return analysis and suggested updates in JSON format.
```

## Best Practices

1. **Context Management**
   - Keep relevant context in memory
   - Prune outdated information
   - Maintain conversation coherence

2. **Response Generation**
   - Ensure consistency with memory
   - Maintain appropriate tone/style
   - Handle edge cases gracefully

3. **Memory Updates**
   - Validate new information
   - Resolve conflicts with existing data
   - Maintain knowledge graph integrity

## Future Enhancements

1. **Advanced Dialogue Management**
   - Multi-turn conversation planning
   - Goal-oriented dialogue strategies
   - Dynamic context prioritization

2. **Enhanced Learning**
   - Active learning from interactions
   - Pattern recognition in conversations
   - Automatic knowledge base expansion

3. **Performance Optimization**
   - Selective memory inclusion
   - Response caching
   - Parallel processing for reflection
