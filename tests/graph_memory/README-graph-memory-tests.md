# graph-memory-tests

IMPORTANT: Tests must use actual LLM calls

Use these environment variables (with sensible defaults):

OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}
OLLAMA_MODEL=${OLLAMA_MODEL:-gemma3}
OLLAMA_EMBED_MODEL=${OLLAMA_EMBED_MODEL:-mxbai-embed-large}
DEV_MODE=${DEV_MODE:-false}
```

### General

In order to test the graph memory entity/node and relationship/edge extraction
- Use the sample_data/graph_data files to simulate an existing graph
  - graph_nodes.json
  - graph_edges.json
- Use sample_data/agent_memory_conversations.json as example conversation entries from which nodes and edges should be extracted
- Use domain-specific configuration from sample_data/domain_configs.py
  - i.e. D&D specific topic_taxonomy and topic_normalization

The goal is to add all graph-worthy nodes and edges without missing any and without creating redundant/duplicate nodes and edges.


Temp output files should be written to <project-root>/tests/test_files/tmp/ so they can be examined for troubleshooting

Updated graph files (graph_nodes.json and graph_edges.json) should be copied to <project-root>/graph-viewer/public/sample-data so they can be analyzed using the graph-viewer (react app)


### The EntityResolver

This is the most important feature in the graph memory system. For the graph to be constructed in a useful, valuable way, the system needs to make sure that meaningful nodes are added to the graph AND that redundant, duplicate nodes are not. Duplicate nodes fill the graph with noise and make it impossible to query the graph effectively.

There needs to be a good way to test the EntityResolver so that its input is realistic and its output is saved to temp files where it can be analyzed.

Available input data includes:
- Input data: <project-root>/tests/graph_memory/sample_data
  - agent_memory_conversations.json - an example conversation history file containing unstructured data that can be added to the graph
  - graph_data/ - an existing graph that can be used to prepopulate embeddings and a graph for new node resolution testing
    - graph_edges.json
    - graph_metadata.json
    - graph_nodes.json

Logs (including LLM input and output) from graph memory tests should be written to <project-root>/tests/graph_memory/logs so they can be analyzed.

**Note:** Tests now use `LoggingConfig` for consistent logging patterns. Logs are automatically organized by test GUID and component.


## Test Structure (Cleaned Up)

### **Core EntityResolver Tests**

1. **`test_entity_resolver.py`** - **Unit Tests**
   - Mock LLM service for fast, reliable testing
   - Tests basic functionality, parsing, error handling
   - **Use for:** Development and CI/CD

2. **`test_entity_resolver_real_llm.py`** - **Integration Tests**
   - Uses actual Ollama LLM calls
   - Tests individual vs batch processing
   - Tests confidence thresholds
   - Tests RAG candidate selection
   - Tests full graph building workflow
   - Tests full pipeline duplicate detection
   - **Use for:** Validation and real-world testing

### **Relationship Extractor Tests**

3. **`test_relationship_extractor_real_llm.py`** - **Integration Tests**
   - Uses actual Ollama LLM calls
   - Tests relationship extraction from conversations
   - Tests relationship extraction with entity context
   - Tests relationship deduplication and validation
   - **Use for:** Validation of relationship extraction accuracy

### **Running Tests**

# Quick unit tests (no LLM required)
pytest tests/graph_memory/test_entity_resolver.py -v

# Full integration tests (requires Ollama)
# Uses environment variables with defaults to localhost
OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
pytest tests/graph_memory/test_entity_resolver_real_llm.py -v

# Relationship extractor tests
OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
pytest tests/graph_memory/test_relationship_extractor_real_llm.py -v

# All graph memory tests
OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
pytest tests/graph_memory/ -v