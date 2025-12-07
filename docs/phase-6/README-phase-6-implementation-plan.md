# Phase 6 Implementation Plan: Agent System as a Service

## Overview

Transform the existing agent system into a service-oriented architecture with REST API and MCP (Model Context Protocol) endpoints to enable remote interaction and tool integration.

## Architecture Design

### 1. API Service Layer

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway/Router                        │
├─────────────────────────────────────────────────────────────┤
│  REST API          │  WebSocket API    │  MCP Server       │
│  /api/v1/...       │  /ws/agent        │  /mcp/...         │
├─────────────────────────────────────────────────────────────┤
│                 Agent Service Manager                       │
├─────────────────────────────────────────────────────────────┤
│  Agent Pool        │  Memory Manager   │  Graph Manager    │
│  (Multi-tenant)    │  Service          │  Service          │
└─────────────────────────────────────────────────────────────┘
```

### 2. Core Components

- **API Server**: FastAPI-based REST and WebSocket server
- **Agent Service Manager**: Manages multiple agent instances and sessions
- **MCP Server**: Implements Model Context Protocol for tool integration
- **Session Management**: Handle concurrent agent conversations
- **Authentication**: Basic auth for API access

## Implementation Steps

### Step 1: Create API Foundation (Week 1)

#### 1.1 Setup FastAPI Server
- Create `src/api/` directory structure
- Implement base FastAPI application with middleware
- Add CORS, logging, and error handling

#### 1.2 Agent Service Wrapper
- Create `AgentServiceManager` class
- Implement session-based agent instance management
- Add thread-safe memory access patterns

#### 1.3 Basic REST Endpoints
```python
POST   /api/v1/sessions                    # Create new agent session
GET    /api/v1/sessions/{session_id}       # Get session info
DELETE /api/v1/sessions/{session_id}       # End session

POST   /api/v1/sessions/{session_id}/query # Send query to agent
GET    /api/v1/sessions/{session_id}/memory # Get memory state
GET    /api/v1/sessions/{session_id}/graph  # Get graph data
```

### Step 2: WebSocket Real-time Communication (Week 2)

#### 2.1 WebSocket Handler
- Implement WebSocket endpoint for real-time agent interaction
- Add connection management and heartbeat
- Stream agent responses as they're generated

#### 2.2 Event System
- Create event-driven architecture for agent state changes
- Implement memory update notifications
- Add graph change broadcasts

### Step 3: MCP Server Implementation (Week 3)

#### 3.1 MCP Protocol Integration
- Implement MCP server following the protocol specification
- Create tool definitions for agent capabilities
- Add resource management for memory and graph access

#### 3.2 Tool Endpoints
```python
# MCP Tools
memory_query_tool     # Query agent memory
entity_lookup_tool    # Find entities in graph
relationship_tool     # Query relationships
graph_context_tool    # Get contextual graph data
```

#### 3.3 Resource Definitions
```python
# MCP Resources
memory://session/{id}/conversations
memory://session/{id}/entities
graph://session/{id}/nodes
graph://session/{id}/edges
```

### Step 4: Enhanced Features (Week 4)

#### 4.1 Multi-tenant Support
- Implement user/tenant isolation
- Add per-tenant configuration management
- Create resource usage tracking

#### 4.2 Advanced Memory Operations
- Add bulk memory import/export
- Implement memory search and filtering
- Create memory analytics endpoints

#### 4.3 Graph Visualization API
- Enhance graph data export for web viewers
- Add real-time graph updates via WebSocket
- Implement graph query language support

## Technical Implementation Details

### Directory Structure
```
src/api/
├── __init__.py
├── main.py                    # FastAPI app entry point
├── routers/
│   ├── __init__.py
│   ├── sessions.py            # Session management endpoints
│   ├── agent.py               # Agent interaction endpoints
│   ├── memory.py              # Memory management endpoints
│   └── graph.py               # Graph data endpoints
├── services/
│   ├── __init__.py
│   ├── agent_manager.py       # Agent service management
│   ├── session_manager.py     # Session lifecycle management
│   └── mcp_server.py          # MCP protocol implementation
├── models/
│   ├── __init__.py
│   ├── requests.py            # Pydantic request models
│   ├── responses.py           # Pydantic response models
│   └── sessions.py            # Session data models
├── middleware/
│   ├── __init__.py
│   ├── auth.py                # Authentication middleware
│   ├── cors.py                # CORS configuration
│   └── logging.py             # Request/response logging
└── websocket/
    ├── __init__.py
    ├── manager.py             # WebSocket connection management
    └── handlers.py            # WebSocket message handlers
