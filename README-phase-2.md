# README-phase-2

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



## Overall Goals

- Create an Agent Framework tha can be used for a variety of purposes
- Use the Agent Framework to create an Agent that can be used to help manage the creation of this framework (i.e. make the framework "self-hosted")
  - Including acting as the project ProjewctManager/ScrumMaster
- Use the Agent Framework to create an Agent that can act like a "Jarvis" in a home workshop to assist with projects and preserve project details - like a voice-driven lab notebook
- Use the Agent Framework to create a DND Dungeon Master

## TODO

### Set things up to handle mutliple conversations

- Memory files should have a GUID that identifies them

### Save the Conversation History in a separate file to preserve all conversation information

- Continually append queries and responses to the Conversation History file
- The Conversation History should include the GUID of the associated memory file
- Each conversation entry should have a GUID
  - To be used to map entryies to associated digests

Example Conversation History File JSON

```json
{
    "memoryFileGuid": "596ab0a4-2ad8-4370-8919-6d34288200c8",
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

### Improve the generation of query digests

- Each digest should include the GUID of the conversation history entry from which it was generated
- Generation of digests should be a separate step, making its own LLM calls
  - Step 1: Segment the query/response into phrases, each of which contains one idea and/or piece of distinct information
  - Step 2: Extract the data from each segment into structured data that is included in the digest
- Implement a general orchestrator to handle the multiple LLM calls
   - Future
     - Create a RAG DB of all of the ideas and info
     - Should be able to identify where in the converstation timeline the info/ideas came from

Example Digest JSON

```json
"digest": 
    {
        "conversationHistoryGuid": "519b036c-a652-4849-a037-cae3fd9ee767",
        "segments": [
            "The air hangs heavy with the scent of pine and damp earth as you recall the recent events.",
            "Just yesterday, Captain Silas, a grizzled veteran of the Merchant Guard, approached you with a proposition.",
            "He'd detected unusual activity near the Blackwood Caves \u2013 whispers of monstrous spiders weaving webs of shadow and venom.",
            "He offered a reward of 50 gold pieces plus a share of any recovered goods, a considerable sum considering the dangers.",
            "You accepted, eager for adventure and a bit of coin.",
            "The task: track down these venomous spiders and eliminate the threat to the surrounding settlements.",
            "The caves themselves are known to be a labyrinthine network, riddled with traps and, as Silas ominously warned, the spiders themselves."
        ]
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
