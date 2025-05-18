#!/usr/bin/env python3

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
import sys
import os

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
    memory = memory_manager.get_memory()
    print(f"Memory GUID: {memory_manager.get_memory_guid()}")
    print(json.dumps(memory, indent=2))

async def demonstrate_memory_creation():
    """Demonstrate creating and using memory with the MemoryManager"""
    print("\n=== Memory Creation Example ===")
    
    # Create logs directory structure
    logs_dir = os.path.join(project_root, "logs")
    guid = str(uuid.uuid4())
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    print(f"Logs directory: {guid_logs_dir}")
    
    # Create separate debug files for each service within the GUID directory
    general_debug_file = os.path.join(guid_logs_dir, "general.log")
    digest_debug_file = os.path.join(guid_logs_dir, "digest.log")
    embed_debug_file = os.path.join(guid_logs_dir, "embed.log")
    
    print(f"Debug log files:")
    print(f"  General: {general_debug_file}")
    print(f"  Digest: {digest_debug_file}")
    print(f"  Embed: {embed_debug_file}")
    
    # Initialize LLM services
    print("\nInitializing LLM services...")
    
    # General query service
    general_llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": general_debug_file,
        "debug_scope": "memory_example_general"
    })
    
    # Digest generation service
    digest_llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": digest_debug_file,
        "debug_scope": "memory_example_digest"
    })
    
    # Initialize embeddings service
    embeddings_llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "mxbai-embed-large",
        "debug": False,
        "debug_file": embed_debug_file  # Still specify the file even though logging is disabled
    })
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_file=f"memory_{guid}.json",
        domain_config=USER_STORY_CONFIG,
        llm_service=general_llm_service,
        digest_llm_service=digest_llm_service,
        embeddings_llm_service=embeddings_llm_service,
        memory_guid=guid
    )
    
    # Create initial memory
    print("\nCreating initial memory...")
    input_data = """
    The party consists of:
    - A human fighter named Thorne who wields a magical greatsword
    - An elven wizard named Elara who specializes in fire magic
    - A dwarven cleric named Durin who worships Moradin
    - A halfling rogue named Pip who is an expert lockpick
    
    They are currently in the town of Winterhaven, investigating rumors of undead in the nearby ruins.
    The town's mayor, Padraig, has offered a reward for clearing out the ruins.
    The party has learned that the ruins were once a temple to Orcus, and the undead are likely being raised by a necromancer.
    """
    
    await memory_manager.create_memory(input_data)
    print("Initial memory created successfully")
    
    # Query the memory
    print("\nQuerying memory...")
    query = "Tell me about the party members and their current mission"
    response = await memory_manager.query_memory(query)
    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    
    # Update the memory
    print("\nUpdating memory...")
    update_data = """
    The party has discovered that the necromancer is a former priest of Orcus named Kalarel.
    He is using a portal to the Shadowfell to raise undead.
    The party needs to find the key to the portal, which is hidden in the temple's crypt.
    """
    
    await memory_manager.update_memory(update_data)
    print("Memory updated successfully")
    
    # Query again
    print("\nQuerying updated memory...")
    query = "What have they learned about the necromancer and what do they need to do?"
    response = await memory_manager.query_memory(query)
    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    
    # Clean up
    print("\nCleaning up...")
    if os.path.exists(memory_manager.memory_file):
        os.remove(memory_manager.memory_file)
    print("Memory file removed")

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
        await demonstrate_memory_creation()
        
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

