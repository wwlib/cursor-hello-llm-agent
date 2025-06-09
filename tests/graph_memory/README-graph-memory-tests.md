# graph-memory-tests

IMPORTAT: Tests must use actual LLM calls

Use these environment variables:

DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large 

In order to test the graph memory entity/node and relationship/edge extraction
- Use the sample_data/graph_data files to simulate an existing graph
  - graph_nodes.json
  - graph_edges.json
- Use sample_data/agent_memory_conversations.json as example conversation entries from which nodes and edges should be extracted
- Use domain-specific configuraion from sample_data/domain_configs.py
  - i.e. D&D specific topic_taxonomy and topic_normalization

The goal is to add all graph-worthy nodes and edges without missing any and without creating redundant/duplicate nodes and edges.


Temp output files should be written to tests/test_files/tmp so they can be examined for troubeshooting

Uopdated graph files (graph_nodes.json and graph_edges.json) should be copied to graph-viewer/public/sample-data so they can be analyzed using the graph-viewer (react app)

