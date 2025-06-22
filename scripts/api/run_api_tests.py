#!/usr/bin/env python3
"""
API Test Runner

Orchestrates all API tests and provides a comprehensive evaluation of the
agent system API implementation.
"""

import sys
import subprocess
import time
import requests
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def check_api_server() -> bool:
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_api_server():
    """Instructions to start the API server"""
    print("🚀 To start the API server, run one of these commands in another terminal:")
    print("   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload")
    print("   OR")
    print("   python src/api/main.py")

def run_test_script(script_name: str, description: str) -> bool:
    """Run a test script and return success status"""
    print(f"\n🧪 Running {description}...")
    print(f"   Script: {script_name}")
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True, 
                              timeout=300)  # 5 minute timeout
        
        success = result.returncode == 0
        
        if success:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def main():
    """Main test orchestrator"""
    print_header("AGENT SYSTEM API COMPREHENSIVE TEST SUITE")
    print(f"Target API: {API_BASE_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if API server is running
    print("\n🔍 Checking API server status...")
    if not check_api_server():
        print("❌ API server is not responding!")
        start_api_server()
        print("\nWaiting 10 seconds for you to start the server...")
        time.sleep(10)
        
        if not check_api_server():
            print("❌ API server still not responding. Please start the server and try again.")
            sys.exit(1)
    
    print("✅ API server is responding")
    
    # Test scripts to run
    test_scripts = [
        ("test_session_manager.py", "Session Manager Evaluation"),
        ("test_rest_api.py", "REST API Comprehensive Tests"),
        ("test_websocket_api.py", "WebSocket API Comprehensive Tests")
    ]
    
    results = {}
    
    print_header("RUNNING TEST SUITE")
    
    for script_path, description in test_scripts:
        results[description] = run_test_script(script_path, description)
        time.sleep(2)  # Brief pause between test suites
    
    # Print final summary
    print_header("FINAL TEST RESULTS")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"Test Suites Run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print_header("API READINESS ASSESSMENT")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ The agent system API is working correctly")
        print("✅ Session management is functional")
        print("✅ REST endpoints are operational")
        print("✅ WebSocket communication is working")
        print("✅ Ready for browser app integration!")
        
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY WORKING")
        print("✅ Most API components are functional")
        print("⚠️  Some issues found that should be investigated")
        print("📋 Review failed tests before browser app integration")
        
    elif passed >= total * 0.5:
        print("⚠️  PARTIAL FUNCTIONALITY")
        print("⚠️  Significant issues found in API implementation")
        print("📋 Fix major issues before proceeding with browser app")
        print("🔧 API needs improvements and fixes")
        
    else:
        print("❌ MAJOR ISSUES FOUND")
        print("❌ API implementation has serious problems")
        print("🚫 Do not proceed with browser app until API is fixed")
        print("🔧 Requires significant debugging and fixes")
    
    print(f"\nNext Steps:")
    print(f"1. Review detailed output from each test suite above")
    print(f"2. Fix any failing tests")
    print(f"3. Re-run this test suite to verify fixes")
    if passed >= total * 0.8:
        print(f"4. Proceed with browser app analysis and troubleshooting")
    
    print(f"\nFor more details, run individual test scripts:")
    for script_path, description in test_scripts:
        print(f"   python scripts/api/{script_path}")

if __name__ == "__main__":
    main() 