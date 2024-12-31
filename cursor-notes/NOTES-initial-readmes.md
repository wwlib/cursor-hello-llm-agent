# Notes about using cursor - Initial READMEs

## Creating the project's initial READMEs

### Initial `README.md`

Wrote the initial project README with cursor's help.

Described the `llm-driven-agent-with-session-memory`
- Overview
- Example Use Case - Agent to act as a Dungeon Master for a D&D campaign
- Example Campaign
  - Campaign Details for Phase 1 - A simple, hello world campaign
- Code Design and Architecture
  - Agent Service
  - Agent
  - Memory
    - Memory Manager
    - Knowledge Graph
    - Structured Data
  - AI
    - LLM
    - Prompt Manager
    - Prompt Template
  - Utils


### Memory Manager `README-memory-manager.md`

Then had a **chat** with cursor about the Memory Manager - to produce a detailed README about the Memory Manager

```
Let's design the Memory Manager, initially focusing on processing and storing the Phase 1 (campaig) data.
```

```
This is OK. But a better approach would be more data driven so that the code does not need to contain specific details like "world_description" and "inhabitants". It would be better to assume tha the LLM will be able to accept data in any form and come up with its own representations for the structured data and knowledge graph. Then the memory can be accessed and updated via prompting - without the need for hard-coded data-specific classes.

Given this constraint, how would you design the memory mnager?
```

```
Yes, exactly. Let's imagine an example scenario where Agent prompts the user with a question, asking for the Phase 1 details about the campaign and the user responds with "Campaign Details for Phase 1 - A simple, hello world campaign" from the README. Then the Agent would prompt the LLM to store generate a JSON data structure containing Phase 1 data as well as a knolwedge graph data structure to store the importan relationshipt in the Phase 1 data. This bespoke data format would then be used for the rest of the interactions in the session.

The agent could access and update the data using prompts for the LLM. A Query Prompt would include the accumulated data and ask for a response that uses the data. An Update Prompt would include the accumulated data and as well as new data and ask the LLM to return updated data structures to replace the existing memory.

Please summarize this design using concise, high-level pseudo code and state diagram notation.
```

```
Yes. Now let's design the memory management prompt template: Create Memory Prompt, Query Memory Prompt, Update Memory Prompt.

First, what should the Create Memory Prompt LLM prompt look like - using `{INPUT_DATA}` as the placeholder for the text data provided by the user?
```

```
Yes. Sounds great. Now, please write the memory manager code to populate the memory using the approach described above.
```

```
Great. Please write a detailed README about the memory_manager and the proposed impoementatino approach.
```

### AI (LLM) README

Then continued the **chat** to create a `README-ai.md` for the llm class.

```
Great. Please write a README for the ai llm class. It should define a base class used to interface with llm services. The README should also describe a specialized (subclass) llm_openai.py that uses the openai llm api. The README should also describe a specialized (subclass) llm_ollama.py that uses the ollama llm api.
```

