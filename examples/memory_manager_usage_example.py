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

from src.utils.logging_config import LoggingConfig
from examples.domain_configs import USER_STORY_CONFIG
from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager

# Configuration - use environment variables with sensible defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Base directory for all example memory files
EXAMPLE_BASE_DIR = "agent_memories/standard/memory_manager_usage_example"
os.makedirs(EXAMPLE_BASE_DIR, exist_ok=True)

def get_memory_file_path(filename):
    """Get the full path for a memory file in the example directory"""
    return os.path.join(EXAMPLE_BASE_DIR, filename)

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
    
    # Use a fixed example GUID for this standalone example
    EXAMPLE_GUID = "memory_creation_example"
    
    # Set up logging using LoggingConfig
    general_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_general",
        log_to_console=False
    )
    digest_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_digest",
        log_to_console=False
    )
    embeddings_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_embeddings",
        log_to_console=False
    )
    memory_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "memory_manager",
        log_to_console=False
    )
    
    # Initialize LLM services
    print("\nInitializing LLM services...")
    
    # General query service
    general_llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "stream": False,
        "logger": general_logger
    })
    
    # Digest generation service
    digest_llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "stream": False,
        "logger": digest_logger
    })
    
    # Initialize embeddings service
    embeddings_llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "logger": embeddings_logger
    })
    
    # Create memory manager (memory_guid is first parameter)
    guid = EXAMPLE_GUID
    memory_file = get_memory_file_path(f"memory_{guid}.json")
    memory_manager = MemoryManager(
        memory_guid=guid,
        memory_file=memory_file,
        domain_config=USER_STORY_CONFIG,
        llm_service=general_llm_service,
        digest_llm_service=digest_llm_service,
        embeddings_llm_service=embeddings_llm_service,
        logger=memory_logger
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
    
    success = memory_manager.create_initial_memory(input_data)
    if success:
        print("Initial memory created successfully")
    else:
        print("Failed to create initial memory")
        return
    
    # Query the memory
    print("\nQuerying memory...")
    query = "Tell me about the party members and their current mission"
    response = memory_manager.query_memory({"query": query})
    print(f"\nQuery: {query}")
    print(f"Response: {response.get('response', 'No response')}")
    
    # Wait a bit for async processing to complete
    await asyncio.sleep(1)
    
    # Update the memory (compression)
    print("\nUpdating memory (compressing conversation history)...")
    # Note: update_memory compresses conversation history, it doesn't add new content directly
    # To add new content, we'd add it to conversation history first
    update_context = {"operation": "update"}
    success = memory_manager.update_memory(update_context)
    if success:
        print("Memory updated (compressed) successfully")
    else:
        print("Memory update failed")
    
    # Query again
    print("\nQuerying updated memory...")
    query = "What have they learned about the necromancer and what do they need to do?"
    response = memory_manager.query_memory({"query": query})
    print(f"\nQuery: {query}")
    print(f"Response: {response.get('response', 'No response')}")
    
    # Wait for async processing to complete
    await asyncio.sleep(1)
    
    print(f"\nMemory file saved to: {memory_file}")
    print(f"Logs saved to: {LoggingConfig.get_log_base_dir(EXAMPLE_GUID)}")

async def demonstrate_multiple_memories():
    """Demonstrate working with multiple memory files using GUIDs"""
    print_section_header("Multiple Memories Demo")
    
    # Use fixed GUIDs for this example
    EXAMPLE_GUID_1 = "multiple_memories_example_1"
    EXAMPLE_GUID_2 = "multiple_memories_example_2"
    
    # Set up logging
    llm_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID_1,
        "ollama",
        log_to_console=False
    )
    memory_logger_1 = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID_1,
        "memory_manager",
        log_to_console=False
    )
    memory_logger_2 = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID_2,
        "memory_manager",
        log_to_console=False
    )
    
    # Initialize service
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "stream": False,
        "logger": llm_logger
    })
    
    # Create first memory
    guid1 = EXAMPLE_GUID_1
    print(f"Creating first memory with GUID: {guid1}")
    memory_file_1 = get_memory_file_path("example_memory_1.json")
    memory1 = MemoryManager(
        memory_guid=guid1,
        memory_file=memory_file_1,
        domain_config=USER_STORY_CONFIG,
        llm_service=llm_service,
        logger=memory_logger_1
    )
    
    # Create initial memory structure
    success1 = memory1.create_initial_memory("This is the first memory file about Project A.")
    if success1:
        print(f"Memory 1 created with GUID: {memory1.get_memory_guid()}")
    else:
        print("Failed to create memory 1")
    
    # Create second memory 
    guid2 = EXAMPLE_GUID_2
    print(f"Creating second memory with GUID: {guid2}")
    memory_file_2 = get_memory_file_path("example_memory_2.json")
    memory2 = MemoryManager(
        memory_guid=guid2,
        memory_file=memory_file_2,
        domain_config=USER_STORY_CONFIG,
        llm_service=llm_service,
        logger=memory_logger_2
    )
    
    # Create initial memory structure
    success2 = memory2.create_initial_memory("This is the second memory file about Project B.")
    if success2:
        print(f"Memory 2 created with GUID: {memory2.get_memory_guid()}")
    else:
        print("Failed to create memory 2")
    
    # Show both memories
    print("\nMemory 1:")
    print_memory_state(memory1, "Memory 1 State")
    
    print("\nMemory 2:")
    print_memory_state(memory2, "Memory 2 State")
    
    return guid1, guid2

