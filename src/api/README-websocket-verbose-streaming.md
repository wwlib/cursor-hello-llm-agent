# WebSocket Verbose Status Streaming

This document explains how to use the WebSocket verbose status streaming feature to display real-time agent processing status in the web UI.

## Overview

The WebSocket verbose status streaming feature allows web clients to receive real-time status updates during agent processing operations. This provides detailed visibility into:

- Initial memory creation steps (preprocessing, digest generation, embeddings, graph memory)
- Entity extraction and resolution progress
- Individual entity processing with timing
- Background processing status

## Enabling Verbose Mode

### For API Service

Set the `VERBOSE` environment variable when starting the API service:

```bash
# Enable verbose streaming for all sessions
VERBOSE=true DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Per-Session Configuration

The verbose mode is determined when a session is created. If `VERBOSE=true` is set, all new sessions will have verbose streaming enabled.

## WebSocket Message Types

### 1. Subscribe to Verbose Status

Subscribe to receive verbose status updates for a session:

```json
{
  "type": "subscribe_verbose",
  "data": {}
}
```

Response:
```json
{
  "type": "verbose_subscribed",
  "data": {
    "session_id": "session-uuid",
    "connection_id": "connection-uuid",
    "timestamp": "2025-09-02T10:30:00.000Z"
  }
}
```

### 2. Unsubscribe from Verbose Status

Unsubscribe from verbose status updates:

```json
{
  "type": "unsubscribe_verbose",
  "data": {}
}
```

Response:
```json
{
  "type": "verbose_unsubscribed",
  "data": {
    "session_id": "session-uuid",
    "connection_id": "connection-uuid",
    "timestamp": "2025-09-02T10:30:00.000Z"
  }
}
```

### 3. Receive Verbose Status Messages

Once subscribed, you'll receive real-time verbose status messages:

```json
{
  "type": "verbose_status",
  "data": {
    "message_type": "status",
    "message": "Preprocessing domain data...",
    "level": 2,
    "duration": null,
    "timestamp": "2025-09-02T10:30:00.000Z",
    "session_id": "session-uuid",
    "operation_stack": ["Processing initial domain data", "Converting domain data to prose format"]
  }
}
```

```json
{
  "type": "verbose_status",
  "data": {
    "message_type": "success",
    "message": "Preprocessing domain data",
    "level": 2,
    "duration": 16.90,
    "timestamp": "2025-09-02T10:30:16.900Z",
    "session_id": "session-uuid",
    "operation_stack": ["Processing initial domain data"]
  }
}
```

## Message Types

### Status Message Types

- **`status`**: Indicates an operation is starting or in progress
- **`success`**: Indicates an operation completed successfully (includes timing)
- **`warning`**: Indicates a non-critical issue or fallback behavior
- **`error`**: Indicates an error occurred during processing

### Hierarchical Levels

The `level` field indicates the nesting depth of operations:

- **Level 0**: Top-level operations (e.g., "Processing query")
- **Level 1**: Main sub-operations (e.g., "Enhancing query with RAG", "Generating response")
- **Level 2**: Detailed sub-operations (e.g., "Preprocessing domain data", "Building knowledge graph")
- **Level 3**: Graph processing stages (e.g., "Analyzing digest segments", "Extracting entities")
- **Level 4**: Entity processing stages (e.g., "Stage 1: Extracting candidates")
- **Level 5**: Individual processing (e.g., "Processing 10 entities individually")
- **Level 6**: Per-entity operations (e.g., "Resolving entity 1/10: Elena")
- **Level 7**: Entity sub-steps (e.g., "Searching for similar entities", "Calling LLM")

## Example Usage in JavaScript

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/sessions/your-session-id');

// Subscribe to verbose status updates
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'subscribe_verbose',
        data: {}
    }));
};

// Handle verbose status messages
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'verbose_status') {
        const { message_type, message: text, level, duration, timestamp } = message.data;
        
        // Create indentation based on level
        const indent = '  '.repeat(level);
        
        // Format message with appropriate emoji and timing
        let formattedMessage;
        switch (message_type) {
            case 'status':
                formattedMessage = `🔄 ${indent}${text}`;
                break;
            case 'success':
                const timing = duration ? ` (${duration.toFixed(2)}s)` : '';
                formattedMessage = `✅ ${indent}${text}${timing}`;
                break;
            case 'warning':
                formattedMessage = `⚠️ ${indent}${text}`;
                break;
            case 'error':
                formattedMessage = `❌ ${indent}${text}`;
                break;
        }
        
        // Display in your UI
        console.log(formattedMessage);
        // Or append to a status display area
        document.getElementById('status-log').innerHTML += formattedMessage + '<br>';
    }
};
```

## Example Verbose Status Flow

Here's what a typical verbose status flow looks like during initial memory creation:

```
🔄 Processing initial domain data...
🔄   This may take a moment for complex domains...
🔄   Converting domain data to prose format...
🔄     Preprocessing domain data...
✅     Preprocessing domain data (16.90s)
🔄     Generating digest for domain data...
✅     Generating digest for domain data (24.94s)
🔄     Creating embeddings for semantic search...
✅     Creating embeddings for semantic search (0.46s)
🔄     Building knowledge graph from domain data...
🔄       Analyzing digest segments...
✅       Found 9 important segments
🔄       Preparing text for entity extraction...
✅       Prepared 1238 chars for processing
🔄       Extracting entities and relationships...
🔄         Stage 1: Extracting candidate entities...
✅         Found 10 candidate entities
🔄         Stage 2: Converting to resolver candidates...
✅         Prepared 10 candidates for resolution
🔄         Stage 3: Resolving entities (this may take time)...
🔄           Processing 10 entities individually...
🔄             Resolving entity 1/10: The Lost Valley...
🔄               Searching for similar entities...
✅               No similar entities found
🔄               Calling LLM for entity resolution...
✅               Will create new entity (confidence: 0.00)
✅             Resolving entity 1/10: The Lost Valley (5.34s)
... (continues for all 10 entities)
✅           Individual processing completed
✅         Resolved 10 entities
✅       Extracted 10 entities, 7 relationships
✅     Building knowledge graph from domain data (119.92s)
```

## Integration with Existing Features

### Compatibility with Log Streaming

Verbose status streaming works alongside the existing log streaming feature:

- **Log streaming**: Provides detailed technical logs from various components
- **Verbose status**: Provides user-friendly progress updates with timing

### Performance Profiles

Verbose status respects the performance profile settings:

- **Speed profile**: Shows simplified processing steps
- **Balanced profile**: Shows standard processing with some optimizations
- **Comprehensive profile**: Shows full detailed processing including all entity resolution steps

## Environment Variables

- **`VERBOSE`**: Enable/disable verbose status streaming (`true`/`false`)
- **`OLLAMA_BASE_URL`**: Ollama service URL (required for agent operations)
- **`OLLAMA_MODEL`**: LLM model to use (e.g., `gemma3`)
- **`OLLAMA_EMBED_MODEL`**: Embeddings model (e.g., `mxbai-embed-large`)

## Benefits

1. **Complete Transparency**: Users see exactly what's happening during long operations
2. **Performance Insights**: Timing information helps identify bottlenecks
3. **Real-time Feedback**: No more wondering "is it stuck or just slow?"
4. **Hierarchical Detail**: Multiple levels of detail from high-level operations to individual entity processing
5. **WebSocket Efficiency**: Real-time updates without polling
6. **Backward Compatible**: Works alongside existing logging and doesn't break CLI usage

The verbose status streaming provides the same detailed visibility that was added to the CLI, but now available to web clients in real-time!


