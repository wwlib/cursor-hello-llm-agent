# WebSocket Log Streaming

This document explains how to use the WebSocket log streaming feature to display agent service logs in real-time in the web UI.

## Overview

The WebSocket log streaming feature allows the web UI to receive real-time log messages from different components of the agent system. This enables displaying logs in dedicated tabs for better debugging and monitoring.

## Available Log Sources

Each agent session can stream logs from the following sources:

- **`agent`** - Main agent processing logs
- **`memory_manager`** - Memory management and storage logs
- **`ollama_general`** - General LLM service logs
- **`ollama_digest`** - Memory digest generation logs
- **`ollama_embed`** - Embedding generation logs
- **`api`** - General API request/response logs

## WebSocket Message Types

### 1. Get Available Log Sources

Request available log sources for a session:

```json
{
  "type": "get_log_sources",
  "data": {}
}
```

Response:
```json
{
  "type": "log_sources_response",
  "data": {
    "session_id": "session-uuid",
    "available_sources": ["agent", "memory_manager", "ollama_general", "ollama_digest", "ollama_embed", "api"],
    "subscription_status": {
      "agent": ["connection-id-1"],
      "api": ["connection-id-1", "connection-id-2"]
    },
    "timestamp": "2025-01-13T10:30:00.000Z"
  }
}
```

### 2. Subscribe to Log Sources

Subscribe to specific log sources:

```json
{
  "type": "subscribe_logs",
  "data": {
    "connection_id": "your-connection-id",
    "log_sources": ["agent", "memory_manager", "api"]
  }
}
```

Response:
```json
{
  "type": "logs_subscribed",
  "data": {
    "session_id": "session-uuid",
    "connection_id": "your-connection-id",
    "log_sources": ["agent", "memory_manager", "api"],
    "timestamp": "2025-01-13T10:30:00.000Z"
  }
}
```

### 3. Receive Log Messages

Once subscribed, you'll receive log messages in real-time:

```json
{
  "type": "log_stream",
  "data": {
    "timestamp": "2025-01-13T10:30:15.123Z",
    "level": "INFO",
    "logger": "agent.session_abc123",
    "message": "Processing user query: 'Tell me about dragons'",
    "source": "agent",
    "session_id": "session-uuid",
    "module": "agent",
    "function": "process_message",
    "line": 145
  }
}
```

### 4. Unsubscribe from Log Sources

Unsubscribe from specific or all log sources:

```json
{
  "type": "unsubscribe_logs",
  "data": {
    "connection_id": "your-connection-id",
    "log_sources": ["api"]  // Optional: omit to unsubscribe from all
  }
}
```

Response:
```json
{
  "type": "logs_unsubscribed",
  "data": {
    "session_id": "session-uuid",
    "connection_id": "your-connection-id",
    "log_sources": ["api"],
    "timestamp": "2025-01-13T10:30:00.000Z"
  }
}
```

## Implementation in Web UI

### 1. Basic Setup

```javascript
// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/sessions/${sessionId}`);

// Handle connection establishment
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'connection_established') {
    const connectionId = message.data.connection_id;
    // Store connection ID for future use
    subscribeToLogs(connectionId);
  }
};

function subscribeToLogs(connectionId) {
  // Subscribe to desired log sources
  ws.send(JSON.stringify({
    type: 'subscribe_logs',
    data: {
      connection_id: connectionId,
      log_sources: ['agent', 'memory_manager', 'api']
    }
  }));
}
```

### 2. Handle Log Messages

```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'log_stream':
      handleLogMessage(message.data);
      break;
    case 'logs_subscribed':
      console.log('Subscribed to logs:', message.data.log_sources);
      break;
    // ... handle other message types
  }
};

function handleLogMessage(logData) {
  const { source, level, message, timestamp } = logData;
  
  // Add to appropriate log tab
  addLogToTab(source, {
    timestamp: new Date(timestamp),
    level: level,
    message: message,
    logger: logData.logger,
    module: logData.module,
    function: logData.function,
    line: logData.line
  });
}
```

### 3. Log Tab Implementation

```jsx
// React component example
function LogTabs({ sessionId }) {
  const [logs, setLogs] = useState({
    agent: [],
    memory_manager: [],
    api: [],
    ollama_general: [],
    ollama_digest: [],
    ollama_embed: []
  });
  
  const [activeTab, setActiveTab] = useState('agent');
  
  const addLogToTab = (source, logEntry) => {
    setLogs(prev => ({
      ...prev,
      [source]: [...prev[source], logEntry].slice(-1000) // Keep last 1000 logs
    }));
  };
  
  return (
    <div className="log-viewer">
      <div className="log-tabs">
        {Object.keys(logs).map(source => (
          <button
            key={source}
            onClick={() => setActiveTab(source)}
            className={`tab ${activeTab === source ? 'active' : ''}`}
          >
            {source} ({logs[source].length})
          </button>
        ))}
      </div>
      
      <div className="log-content">
        <LogList logs={logs[activeTab]} />
      </div>
    </div>
  );
}

function LogList({ logs }) {
  return (
    <div className="log-list">
      {logs.map((log, index) => (
        <div key={index} className={`log-entry log-${log.level.toLowerCase()}`}>
          <span className="log-timestamp">{log.timestamp.toLocaleTimeString()}</span>
          <span className="log-level">{log.level}</span>
          <span className="log-message">{log.message}</span>
          <span className="log-location">{log.module}:{log.function}:{log.line}</span>
        </div>
      ))}
    </div>
  );
}
```

### 4. CSS Styling

```css
.log-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.log-tabs {
  display: flex;
  border-bottom: 1px solid #ccc;
}

.tab {
  padding: 8px 16px;
  border: none;
  background: #f5f5f5;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab.active {
  background: white;
  border-bottom-color: #007acc;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.log-entry {
  font-family: monospace;
  font-size: 12px;
  margin-bottom: 2px;
  padding: 4px;
  border-left: 3px solid #ccc;
}

.log-debug { border-left-color: #666; }
.log-info { border-left-color: #007acc; }
.log-warning { border-left-color: #ff9500; }
.log-error { border-left-color: #e74c3c; }

.log-timestamp { color: #666; margin-right: 8px; }
.log-level { font-weight: bold; margin-right: 8px; }
.log-message { margin-right: 8px; }
.log-location { color: #888; font-size: 10px; }
```

## Testing

Use the provided test script to verify log streaming functionality:

```bash
python test_websocket_log_streaming.py
```

Or run the comprehensive WebSocket tests:

```bash
python scripts/api/test_websocket_api.py
```

## Log Levels

The following log levels are supported:

- **DEBUG** - Detailed diagnostic information
- **INFO** - General information about system operation
- **WARNING** - Something unexpected happened but the system continues
- **ERROR** - A serious problem occurred
- **CRITICAL** - A very serious error occurred

## Performance Considerations

- Logs are streamed in real-time and can be high-volume
- Consider implementing client-side filtering and pagination
- Limit the number of logs stored in memory (e.g., last 1000 per tab)
- Use efficient data structures for log storage and display
- Implement auto-scroll and scroll-to-bottom functionality

## Cleanup

Log subscriptions are automatically cleaned up when WebSocket connections close. The system handles this gracefully and removes all associated subscriptions. 