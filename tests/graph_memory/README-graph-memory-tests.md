# graph-memory-tests

IMPORTAT: Tests must use actual LLM calls

Use these environment variables:

DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large 


### General

In order to test the graph memory entity/node and relationship/edge extraction
- Use the sample_data/graph_data files to simulate an existing graph
  - graph_nodes.json
  - graph_edges.json
- Use sample_data/agent_memory_conversations.json as example conversation entries from which nodes and edges should be extracted
- Use domain-specific configuraion from sample_data/domain_configs.py
  - i.e. D&D specific topic_taxonomy and topic_normalization

The goal is to add all graph-worthy nodes and edges without missing any and without creating redundant/duplicate nodes and edges.


Temp output files should be written to <project-root>/tests/test_files/tmp/ so they can be examined for troubeshooting

Updated graph files (graph_nodes.json and graph_edges.json) should be copied to <project-root>/graph-viewer/public/sample-data so they can be analyzed using the graph-viewer (react app)


### The EntityResolver

This is the most important feature in the graph memory system. For the graph to be constructed in a useful, valuable way, the system need to make sure that meaningful nodes are added to the graph AND that redundnan, dupicate nodes are not. Duplicate nodes fill the graph with noise and make it impossible to query the graph effectively.

There needs to be a good way to test the EntityResolver so that its input is realistic and its output is saved to temp files where it can be analyzed.

Available input data includes:
- Input data: <project-root>/tests/graph_memory/sample_data
  - agent_memory_conversations.json - an example conversation history file containing unstructure data that can be added to the graph
  - graph_data/ - an existing graph that can be used to prepopulate embeddings and a graph for new node resolution testing
    - graph_edges.json
    - graph_metadata.json
    - graph_nodes.json

Logs (including LLM input and output) from graph memory tests should be written to <project-root>/tests/graph_memory/logs so they can be analyzed.


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

### **Running Tests**

```bash
# Quick unit tests (no LLM required)
pytest tests/graph_memory/test_entity_resolver.py -v

# Full integration tests (requires Ollama)
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
pytest tests/graph_memory/test_entity_resolver_real_llm.py -v

# All graph memory tests
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large \
pytest tests/graph_memory/ -v
```




