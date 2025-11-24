# README-agent-api-scripts

## Status ✅ COMPLETE

We have a brand new REST and WebSocket API implementation that is passing tests and working to some extent.

Now, we need to determine where fixes and improvements need to be made.

There is also a new Browser app that calls the API. Before we analyze and troubleshoot the browser app, let's make sure the API is working correctly.

## IMPORTANT
- Start the server using these environment variables:
  - DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python -m 
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000

## Test Scripts Created

### 🧪 test_rest_api.py
Comprehensive REST API testing script that validates all endpoints:
- Session management (create, list, delete, cleanup)
- Agent interaction (status, query processing)
- Memory management (stats, retrieval, search)
- Graph data access (stats, JSON/D3 formats)
- Health checks and error handling

### 🧪 test_websocket_api.py
WebSocket API testing script for real-time communication:
- Connection establishment and management
- All message types (ping/pong, query, status, memory, graph)
- Heartbeat and typing indicators
- Monitor endpoint testing
- Connection cleanup and error scenarios

### 🧪 test_session_manager.py
Focused session manager evaluation:
- Session creation with various configurations
- Agent and memory manager initialization
- Concurrent session handling
- Session persistence and state management
- Session cleanup and resource management

### 🧪 run_api_tests.py
Master test orchestrator that:
- Checks API server availability
- Runs all test suites in sequence
- Provides comprehensive evaluation
- Generates readiness assessment for browser app integration

## Usage

### Quick Start - Run All Tests
```bash
# Start the API server first
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

DEV_MODE=true OLLAMA_BASE_URL=http://192.168.1.173:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, run all tests
python scripts/api/run_api_tests.py
```

### Individual Test Scripts
```bash
# Test session manager specifically
python scripts/api/test_session_manager.py

# Test REST API endpoints
python scripts/api/test_rest_api.py

# Test WebSocket functionality
python scripts/api/test_websocket_api.py
```

## Expected Results

The test scripts will:
1. ✅ Validate that the API server is responding
2. ✅ Test session creation and management
3. ✅ Verify agent initialization and query processing
4. ✅ Check memory and graph data access
5. ✅ Test WebSocket real-time communication
6. ✅ Provide detailed evaluation and readiness assessment

## Next Steps

After running the tests:
1. **If all tests pass**: The API is ready for browser app integration
2. **If some tests fail**: Review output and fix identified issues
3. **If many tests fail**: Debug API implementation before browser app work

The test results will guide whether to proceed with browser app analysis or focus on API fixes first.

## Reference

- ../../README-phase-6-status-week-1.md - REST API details
- ../../README-phase-6-status-week-2.md - WebSocket API details
- ../../src/api - API implementation
- ../../examples/agent_usage_example.py - Pre-API example, runs directly as a CLI interface to the agent system

## TODO
- Create scripts to test both the REST and WebSocket APIs
- Start to evaluate the API session manager to see if it is correctly initializing and running the agent system