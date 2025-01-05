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
from src.memory.memory_manager import MemoryManager
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
    print(json.dumps(memory_manager.get_memory_context(), indent=2))

def print_conversation_history(memory_manager, title="Conversation History"):
    """Print the accumulated conversation history from memory"""
    print(f"\n{title}")
    print("=" * len(title))
    messages = memory_manager.memory.get("conversation_history", [])
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
        print("Creating MemoryManager and Agent instances...")
        memory_manager = MemoryManager(
            llm_service, 
            "agent_memory.json",
            domain_config=DND_CONFIG
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
    
    # First check if memory already exists
    if memory_manager.memory:
        print("Campaign already initialized, using existing memory")
        print_memory_state(memory_manager, "Existing Campaign State")
        # Ensure we're in INTERACTION phase
        if agent.get_current_phase() == AgentPhase.INITIALIZATION:
            print("Moving to INTERACTION phase for existing campaign")
            agent.current_phase = AgentPhase.INTERACTION
        return True
    
    print("Creating new campaign memory...")
    campaign_data = """
Entities:
1. The Lost Valley
   - Type: region
   - Features: Hidden valley, impassable mountains, ancient ruins, magical anomalies

2. Settlements:
   - Haven (central settlement)
   - Riverwatch (eastern settlement)
   - Mountainkeep (western settlement)

3. Key NPCs:
   - Elena (Mayor of Haven, quest giver)
   - Theron (Master Scholar, ruins expert)
   - Sara (Captain of Riverwatch, military leader)

4. Current Issues:
   - Strange creatures
   - Disrupted trade
   - Ancient artifacts
   - Guild recruitment
"""
    
    print(f"Phase before learning: {agent.get_current_phase().name}")
    success = await agent.learn(campaign_data)
    print(f"Phase after learning: {agent.get_current_phase().name}")
    
    if not success:
        print("Failed to initialize campaign!")
        return False
    
    print("\nCampaign world initialized successfully!")
    print_memory_state(memory_manager, "Initial Campaign State")
    
    # Double check we're in INTERACTION phase
    if agent.get_current_phase() != AgentPhase.INTERACTION:
        print("Ensuring transition to INTERACTION phase")
        agent.current_phase = AgentPhase.INTERACTION
    
    print(f"Final phase: {agent.get_current_phase().name}")
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
                print("\nReflecting on recent interactions...")
                success = await agent.reflect()
                if success:
                    print("Reflection completed successfully!")
                    print_memory_state(memory_manager, "Memory After Reflection")
                else:
                    print("Reflection failed!")
                continue
            
            print(f"\nProcessing message (Phase: {agent.get_current_phase().name})...")
            response = await agent.process_message(user_input)
            print(f"\nAgent: {response}")
            print(f"Current phase: {agent.get_current_phase().name}")
            
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