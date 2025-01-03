# Notes about using cursor composer - Agent

## Creating the main Agent class using composer

### Writing the initial code - Composer: `Creating Detailed README for Agent`

```
Please write a detailed README-agent.md based on the plan described in the main README.md and the MemoryManager implementation.
```

![](screenshots/cursor-agent-1.png)


```
Great. Now please write the Agent code and pytest tests for the Agent based on README_agent.md
```

![](screenshots/cursor-agent-2.png)

The implementation follows the design specified in the README and integrates well with the existing Memory Manager and LLM![](screenshots/cursor-agent-2.png) services.
Would you like me to:
- Add any additional test cases?
- Enhance any specific part of the implementation?
- Add more documentation or comments?
- Create an example usage script?

```
Yes. Please write example code in agent_usage_example.py that demonstrates interactions with the Agent using the OllamaService to communicate with an LLM.
```

![](screenshots/cursor-agent-3.png)

To run this example:
1. Make sure Ollama is running locally
2. Have the llama2 model installed (or modify the script to use another model)
3. Run the script:

```
python scripts/agent_usage_example.py
```

The script allows for two modes of interaction:
1. Interactive mode (main function) - Real-time interaction with the agent
2. Example mode (example_interactions function) - Demonstrates preset interactions

Would you like me to:
1. Add more example interactions?
2. Add additional error handling?
3. Include more debugging/logging features?
4. Create a separate script for testing different LLM models?


## Revisions

```
I just tested the script and am noticing some issues that we should address. Most important: The Agent class and the MemoryManager class are both making similar calls to the LLM generate and update data that should be remembered. This is inefficient. Calls to the LLM are relatively slow and expensive. The Agent should be revised to rely more on the MemoryManager to interface with the LLM. What do you think?
```

![](screenshots/cursor-agent-4.png)


```
Yes, please update the tests to reflect these changes.
```

![](screenshots/cursor-agent-5.png)

```
There are 2 failed tests in test_memory_manager.py
```

![](screenshots/cursor-agent-6.png)


```
Great. Let's focus on the memory manager. Please make a memory_manager_usage_example.py script that exercises the features of the MemoryManager - as thought it was being used by an Agent. The goal is to isolate the complex functionality of the MemoryManager so it is easy to evaluate and troubleshoot.
```

![](screenshots/cursor-agent-7.png)


```
Great. One more thing, the memory manager expects responses from the LLM to be strict, parsable JSON. Sometimes the LLM is returning extra, non-JSON commentary.  For prompts that are expecting JSON, an instruction like this needs to be added:

You are a helpful assistant that communicates using JSON. All your responses should be in strict, parsable JSON format.
```

![](screenshots/cursor-agent-8.png)

```
For future reference, please use llama3 rather than llama2 when initializing an OllamaService
```

![](screenshots/cursor-agent-9.png)



```
Things are looking good! There was an error in Phase 4 when running the memory manager usage example:

Phase 4: Testing Memory Reflection...

Performing memory reflection...
Error updating memory: 'metadata'
Failed to complete reflection!

It could be that the LLM did not return strict, parsable JSON. But it is hard to know. It would be helpful if the LLMService (i.e. OllamaService) had a debug mode so that prompts and responses could be logged to make troubleshooting easier.
```

![](screenshots/cursor-agent-10.png)


```
Really great. Now that I see the log, I think that logging each ollama stream chunk will often be too verbose. Let's have a way to disable that.
```


```
Great. Let's also add a control to determine if logs should be printed to the console. Often the log file will be sufficient.
```

```
When running memory_manager_usage_example.py let's use the non-streaming api for ollama.
```


```
Yes, please add timing information to see response latency and response size logging.
```

```
OK. The memory manager is working well. Now, please update/rewrite the agent_usage_exampe.py so we can see how the memory manager works in a real, ineractive session.
```



## First test run of the agent - 1/1/2025 12:47am

See: `cursor-notes/logs/agent-usage-example/agent_debug_1.log`
See: `cursor-notes/data/agent-usage-example/agent_memory_1.json`

