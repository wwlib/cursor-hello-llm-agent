"""
WebSocket Connection Manager

Handles WebSocket connections, message broadcasting, and connection lifecycle.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections: {session_id: [WebSocket connections]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        # Heartbeat tracking: {connection_id: last_heartbeat}
        self.heartbeats: Dict[str, datetime] = {}
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60  # seconds
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: Optional[str] = None) -> str:
        """Accept a new WebSocket connection and associate it with a session."""
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = f"{session_id}_{datetime.now().timestamp()}"
        
        # Add to active connections
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "connected_at": datetime.now(),
            "websocket": websocket
        }
        
        # Initialize heartbeat
        self.heartbeats[connection_id] = datetime.now()
        
        logger.info(f"WebSocket connected: {connection_id} for session {session_id}")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        }, websocket)
        
        return connection_id
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                
                # Clean up empty session lists
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
        
        # Clean up metadata and heartbeat tracking
        connection_id = None
        for conn_id, metadata in self.connection_metadata.items():
            if metadata["websocket"] == websocket:
                connection_id = conn_id
                break
        
        if connection_id:
            # Clean up log subscriptions
            try:
                from .log_streamer import log_streamer
                log_streamer.cleanup_connection(session_id, connection_id)
            except Exception as e:
                logger.warning(f"Error cleaning up log subscriptions: {e}")
            
            del self.connection_metadata[connection_id]
            if connection_id in self.heartbeats:
                del self.heartbeats[connection_id]
                
        logger.info(f"WebSocket disconnected: {connection_id or 'unknown'} for session {session_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast_to_session(self, message: Dict[str, Any], session_id: str):
        """Broadcast a message to all connections for a specific session."""
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
        
        # Send to all connections for this session
        disconnected_connections = []
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                disconnected_connections.append(websocket)
        
        # Clean up failed connections
        for websocket in disconnected_connections:
            self.disconnect(websocket, session_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all active connections."""
        for session_id in list(self.active_connections.keys()):
            await self.broadcast_to_session(message, session_id)
    
    def get_session_connections(self, session_id: str) -> List[WebSocket]:
        """Get all active connections for a session."""
        return self.active_connections.get(session_id, [])
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def update_heartbeat(self, connection_id: str):
        """Update heartbeat timestamp for a connection."""
        if connection_id in self.heartbeats:
            self.heartbeats[connection_id] = datetime.now()
    
    async def cleanup_stale_connections(self):
        """Remove connections that haven't sent heartbeat recently."""
        now = datetime.now()
        stale_connections = []
        
        for connection_id, last_heartbeat in self.heartbeats.items():
            if now - last_heartbeat > timedelta(seconds=self.heartbeat_timeout):
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            metadata = self.connection_metadata.get(connection_id)
            if metadata:
                websocket = metadata["websocket"]
                session_id = metadata["session_id"]
                try:
                    await websocket.close(code=1000, reason="Heartbeat timeout")
                except:
                    pass
                self.disconnect(websocket, session_id)
                logger.info(f"Cleaned up stale connection: {connection_id}")
    
    async def start_heartbeat_monitor(self):
        """Start background task to monitor connection health."""
        while True:
            try:
                await self.cleanup_stale_connections()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(5)  # Wait before retrying


# Global connection manager instance
manager = ConnectionManager() 