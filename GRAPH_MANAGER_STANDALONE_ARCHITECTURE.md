# Standalone GraphManager Architecture

This document describes the new standalone GraphManager architecture that decouples graph processing from the main agent for improved performance and responsiveness.

## Overview

The standalone architecture separates the computationally intensive graph operations (entity/relationship extraction, embeddings) into a separate background process. This provides:

- **Improved Responsiveness**: Main agent remains responsive while graph processing happens in background
- **Scalability**: Graph processing can be scaled independently
- **Fault Tolerance**: Graph processing failures don't crash the main agent
- **Resource Isolation**: Graph processing can use dedicated resources

## Architecture Components

### 1. Main Agent Process
- Runs the conversational agent with MemoryManager
- Uses `QueueWriter` to send conversation data to standalone process
- Uses `StandaloneGraphQueries` to read graph data for context
- Operates normally without waiting for graph processing

### 2. Standalone GraphManager Process
- Runs independently as `graph_manager_process.py`
- Reads conversation queue from `conversation_queue.jsonl`
- Processes entries using full GraphManager with entity/relationship extraction
- Updates graph files atomically
- Handles crash recovery via metadata

### 3. File-Based Communication
- **Queue File**: `conversation_queue.jsonl` - JSONL file with conversation entries
- **Graph Files**: `graph_nodes.json`, `graph_edges.json`, `graph_metadata.json`
- **Embeddings**: `graph_memory_embeddings.jsonl`
- **Locking**: Uses `filelock` for atomic operations

## File Structure

```
agent_memories/standard/{GUID}/
├── agent_memory.json              # Main memory file
├── agent_memory_conversations.json # Conversation history  
├── agent_memory_graph_data/       # Graph data directory
│   ├── conversation_queue.jsonl   # Queue for standalone process
│   ├── conversation_queue.jsonl.lock # Lock file for queue
│   ├── graph_nodes.json           # Entity storage
│   ├── graph_edges.json           # Relationship storage
│   ├── graph_metadata.json        # Graph statistics
│   ├── graph_memory_embeddings.jsonl # Entity embeddings
│   ├── graph_manager.log          # Standalone process logs
│   └── graph_verbose.log          # Verbose operation logs
└── logs/                          # Agent logs
    ├── ollama_*.log               # LLM service logs
    └── *.log                      # Other component logs
```

## Usage

### 1. Start the Main Agent
```bash
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large

# Start agent with graph memory enabled
python examples/agent_usage_example.py --verbose --guid my_session --config dnd
```

### 2. Start the Standalone GraphManager
```bash
# In a separate terminal
export DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large

# Start standalone process (matches agent config)
python launcher.py --guid my_session --config dnd --verbose
```

### 3. Alternative: Direct Process Start
```bash
# Start GraphManager directly
python graph_manager_process.py --storage-path agent_memories/standard/my_session/agent_memory_graph_data --config dnd --verbose
```

## Key Features

### Atomic Operations
- Queue writes use file locking to prevent corruption
- Graph updates are atomic (temp files + rename)
- Metadata tracks processing state for recovery

### Error Recovery
- Standalone process can restart and resume from last processed entry
- Main agent continues working if standalone process is down
- Graceful degradation: agent works without graph context if needed

### Performance Optimizations
- Batch processing (5-10 entries at once)
- Embedding caching via EmbeddingsManager
- Incremental graph updates only
- Background processing with configurable throttling

### Monitoring and Debugging
- Comprehensive logging in both processes
- Queue size monitoring
- Processing statistics
- Verbose operation logs for troubleshooting

## Configuration

### Domain Configuration
Both processes must use the same domain configuration:

```python
DND_CONFIG = {
    "domain_name": "dnd_campaign",
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["character", "location", "object", "event", "concept", "organization"],
        "relationship_types": ["located_in", "owns", "allies_with", "enemies_with", ...],
        "similarity_threshold": 0.8
    }
    # ... other config
}
```

### Environment Variables
```bash
export DEV_MODE=true                                    # Enable development mode
export OLLAMA_BASE_URL=http://192.168.10.28:11434      # Ollama server URL
export OLLAMA_MODEL=gemma3                              # Primary model
export OLLAMA_EMBED_MODEL=mxbai-embed-large            # Embedding model
```

## API Changes

### MemoryManager Changes
- `self.graph_manager` → `self.graph_queue_writer` + `self.graph_queries`
- Graph processing is queued, not awaited
- Context queries read from files, not live objects

### RAGManager Changes
- `graph_manager` parameter → `graph_queries` parameter
- Same interface for context retrieval
- Works with standalone graph data

## Migration Guide

### From Integrated to Standalone

1. **Update Dependencies**:
   ```bash
   pip install filelock>=3.12.0
   ```

2. **No Agent Code Changes**: The agent code remains the same due to maintained interfaces

3. **Start Processes**: Run both agent and standalone process

4. **Monitor Queue**: Check logs for queue processing status

### Backwards Compatibility
- Old memory files are compatible
- Agent works without standalone process (degraded functionality)
- Graph data format unchanged

## Troubleshooting

### Common Issues

1. **Queue Not Processing**:
   - Check if standalone process is running
   - Verify storage paths match between processes
   - Check file permissions on queue directory

2. **Lock File Issues**:
   - Remove `.lock` files if processes crashed
   - Ensure only one standalone process per storage directory

3. **Configuration Mismatch**:
   - Verify both processes use same domain config
   - Check environment variables are consistent

4. **Performance Issues**:
   - Monitor queue size growth
   - Adjust batch processing size
   - Check available system resources

### Debugging Commands

```bash
# Check queue size
ls -la agent_memories/standard/{guid}/agent_memory_graph_data/

# View recent queue entries  
tail -f agent_memories/standard/{guid}/agent_memory_graph_data/conversation_queue.jsonl

# Monitor standalone process logs
tail -f agent_memories/standard/{guid}/agent_memory_graph_data/graph_manager.log

# Test architecture
python test_standalone_architecture.py
```

## Performance Characteristics

### Before (Integrated)
- Graph processing blocks agent responses
- Memory usage spikes during entity extraction
- Single point of failure

### After (Standalone)  
- Agent responds immediately
- Consistent memory usage in main process
- Isolated failure domains
- Scalable graph processing

### Typical Performance
- Queue write: < 1ms
- Context query: < 10ms  
- Graph processing: 30-120s per conversation (background)
- Agent responsiveness: Unaffected by graph processing

## Future Enhancements

- Multiple standalone processes for load balancing
- SQLite queue for better performance at scale
- Process management with supervisord
- Metrics and monitoring dashboard
- Graph data compression and archival