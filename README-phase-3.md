# README-phase-3

## Overall Goals

- Create an Agent Framework that can be used for a variety of purposes
- Use the Agent Framework as a tool to help continually improve this Agent Framework (i.e. make the framework "self-hosted")
  - Including acting as the project ProjectManager/ScrumMaster
- Use the Agent Framework to create an Agent that can act like a "Jarvis" in a home workshop to assist with projects and preserve project details - like a voice-driven lab notebook
- Use the Agent Framework to power a DND Dungeon Master agent


## TODO

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

## Phase 3 Update – May 12, 2025 – Async Memory, Logging, Preprocessing, and Usability

The Agent Framework has seen significant improvements in memory management, logging, data preprocessing, and usability. Here’s a summary of the most important changes:

### 1. Asynchronous Memory Processing
- Digest generation and embeddings updates are now fully asynchronous.
  - User queries return immediately, while memory operations (digest, embeddings, compression) are processed in the background.
  - The interactive session and agent workflow now gracefully handle pending operations, ensuring data consistency and a responsive user experience.
  - Memory compression is also moved to a background task, further reducing latency.

### 2. Improved Data Preprocessing and Segmentation
- DataPreprocessor now performs a two-step process:
  1. Converts input (including markdown, YAML, or bulleted lists) to prose using the LLM.
  2. Segments the resulting prose into embeddable phrases using the ContentSegmenter.
- Both the prose and the segment array are returned, improving downstream memory and embedding quality.
- The query prompt and preprocessing prompt have been improved for clarity and accuracy.
- A new CLI --config option in agent_usage_example.py allows users to select the domain config for the session, supporting more flexible and domain-specific agent behavior.
- A new example lab_assistant domain config has been added.

### 3. Logging System Overhaul
- All print statements have been replaced with structured logger calls across all major modules:
  - src/agent/agent.py
  - src/memory/memory_manager.py, base_memory_manager.py, simple_memory_manager.py
  - src/memory/digest_generator.py, embeddings_manager.py, memory_compressor.py, content_segmenter.py, data_preprocessor.py, rag_manager.py
  - examples/agent_usage_example.py
- Loggers and file handlers are set to DEBUG level for full traceability.
- User-facing output is now cleanly separated from internal logs, which are written to log files.
- Improved error handling and traceability throughout the memory management and agent workflow.
- Console logging in agent_usage_example.py has been cleaned up to show only user-relevant information.

### 4. Embeddings and Memory Management Refactor
- EmbeddingsManager now includes deduplication:
  - The new deduplicate_embeddings_file() method removes redundant embeddings by text after batch updates, logging the number of unique and removed embeddings.
  - update_embeddings() now logs and returns the number of redundant embeddings removed.
  - The method for incremental embedding addition has been renamed to add_new_embeddings() for clarity.
- All incremental embedding additions now use add_new_embeddings().
- Improved logging and docstrings clarify the distinction between batch and incremental embedding updates.
- General code cleanup and improved naming for maintainability and reliability.

### 5. Usability and Developer Experience
- Refactored logging setup in agent_usage_example.py:
  - All handlers are removed from the root logger to suppress console output.
  - Only a FileHandler is added for the main logger, writing to logs/agent_usage_example.log.
  - The root logger is set to WARNING to suppress all INFO/DEBUG logs globally.
- Argument order in MemoryManager and SimpleMemoryManager constructors has been fixed and standardized.
- All super() calls now use the correct argument order.
- Legacy/incorrect print statements have been removed.

---

### Summary

These changes make the Agent Framework:
- Faster and more responsive (thanks to async memory processing)
- Easier to debug and maintain (due to comprehensive, structured logging)
- More robust and reliable (with deduplicated embeddings and improved error handling)
- More flexible and user-friendly (with better preprocessing, segmentation, and domain config selection)

The framework is now well-positioned for further improvements in RAG, topic assignment, knowledge graph integration, and advanced agent behaviors.

