# Memory Manager for LLM-Driven Agent

A flexible, LLM-driven approach to managing structured data and knowledge graphs for conversational agents.

## Overview

The Memory Manager uses LLM prompts to structure, query, and update memory without imposing predefined data schemas. Instead of hard-coding data structures, it allows the LLM to determine the most appropriate way to organize information based on the context and requirements.

### Key Features

- **Dynamic Data Structuring**: LLM determines optimal data organization
- **Flexible Knowledge Representation**: Adapts to any domain or use case
- **Prompt-Driven Operations**: All memory operations handled via LLM prompts
- **Persistent Storage**: Automatic JSON-based file storage
- **Session Management**: Maintains context across conversations

## Architecture

### Components

```
memory/
├── memory_manager.py     # Core memory management functionality
├── README.md            # This documentation
└── prompts/            # LLM prompt templates
    ├── create.txt      # Initial memory structure prompt
    ├── query.txt       # Memory query prompt
    └── update.txt      # Memory update prompt
```

### Memory Structure

The memory is stored as a JSON object with three main sections:

```json
{
    "structured_data": {
        // LLM-defined structure for facts and details
    },
    "knowledge_graph": {
        // LLM-defined structure for relationships
    },
    "metadata": {
        "categories": [],
        "timestamp": "",
        "version": "1.0",
        "created_at": "",
        "last_updated": ""
    }
}
```

## Usage

### Initialization

```python
from memory.memory_manager import MemoryManager
from ai.llm import LLMService

llm_service = LLMService()
memory_manager = MemoryManager(llm_service)
```

### Creating Initial Memory

```python
# Provide initial data
initial_data = """
[Your campaign or domain data here]
"""

# LLM will structure this into appropriate memory format
memory_manager.create_initial_memory(initial_data)
```

### Accessing Memory

```python
# Get full memory context
context = memory_manager.get_memory_context()
```

## LLM Prompts

### Create Memory Prompt

Used to establish initial memory structure:

```text
You are a memory management system. Your task is to analyze the provided information 
and create two organized data structures:

1. A structured_data JSON object to store key facts and details
2. A knowledge_graph JSON object to map relationships between entities

Input Data:
{INPUT_DATA}

Requirements:
- Structure the data in a way that will be useful for the specific domain
- Include all relevant information from the input
- Create meaningful relationships in the knowledge graph
- Use consistent naming and structure that can be extended in future updates
- Include metadata about data categories to help with future queries

Return only a valid JSON object...
```

### Query Memory Prompt (Planned)

Used to retrieve relevant information:

```text
Given this memory context: {MEMORY_JSON}
And this query: {QUERY}
Provide a response using the stored information.
```

### Update Memory Prompt (Planned)

Used to incorporate new information:

```text
Given this memory context: {MEMORY_JSON}
And this new information: {NEW_DATA}
Return updated JSON structures that incorporate the new information.
```

## Implementation Approach

1. **Initial Memory Creation**
   - Receive raw input data
   - Use LLM to structure into JSON format
   - Store structured data and relationships
   - Maintain metadata about the structure

2. **Memory Queries**
   - Include full memory context in prompt
   - Let LLM determine relevant information
   - Return formatted response

3. **Memory Updates**
   - Include current memory and new data in prompt
   - LLM determines how to merge/update information
   - Save updated structure

## Best Practices

1. **Prompt Design**
   - Be explicit about expected output format
   - Include examples where helpful
   - Specify requirements clearly

2. **Error Handling**
   - Validate LLM responses
   - Handle JSON parsing errors
   - Maintain data consistency

3. **Performance**
   - Only include relevant context in prompts
   - Cache frequently accessed data
   - Optimize file I/O operations

## Future Enhancements

1. **Memory Pruning**
   - LLM-driven relevance assessment
   - Automatic cleanup of outdated information

2. **Version Control**
   - Track memory changes over time
   - Ability to rollback to previous states

3. **Multi-Session Support**
   - Handle multiple concurrent conversations
   - Session isolation and management

## Proposed memory_manager.py - draft

```python
from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class MemoryManager:
    def __init__(self, llm_service, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.llm = llm_service
        self.memory: Dict[str, Any] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        """Load memory from JSON file if it exists"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                self.memory = json.load(f)

    def save_memory(self) -> None:
        """Save current memory state to JSON file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)

    def create_initial_memory(self, input_data: str) -> None:
        """Use LLM to structure initial input data into memory format"""
        create_memory_prompt = """
You are a memory management system. Your task is to analyze the provided campaign information and create two organized data structures:

1. A structured_data JSON object to store key facts and details
2. A knowledge_graph JSON object to map relationships between entities

Input Data:
{INPUT_DATA}

Requirements:
- Structure the data in a way that will be useful for a D&D campaign management system
- Include all relevant information from the input
- Create meaningful relationships in the knowledge graph
- Use consistent naming and structure that can be extended in future updates
- Include metadata about data categories to help with future queries

Return only a valid JSON object with this structure:
{
    "structured_data": {
        // Your structured organization of the facts and details
    },
    "knowledge_graph": {
        // Your graph of relationships between entities
    },
    "metadata": {
        "categories": [],
        "timestamp": "",
        "version": "1.0"
    }
}

Important: Return ONLY the JSON object, with no additional explanation or text."""

        # Get structured memory from LLM
        prompt = create_memory_prompt.replace("{INPUT_DATA}", input_data)
        try:
            llm_response = self.llm.generate(prompt)
            memory_data = json.loads(llm_response)
            
            # Add system metadata
            memory_data["metadata"]["created_at"] = datetime.now().isoformat()
            memory_data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.memory = memory_data
            self.save_memory()
            return True
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error creating memory structure: {str(e)}")
            return False

    def get_memory_context(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
```
