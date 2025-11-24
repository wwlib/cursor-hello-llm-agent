#!/usr/bin/env python3
"""
WebSocket API Test Script

Tests all WebSocket API endpoints and message types for the agent system.
This script validates the WebSocket implementation described in README-phase-6-status-week-2.md.
"""

import asyncio
import json
import logging
import websockets
import requests
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"
TEST_USER_ID = "test_user_websocket"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketAPITester:
    """Comprehensive WebSocket API testing class"""
    
    def __init__(self, api_base_url: str = API_BASE_URL, ws_base_url: str = WS_BASE_URL):
        self.api_base_url = api_base_url
        self.ws_base_url = ws_base_url
        self.created_sessions = []
        self.test_results = {}
    
    def print_test_header(self, test_name: str):
        """Print formatted test header"""
        print(f"\n{'='*60}")
        print(f"  {test_name}")
        print(f"{'='*60}")
    
    def print_result(self, success: bool, message: str, data: Any = None):
        """Print test result with formatting"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")
        if data:
            print(f"   Data: {str(data)[:200]}...")
    
    def create_test_session(self) -> Optional[str]:
        """Create a test session using REST API"""
        session_config = {
            "config": {
                "domain": "dnd",
                "enable_graph": True,
                "max_memory_size": 1000
            },
            "user_id": TEST_USER_ID
        }
        
        try:
            response = requests.post(f"{self.api_base_url}/api/v1/sessions", json=session_config)
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                self.created_sessions.append(session_id)
                print(f"✅ Test session created: {session_id}")
                return session_id
            else:
                print(f"❌ Failed to create session: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Session creation failed: {e}")
            return None
    
    def cleanup_session(self, session_id: str):
        """Clean up a test session"""
        try:
            response = requests.delete(f"{self.api_base_url}/api/v1/sessions/{session_id}")
            if response.status_code == 200:
                print(f"✅ Session {session_id} cleaned up")
                if session_id in self.created_sessions:
                    self.created_sessions.remove(session_id)
            else:
                print(f"⚠️  Failed to cleanup session {session_id}: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Session cleanup error: {e}")
    
    async def test_websocket_connection(self, session_id: str) -> bool:
        """Test basic WebSocket connection"""
        self.print_test_header("WebSocket Connection")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Wait for connection confirmation
                try:
                    connection_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    connection_data = json.loads(connection_msg)
                    self.print_result(True, f"WebSocket connected successfully", connection_data)
                    return True
                except asyncio.TimeoutError:
                    self.print_result(True, "Connected (no initial message)", None)
                    return True
                    
        except Exception as e:
            self.print_result(False, f"WebSocket connection failed: {e}")
            return False
    
    async def test_ping_pong(self, session_id: str) -> bool:
        """Test ping/pong message exchange"""
        self.print_test_header("Ping/Pong Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "data": {
                        "message": "Hello WebSocket!",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket.send(json.dumps(ping_message))
                
                # Wait for pong response
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong_response)
                
                success = pong_data.get("type") in ["pong", "ping_response"]
                self.print_result(success, f"Ping/Pong exchange", pong_data)
                return success
                
        except Exception as e:
            self.print_result(False, f"Ping/Pong test failed: {e}")
            return False
    
    async def test_get_status(self, session_id: str) -> bool:
        """Test get_status message type"""
        self.print_test_header("Get Status Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"🔍 Connected to WebSocket for status test")
                
                # Skip connection message if present
                try:
                    initial_msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    print(f"🔍 Skipped initial message: {initial_msg[:100]}...")
                except asyncio.TimeoutError:
                    print(f"🔍 No initial message to skip")
                
                # Send status request
                status_message = {
                    "type": "get_status",
                    "data": {}
                }
                
                print(f"🔍 Sending status message: {status_message}")
                await websocket.send(json.dumps(status_message))
                print(f"🔍 Status message sent, waiting for response...")
                
                # Wait for status response with more detailed timeout handling
                try:
                    status_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"🔍 Received status response: {status_response[:200]}...")
                    status_data = json.loads(status_response)
                    
                    success = status_data.get("type") in ["status_response", "status"]
                    self.print_result(success, f"Status retrieval", status_data)
                    return success
                    
                except asyncio.TimeoutError:
                    print(f"🔍 Timeout waiting for status response")
                    self.print_result(False, f"Status test timed out after 5 seconds")
                    return False
                
        except Exception as e:
            print(f"🔍 Exception in status test: {e}")
            self.print_result(False, f"Get status test failed: {e}")
            return False
    
    async def test_agent_query(self, session_id: str) -> bool:
        """Test agent query with typing indicators and streaming"""
        self.print_test_header("Agent Query Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send query message
                query_message = {
                    "type": "query",
                    "data": {
                        "message": "Hello! Can you tell me about dragons in D&D? This is a WebSocket test.",
                        "context": {"test": True, "websocket": True}
                    }
                }
                
                await websocket.send(json.dumps(query_message))
                
                # Collect all responses
                responses = []
                timeout_count = 0
                max_timeout = 5
                
                while timeout_count < max_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        
                        print(f"📨 Received: {response_data['type']}")
                        
                        # Stop if we get the final response
                        if response_data.get("type") in ["query_response", "response"]:
                            break
                            
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        print(f"⏰ Timeout {timeout_count}/{max_timeout}")
                
                success = len(responses) > 0 and any(
                    r.get("type") in ["query_response", "response"] for r in responses
                )
                
                self.print_result(success, f"Agent query (received {len(responses)} responses)", responses)
                return success
                
        except Exception as e:
            self.print_result(False, f"Agent query test failed: {e}")
            return False
    
    async def test_get_memory(self, session_id: str) -> bool:
        """Test memory data retrieval"""
        self.print_test_header("Get Memory Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send memory request
                memory_message = {
                    "type": "get_memory",
                    "data": {
                        "type": "conversations",
                        "limit": 10,
                        "offset": 0
                    }
                }
                
                await websocket.send(json.dumps(memory_message))
                
                # Wait for memory response
                memory_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                memory_data = json.loads(memory_response)
                
                success = memory_data.get("type") in ["memory_response", "memory"]
                self.print_result(success, f"Memory retrieval", memory_data)
                return success
                
        except Exception as e:
            self.print_result(False, f"Get memory test failed: {e}")
            return False
    
    async def test_search_memory(self, session_id: str) -> bool:
        """Test memory search functionality"""
        self.print_test_header("Search Memory Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send search request
                search_message = {
                    "type": "search_memory",
                    "data": {
                        "query": "dragon",
                        "limit": 5,
                        "type": "semantic"
                    }
                }
                
                await websocket.send(json.dumps(search_message))
                
                # Wait for search response
                search_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                search_data = json.loads(search_response)
                
                success = search_data.get("type") in ["search_response", "memory_search_response"]
                self.print_result(success, f"Memory search", search_data)
                return success
                
        except Exception as e:
            self.print_result(False, f"Search memory test failed: {e}")
            return False
    
    async def test_get_graph(self, session_id: str) -> bool:
        """Test graph data retrieval"""
        self.print_test_header("Get Graph Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send graph request
                graph_message = {
                    "type": "get_graph",
                    "data": {
                        "format": "json",
                        "include_metadata": True
                    }
                }
                
                await websocket.send(json.dumps(graph_message))
                
                # Wait for graph response
                graph_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                graph_data = json.loads(graph_response)
                
                success = graph_data.get("type") in ["graph_response", "graph"]
                self.print_result(success, f"Graph retrieval", graph_data)
                return success
                
        except Exception as e:
            self.print_result(False, f"Get graph test failed: {e}")
            return False
    
    async def test_heartbeat(self, session_id: str) -> bool:
        """Test heartbeat functionality"""
        self.print_test_header("Heartbeat Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message if present
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                # Send heartbeat
                heartbeat_message = {
                    "type": "heartbeat",
                    "data": {
                        "connection_id": "test_connection",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket.send(json.dumps(heartbeat_message))
                
                # Wait for heartbeat response (may be silent)
                try:
                    heartbeat_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    heartbeat_data = json.loads(heartbeat_response)
                    self.print_result(True, f"Heartbeat with response", heartbeat_data)
                except asyncio.TimeoutError:
                    self.print_result(True, f"Heartbeat (silent acknowledgment)", None)
                
                return True
                
        except Exception as e:
            self.print_result(False, f"Heartbeat test failed: {e}")
            return False
    
    async def test_log_streaming(self, session_id: str) -> bool:
        """Test log streaming functionality"""
        self.print_test_header("Log Streaming Test")
        
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Skip connection message and get connection ID
                connection_id = None
                try:
                    initial_msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    connection_data = json.loads(initial_msg)
                    connection_id = connection_data.get("data", {}).get("connection_id")
                except asyncio.TimeoutError:
                    connection_id = f"{session_id}_test"
                
                # Test 1: Get log sources
                await websocket.send(json.dumps({
                    "type": "get_log_sources",
                    "data": {}
                }))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "log_sources_response":
                    available_sources = response_data.get("data", {}).get("available_sources", [])
                    self.print_result(True, f"Got log sources: {available_sources}")
                else:
                    self.print_result(False, f"Failed to get log sources: {response_data}")
                    return False
                
                # Test 2: Subscribe to logs
                await websocket.send(json.dumps({
                    "type": "subscribe_logs",
                    "data": {
                        "connection_id": connection_id,
                        "log_sources": ["agent", "api"]
                    }
                }))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "logs_subscribed":
                    self.print_result(True, f"Subscribed to logs successfully")
                else:
                    self.print_result(False, f"Failed to subscribe to logs: {response_data}")
                    return False
                
                # Test 3: Unsubscribe from logs
                await websocket.send(json.dumps({
                    "type": "unsubscribe_logs",
                    "data": {
                        "connection_id": connection_id,
                        "log_sources": ["api"]
                    }
                }))
                
                # Look for unsubscribe response among possible log stream messages
                unsubscribe_success = False
                for _ in range(5):  # Check up to 5 messages
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "logs_unsubscribed":
                            unsubscribe_success = True
                            break
                        elif response_data.get("type") == "log_stream":
                            # Skip log stream messages and continue looking
                            continue
                    except asyncio.TimeoutError:
                        break
                
                success = unsubscribe_success
                self.print_result(success, f"Log streaming functionality", {"unsubscribe_received": unsubscribe_success})
                
                return success
                
        except Exception as e:
            self.print_result(False, f"Log streaming test failed: {e}")
            return False
    
    async def test_monitor_websocket(self) -> bool:
        """Test the monitor WebSocket endpoint"""
        self.print_test_header("Monitor WebSocket Test")
        
        monitor_url = f"{self.ws_base_url}/api/v1/ws/monitor"
        
        try:
            async with websockets.connect(monitor_url) as websocket:
                # Wait for connection confirmation
                try:
                    initial_msg = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    initial_data = json.loads(initial_msg)
                    self.print_result(True, f"Monitor connected", initial_data)
                except asyncio.TimeoutError:
                    self.print_result(True, f"Monitor connected (no initial message)", None)
                
                # Send ping to monitor
                ping_message = {
                    "type": "ping",
                    "data": {"timestamp": datetime.now().isoformat()}
                }
                
                await websocket.send(json.dumps(ping_message))
                
                # Wait for pong
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                pong_data = json.loads(pong_response)
                
                success = pong_data.get("type") == "pong"
                self.print_result(success, f"Monitor ping/pong", pong_data)
                return success
                
        except Exception as e:
            self.print_result(False, f"Monitor WebSocket test failed: {e}")
            return False
    
    async def test_invalid_session_websocket(self) -> bool:
        """Test WebSocket connection with invalid session"""
        self.print_test_header("Invalid Session WebSocket Test")
        
        invalid_session_id = "invalid-session-id-12345"
        ws_url = f"{self.ws_base_url}/api/v1/ws/sessions/{invalid_session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # This should fail or close immediately
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    self.print_result(False, "Invalid session should be rejected", None)
                    return False
                except asyncio.TimeoutError:
                    self.print_result(False, "Invalid session should be rejected (timeout)", None)
                    return False
                    
        except websockets.exceptions.ConnectionClosed as e:
            if e.code == 4004:  # Session not found
                self.print_result(True, f"Invalid session properly rejected (code {e.code})", None)
                return True
            else:
                self.print_result(False, f"Unexpected close code {e.code}", None)
                return False
        except Exception as e:
            # Connection should be rejected
            self.print_result(True, f"Invalid session rejected: {e}", None)
            return True
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all WebSocket API tests"""
        print("🚀 Starting WebSocket API Comprehensive Tests")
        print(f"API URL: {self.api_base_url}")
        print(f"WebSocket URL: {self.ws_base_url}")
        print(f"Test User ID: {TEST_USER_ID}")
        
        # Create a test session
        session_id = self.create_test_session()
        if not session_id:
            print("❌ Cannot create session. Aborting tests.")
            return {"session_creation": False}
        
        # Give session time to initialize
        time.sleep(2)
        
        results = {}
        
        # Basic connection tests
        results["websocket_connection"] = await self.test_websocket_connection(session_id)
        results["ping_pong"] = await self.test_ping_pong(session_id)
        results["get_status"] = await self.test_get_status(session_id)
        
        # Agent interaction tests
        results["agent_query"] = await self.test_agent_query(session_id)
        
        # Give time for memory updates
        await asyncio.sleep(2)
        
        # Memory and graph tests
        results["get_memory"] = await self.test_get_memory(session_id)
        results["search_memory"] = await self.test_search_memory(session_id)
        results["get_graph"] = await self.test_get_graph(session_id)
        
        # Connection management tests
        results["heartbeat"] = await self.test_heartbeat(session_id)
        results["log_streaming"] = await self.test_log_streaming(session_id)
        results["monitor_websocket"] = await self.test_monitor_websocket()
        results["invalid_session"] = await self.test_invalid_session_websocket()
        
        return results
    
    def cleanup_sessions(self):
        """Clean up any remaining test sessions"""
        if self.created_sessions:
            print(f"\nCleaning up {len(self.created_sessions)} remaining sessions...")
            for session_id in self.created_sessions.copy():
                self.cleanup_session(session_id)
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("  WEBSOCKET TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        if passed == total:
            print("\n🎉 All WebSocket tests passed! The WebSocket API is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")


async def main():
    """Main test runner"""
    tester = WebSocketAPITester()
    
    try:
        results = await tester.run_all_tests()
        tester.print_summary(results)
    finally:
        # Ensure cleanup
        tester.cleanup_sessions()


if __name__ == "__main__":
    asyncio.run(main()) 