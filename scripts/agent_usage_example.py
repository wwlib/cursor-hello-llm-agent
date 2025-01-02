#!/usr/bin/env python3

import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.agent.agent import Agent, AgentPhase

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

async def setup_services():
    """Initialize the LLM service and memory manager"""
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "agent_debug.log",
        "console_output": False
    })
    
    try:
        memory_manager = MemoryManager(llm_service, "agent_memory.json")
        agent = Agent(llm_service, memory_manager)
        return agent, memory_manager
    except Exception as e:
        print(f"Error initializing services: {str(e)}")
        raise

async def initialize_campaign(agent, memory_manager):
    """Set up initial campaign state"""
    print("\nInitializing campaign world...")
    
    campaign_data = """Please structure the following campaign information into a JSON format with structured_data for facts, knowledge_graph for relationships, and appropriate metadata.

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
- Captain Sara of Riverwatch (military leader)

Return ONLY a valid JSON object with structured_data, knowledge_graph, and metadata sections. No additional text or explanation."""
    
    success = await agent.learn(campaign_data)
    if not success:
        print("Failed to initialize campaign!")
        return False
    
    print("\nCampaign world initialized successfully!")
    print_memory_state(memory_manager, "Initial Campaign State")
    return True

async def interactive_session(agent, memory_manager):
    """Run an interactive session with the agent"""
    print("\nStarting interactive session...")
    print("Type 'memory' to see current memory state")
    print("Type 'reflect' to trigger memory reflection")
    print("Type 'quit' to end session")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'memory':
                print_memory_state(memory_manager)
                continue
            elif user_input.lower() == 'reflect':
                print("\nReflecting on recent interactions...")
                success = await agent.reflect()
                if success:
                    print("Reflection completed successfully!")
                    print_memory_state(memory_manager, "Memory After Reflection")
                else:
                    print("Reflection failed!")
                continue
            
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
