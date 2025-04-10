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

from src.ai.llm_ollama import OllamaService
# from src.memory.memory_manager import MemoryManager
from src.memory.simple_memory_manager import SimpleMemoryManager
from src.agent.agent import Agent, AgentPhase
from examples.domain_configs import DND_CONFIG

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
    
    # Print static memory
    print("\nStatic Memory (Read-Only):")
    print("-" * 30)
    if "static_memory" in memory_context:
        static_mem = memory_context["static_memory"]
        print("\nStructured Data:")
        print(json.dumps(static_mem.get("structured_data", {}), indent=2))
        print("\nKnowledge Graph:")
        print(json.dumps(static_mem.get("knowledge_graph", {}), indent=2))
    else:
        print("No static memory")
    
    # Print working memory
    print("\nWorking Memory:")
    print("-" * 30)
    if "working_memory" in memory_context:
        working_mem = memory_context["working_memory"]
        print("\nStructured Data:")
        print(json.dumps(working_mem.get("structured_data", {}), indent=2))
        print("\nKnowledge Graph:")
        print(json.dumps(working_mem.get("knowledge_graph", {}), indent=2))
    else:
        print("No working memory")
    
    # Print metadata
    if "metadata" in memory_context:
        print("\nMetadata:")
        print("-" * 30)
        print(json.dumps(memory_context["metadata"], indent=2))
    
    # Print conversation history length
    if "conversation_history" in memory_context:
        print(f"\nConversation History: {len(memory_context['conversation_history'])} messages")

def print_conversation_history(memory_manager, title="Conversation History"):
    """Print the accumulated conversation history from memory"""
    print(f"\n{title}")
    print("=" * len(title))
    memory_context = memory_manager.get_memory_context()
    messages = memory_context.get("conversation_history", [])
    if not messages:
        print("No conversation history in memory")
        return
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        print(f"\n[{role.upper()}] {timestamp}")
        print(f"{content}")

def print_recent_history(agent, title="Recent History"):
    """Print the agent's current session history"""
    print(f"\n{title}")
    print("=" * len(title))
    history = agent.get_conversation_history()
    if not history:
        print("No recent history")
        return
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        print(f"\n[{role.upper()}] {timestamp}")
        print(f"{content}")

def print_help():
    """Print available commands and their descriptions"""
    print("\nAvailable Commands:")
    print("------------------")
    print("help        - Show this help message")
    print("memory      - View current memory state")
    print("conversation- View full conversation history")
    print("history     - View recent session history")
    print("reflect     - Trigger memory reflection")
    print("quit        - End session")

async def setup_services():
    """Initialize the LLM service and memory manager"""
    print("\nSetting up services...")
    print("Initializing LLM service (Ollama)...")
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "agent_debug.log",
        "debug_scope": "agent_example",
        "console_output": False
    })
    
    try:
        print("Creating SimpleMemoryManager and Agent instances...")
        memory_manager = SimpleMemoryManager(
            memory_file="agent_memory_simple.json",
            domain_config=DND_CONFIG,
            llm_service=llm_service
        )
        agent = Agent(llm_service, memory_manager, domain_name="dnd_campaign")
        print("Services initialized successfully")
        return agent, memory_manager
    except Exception as e:
        print(f"Error initializing services: {str(e)}")
        raise

async def initialize_campaign(agent, memory_manager):
    """Set up initial campaign state"""
    print("\nInitializing campaign...")
    print(f"Current phase: {agent.get_current_phase().name}")
    
    # First check if memory already exists and has content
    memory_context = memory_manager.get_memory_context()
    if memory_context and memory_context.get("conversation_history"):
        print("Campaign already initialized, using existing memory")
        
        # Display recent conversation history
        messages = memory_context["conversation_history"]
        if messages:
            print("\nRecent Conversation History:")
            print("-" * 30)
            # Show last 3 messages
            for msg in messages[-3:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                print(f"\n[{role.upper()}] {timestamp}")
                print(f"{content}")
        
        # Ensure we're in INTERACTION phase
        if agent.get_current_phase() == AgentPhase.INITIALIZATION:
            print("\nMoving to INTERACTION phase for existing campaign")
            agent.current_phase = AgentPhase.INTERACTION
        return True
    
    # If no existing memory, create new campaign
    print("Creating new campaign memory...")
    success = await agent.learn(DND_CONFIG["initial_data"])
    if not success:
        print("Failed to initialize campaign!")
        return False
    
    print("\nCampaign world initialized successfully!")
    print_memory_state(memory_manager, "Initial Campaign State")
    print(f"Current phase: {agent.get_current_phase().name}")
    return True

async def interactive_session(agent, memory_manager):
    """Run an interactive session with the agent"""
    print("\nStarting interactive session...")
    print(f"Current phase: {agent.get_current_phase().name}")
    print('Type "help" to see available commands')
    
    while True:
        try:
            user_input = input("\nYou: ").strip().lower()
            
            if user_input == 'quit':
                print("\nEnding session...")
                break
            elif user_input == 'help':
                print_help()
                continue
            elif user_input == 'memory':
                print_memory_state(memory_manager)
                continue
            elif user_input == 'conversation':
                print_conversation_history(memory_manager)
                continue
            elif user_input == 'history':
                print_recent_history(agent)
                continue
            elif user_input == 'reflect':
                print("\nTriggering memory reflection...")
                await agent.reflect()
                print("Reflection completed")
                print_memory_state(memory_manager, "Memory After Reflection")
                continue
            
            print(f"\nProcessing message...")
            response = await agent.process_message(user_input)
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nSession interrupted by user.")
            break
        except Exception as e:
            print(f"\nError during interaction: {str(e)}")
            continue

async def main():
    """Main function to run the agent example"""
    print_section_header("D&D Campaign Agent Example")
    
    try:
        # Setup
        agent, memory_manager = await setup_services()
        
        # Initialize campaign
        if not await initialize_campaign(agent, memory_manager):
            return
        
        # Interactive session
        await interactive_session(agent, memory_manager)
        
    except Exception as e:
        print(f"\nError during example: {str(e)}")
    finally:
        print("\nExample completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample ended by user.") 