# README-phase-3

## Overall Goals

- Create an Agent Framework tha can be used for a variety of purposes
- Use the Agent Framework as a tool to help continually improve this Agent Framework (i.e. make the framework "self-hosted")
  - Including acting as the project ProjewctManager/ScrumMaster
- Use the Agent Framework to create an Agent that can act like a "Jarvis" in a home workshop to assist with projects and preserve project details - like a voice-driven lab notebook
- Use the Agent Framework to power a DND Dungeon Master agent


## TODO

- Make the logs more useful/readable
- Write all test log data to /logs so it can be easily cleaned-up
- Improve the way topics are assigned to digest segments
- Agent Improvements - RAG Integration
  - RAG should prioritize semantic search results using the segment classifications
    - i.e. filter out user commands (type == command) when only information (type == information)
    - i.e. prioritize segments with higer importance
  - When appropriate, look up other segments in the same conversation entry to see if they should be inclueded
    - might require another LLM call to determine which to include
- Add metadata to track memory usage statistics and performance
- Develop tools for memory visualization and analysis
- Review all tests and fix or clean up as needed
- Figure out how to organize the data in the conversation history into a knowledge graph


## Phase 3 Update - May 06, 2025 - Updated Documentation and Added RAG Support

We've completed several major improvements to the documentation and RAG capabilities:

1. **Comprehensive Documentation Updates**:
- Rewrote main README.md to reflect RAG-enabled, segment-level memory, turn-based compression, and provider-agnostic LLM service
- Completely updated src/memory/README-memory-manager.md:
  - Removed outdated knowledge graph/JSON schema content
  - Described new static_memory/context/conversation_history structure
  - Documented segment-level embeddings, RAG, and turn-based compression
  - Added modern usage, extensibility, and best practices sections
- Updated src/ai/README-ai.md:
  - Clarified support for both text generation and embedding APIs
  - Added modern usage examples for Ollama and OpenAI
  - Explained per-call options and RAG/memory integration
- Updated src/agent/README-agent.md for phase-driven, stateless agent design
- Ensured all docs are concise, up to date, and reflect the current modular, extensible architecture