#!/usr/bin/env python3
"""
Debug Status Test

Focused test to debug the get_status WebSocket message issue.
"""

import asyncio
import json
import websockets
import requests

API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

async def debug_status_test():
    """Debug the get_status WebSocket message"""
    
    # Create a test session first
    print("🔧 Creating test session...")
    session_config = {
        "config": {"domain": "dnd", "enable_graph": True},
        "user_id": "debug_test_user"
    }
    
    response = requests.post(f"{API_BASE_URL}/api/v1/sessions", json=session_config)
    if response.status_code != 200:
        print(f"❌ Failed to create session: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"✅ Session created: {session_id}")
    
    # Connect to WebSocket
    ws_url = f"{WS_BASE_URL}/api/v1/ws/sessions/{session_id}"
    print(f"🔌 Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected")
            
            # Skip initial connection message
            try:
                initial_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📨 Initial message: {initial_msg}")
            except asyncio.TimeoutError:
                print("📨 No initial message")
            
            # Send get_status message
            status_message = {
                "type": "get_status",
                "data": {}
            }
            
            print(f"📤 Sending: {json.dumps(status_message)}")
            await websocket.send(json.dumps(status_message))
            print("📤 Message sent, waiting for response...")
            
            # Wait for response
            try:
                response_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"📥 Response received: {response_msg}")
                response_data = json.loads(response_msg)
                print(f"📥 Parsed response: {json.dumps(response_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⏰ Timeout - no response received after 10 seconds")
            except Exception as e:
                print(f"❌ Error receiving response: {e}")
                
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
    
    finally:
        # Cleanup session
        print(f"🧹 Cleaning up session {session_id}")
        cleanup_response = requests.delete(f"{API_BASE_URL}/api/v1/sessions/{session_id}")
        if cleanup_response.status_code == 200:
            print("✅ Session cleaned up")
        else:
            print(f"⚠️  Failed to cleanup session: {cleanup_response.status_code}")

if __name__ == "__main__":
    asyncio.run(debug_status_test()) 