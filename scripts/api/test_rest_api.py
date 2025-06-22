#!/usr/bin/env python3
"""
REST API Test Script

Tests all REST API endpoints for the agent system to ensure proper functionality.
This script validates the API implementation described in README-phase-6-status-week-1.md.
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_rest"

class RestAPITester:
    """Comprehensive REST API testing class"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.created_sessions = []
    
    def print_test_header(self, test_name: str):
        """Print formatted test header"""
        print(f"\n{'='*60}")
        print(f"  {test_name}")
        print(f"{'='*60}")
    
    def print_result(self, success: bool, message: str, response_data: Any = None):
        """Print test result with formatting"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")
        if response_data and isinstance(response_data, dict):
            print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
        elif response_data:
            print(f"   Response: {str(response_data)[:200]}...")
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        self.print_test_header("Health Check")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            success = response.status_code == 200
            data = response.json() if response.status_code == 200 else response.text
            
            self.print_result(success, f"Health check (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Health check failed with exception: {e}")
            return False
    
    def test_session_creation(self) -> Optional[str]:
        """Test session creation endpoint"""
        self.print_test_header("Session Creation")
        
        session_config = {
            "config": {
                "domain": "dnd",
                "llm_model": "gemma3",
                "embed_model": "mxbai-embed-large",
                "max_memory_size": 1000,
                "enable_graph": True,
                "custom_config": {"test_mode": True}
            },
            "user_id": TEST_USER_ID
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/sessions",
                json=session_config
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                session_id = data.get("session_id")
                self.created_sessions.append(session_id)
                self.print_result(True, f"Session created: {session_id}", data)
                return session_id
            else:
                self.print_result(False, f"Session creation failed (HTTP {response.status_code})", response.text)
                return None
                
        except Exception as e:
            self.print_result(False, f"Session creation failed with exception: {e}")
            return None
    
    def test_session_info(self, session_id: str) -> bool:
        """Test getting session information"""
        self.print_test_header("Session Information")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Get session info (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Get session info failed with exception: {e}")
            return False
    
    def test_session_list(self) -> bool:
        """Test listing all sessions"""
        self.print_test_header("Session List")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/sessions")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"List sessions (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"List sessions failed with exception: {e}")
            return False
    
    def test_agent_status(self, session_id: str) -> bool:
        """Test getting agent status"""
        self.print_test_header("Agent Status")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}/status")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Get agent status (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Get agent status failed with exception: {e}")
            return False
    
    def test_agent_query(self, session_id: str) -> bool:
        """Test sending a query to the agent"""
        self.print_test_header("Agent Query")
        
        query_data = {
            "message": "Hello! Can you tell me about dragons in D&D? This is a test query.",
            "context": {
                "test_mode": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/query",
                json=query_data
            )
            
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Agent query (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Agent query failed with exception: {e}")
            return False
    
    def test_memory_stats(self, session_id: str) -> bool:
        """Test getting memory statistics"""
        self.print_test_header("Memory Statistics")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}/memory/stats")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Memory stats (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Memory stats failed with exception: {e}")
            return False
    
    def test_memory_retrieval(self, session_id: str) -> bool:
        """Test retrieving memory data"""
        self.print_test_header("Memory Retrieval")
        
        try:
            # Test with pagination parameters
            params = {
                "type": "conversations",
                "limit": 10,
                "offset": 0
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/memory",
                params=params
            )
            
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Memory retrieval (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Memory retrieval failed with exception: {e}")
            return False
    
    def test_memory_search(self, session_id: str) -> bool:
        """Test searching memory contents"""
        self.print_test_header("Memory Search")
        
        search_data = {
            "query": "dragon",
            "limit": 5,
            "type": "semantic"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/memory/search",
                json=search_data
            )
            
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Memory search (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Memory search failed with exception: {e}")
            return False
    
    def test_graph_stats(self, session_id: str) -> bool:
        """Test getting graph statistics"""
        self.print_test_header("Graph Statistics")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}/graph/stats")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Graph stats (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Graph stats failed with exception: {e}")
            return False
    
    def test_graph_data(self, session_id: str) -> bool:
        """Test retrieving graph data"""
        self.print_test_header("Graph Data Retrieval")
        
        try:
            # Test JSON format
            params = {"format": "json", "include_metadata": "true"}
            response = self.session.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/graph",
                params=params
            )
            
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Graph data JSON (HTTP {response.status_code})", data)
            
            # Test D3 format
            params = {"format": "d3"}
            response = self.session.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/graph",
                params=params
            )
            
            success2 = response.status_code == 200
            data2 = response.json() if success2 else response.text
            
            self.print_result(success2, f"Graph data D3 (HTTP {response.status_code})", data2)
            
            return success and success2
            
        except Exception as e:
            self.print_result(False, f"Graph data retrieval failed with exception: {e}")
            return False
    
    def test_session_cleanup(self) -> bool:
        """Test manual session cleanup"""
        self.print_test_header("Session Cleanup")
        
        try:
            response = self.session.post(f"{self.base_url}/api/v1/sessions/cleanup")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Session cleanup (HTTP {response.status_code})", data)
            return success
            
        except Exception as e:
            self.print_result(False, f"Session cleanup failed with exception: {e}")
            return False
    
    def test_session_deletion(self, session_id: str) -> bool:
        """Test session deletion"""
        self.print_test_header("Session Deletion")
        
        try:
            response = self.session.delete(f"{self.base_url}/api/v1/sessions/{session_id}")
            success = response.status_code == 200
            data = response.json() if success else response.text
            
            self.print_result(success, f"Session deletion (HTTP {response.status_code})", data)
            
            if success and session_id in self.created_sessions:
                self.created_sessions.remove(session_id)
            
            return success
            
        except Exception as e:
            self.print_result(False, f"Session deletion failed with exception: {e}")
            return False
    
    def cleanup_sessions(self):
        """Clean up any remaining test sessions"""
        if self.created_sessions:
            print(f"\nCleaning up {len(self.created_sessions)} remaining sessions...")
            for session_id in self.created_sessions.copy():
                self.test_session_deletion(session_id)
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all REST API tests"""
        print("🚀 Starting REST API Comprehensive Tests")
        print(f"Target URL: {self.base_url}")
        print(f"Test User ID: {TEST_USER_ID}")
        
        results = {}
        
        # Basic health check
        results["health_check"] = self.test_health_check()
        
        if not results["health_check"]:
            print("\n❌ API server is not responding. Aborting tests.")
            return results
        
        # Session management tests
        session_id = self.test_session_creation()
        results["session_creation"] = session_id is not None
        
        if not session_id:
            print("\n❌ Cannot create session. Aborting remaining tests.")
            return results
        
        # Wait a moment for session initialization
        time.sleep(1)
        
        results["session_info"] = self.test_session_info(session_id)
        results["session_list"] = self.test_session_list()
        results["agent_status"] = self.test_agent_status(session_id)
        
        # Agent interaction tests
        results["agent_query"] = self.test_agent_query(session_id)
        
        # Give agent time to process and update memory
        time.sleep(2)
        
        # Memory management tests
        results["memory_stats"] = self.test_memory_stats(session_id)
        results["memory_retrieval"] = self.test_memory_retrieval(session_id)
        results["memory_search"] = self.test_memory_search(session_id)
        
        # Graph data tests
        results["graph_stats"] = self.test_graph_stats(session_id)
        results["graph_data"] = self.test_graph_data(session_id)
        
        # Cleanup tests
        results["session_cleanup"] = self.test_session_cleanup()
        results["session_deletion"] = self.test_session_deletion(session_id)
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("  TEST SUMMARY")
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
            print("\n🎉 All tests passed! The REST API is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")


def main():
    """Main test runner"""
    tester = RestAPITester()
    
    try:
        results = tester.run_all_tests()
        tester.print_summary(results)
    finally:
        # Ensure cleanup
        tester.cleanup_sessions()


if __name__ == "__main__":
    main() 