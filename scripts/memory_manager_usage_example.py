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

async def main():
    """Example of using MemoryManager with Ollama."""
    
    print("Initializing Memory Manager...")
    
    # Initialize services
    llm_service = OllamaService({
        "base_url": "http://localhost:11434",
        "model": "llama3",  # or another model you have installed
        "temperature": 0.7,
        "stream": False,  # Disable streaming for simpler response handling
        "debug": True,  # Enable debug logging
        "debug_file": "memory_manager_debug.log",  # Specify debug log file
        "log_chunks": False,  # Disable verbose chunk logging
        "console_output": False  # Enable console output for easier debugging
    })
    
    memory_file = "example_memory.json"
    memory_manager = MemoryManager(llm_service, memory_file)
    
    # Phase 1: Create Initial Memory
    print("\nPhase 1: Creating Initial Memory...")
    initial_data = """
    
This is a D&D campaign world with the following details:
    
World Structure:
- Type: Flat world
- Geography: Single continent with one ocean and mountain range
- Scale: Medium-sized continent with varied terrain

Population:
- Primary Inhabitants: Humanoid creatures
- Government: Benevolent monarchy
- Current State: Generally peaceful

Current Conflict:
- Threat: Mountain Troll
- Location: Mountain cave near village
- Impact: Attacking local village
- Quest Reward: 1000 gold coins for troll elimination

Please structure this information into a JSON format with structured_data for facts, knowledge_graph for relationships, and appropriate metadata."""
    
    success = memory_manager.create_initial_memory(initial_data)
    if not success:
        print("Failed to create initial memory!")
        return
    
    print_memory_state(memory_manager, "Initial Memory Created")
    
    # Phase 2: Query Memory
    print("\nPhase 2: Testing Memory Queries...")
    
    # Example query about the world
    query_context = {
        "current_phase": "LEARNING",
        "recent_messages": [
            {
                "role": "user",
                "content": "Tell me about the world.",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "user_message": "Tell me about the world."
    }
    
    print("\nQuerying about the world...")
    result = memory_manager.query_memory(json.dumps(query_context))
    print("\nQuery Result:")
    print(json.dumps(result, indent=2))
    
    # Phase 3: Update Memory with New Information
    print("\nPhase 3: Testing Memory Updates...")
    
    # Add new information about the troll
    update_context = {
        "phase": "LEARNING",
        "information": """
        New information about the Mountain Troll:
        - Recently seen near the village's eastern farms
        - Described as 12 feet tall with grey skin
        - Known to be afraid of fire
        - Has been stealing livestock at night
        """,
        "recent_history": [
            {
                "role": "user",
                "content": "What have the villagers learned about the troll?",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    print("\nUpdating memory with troll information...")
    success = memory_manager.update_memory(json.dumps(update_context))
    if success:
        print("Memory updated successfully")
        print_memory_state(memory_manager, "Memory After Update")
    else:
        print("Failed to update memory!")
    
    # Phase 4: Memory Reflection
    print("\nPhase 4: Testing Memory Reflection...")
    
    reflection_context = {
        "phase": "INTERACTION",
        "recent_history": [
            {
                "role": "user",
                "content": "Tell me about the world.",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "It's a flat world with a single continent...",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "user",
                "content": "What about the troll?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "The troll is 12 feet tall with grey skin...",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "operation": "reflect"
    }
    
    print("\nPerforming memory reflection...")
    success = memory_manager.update_memory(json.dumps(reflection_context))
    if success:
        print("Reflection completed successfully")
        print_memory_state(memory_manager, "Memory After Reflection")
    else:
        print("Failed to complete reflection!")
    
    # Phase 5: Complex Query Using Updated Memory
    print("\nPhase 5: Testing Complex Query...")
    
    query_context = {
        "current_phase": "INTERACTION",
        "recent_messages": reflection_context["recent_history"],
        "user_message": "What's the best strategy for dealing with the troll based on what we know?"
    }
    
    print("\nQuerying for troll strategy...")
    result = memory_manager.query_memory(json.dumps(query_context))
    print("\nStrategy Query Result:")
    print(json.dumps(result, indent=2))
    
    # Clean up
    print("\nCleaning up...")
    memory_manager.clear_memory()
    print("Memory cleared.")

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

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