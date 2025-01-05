#!/usr/bin/env python3

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from examples.domain_configs import USER_STORY_CONFIG
from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_memory_state(memory_manager, title="Current Memory State"):
    """Helper to print memory state in a readable format"""
    print(f"\n{title}")
    print("=" * len(title))
    print(json.dumps(memory_manager.get_memory_context(), indent=2))

async def demonstrate_memory_creation():
    """Demonstrate creating initial memory structure"""
    print_section_header("Memory Creation Demo")
    
    # Initialize services
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "example_memory_debug.log",
        "debug_scope": "memory_demo"
    })
    
    # Create memory manager with test file
    memory_manager = MemoryManager(llm_service, "example_memory.json", USER_STORY_CONFIG)
    
    # Example input data
    # llm-driven-agent-with-session-memory
    input_data = """
Project Details:
- Project Name: LLM-Driven Agent with Session Memory
- Project Description: A service framework for providing lightweightmulti-use-case LLM-driven agents
- Project Features:
    - Memory Manager to manage session memory
        - Generates LLM prompts for memory management
        - Manages memory of user interactions
        - Accumulates memory datat that is important for the current use case
    - LLM Service to provide LLM services
        - Provides an interface to LLM services like Ollama and OpenAI
    - Agent to handle user interactions
        - Handles user interactions and uses the Memory Manager provde responses and remember new details
- Project Technology:
    - Python
    - Ollama
    - pytest

- Agent Role:
    - Understand the project's current features, requirements and technology
    - Receive user input about new, proposed features
    - Break new features into smaller, manageable user stories
    - Generate user stories with clear descriptions and acceptance criteria
"""
    
    # Create initial memory
    success = memory_manager.create_initial_memory(input_data)
    if success:
        print("\nInitial memory created successfully!")
        print_memory_state(memory_manager, "Initial Memory State")
    else:
        print("\nFailed to create initial memory")
    
    return memory_manager

async def demonstrate_memory_queries(memory_manager):
    """Demonstrate querying memory"""
    print_section_header("Memory Query Demo")
    
    # Example queries
    queries = [
        "New feature: Modify the memory so that it has 2 sections. One for static/read-only memory that does not change. And one for dynamic/working memory that is used to accumulate new, relevant information."
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = memory_manager.query_memory(json.dumps({"user_message": query}))
        print(f"Response: {result['response']}")
        
    print_memory_state(memory_manager, "Memory State After Queries")

async def demonstrate_memory_updates(memory_manager):
    """Demonstrate updating memory with new information"""
    print_section_header("Memory Update Demo")
    
    # Example new information
    new_info = {
        "project_update": "The project should eventually have a FastAPI API so it can be used as a REST service"
    }
    
    print("\nAdding new information:")
    print(json.dumps(new_info, indent=2))
    
    success = memory_manager.update_memory(json.dumps(new_info))
    if success:
        print("\nMemory updated successfully!")
        print_memory_state(memory_manager, "Memory State After Update")
    else:
        print("\nFailed to update memory")

async def demonstrate_memory_reflection(memory_manager):
    """Demonstrate memory reflection"""
    print_section_header("Memory Reflection Demo")
    
    # Add some conversation history
    queries = [
        "Please describe appripriate user stories to complete the proposed feature",
        "Please describe appripriate acceptance criteria for the proposed user stories",
    ]
    
    print("\nGenerating some conversation history...")
    for query in queries:
        memory_manager.query_memory(json.dumps({"user_message": query}))
    
    print("\nTriggering reflection...")
    reflection_context = {
        "operation": "reflect",
        "messages": memory_manager.memory.get("conversation_history", [])
    }
    
    success = memory_manager.update_memory(json.dumps(reflection_context))
    if success:
        print("\nReflection completed successfully!")
        print_memory_state(memory_manager, "Memory State After Reflection")
    else:
        print("\nReflection failed")

async def main():
    """Main function to run the memory manager examples"""
    try:
        # Create initial memory
        memory_manager = await demonstrate_memory_creation()
        
        # Demonstrate queries
        #await demonstrate_memory_queries(memory_manager)
        
        # Demonstrate updates
        #await demonstrate_memory_updates(memory_manager)
        
        # Demonstrate reflection
        #await demonstrate_memory_reflection(memory_manager)
        
        # Clean up
        # memory_manager.clear_memory()
        # print("\nExample completed and test memory cleared.")
        
    except Exception as e:
        print(f"\nError during example: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample ended by user.")

