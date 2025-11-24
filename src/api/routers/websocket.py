"""
WebSocket Router

Provides WebSocket endpoints for real-time agent communication.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Optional

from ..websocket.manager import manager
from ..websocket.handlers import message_handler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time agent communication.
    
    Args:
        websocket: WebSocket connection
        session_id: Agent session ID
        user_id: Optional user identifier
    
    Message Format:
        {
            "type": "message_type",
            "data": {
                // Message-specific data
            }
        }
    
    Supported Message Types:
        - query: Send message to agent
        - heartbeat: Keep connection alive
        - get_status: Get session status
        - get_memory: Get memory data
        - search_memory: Search memory contents
        - get_graph: Get graph data
        - ping: Connection test
    """
    
    # Get session manager from global variable
    from ..main import session_manager
    if not session_manager:
        await websocket.close(code=4001, reason="Session manager not initialized")
        return
    
    # Verify session exists
    session = await session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason=f"Session {session_id} not found")
        return
    
    # Connect to WebSocket manager
    connection_id = await manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {
                        "error": "Invalid JSON format",
                        "timestamp": "now"
                    }
                }, websocket)
                continue
            
            # Handle the message
            await message_handler.handle_message(websocket, session_id, message, session_manager)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Clean up connection
        manager.disconnect(websocket, session_id)


@router.websocket("/ws/monitor")
async def monitor_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for monitoring system-wide events.
    
    Provides real-time updates about:
    - New session creation
    - Session deletion
    - Connection count changes
    - System health updates
    """
    
    await websocket.accept()
    
    # Get session manager from global variable
    from ..main import session_manager
    
    # Send initial status
    await websocket.send_text(json.dumps({
        "type": "monitor_connected",
        "data": {
            "active_sessions": len(session_manager.active_sessions) if session_manager else 0,
            "active_connections": manager.get_connection_count(),
            "timestamp": "now"
        }
    }))
    
    try:
        while True:
            # For now, just echo ping messages
            # In future, this could broadcast system events
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "data": {
                            "active_sessions": len(session_manager.active_sessions) if session_manager else 0,
                            "active_connections": manager.get_connection_count(),
                            "timestamp": "now"
                        }
                    }))
            except json.JSONDecodeError:
                continue
                
    except WebSocketDisconnect:
        logger.info("Monitor WebSocket disconnected")
    except Exception as e:
        logger.error(f"Monitor WebSocket error: {e}")


# Event broadcasting functions for integration with other parts of the API

async def broadcast_session_created(session_id: str, config: dict):
    """Broadcast session creation event."""
    await manager.broadcast_to_all({
        "type": "session_created",
        "data": {
            "session_id": session_id,
            "config": config,
            "timestamp": "now"
        }
    })


async def broadcast_session_deleted(session_id: str):
    """Broadcast session deletion event."""
    await manager.broadcast_to_all({
        "type": "session_deleted",
        "data": {
            "session_id": session_id,
            "timestamp": "now"
        }
    })


async def broadcast_memory_updated(session_id: str, update_type: str):
    """Broadcast memory update event to session connections."""
    await manager.broadcast_to_session({
        "type": "memory_updated",
        "data": {
            "session_id": session_id,
            "update_type": update_type,
            "timestamp": "now"
        }
    }, session_id)


async def broadcast_graph_updated(session_id: str, update_type: str):
    """Broadcast graph update event to session connections."""
    await manager.broadcast_to_session({
        "type": "graph_updated",
        "data": {
            "session_id": session_id,
            "update_type": update_type,
            "timestamp": "now"
        }
    }, session_id) 