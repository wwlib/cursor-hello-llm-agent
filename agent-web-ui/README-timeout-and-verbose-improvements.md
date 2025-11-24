# Web UI Timeout and Verbose Status Improvements

This document outlines the improvements made to the agent web UI to handle long initialization timeouts and display real-time verbose status messages.

## Overview

The web UI has been enhanced to:

1. **Handle Long Operations**: Graph memory initialization can take 120+ seconds, which previously caused timeouts
2. **Real-time Status Updates**: Display detailed verbose status messages showing exactly what the agent is doing
3. **Better User Experience**: Clear feedback during long operations so users know the system is working

## Key Improvements

### 1. Enhanced WebSocket Connection Handling

**File**: `src/services/websocket.ts`

**Changes**:
- **Increased timeout resilience**: Connection timeout extended to 10 seconds
- **Exponential backoff**: Reconnection delays increase progressively (2s, 4s, 6s, 8s, 10s max)
- **More reconnection attempts**: Increased from 5 to 10 attempts
- **Better heartbeat**: Heartbeat every 30 seconds with connection state checking
- **Improved error handling**: Better distinction between normal closes and errors

**Benefits**:
- Handles network hiccups during long operations
- Maintains connection during 120+ second graph initialization
- Automatic recovery from temporary disconnections

### 2. Verbose Status Message System

**New Files**:
- `src/types/api.ts` - Added verbose status TypeScript definitions
- `src/components/ui/VerboseStatusDisplay.tsx` - Real-time status display component
- `src/stores/verboseStore.ts` - State management for verbose messages

**New WebSocket Message Types**:
- `subscribe_verbose` - Subscribe to verbose status updates
- `unsubscribe_verbose` - Unsubscribe from verbose status
- `verbose_status` - Real-time status message from server

**Message Format**:
```json
{
  "type": "verbose_status",
  "data": {
    "message_type": "status|success|warning|error",
    "message": "Processing entity 1/10: Elena",
    "level": 6,
    "duration": 5.34,
    "timestamp": "2025-09-02T11:15:00.000Z",
    "session_id": "uuid",
    "operation_stack": ["Building knowledge graph", "Stage 3: Resolving entities"]
  }
}
```

### 3. Enhanced Chat Interface

**File**: `src/features/chat/ChatInterface.tsx`

**Improvements**:
- **Automatic verbose subscription**: Subscribes to verbose status when WebSocket connects
- **Integrated status display**: Shows verbose status panel below chat messages
- **Message clearing**: Clears previous verbose messages when sending new queries

**New UI Elements**:
- **Verbose Status Display**: Collapsible panel showing real-time processing steps
- **Hierarchical indentation**: Shows operation nesting (Level 0-7 supported)
- **Timing information**: Displays duration for completed operations
- **Status icons**: Visual indicators (🔄 status, ✅ success, ⚠️ warning, ❌ error)

### 4. Improved Typing Indicator

**File**: `src/features/chat/TypingIndicator.tsx`

**Enhancements**:
- **Long operation detection**: Automatically detects operations > 10 seconds
- **Elapsed time display**: Shows running timer for long operations
- **Visual differentiation**: Blue styling for long operations vs. gray for normal
- **Helpful context**: Explains what long operations are (memory creation, entity resolution)

**Example Messages**:
- Normal: "Agent is typing"
- Long operation: "Processing complex operation... (45s)"
- Help text: "This may take a while for complex operations like initial memory creation or entity resolution"

### 5. Enhanced Chat Store

**File**: `src/stores/chatStore.ts`

**New State**:
- `isLongOperation: boolean` - Tracks if current operation is long-running
- `operationStartTime: number | null` - Timestamp when operation started

**New Logic**:
- **Long operation detection**: Automatically flags operations > 10 seconds
- **Better error handling**: Improved error message extraction from WebSocket responses
- **Connection state management**: Handles connection establishment events

## User Experience Improvements

### Before These Changes
- ❌ Web UI would timeout during long operations (120+ seconds)
- ❌ No visibility into what the agent was doing
- ❌ Users unsure if system was stuck or working
- ❌ Poor feedback during complex operations

### After These Changes
- ✅ **Complete transparency**: Users see exactly what's happening
- ✅ **No more timeouts**: Robust connection handling for long operations
- ✅ **Real-time feedback**: Live updates during processing
- ✅ **Hierarchical detail**: From high-level operations down to individual entity processing
- ✅ **Timing information**: Know exactly how long each step takes

## Example Verbose Status Flow

When a user sends their first message to a new session, they now see:

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
✅       Found 9 important segments (0.02s)
🔄       Preparing text for entity extraction...
✅       Prepared 1238 chars for processing (0.01s)
🔄       Extracting entities and relationships...
🔄         Stage 1: Extracting candidate entities...
✅         Found 10 candidate entities (2.34s)
🔄         Stage 2: Converting to resolver candidates...
✅         Prepared 10 candidates for resolution (0.15s)
🔄         Stage 3: Resolving entities (this may take time)...
🔄           Processing 10 entities individually...
🔄             Resolving entity 1/10: Elena...
🔄               Searching for similar entities...
✅               No similar entities found (0.23s)
🔄               Calling LLM for entity resolution...
✅               Will create new entity (confidence: 0.00) (5.11s)
✅             Resolving entity 1/10: Elena (5.34s)
... (continues for all 10 entities)
✅           Individual processing completed (53.67s)
✅         Resolved 10 entities (53.82s)
✅       Extracted 10 entities, 7 relationships (56.31s)
✅     Building knowledge graph from domain data (119.92s)
```

## Technical Architecture

### WebSocket Message Flow

```
Web Client                    API Server
    |                             |
    |-- subscribe_verbose ------->|
    |<-- verbose_subscribed ------|
    |                             |
    |-- query ------------------>|
    |<-- typing_start ------------|
    |<-- verbose_status ----------| (multiple messages)
    |<-- verbose_status ----------|
    |<-- verbose_status ----------|
    |<-- query_response ----------|
    |<-- typing_end --------------|
```

### Component Hierarchy

```
ChatInterface
├── VerboseStatusDisplay (new)
│   ├── Collapsible header
│   ├── Message list with hierarchical indentation
│   └── Auto-scroll to latest
├── MessageList
├── TypingIndicator (enhanced)
└── LogPanel
```

### State Management

```
verboseStore
├── messages: VerboseStatusMessage[]
├── isSubscribed: boolean
├── isVisible: boolean
└── currentSessionId: string | null

chatStore (enhanced)
├── isLongOperation: boolean (new)
├── operationStartTime: number | null (new)
└── existing chat state...
```

## Environment Variables

To enable verbose status streaming on the API server:

```bash
# Enable verbose mode for all sessions
VERBOSE=true DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## Benefits for Troubleshooting

The enhanced web UI is now an excellent troubleshooting tool:

1. **Performance Analysis**: See exactly which operations take the most time
2. **Progress Tracking**: Monitor long-running operations in real-time  
3. **Error Diagnosis**: Clear error messages with context
4. **System Understanding**: Visibility into the agent's internal processes
5. **User Confidence**: Users know the system is working, not stuck

## Compatibility

- ✅ **Backward compatible**: All existing functionality preserved
- ✅ **Graceful degradation**: Works with or without verbose status enabled
- ✅ **Optional feature**: Can be enabled/disabled via environment variables
- ✅ **No breaking changes**: Existing API contracts maintained

The web UI now provides the same detailed visibility that was previously only available in the CLI, making it an excellent tool for both users and developers to understand what the agent system is doing during complex operations.

