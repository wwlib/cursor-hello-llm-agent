#!/usr/bin/env python3

import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager

def print_memory_state(memory_manager, title="Current Memory State"):
    """Helper to print memory state in a readable format"""
    print(f"\n{title}")
    print("=" * len(title))
    print(json.dumps(memory_manager.get_memory_context(), indent=2))

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

async def main():
    """Example of using MemoryManager with Ollama."""
    
    print("Initializing Memory Manager...")
    
    # Initialize services
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",  # Update to match your Ollama server
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "memory_manager_debug.log",
        "debug_scope": "memory_manager_example",
        "console_output": False
    })
    
    memory_file = "example_memory.json"
    memory_manager = MemoryManager(llm_service, memory_file)
    
    # Phase 1: Create Initial Memory
    print("\nPhase 1: Creating Initial Memory...")
    initial_data = """Please structure the following campaign information into a JSON format with structured_data for facts, knowledge_graph for relationships, and appropriate metadata.

Campaign Setting: The Lost Valley

World Details:
- Hidden valley surrounded by impassable mountains
- Ancient ruins scattered throughout
- Mysterious magical anomalies
- Three main settlements: Haven (central), Riverwatch (east), Mountainkeep (west)

Current Situation:
- Strange creatures emerging from the ruins
- Trade routes between settlements disrupted
- Ancient artifacts being discovered
- Local guilds seeking adventurers

Key NPCs:
- Mayor Elena of Haven (quest giver)
- Master Scholar Theron (knowledge about ruins)
- Captain Sara of Riverwatch (military leader)"""
    
    success = memory_manager.create_initial_memory(initial_data)
    if not success:
        print("Failed to create initial memory!")
        return
    
    print_memory_state(memory_manager, "Initial Memory Created")
    
    # Phase 2: Query Memory
    print("\nPhase 2: Testing Memory Queries...")
    
    # Example query about the world
    query_context = {
        "current_phase": "INTERACTION",
        "user_message": "Tell me about the settlements in the valley."
    }
    
    print("\nQuerying about settlements...")
    result = memory_manager.query_memory(json.dumps(query_context))
    print("\nQuery Result:")
    print(json.dumps(result, indent=2))
    
    # Phase 3: Update Memory with New Information
    print("\nPhase 3: Testing Memory Updates...")
    
    # Add new information about the ruins
    update_context = {
        "operation": "reflect",
        "message": {
            "role": "user",
            "content": """New discoveries about the ruins:
            - Glowing runes found on ancient doorways
            - Evidence of an advanced civilization
            - Strange energy readings detected by scholars
            - Hidden chambers discovered beneath the surface""",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    print("\nUpdating memory with new information about ruins...")
    success = memory_manager.update_memory(json.dumps(update_context))
    if success:
        print("Memory updated successfully")
        print_memory_state(memory_manager, "Memory After Update")
    else:
        print("Failed to update memory!")
    
    # Phase 4: Memory Reflection
    print("\nPhase 4: Testing Memory Reflection...")
    
    # Add some conversation history to trigger reflection
    for i in range(10):
        query_context = {
            "current_phase": "INTERACTION",
            "user_message": f"Test message {i+1} about the valley"
        }
        memory_manager.query_memory(json.dumps(query_context))
    
    # Trigger reflection
    reflection_context = {
        "operation": "reflect",
        "message": {
            "role": "system",
            "content": "Reflection triggered",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    print("\nPerforming memory reflection...")
    success = memory_manager.update_memory(json.dumps(reflection_context))
    if success:
        print("Reflection completed successfully")
        print_memory_state(memory_manager, "Memory After Reflection")
    else:
        print("Failed to complete reflection!")
    
    # Clean up
    print("\nCleaning up...")
    memory_manager.clear_memory()
    print("Memory cleared.")

if __name__ == "__main__":
    print_section_header("Memory Manager Usage Example")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample ended by user.")
    except Exception as e:
        print(f"\nError during example: {str(e)}")
    finally:
        print("\nExample completed.") 