```
python scripts/agent_usage_example.py
```


```
(.venv) (base) AndrewsMacBookPro16b:cursor-hello andrewrapo$ python scripts/agent_usage_example.py

================================================================================
  D&D Campaign Agent Example
================================================================================


Initializing campaign world...
Error updating memory: 'metadata'
Failed to initialize campaign!

Example completed.
(.venv) (base) AndrewsMacBookPro16b:cursor-hello andrewrapo$ python scripts/agent_usage_example.py

================================================================================
  D&D Campaign Agent Example
================================================================================


Initializing campaign world...

Campaign world initialized successfully!

Initial Campaign State
======================
{
  "structured_data": [
    {
      "fact": "The Lost Valley",
      "type": "campaign setting"
    },
    {
      "fact": "Hidden valley surrounded by impassable mountains",
      "type": "world detail"
    },
    {
      "fact": "Ancient ruins scattered throughout",
      "type": "world detail"
    },
    {
      "fact": "Mysterious magical anomalies",
      "type": "world detail"
    },
    {
      "fact": "Three main settlements: Haven (central), Riverwatch (east), Mountainkeep (west)",
      "type": "world detail"
    },
    {
      "fact": "Strange creatures emerging from the ruins",
      "type": "current situation"
    },
    {
      "fact": "Trade routes between settlements disrupted",
      "type": "current situation"
    },
    {
      "fact": "Ancient artifacts being discovered",
      "type": "current situation"
    },
    {
      "fact": "Local guilds seeking adventurers",
      "type": "current situation"
    },
    {
      "fact": "Mayor Elena of Haven (quest giver)",
      "type": "key NPC"
    },
    {
      "fact": "Master Scholar Theron (knowledge about ruins)",
      "type": "key NPC"
    },
    {
      "fact": "Captain Sara of Riverwatch (military leader)",
      "type": "key NPC"
    }
  ],
  "knowledge_graph": [
    {
      "node": "The Lost Valley",
      "relationships": [
        {
          "type": "campaign setting for",
          "target": "Strange creatures emerging from the ruins"
        },
        {
          "type": "campaign setting for",
          "target": "Trade routes between settlements disrupted"
        },
        {
          "type": "campaign setting for",
          "target": "Ancient artifacts being discovered"
        }
      ]
    },
    {
      "node": "Mayor Elena of Haven",
      "relationships": [
        {
          "type": "quest giver in",
          "target": "The Lost Valley"
        }
      ]
    },
    {
      "node": "Master Scholar Theron",
      "relationships": [
        {
          "type": "knowledge provider about",
          "target": "Ancient ruins"
        }
      ]
    },
    {
      "node": "Captain Sara of Riverwatch",
      "relationships": [
        {
          "type": "military leader in",
          "target": "The Lost Valley"
        }
      ]
    }
  ],
  "metadata": {
    "campaign_name": "The Lost Valley",
    "phase": "LEARNING",
    "recent_history": [],
    "last_updated": "2025-01-02T00:42:07.191435"
  }
}

Starting interactive session...
Type 'memory' to see current memory state
Type 'reflect' to trigger memory reflection
Type 'quit' to end session

You: What quest could I undertake that would earn me some gold?

Agent: Mayor Elena of Haven is looking for brave adventurers like you to help retrieve a lost artifact from one of the ancient ruins. She's willing to pay a handsome sum in gold and other rewards.

You: I'm in. Do I have the right equipment to set off?

Agent: You're likely equipped for the journey, but it's always a good idea to check with Master Scholar Theron at Haven before heading out. He might have some valuable insights on what you'll need and how to navigate the ruins safely.

You: reflect

Reflecting on recent interactions...
Reflection completed successfully!

Memory After Reflection
=======================
{
  "structured_data": [
    {
      "fact": "Mayor Elena of Haven is willing to pay gold and other rewards",
      "type": "quest"
    },
    {
      "fact": "Master Scholar Theron at Haven has valuable insights on ruins navigation",
      "type": "tip"
    }
  ],
  "knowledge_graph": [
    {
      "node": "The Lost Valley",
      "relationships": [
        {
          "type": "campaign setting for",
          "target": "Strange creatures emerging from the ruins"
        },
        {
          "type": "campaign setting for",
          "target": "Trade routes between settlements disrupted"
        },
        {
          "type": "campaign setting for",
          "target": "Ancient artifacts being discovered"
        }
      ]
    },
    {
      "node": "Master Scholar Theron",
      "relationships": [
        {
          "type": "knowledge provider about",
          "target": "Ruins navigation"
        }
      ]
    },
    {
      "node": "Mayor Elena of Haven",
      "relationships": [
        {
          "type": "quest giver in",
          "target": "The Lost Valley"
        }
      ]
    }
  ],
  "metadata": {
    "campaign_name": "The Lost Valley",
    "phase": "EXECUTING",
    "recent_history": [
      {
        "role": "system",
        "content": "Learned new information successfully",
        "timestamp": "2025-01-02T00:42:07.192072"
      },
      {
        "role": "user",
        "content": "What quest could I undertake that would earn me some gold?",
        "timestamp": "2025-01-02T00:44:18.895000"
      },
      {
        "role": "assistant",
        "content": "Mayor Elena of Haven is looking for brave adventurers like you to help retrieve a lost artifact from one of the ancient ruins. She's willing to pay a handsome sum in gold and other rewards.",
        "timestamp": "2025-01-02T00:44:18.895008"
      },
      {
        "role": "user",
        "content": "I'm in. Do I have the right equipment to set off?",
        "timestamp": "2025-01-02T00:45:14.089139"
      },
      {
        "role": "assistant",
        "content": "You're likely equipped for the journey, but it's always a good idea to check with Master Scholar Theron at Haven before heading out. He might have some valuable insights on what you'll need and how to navigate the ruins safely.",
        "timestamp": "2025-01-02T00:45:14.089148"
      }
    ],
    "last_updated": "2025-01-02T00:47:15.393223"
  }
}

You: 
```

