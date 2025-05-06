#!/usr/bin/env python3

import asyncio
import json
import uuid
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
    memory_context = memory_manager.get_memory_context()
    print(f"Memory GUID: {memory_manager.get_memory_guid()}")
    print(json.dumps(memory_context, indent=2))

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
    
    # Create memory manager with test file and a specific GUID
    demo_guid = str(uuid.uuid4())
    print(f"Using predefined GUID for new memory: {demo_guid}")
    
    memory_manager = MemoryManager(
        llm_service=llm_service, 
        memory_file="example_memory.json", 
        domain_config=USER_STORY_CONFIG, 
        memory_guid=demo_guid
    )
    
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
    
    return memory_manager, demo_guid

async def demonstrate_multiple_memories():
    """Demonstrate working with multiple memory files using GUIDs"""
    print_section_header("Multiple Memories Demo")
    
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
    
    # Create first memory
    guid1 = str(uuid.uuid4())
    print(f"Creating first memory with GUID: {guid1}")
    memory1 = MemoryManager(
        llm_service=llm_service, 
        memory_file="example_memory_1.json", 
        domain_config=USER_STORY_CONFIG, 
        memory_guid=guid1
    )
    
    # Create initial memory structure
    success1 = memory1.create_initial_memory("This is the first memory file about Project A.")
    if success1:
        print(f"Memory 1 created with GUID: {memory1.get_memory_guid()}")
    
    # Create second memory 
    guid2 = str(uuid.uuid4())
    print(f"Creating second memory with GUID: {guid2}")
    memory2 = MemoryManager(
        llm_service=llm_service,
        memory_file="example_memory_2.json",
        domain_config=USER_STORY_CONFIG,
        memory_guid=guid2
    )
    
    # Create initial memory structure
    success2 = memory2.create_initial_memory("This is the second memory file about Project B.")
    if success2:
        print(f"Memory 2 created with GUID: {memory2.get_memory_guid()}")
    
    # Show both memories
    print("\nMemory 1:")
    print_memory_state(memory1, "Memory 1 State")
    
    print("\nMemory 2:")
    print_memory_state(memory2, "Memory 2 State")
    
    return guid1, guid2

async def demonstrate_load_memory_by_guid(guid):
    """Demonstrate loading a specific memory by GUID"""
    print_section_header(f"Loading Memory with GUID: {guid}")
    
    # Initialize service
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "example_memory_debug.log",
        "debug_scope": "memory_demo"
    })
    
    # In a real application, you might look up the file by GUID in a registry
    # For this example, we'll use hardcoded values based on the previous demo
    
    # Determine which file to load based on the GUID
    # This is a placeholder for a real GUID-to-filename mapping system
    memory_file = "example_memory_1.json"  # Default
    if guid.endswith(guid[-6:]):  # Simple check, would be more robust in production
        # Check both files to find the matching GUID
        try:
            with open("example_memory_1.json", 'r') as f:
                data = json.load(f)
                if data.get("guid") == guid:
                    memory_file = "example_memory_1.json"
        except Exception:
            pass
            
        try:
            with open("example_memory_2.json", 'r') as f:
                data = json.load(f)
                if data.get("guid") == guid:
                    memory_file = "example_memory_2.json"
        except Exception:
            pass
    
    print(f"Loading memory from file: {memory_file}")
    
    # Load the memory with the specified GUID
    memory_manager = MemoryManager(
        llm_service=llm_service,
        memory_file=memory_file,
        domain_config=USER_STORY_CONFIG,
        memory_guid=guid  # Specify the expected GUID
    )
    
    # Check if loaded correctly
    loaded_guid = memory_manager.get_memory_guid()
    if loaded_guid == guid:
        print(f"Successfully loaded memory with GUID: {loaded_guid}")
        print_memory_state(memory_manager, "Loaded Memory State")
    else:
        print(f"Warning: Loaded memory has different GUID. Expected {guid}, got {loaded_guid}")
    
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
        memory_manager, demo_guid = await demonstrate_memory_creation()
        
        # Demonstrate multiple memories
        guid1, guid2 = await demonstrate_multiple_memories()
        
        # Demonstrate loading memory by GUID
        loaded_memory = await demonstrate_load_memory_by_guid(guid2)
        
        # Demonstrate queries on loaded memory
        await demonstrate_memory_queries(loaded_memory)
        
        # Demonstrate updates
        # await demonstrate_memory_updates(memory_manager)
        
        # Demonstrate reflection
        # await demonstrate_memory_reflection(memory_manager)
        
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

