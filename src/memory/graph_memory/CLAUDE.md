The graph_manager's graph processor now works as a standalone "service" that process input from a queue.

The memory_manager can write to the queue, currently via queue_writer

The graph_manager works when started independently, like:

export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large; python launcher.py --create-storage --guid sep21_graph_test_1

If memory_manager data files already exist, the graph processing queue can be populated using:

python populate_queue_from_conversations.py --guid sep21_graph_test_1