Wow. It works! That's pretty cool.


## January 2 & 3, 2025 - after a long conversation with cursor composer and extensive refactoring

See: `cursor-notes/cursor-chat-and-composer-transcripts/Composer - Creating Detailed README for Agent.md`

From:
```
OK. The memory manager is working well. Now, please update/rewrite the agent_usage_exampe.py so we can see how the memory manager works in a real, ineractive session.
```

To:

```
I've updated the `query_memory` method to:

1. Properly handle reflection by:
   - Getting the last 10 messages from conversation history
   - Passing them to `_perform_reflection`
   - Clearing processed messages only after successful reflection

2. Added better error handling and logging:
   - Safely accessing conversation history with `get()`
   - Printing confirmation when messages are cleared
   - Preserving older messages after reflection

Would you like to try running the script again to verify that reflection now works correctly?
```


- I am testing the agent_usage_example. It would be helpful to add console logs to keep track of the steps as the are executed. I think the MemoryManager is getting initialzed even if memory was loaded from a file. In general, I want to make sure the LLM isn't called more often than necessary.
- It seems that the agent phase is always INITIALIZATION and never moves to LEARNING and INTERACTION
- Even though the interaction has started, the agent phase is still INITIALIZATION
- Great. Transitions seem to be working now. But I am noticing that not all messages are being remembered. It seems that the recent_history section of the metadata is not accumulating messages correctly.
- Thanks. Please add a "messages" command that list the current accumulated messages and a "history" command that will list the current recent history.
- The log about the "history" command refers to "conversation history" but it is actually recent history. Also, the "messages" command actually shows "conversation history" so we should change that command to "conversation"
- Take a look at "agent_memory copy 3.json" this is the starting point. After issuing one command to "Take an artifact" the memory gets updated to "agemnt_memory.json". A lot of information seems to have been lost. The converstation history has only 4 messages, now. And the infor from the original set of messages seems to be lost. Something isn't working correctly.
- The LLM needs to manage the structured_data and knowledge_graph sections of the memory. But the metadata  and  conversation_history sections of the memory should be maintained by the MemoryManager. The  metadata  and  conversation_history sections shuold be included in the the LLM interaction prompts as context. But the LLM can be instructed to only populate the structured_data and knowledge_graph sections in its response - to save time and tokens. What do you think about that?
- OK. That seems to be working much better. Tell me about the "reflect" command/phase. I assume this is when the recent history is incorporated into the memory via a call to the LLM - and then the updated memory is saved. Is this right?
- That makes sense. Now I wonder if it makes sense to have both a conversation_history and a recent_history. Would it be better to just have conversation_history and keep all of the recent interaction data there?
- Yes, please update the Agent class.
- The reflect phase is faling.
- Great. Please add a "help" command that lists the availale commands.
- Right now, reflection only happens when the reflect command is explicitly given. And reflection only incorparates data from tha last n conversation messages.
- Things are really starting to work well. One issue: In general, all user and assistant messages are getting added to the converstation history correctly. However, one of the Assistant responses did not get added to the conversation history. What might cause that?
- Great. Sometimes the LLM is dropping important strutured data and knowledge graph data. We want the memory to be as concise and eficcient as possible, but we do want all useful data to be preserved.
- To improve debugging, please add an optional debug_scope argumment to the LLMService init/constructore. It should be a string or "". It should be prepended to debug logs to identify them.
- Great. Now lets also add a debug_generate_scope to LLMService generate() calls. It should also be prepended to debug logs to identify them.
- It seems that the initiall LLM call to enerate/create the initial memory is working as expected. But then there is another LLM call to update the memory results in a lot of useful data being lost. 1) Is it important to call update immediately after creating the new memory? 2) Is there something wrong with the update call/prompt?
- Yes, please make the changes you have proposed.
- Interactions are getting better. I think that the memory udate and query can be combined into one LLM request. This will make interactions more responsive and it might help keep important data from being inadertently removed from the memory.
- Great. To help troubleshoot the memory, can you make sure that a backup of the memory file is created whenever the memory is saved. Memory backuos should have a suffix like _bak_[n].json i.e. _bak_1.json
- Getting an errror:
- I am noticing that user messages are note being added to the conversation history.
- It seems that the reflect phase is not being triggered.
- It looks like the reflect phase is failing due to a JSON parsing error. But good news: The error is handled gracefully and the interactions continue. Still, need to be able to parse the JSON. It looks ike the LLM is adding a non-JSON preamble:
- Great. Btw: If the LLM suggests and invalid suggested phase, it should be ignored and the standard INTERACTION phase should be used instead.
- Now that we have made all of these changes, will the pytest tests still work?
- getting lots of pytest errors
- Getting better but there are still 14 failures:
- Oh, no. The INTERACTION phase prompt is generating an error because of invalid JSON in response to "where can i get a quest to earn some gold?"
- Still getting an error - before making an LLM call, it seems.
- Still getting an error. Here is the debug log: And the interaction output:
- Now agent and system message are not being added to the conversation history.
- OK. Messages are getting added to the conversation history correctly. BUT ... the query memory phase is deleting a lot of good data again. See agent_memory.json compared to the initial memory agent_memory_bak_28.json
- Had some good interactions but then got an error in the reflect phase:
- 

See:
- `cursor-notes/data/agent-usage-example/agent_interaction_transcript_jan3.txt`
- `cursor-notes/data/agent-usage-example/agent_memory_jan3_1.json`
  - inital
- `cursor-notes/data/agent-usage-example/agent_memory_jan3_2.json`
  - before reflection
- `cursor-notes/data/agent-usage-example/agent_memory_jan3_3.json`
  - after reflection
- `cursor-notes/data/agent-usage-example/agent_memory_jan3_4.json`
  - after next query memory

See: `cursor-notes/logs/agent-usage-example/agent_debug_jan3.log`
