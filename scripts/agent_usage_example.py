#!/usr/bin/env python3

import asyncio
import json
from pathlib import Path

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.agent.agent import Agent

async def main():
    """Example of using the Agent with Ollama for a D&D campaign."""
    
    print("Initializing D&D Campaign Agent...")
    
    # Initialize services
    llm_service = OllamaService({
        "model": "llama3",  # or another model you have installed
        "temperature": 0.7
    })
    
    memory_manager = MemoryManager(llm_service, "campaign_memory.json")
    agent = Agent(llm_service, memory_manager)
    
    # Phase 1: Learn about the campaign world
    print("\nPhase 1: Learning Campaign Details...")
    campaign_details = """
    The world is a simple, flat world with a single continent, a single ocean, and a single mountain range.
    The world is inhabited by a single species of intelligent humanoid creatures.
    The world is ruled by a single, benevolent monarch.
    The world is at peace, except for reports of a monster attacking a nearby village from its lair in a mountain cave system.
    The monster is known as the "Mountain Troll" and has reportedly wandered down from the wilds of the North.
    The players' quest is to find the monster and kill it.
    The village has offered a reward of 1000 gold coins for the destruction of the monster and delivery of its head to the village.
    """
    
    success = await agent.learn(campaign_details)
    if not success:
        print("Failed to learn campaign details!")
        return
    
    # Phase 2: Learn about the party
    print("\nPhase 2: Learning Party Details...")
    party_details = """
    The party consists of 4 players:
    1. The Wizard (Arcane Master) - High intelligence (18), skilled spellcaster
    2. The Fighter (Battle Master) - High strength (18), melee combat specialist
    3. The Cleric (Healer) - High wisdom (18), divine magic and healing
    4. The Thief (Shadow Master) - High dexterity (18), stealth and skills
    
    They are inexperienced adventurers but skilled in their respective areas.
    They have basic equipment appropriate for their classes.
    """
    
    success = await agent.learn(party_details)
    if not success:
        print("Failed to learn party details!")
        return
    
    # Phase 3: Interactive Campaign Session
    print("\nPhase 3: Starting Campaign Session...")
    print("(Type 'quit' to end the session, 'reflect' to trigger agent reflection)")
    
    while True:
        # Get user input
        user_input = input("\nWhat would you like to do? > ")
        
        if user_input.lower() == 'quit':
            break
        
        if user_input.lower() == 'reflect':
            print("\nAgent is reflecting on the session...")
            await agent.reflect()
            continue
        
        # Process message and get response
        response = await agent.process_message(user_input)
        print(f"\nDungeon Master: {response}")
        
        # Optional: Print current phase for debugging
        print(f"\n[Current Phase: {agent.get_current_phase().name}]")

async def example_interactions():
    """Example of typical interactions with the agent."""
    agent = await setup_agent()
    
    # Example interactions
    interactions = [
        "Tell me about the world we're in.",
        "What do we know about the Mountain Troll?",
        "What abilities does our party have?",
        "We approach the village. What do we see?",
        "We ask the villagers about recent troll sightings."
    ]
    
    for interaction in interactions:
        print(f"\nPlayer: {interaction}")
        response = await agent.process_message(interaction)
        print(f"Dungeon Master: {response}")
        await asyncio.sleep(1)  # Pause between interactions

async def setup_agent() -> Agent:
    """Setup the agent with necessary services."""
    llm_service = OllamaService({
        "model": "llama3",
        "temperature": 0.7
    })
    memory_manager = MemoryManager(llm_service, "example_memory.json")
    return Agent(llm_service, memory_manager)

if __name__ == "__main__":
    print("D&D Campaign Agent Example")
    print("=========================")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession ended by user.")
    except Exception as e:
        print(f"\nError during session: {str(e)}")
    finally:
        print("\nSession ended. Thank you for playing!")
