#!/usr/bin/env python3

import asyncio
import json
import os
from pathlib import Path
import sys
import uuid

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
    """Demonstrate different memory configurations"""
    print("\n=== Memory Configuration Example ===")
    
    # Create a temporary directory for memory storage
    temp_dir = os.path.join(project_root, "temp_memory")
    os.makedirs(temp_dir, exist_ok=True)
    
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
    
    # Sample domain config
    domain_config = {
        "domain_specific_prompt_instructions": {
            "create_memory": "You are creating memory for a note-taking agent.",
            "query": "You are a helpful note-taking agent.",
            "update": "You are updating memory for a note-taking agent."
        },
        "initial_data": (
            "This is a note-taking agent that helps users organize their thoughts and ideas. "
            "It can take notes, categorize them, and retrieve them based on user queries."
        )
    }
    
    try:
        # Initialize LLM services
        print("Initializing LLM services...")
        
        # General query service
        general_llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",
            "model": "gemma3",
            "temperature": 0.7,
            "stream": False,
            "debug": True,
            "debug_file": general_debug_file,
            "debug_scope": "memory_config_general"
        })
        
        # Digest generation service
        digest_llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",
            "model": "gemma3",
            "temperature": 0.7,
            "stream": False,
            "debug": True,
            "debug_file": digest_debug_file,
            "debug_scope": "memory_config_digest"
        })
        
        # Initialize embeddings service
        embeddings_llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",
            "model": "mxbai-embed-large",
            "debug": False,
            "debug_file": embed_debug_file  # Still specify the file even though logging is disabled
        })
        
        # Create the first MemoryManager with default settings
        print("\nCreating MemoryManager with default settings...")
        default_memory_file = os.path.join(temp_dir, "default_memory.json")
        default_memory = MemoryManager(
            memory_file=default_memory_file,
            domain_config=domain_config,
            llm_service=general_llm_service,
            digest_llm_service=digest_llm_service,
            embeddings_llm_service=embeddings_llm_service
        )
        
        # Create the second MemoryManager with custom compression settings
        print("\nCreating MemoryManager with custom compression settings...")
        custom_memory_file = os.path.join(temp_dir, "custom_memory.json")
        custom_memory = MemoryManager(
            memory_file=custom_memory_file,
            domain_config=domain_config,
            llm_service=general_llm_service,
            digest_llm_service=digest_llm_service,
            embeddings_llm_service=embeddings_llm_service,
            max_recent_conversation_entries=5,      # Keep only 5 recent conversations (default is 10)
            importance_threshold=4           # Only keep very important segments (default is 3)
        )
        
        # Initialize agent with default memory manager
        default_agent = Agent(general_llm_service, default_memory, domain_name="notes")
        
        # Initialize agent with custom memory manager
        custom_agent = Agent(general_llm_service, custom_memory, domain_name="notes")
        
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
        print("the conversation history file maintains a complete record of all interactions.")
        
    except Exception as e:
        print(f"Error during example: {str(e)}")
    finally:
        print_section_header("Example Complete")

if __name__ == "__main__":
    asyncio.run(main()) 