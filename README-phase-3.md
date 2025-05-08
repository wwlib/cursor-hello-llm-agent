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
- Rewritten main README.md to reflect RAG-enabled, segment-level memory, turn-based compression, and provider-agnostic LLM service
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

## Phase 3 Update - May 07, 2025 - Improved log management in the code and tests

We've made significant improvements to the logging system and test infrastructure:

1. **Enhanced Logging System**:
   - Added dedicated log files for different services:
     - General service logs for core operations
     - Digest generation logs for memory processing
     - Embedding service logs for RAG operations
   - Improved log organization with GUID-based directory structure
   - Added detailed logging for memory operations and embeddings generation

2. **Test Infrastructure Improvements**:
   - Centralized test log management in `/logs` directory
   - Added automatic cleanup of test logs
   - Improved test output readability with better formatting
   - Enhanced error reporting in test failures

These improvements make the system more maintainable and easier to debug, while providing better visibility into the system's operation and test execution.

