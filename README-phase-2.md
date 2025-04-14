# README-phase-2

## Overall Goals

- Create an Agent Framework tha can be used for a variety of purposes
- Use the Agent Framework to create an Agent that can be used to help manage the creation of this framework (i.e. make the framework "self-hosted")
  - Including acting as the project ProjewctManager/ScrumMaster
- Use the Agent Framework to create an Agent that can act like a "Jarvis" in a home workshop to assist with projects and preserve project details - like a voice-driven lab notebook
- Use the Agent Framework to create a DND Dungeon Master
- Future
  - Create a RAG DB of all of the ideas and info in the conversation history
  - Should be able to identify where in the converstation timeline the info/ideas came from

## AI Summary of this README by the Cursor Agent using claude-3.7-sonnet

Looking at README-phase-2.md, I can see you're planning a significant expansion of your LLM-driven agent framework. 

The overall goals are ambitious and practical - you want to create a versatile agent framework that can be applied to multiple use cases, including:
1. A "self-hosted" agent that helps manage its own development (acting as PM/Scrum Master)
2. A "Jarvis-like" workshop assistant for project tracking (voice-driven lab notebook)
3. A D&D Dungeon Master

The TODO list focuses on several key improvements to the memory system:

1. **Multiple conversation handling**: Adding GUIDs to memory files for better identification and management of separate conversations.

2. **Separate conversation history storage**: Moving conversation history to its own file structure with GUIDs to maintain complete interaction records while keeping memory files manageable.

3. **Enhanced digest generation**: Creating a more sophisticated approach to extracting and structuring information from conversations by:
   - Adding GUIDs to link digests with conversation entries
   - Breaking the digest process into separate steps (segmentation and extraction)
   - Using more structured format for digests with segments, context, facts, and relationships

The proposed JSON structures show a thoughtful approach to tracking and organizing conversations and their extracted information. The digest format is particularly interesting - it segments conversations into discrete chunks of information and extracts specific facts and relationships with metadata like importance, topic, and source.

This represents a significant evolution of your current memory system, moving toward a more structured, granular approach to information extraction and management. These changes would make the system more scalable and help with preserving context across multiple, potentially long-running conversations.


## Phase 2 Update - April 13, 2025 - GUID Implementation and Memory Manager Refactoring

Successfully implemented several key features from our Phase 2 roadmap:

1. **Memory GUID Implementation**: All memory files now include a GUID for unique identification. The GUID is generated or preserved during initialization and maintained throughout the memory lifecycle.

2. **Memory Manager Types**: We've created a flexible architecture with two memory manager implementations:
   - `MemoryManager`: Our full-featured implementation with LLM-driven memory organization
   - `SimpleMemoryManager`: A lightweight implementation for testing and simpler use cases

3. **Memory Structure Improvements**:
   - Added proper validation for memory structure
   - Enhanced JSON parsing with fallback mechanisms using regex
   - Implemented memory type identification in the memory structure

4. **Code Organization**:
   - Updated `BaseMemoryManager` abstract class that defines the core interface
   - Moved common functionality like file I/O to the base class
   - Standardized initialization process with GUID handling

The agent example now supports loading specific memory files by GUID and switching between memory manager types, providing a foundation for the conversation history separation in the next implementation phase.


## Phase 2 Update - April 15, 2025 - DigestGenerator Implementation

Successfully implemented the DigestGenerator component, a key part of our enhanced memory management system:

1. **Two-Step Digest Generation Process**: 
   - Segmentation: Breaks down conversation content into meaningful chunks using LLM
   - Extraction: Derives structured facts and relationships from these segments using LLM
   - This approach provides better traceability between raw conversation text and extracted knowledge

2. **Structured Digest Format**:
   - Each digest includes segments, context summary, facts, and relationships
   - Facts include metadata like importance, topic, and source segments
   - Relationships follow subject-predicate-object format with similar metadata
   - Each digest is linked to its source conversation entry via GUID