```

### Configuration Management
```python
# config/api_config.py
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    max_sessions: int = 100
    session_timeout: int = 3600  # 1 hour
    enable_mcp: bool = True
    mcp_port: int = 8001
```

### Session Management
```python
class AgentSession:
    session_id: str
    user_id: str
    agent: Agent
    created_at: datetime
    last_activity: datetime
    config: Dict[str, Any]
    
    def is_expired(self) -> bool:
        return (datetime.now() - self.last_activity).seconds > SESSION_TIMEOUT
```

## API Specification

### REST API Endpoints

#### Session Management
- `POST /api/v1/sessions`
  - Body: `{config: object, user_id?: string}`
  - Response: `{session_id: string, status: string}`

- `GET /api/v1/sessions/{session_id}`
  - Response: `{session_id, user_id, created_at, last_activity, status}`

- `DELETE /api/v1/sessions/{session_id}`
  - Response: `{status: string}`

#### Agent Interaction
- `POST /api/v1/sessions/{session_id}/query`
  - Body: `{message: string, context?: object}`
  - Response: `{response: string, memory_updates?: object, graph_updates?: object}`

#### Memory Management
- `GET /api/v1/sessions/{session_id}/memory`
  - Query params: `?type=conversations|entities|relationships&limit=50&offset=0`
  - Response: `{data: array, total: number, pagination: object}`

- `POST /api/v1/sessions/{session_id}/memory/search`
  - Body: `{query: string, filters?: object}`
  - Response: `{results: array, relevance_scores: array}`

#### Graph Data
- `GET /api/v1/sessions/{session_id}/graph`
  - Query params: `?format=json|d3&include_metadata=true`
  - Response: `{nodes: array, edges: array, metadata: object}`

### WebSocket API

#### Connection
- `WS /api/v1/sessions/{session_id}/ws`
- Authentication via query params or headers

#### Message Types
```json
// Client -> Server
{
  "type": "query",
  "data": {
    "message": "Tell me about Theron",
    "context": {}
  }
}

// Server -> Client
{
  "type": "response",
  "data": {
    "message": "Theron is...",
    "partial": false,
    "memory_updates": [],
    "graph_updates": []
  }
}
```

### MCP Server Specification

#### Tools
1. **memory_query**: Query agent memory with natural language
2. **entity_lookup**: Find specific entities by name or ID
3. **relationship_query**: Query relationships between entities
4. **graph_context**: Get contextual subgraph around entities

#### Resources
1. **Conversations**: Access to agent conversation history
2. **Entities**: Access to extracted entities and their properties
3. **Graph**: Access to relationship graph structure

## Testing Strategy

### Unit Tests
- API endpoint functionality
- Session management logic
- MCP protocol compliance
- WebSocket connection handling

### Integration Tests
- End-to-end agent interaction via API
- Multi-session concurrent access
- Memory consistency across API calls
- Graph data integrity

### Load Tests
- Concurrent session handling
- WebSocket connection limits
- Memory usage under load
- Response time benchmarks

## Deployment Configuration

### Docker Setup
```dockerfile
# Dockerfile.api
FROM python:3.11-slim
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt
COPY src/ /app/src/
WORKDIR /app
EXPOSE 8000 8001
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  agent-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./data:/app/data
    depends_on:
      - ollama
      
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

## Security Considerations

1. **Authentication**: Implement API key or JWT-based auth
2. **Rate Limiting**: Prevent API abuse with request limits
3. **Input Validation**: Sanitize all user inputs
4. **Session Security**: Secure session token generation
5. **CORS**: Proper CORS configuration for web clients

## Monitoring and Observability

1. **Metrics**: Track API usage, response times, error rates
2. **Logging**: Structured logging for debugging and audit
3. **Health Checks**: Endpoint health monitoring
4. **Performance**: Memory usage and session metrics

## Success Criteria

- [ ] REST API functional with all core endpoints
- [ ] WebSocket real-time communication working
- [ ] MCP server compatible with standard MCP clients
- [ ] Multi-session support with proper isolation
- [ ] Complete test coverage (>90%)
- [ ] Load testing passing for 50+ concurrent sessions
- [ ] Documentation and examples for API usage
- [ ] Docker deployment working end-to-end

## Timeline

- **Week 1**: API Foundation + Basic REST endpoints
- **Week 2**: WebSocket implementation + Event system
- **Week 3**: MCP server + Tool integration
- **Week 4**: Enhanced features + Testing + Documentation

## Next Steps for Phase 7

With the API service complete, Phase 7 could focus on:
- Web-based frontend UI for agent interaction
- Mobile API client development  
- Advanced analytics and reporting
- Multi-model agent orchestration
