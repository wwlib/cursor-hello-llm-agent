# llm-driven-agent-with-session-memory-cursor-instructions

This is a simple example of a LLM-driven agent with session memory.

## Overivew

The agent should support multiple turns of conversation about any topic.

The agent should be able to remember the conversation from previous turns.

The agent should be able to use the conversation from previous turns to inform its response to the current turn.

The agent should be able to use the conversation from previous turns to inform its response to the current turn.

To keep thing simple at first, the memory should be implemented as a JOSN file with a section for structured data relevant to the conversation.

The memory should also include a section for storing a knowledge graph of information relevant to the conversation.

The knowledge graph should be implemented as a simple text notation that can be easily saved in the JSON file.

The agent should choose the most relevant information from the strucured data and the knowledge graph to include in each new prompt for the LLM.

The agent should be able to update the memory with new information from the LLM's response.

## Agent Service

The agent service should be implemented as a simple FastAPI application that can be used to interact with the agent.

The agent service should be able to receive a prompt from the user and return a response from the agent.

The agent service should be able to update the memory with new information from the LLM's response.

The agent service should be able to save the memory to a file.

The agent service should be able to load the memory from a file.

The agent service should be able to clear the memory.


## Example Use Case - Agent to act as a Dungeon Master for a D&D campaign

Interactions with the agent would have several phases:

1. Phase 1: The Agent would learn about the details of the campaign, including:
- general rules
- special rules
- the world
- the non-player characters
- the monsters
- the items
- the locations
- map
- history

2. Phase 2: The agent would learn about the player characters, including:
- their background
- their skills
- their equipment
- their goals
- their backstory
- their personality
- their goals

3. Phase 3: The agent would act as a Dungeon Master for the campaign, including:
- generating the world
- generating the non-player characters
- generating the monsters
- generating the items
- generating the locations
- generating the map
- generating the history
- orchestrating each encounter, making up any missing detials, and providing the players with the information they need

In phases 1 and 2, the agent would be populating the structured data and the knowledge graph with the information needed for Phase 3.

In phase 3, the agent will update the structured data and the knowledge graph with the information generated while playing the game.

Phase 3 has these sub-phases:
1. Assembling and equipping the party
2. Exploring the dungeon to complete the quest
3. Fighting the monster
4. Returning to the village with the monster's head

## Example Campaign

### Campaign Details for Phase 1 - A simple, hello world campaign

- The world is a simple, flat world with a single continent, a single ocean, and a single mountain range.
- The world is inhabited by a single species of intelligent humanoid creatures.
- The world is ruled by a single, benevolent monarch.
- The world is at peace, except for remports of a monster attacking a nearby village from its lair in a mountain cave system.
- The monster is known as the "Mountain Troll" and has reportedly wandered down from the wilds of the North.
- The players' quest is to find the monster and kill it.
- The village has offered a reward of 1000 gold coins for the destruction of the monster and delivery of its head to the village.

### Player Character Details for Phase 2
- The players are relatively inexperienced adventurers, having only recently left their home village to seek their fortunes.
- The players are known to be brave and hardy, but they have no formal training in combat or adventure.
- The players are known to be honest and trustworthy, but they have no formal training in diplomacy or negotiation.
- The players are known to be skilled hunters, but they have no formal training in tracking or survival.
- The players are known to be skilled craftsmen, but they have no formal training in crafting or engineering.
- The party consists of 4 players, a Wizard, a Fighter, a Cleric and a Thief (Rogue)
- The Wizard is known as the "Arcane Master" and is the party's spell caster. His stats are:
  - Strength: 10
  - Dexterity: 10
  - Constitution: 10
  - Intelligence: 18
  - Wisdom: 12
  - Charisma: 8
- The Fighter is known as the "Battle Master" and is the party's melee fighter. His stats are:
  - Strength: 18
  - Dexterity: 10
  - Constitution: 12
  - Intelligence: 10
  - Wisdom: 10
  - Charisma: 10
- The Cleric is known as the "Healer" and is the party's healer. Her stats are:
  - Strength: 10
  - Dexterity: 10
  - Constitution: 12
  - Intelligence: 10
  - Wisdom: 18
  - Charisma: 10
- The Thief is known as the "Shadow Master" and is the party's rogue. His stats are:
  - Strength: 10
  - Dexterity: 18
  - Constitution: 10
  - Intelligence: 10
  - Wisdom: 10
  - Charisma: 10


## Code Design and Architecture

The code will be organized into several modules:

- `agent_service/agent_service.py`: The FastAPI application that will be used to interact with the agent.
- `agent/agent.py`: The agent class that will be used to interact with the LLM.
- `memory/memory_manager.py`: The memory class that will be used to store the structured data and the knowledge graph.
- `memory/knowledge_graph.py`: The knowledge graph class that will be used to store the knowledge graph.
- `memory/structured_data.py`: The structured data class that will be used to store the structured data.
- `ai/llm.py`: The LLM class that will be used to interact with the LLM.
- `utils/utils.py`: The utility functions that will be used by the other modules.

### Agent Service

The agent service will be a FastAPI application that will be used to interact with the agent.

### Agent

The agent will be a class that will be used to interact with the LLM.

### Memory

#### Memory Manager



#### Knowledge Graph

#### Structured Data

### AI

#### LLM

#### Prompt Manager

#### Prompt Template

### Utils