3. **Robust Error Handling**:
   - Fallback mechanisms for LLM response parsing
   - Graceful degradation when segmentation fails
   - Comprehensive validation of extract information structure

4. **Integration with Memory System**:
   - Integration tests verify compatibility with existing memory components
   - Example script demonstrates real-world usage in conversation analysis

These changes enable more sophisticated information extraction from conversations, supporting our goal of having agents that can effectively learn from interactions. The DigestGenerator will serve as the foundation for upcoming conversation history separation and RAG-based memory retrieval features.

Next steps include fully integrating the DigestGenerator into the memory update process and implementing separate conversation history storage with efficient cross-referencing.


## TODO

### Integrate the DigestGenerator with the MemoryManager

- Each digest should include the GUID of the conversation history entry from which it was generated

Example Digest JSON

```json
"digest": 
    {
        "conversation_history_entry_guid": "519b036c-a652-4849-a037-cae3fd9ee767",
        "role": "assistant",
        "segments": [
            "The air hangs heavy with the scent of pine and damp earth as you recall the recent events.",
            "Just yesterday, Captain Silas, a grizzled veteran of the Merchant Guard, approached you with a proposition.",
            "He'd detected unusual activity near the Blackwood Caves \u2013 whispers of monstrous spiders weaving webs of shadow and venom.",
            "He offered a reward of 50 gold pieces plus a share of any recovered goods, a considerable sum considering the dangers.",
            "You accepted, eager for adventure and a bit of coin.",
            "The task: track down these venomous spiders and eliminate the threat to the surrounding settlements.",
            "The caves themselves are known to be a labyrinthine network, riddled with traps and, as Silas ominously warned, the spiders themselves."
        ],
        "context": "Reviewing the current situation following Silas's approach and offer.",
        "new_facts": [
          {
            "segmentIndexes": [ 6 ],
            "key": "spider_type",
            "value": "Venomous spiders",
            "context": "The specific type of spiders involved in the task.",
            "source": "assistant|inferred",
            "importance": "high",
            "topic": "Creature Threat"
          },
          {
            "segmentIndexes": [ 3 ],
            "key": "reward_details",
            "value": "50 gold pieces + share of recovered goods",
            "context": "The terms of the reward offered by Silas.",
            "source": "assistant|inferred",
            "importance": "high",
            "topic": "Financial Incentive"
          }
        ],
        "new_relationships": [
          {
            "segmentIndexes": [ 1, 3, 4, 5 ],
            "subject": "user",
            "predicate": "task_assigned",
            "object": "spider_quest",
            "context": "The user has been assigned the task of dealing with the spiders.",
            "source": "assistant|inferred",
            "importance": "high",
            "topic": "Mission Objective"
          }
        ]
    }
```

### Save the Conversation History in a separate file to preserve all conversation information

- Continually append queries and responses to the Conversation History file
- The Conversation History should include the GUID of the associated memory file
- Each conversation entry should have a GUID
  - To be used to map entryies to associated digests

Example Conversation History File JSON

```json
{
    "memory_file_guid": "596ab0a4-2ad8-4370-8919-6d34288200c8",
    "entries": []
}

```

Example Conversation History entry JSON

```json
{
    "guid": "519b036c-a652-4849-a037-cae3fd9ee767",
    "role": "assistant",
    "content": "The air hangs heavy with the scent of pine and damp earth as you recall the recent events. Just yesterday, Captain Silas, a grizzled veteran of the Merchant Guard, approached you with a proposition. He'd detected unusual activity near the Blackwood Caves \u2013 whispers of monstrous spiders weaving webs of shadow and venom. He offered a reward of 50 gold pieces plus a share of any recovered goods, a considerable sum considering the dangers. You accepted, eager for adventure and a bit of coin. The task: track down these venomous spiders and eliminate the threat to the surrounding settlements. The caves themselves are known to be a labyrinthine network, riddled with traps and, as Silas ominously warned, the spiders themselves.",
    "digest": {}
}
```