async def demonstrate_load_memory_by_guid(guid):
    """Demonstrate loading a specific memory by GUID"""
    print_section_header(f"Loading Memory with GUID: {guid}")
    
    # Set up logging
    llm_logger = LoggingConfig.get_component_file_logger(
        guid,
        "ollama",
        log_to_console=False
    )
    memory_logger = LoggingConfig.get_component_file_logger(
        guid,
        "memory_manager",
        log_to_console=False
    )
    
    # Initialize service
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "stream": False,
        "logger": llm_logger
    })
    
    # Determine which file to load based on the GUID
    memory_file = None
    
    # Check both files in the example directory to find the matching GUID
    for filename in ["example_memory_1.json", "example_memory_2.json"]:
        file_path = get_memory_file_path(filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get("guid") == guid:
                        memory_file = file_path
                        break
        except Exception:
            pass
    
    if not memory_file:
        print(f"Error: Could not find memory file with GUID: {guid}")
        return None
    
    print(f"Loading memory from file: {memory_file}")
    
    # Load the memory with the specified GUID
    memory_manager = MemoryManager(
        memory_guid=guid,
        memory_file=memory_file,
        domain_config=USER_STORY_CONFIG,
        llm_service=llm_service,
        logger=memory_logger
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
        result = memory_manager.query_memory({"query": query})
        print(f"Response: {result.get('response', 'No response')}")
        
    # Wait for async processing
    await asyncio.sleep(1)
        
    print_memory_state(memory_manager, "Memory State After Queries")

async def demonstrate_memory_updates(memory_manager):
    """Demonstrate updating memory with compression"""
    print_section_header("Memory Update Demo")
    
    # Add some conversation history first by querying
    print("\nAdding conversation history by making queries...")
    queries = [
        "The project should eventually have a FastAPI API so it can be used as a REST service"
    ]
    
    for query in queries:
        memory_manager.query_memory({"query": query})
    
    # Wait for async processing
    await asyncio.sleep(1)
    
    print("\nCompressing conversation history...")
    update_context = {"operation": "update"}
    success = memory_manager.update_memory(update_context)
    if success:
        print("\nMemory updated (compressed) successfully!")
        print_memory_state(memory_manager, "Memory State After Update")
    else:
        print("\nFailed to update memory")

async def demonstrate_memory_reflection(memory_manager):
    """Demonstrate memory reflection (compression after queries)"""
    print_section_header("Memory Reflection Demo")
    
    # Add some conversation history
    queries = [
        "Please describe appropriate user stories to complete the proposed feature",
        "Please describe appropriate acceptance criteria for the proposed user stories",
    ]
    
    print("\nGenerating some conversation history...")
    for query in queries:
        memory_manager.query_memory({"query": query})
    
    # Wait for async processing
    await asyncio.sleep(1)
    
    print("\nTriggering compression (reflection)...")
    update_context = {"operation": "update"}
    success = memory_manager.update_memory(update_context)
    if success:
        print("\nCompression completed successfully!")
        print_memory_state(memory_manager, "Memory State After Compression")
    else:
        print("\nCompression failed")

async def main():
    """Main function to run the memory manager examples"""
    try:
        # Create initial memory
        await demonstrate_memory_creation()
        
        # Demonstrate multiple memories
        guid1, guid2 = await demonstrate_multiple_memories()
        
        # Demonstrate loading memory by GUID
        loaded_memory = await demonstrate_load_memory_by_guid(guid2)
        if loaded_memory is None:
            print("Failed to load memory, skipping query demo")
            return
        
        # Demonstrate queries on loaded memory
        await demonstrate_memory_queries(loaded_memory)
        
        # Demonstrate updates
        # await demonstrate_memory_updates(loaded_memory)
        
        # Demonstrate reflection
        # await demonstrate_memory_reflection(loaded_memory)
        
        print(f"\nAll memory files saved to: {EXAMPLE_BASE_DIR}")
        print("(No cleanup needed - files are organized in the example directory)")
        
    except Exception as e:
        print(f"\nError during example: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample ended by user.")