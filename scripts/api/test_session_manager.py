#!/usr/bin/env python3
"""
Session Manager Test Script

Tests the API session manager to ensure proper initialization and management
of agent sessions. This addresses the TODO item to evaluate session manager
functionality.
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_PREFIX = "session_test_user"

class SessionManagerTester:
    """Test the API session manager functionality"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.created_sessions = []
    
    def print_test_header(self, test_name: str):
        """Print formatted test header"""
        print(f"\n{'='*60}")
        print(f"  {test_name}")
        print(f"{'='*60}")
    
    def print_result(self, success: bool, message: str, data: Any = None):
        """Print test result with formatting"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")
        if data and isinstance(data, dict):
            print(f"   Data: {json.dumps(data, indent=2)[:300]}...")
        elif data:
            print(f"   Data: {str(data)[:200]}...")
    
    def test_basic_session_creation(self) -> bool:
        """Test basic session creation and configuration"""
        self.print_test_header("Basic Session Creation")
        
        configs = [
            # Standard D&D configuration
            {
                "config": {"domain": "dnd", "enable_graph": True},
                "user_id": f"{TEST_USER_PREFIX}_basic"
            },
            # Custom configuration
            {
                "config": {
                    "domain": "general",
                    "llm_model": "gemma3",
                    "embed_model": "mxbai-embed-large",
                    "max_memory_size": 500,
                    "enable_graph": False
                },
                "user_id": f"{TEST_USER_PREFIX}_custom"
            },
            # Minimal configuration
            {
                "config": {"domain": "dnd"},
                "user_id": f"{TEST_USER_PREFIX}_minimal"
            }
        ]
        
        success_count = 0
        
        for i, config in enumerate(configs):
            try:
                response = self.session.post(f"{self.base_url}/api/v1/sessions", json=config)
                
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get("session_id")
                    if session_id:
                        self.created_sessions.append(session_id)
                        success_count += 1
                        self.print_result(True, f"Config {i+1}: Session created: {session_id}", data)
                    else:
                        self.print_result(False, f"Config {i+1}: No session_id in response", data)
                else:
                    self.print_result(False, f"Config {i+1}: HTTP {response.status_code}", response.text)
                    
            except Exception as e:
                self.print_result(False, f"Config {i+1}: Exception: {e}")
        
        return success_count == len(configs)
    
    def test_session_agent_initialization(self) -> bool:
        """Test that sessions properly initialize agents and memory managers"""
        self.print_test_header("Agent & Memory Manager Initialization")
        
        if not self.created_sessions:
            self.print_result(False, "No sessions available for testing")
            return False
        
        success_count = 0
        
        for session_id in self.created_sessions[:3]:  # Test first 3 sessions
            try:
                # Get session status
                response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}/status")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check critical initialization flags
                    agent_init = data.get("agent_initialized", False)
                    memory_init = data.get("memory_manager_initialized", False)
                    session_status = data.get("session_status", "unknown")
                    
                    if agent_init and memory_init and session_status == "active":
                        success_count += 1
                        self.print_result(True, f"Session {session_id[:8]}... properly initialized", data)
                    else:
                        self.print_result(False, f"Session {session_id[:8]}... incomplete initialization", {
                            "agent_initialized": agent_init,
                            "memory_manager_initialized": memory_init,
                            "session_status": session_status
                        })
                else:
                    self.print_result(False, f"Session {session_id[:8]}... status check failed: HTTP {response.status_code}")
                    
            except Exception as e:
                self.print_result(False, f"Session {session_id[:8]}... exception: {e}")
        
        return success_count == min(len(self.created_sessions), 3)
    
    def test_concurrent_sessions(self) -> bool:
        """Test creation and management of multiple concurrent sessions"""
        self.print_test_header("Concurrent Session Management")
        
        concurrent_configs = []
        for i in range(5):
            concurrent_configs.append({
                "config": {
                    "domain": "dnd",
                    "enable_graph": True,
                    "max_memory_size": 100
                },
                "user_id": f"{TEST_USER_PREFIX}_concurrent_{i}"
            })
        
        # Create sessions concurrently (simulate with rapid requests)
        concurrent_sessions = []
        start_time = time.time()
        
        for config in concurrent_configs:
            try:
                response = self.session.post(f"{self.base_url}/api/v1/sessions", json=config)
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get("session_id")
                    if session_id:
                        concurrent_sessions.append(session_id)
                        self.created_sessions.append(session_id)
            except Exception as e:
                print(f"Concurrent session creation error: {e}")
        
        creation_time = time.time() - start_time
        
        # Verify all sessions are active
        active_sessions = 0
        for session_id in concurrent_sessions:
            try:
                response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_id}")
                if response.status_code == 200:
                    active_sessions += 1
            except:
                pass
        
        success = len(concurrent_sessions) == len(concurrent_configs) and active_sessions == len(concurrent_sessions)
        
        self.print_result(success, f"Created {len(concurrent_sessions)}/{len(concurrent_configs)} concurrent sessions in {creation_time:.2f}s", {
            "created_sessions": len(concurrent_sessions),
            "active_sessions": active_sessions,
            "creation_time": f"{creation_time:.2f}s"
        })
        
        return success
    
    def test_session_persistence(self) -> bool:
        """Test that sessions persist and maintain state"""
        self.print_test_header("Session Persistence")
        
        if not self.created_sessions:
            self.print_result(False, "No sessions available for persistence testing")
            return False
        
        test_session = self.created_sessions[0]
        
        # Send a query to create some memory
        query_data = {
            "message": "Remember that I like red dragons and I'm a wizard.",
            "context": {"test": "persistence"}
        }
        
        try:
            # Send query
            response = self.session.post(
                f"{self.base_url}/api/v1/sessions/{test_session}/query",
                json=query_data
            )
            
            if response.status_code != 200:
                self.print_result(False, f"Query failed: HTTP {response.status_code}")
                return False
            
            # Wait for processing
            time.sleep(2)
            
            # Check memory stats
            response = self.session.get(f"{self.base_url}/api/v1/sessions/{test_session}/memory/stats")
            
            if response.status_code == 200:
                memory_stats = response.json()
                
                # Check if memory was created
                # API returns conversations_count directly, not nested under memory_stats
                conversations_count = memory_stats.get("conversations_count", 0)
                
                success = conversations_count > 0
                
                self.print_result(success, f"Session persistence verified", {
                    "conversations_count": conversations_count,
                    "memory_stats": memory_stats
                })
                
                return success
            else:
                self.print_result(False, f"Memory stats check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Session persistence test failed: {e}")
            return False
    
    def test_session_cleanup(self) -> bool:
        """Test session cleanup and deletion"""
        self.print_test_header("Session Cleanup")
        
        if len(self.created_sessions) < 2:
            self.print_result(False, "Need at least 2 sessions for cleanup testing")
            return False
        
        # Test individual session deletion
        session_to_delete = self.created_sessions[-1]  # Delete last session
        
        try:
            response = self.session.delete(f"{self.base_url}/api/v1/sessions/{session_to_delete}")
            
            if response.status_code == 200:
                # Verify session is gone
                check_response = self.session.get(f"{self.base_url}/api/v1/sessions/{session_to_delete}")
                deleted_success = check_response.status_code == 404
                
                if deleted_success:
                    self.created_sessions.remove(session_to_delete)
                
                self.print_result(deleted_success, f"Individual session deletion", {
                    "deleted_session": session_to_delete[:8] + "...",
                    "verification_status": check_response.status_code
                })
                
                # Test bulk cleanup
                cleanup_response = self.session.post(f"{self.base_url}/api/v1/sessions/cleanup")
                cleanup_success = cleanup_response.status_code == 200
                
                cleanup_data = cleanup_response.json() if cleanup_success else cleanup_response.text
                
                self.print_result(cleanup_success, f"Bulk session cleanup", cleanup_data)
                
                return deleted_success and cleanup_success
                
            else:
                self.print_result(False, f"Session deletion failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Session cleanup test failed: {e}")
            return False
    
    def test_session_list_and_count(self) -> bool:
        """Test session listing and counting"""
        self.print_test_header("Session Listing & Counting")
        
        try:
            # Get session list
            response = self.session.get(f"{self.base_url}/api/v1/sessions")
            
            if response.status_code == 200:
                data = response.json()
                session_list = data.get("sessions", [])
                
                # Check health endpoint for session count
                health_response = self.session.get(f"{self.base_url}/health")
                health_data = health_response.json() if health_response.status_code == 200 else {}
                
                health_session_count = health_data.get("active_sessions", 0)
                list_session_count = len(session_list)
                
                count_match = health_session_count == list_session_count
                
                self.print_result(count_match, f"Session count consistency", {
                    "health_endpoint_count": health_session_count,
                    "session_list_count": list_session_count,
                    "our_created_sessions": len(self.created_sessions)
                })
                
                return count_match
                
            else:
                self.print_result(False, f"Session list failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Session listing test failed: {e}")
            return False
    
    def cleanup_all_sessions(self):
        """Clean up all test sessions"""
        if self.created_sessions:
            print(f"\nCleaning up {len(self.created_sessions)} test sessions...")
            for session_id in self.created_sessions.copy():
                try:
                    response = self.session.delete(f"{self.base_url}/api/v1/sessions/{session_id}")
                    if response.status_code == 200:
                        print(f"✅ Cleaned up session {session_id[:8]}...")
                        self.created_sessions.remove(session_id)
                    else:
                        print(f"⚠️  Failed to cleanup session {session_id[:8]}...: HTTP {response.status_code}")
                except Exception as e:
                    print(f"⚠️  Cleanup error for session {session_id[:8]}...: {e}")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all session manager tests"""
        print("🚀 Starting Session Manager Evaluation")
        print(f"Target URL: {self.base_url}")
        print(f"Test User Prefix: {TEST_USER_PREFIX}")
        
        results = {}
        
        results["basic_session_creation"] = self.test_basic_session_creation()
        results["agent_initialization"] = self.test_session_agent_initialization()
        results["concurrent_sessions"] = self.test_concurrent_sessions()
        results["session_persistence"] = self.test_session_persistence()
        results["session_list_count"] = self.test_session_list_and_count()
        results["session_cleanup"] = self.test_session_cleanup()
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("  SESSION MANAGER EVALUATION SUMMARY")
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
        
        # Evaluation conclusions
        print(f"\n{'='*60}")
        print("  SESSION MANAGER EVALUATION")
        print(f"{'='*60}")
        
        if results.get("basic_session_creation", False):
            print("✅ Session creation mechanism is working correctly")
        else:
            print("❌ Session creation has issues that need fixing")
        
        if results.get("agent_initialization", False):
            print("✅ Agent and memory manager initialization is working")
        else:
            print("❌ Agent/memory initialization needs attention")
        
        if results.get("concurrent_sessions", False):
            print("✅ Concurrent session handling is functional")
        else:
            print("❌ Concurrent session management needs improvement")
        
        if results.get("session_persistence", False):
            print("✅ Session state persistence is working")
        else:
            print("❌ Session persistence needs fixing")
        
        if passed >= total * 0.8:
            print("\n🎉 Session Manager is working well! Ready for browser app integration.")
        elif passed >= total * 0.6:
            print("\n⚠️  Session Manager has some issues but is mostly functional.")
        else:
            print("\n❌ Session Manager has significant issues that should be fixed before browser app integration.")


def main():
    """Main test runner"""
    tester = SessionManagerTester()
    
    try:
        results = tester.run_all_tests()
        tester.print_summary(results)
    finally:
        # Ensure cleanup
        tester.cleanup_all_sessions()


if __name__ == "__main__":
    main() 