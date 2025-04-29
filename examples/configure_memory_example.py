#!/usr/bin/env python3

import asyncio
import json
import os
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.agent.agent import Agent

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

async def main():
    """Demonstrate configurable memory parameters"""
    print_section_header("Configurable Memory Parameters Example")
    
    # Create a temporary directory for this example
    memory_dir = os.path.join(project_root, "examples", "temp_memories")
    os.makedirs(memory_dir, exist_ok=True)
    
    # Sample domain config
    domain_config = {
        "domain_specific_prompt_instructions": {
            "create_memory": "You are creating memory for a note-taking assistant.",
            "query": "You are a helpful note-taking assistant.",
            "update": "You are updating memory for a note-taking assistant."
        },
        "initial_data": (
            "This is a note-taking assistant that helps users organize their thoughts and ideas. "
            "It can take notes, categorize them, and retrieve them based on user queries."
        )
    }
    
    try:
        # Initialize LLM service
        print("Initializing LLM service...")
        llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",  # Update this to your Ollama server
            "model": "gemma3",
            "temperature": 0.7,
            "stream": False
        })
        
        # Create the first MemoryManager with default settings
        print("\nCreating MemoryManager with default settings...")
        default_memory_file = os.path.join(memory_dir, "default_memory.json")
        default_memory = MemoryManager(
            memory_file=default_memory_file,
            domain_config=domain_config,
            llm_service=llm_service
        )
        
        # Create the second MemoryManager with custom compression settings
        print("\nCreating MemoryManager with custom compression settings...")
        custom_memory_file = os.path.join(memory_dir, "custom_memory.json")
        custom_memory = MemoryManager(
            memory_file=custom_memory_file,
            domain_config=domain_config,
            llm_service=llm_service,
            max_recent_conversations=5,      # Keep only 5 recent conversations (default is 10)
            importance_threshold=4           # Only keep very important segments (default is 3)
        )
        
        # Initialize agent with default memory manager
        default_agent = Agent(llm_service, default_memory, domain_name="notes")
        
        # Initialize agent with custom memory manager
        custom_agent = Agent(llm_service, custom_memory, domain_name="notes")
        
        # Initialize memories
        print("\nInitializing memories with initial data...")
        await default_agent.learn(domain_config["initial_data"])
        await custom_agent.learn(domain_config["initial_data"])
        
        # Process some messages for both agents to demonstrate different compression behaviors
        print("\nProcessing messages for both agents...")
        messages = [
            "I need to take notes about my garden project.",
            "The tomatoes should be planted in April.",
            "Carrots need to be thinned once they sprout.",
            "Water the garden daily during hot weather.",
            "Apply fertilizer once a month.",
            "Harvest tomatoes when they're bright red.",
            "Keep an eye out for pests like aphids.",
            "Mulch helps retain moisture in the soil.",
            "Plant flowers to attract beneficial insects.",
            "Rotate crops each season to prevent disease.",
            "Consider using organic pest control methods.",
            "Start seeds indoors for an early start."
        ]
        
        for i, message in enumerate(messages):
            print(f"\nProcessing message {i+1}: {message}")
            
            # Process with default agent
            await default_agent.process_message(message)
            
            # Process with custom agent
            await custom_agent.process_message(message)
            
            # After 8 messages, check memory state to compare compression
            if i == 7:
                print("\nAfter 8 messages:")
                print("\nDefault memory manager state (max_recent_conversations=10, importance_threshold=3):")
                print(f"Conversation history length: {len(default_memory.memory['conversation_history'])}")
                
                print("\nCustom memory manager state (max_recent_conversations=5, importance_threshold=4):")
                print(f"Conversation history length: {len(custom_memory.memory['conversation_history'])}")
                
                # Check for compressed entries
                if "compressed_entries" in custom_memory.memory:
                    print(f"\nCompressed entries in custom memory: {len(custom_memory.memory['compressed_entries'])}")
                    print(f"Total entries compressed: {sum(entry['count'] for entry in custom_memory.memory['compressed_entries'])}")
        
        # Compare final state
        print("\n\nFinal memory state comparison:")
        
        # Default memory
        print("\nDefault memory manager (max_recent_conversations=10, importance_threshold=3):")
        print(f"Conversation history length: {len(default_memory.memory['conversation_history'])}")
        if "compressed_entries" in default_memory.memory:
            print(f"Compressed entries: {len(default_memory.memory['compressed_entries'])}")
            print(f"Total entries compressed: {sum(entry['count'] for entry in default_memory.memory['compressed_entries'])}")
        else:
            print("No compression occurred with default settings")
        
        # Custom memory
        print("\nCustom memory manager (max_recent_conversations=5, importance_threshold=4):")
        print(f"Conversation history length: {len(custom_memory.memory['conversation_history'])}")
        if "compressed_entries" in custom_memory.memory:
            print(f"Compressed entries: {len(custom_memory.memory['compressed_entries'])}")
            print(f"Total entries compressed: {sum(entry['count'] for entry in custom_memory.memory['compressed_entries'])}")
        
        # Compare conversation history files
        print("\nComparing conversation history files:")
        default_convo_file = default_memory.conversation_history_file
        custom_convo_file = custom_memory.conversation_history_file
        
        with open(default_convo_file, 'r') as f:
            default_conversations = json.load(f)
        
        with open(custom_convo_file, 'r') as f:
            custom_conversations = json.load(f)
        
        print(f"Default conversation history file entries: {len(default_conversations['entries'])}")
        print(f"Custom conversation history file entries: {len(custom_conversations['entries'])}")
        
        print("\nThis demonstrates that even though the memory file may contain fewer conversations due to compression,")
        print("all conversations are still preserved in the separate conversation history file.")
        
    except Exception as e:
        print(f"Error during example: {str(e)}")
    finally:
        print_section_header("Example Complete")

if __name__ == "__main__":
    asyncio.run(main()) 