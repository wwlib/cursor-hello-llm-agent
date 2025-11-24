"""
WebSocket Log Streamer

Custom logging handler that streams logs to WebSocket connections in real-time.
Enables the web UI to display logs in dedicated tabs.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from threading import Lock

from .manager import manager


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that streams log messages to WebSocket connections."""
    
    def __init__(self, session_id: str, log_source: str, streamer: 'LogStreamer'):
        super().__init__()
        self.session_id = session_id
        self.log_source = log_source  # e.g., 'agent', 'memory_manager', 'ollama_general'
        self.streamer = streamer
        
    def emit(self, record: logging.LogRecord):
        """Emit a log record to WebSocket connections."""
        try:
            # Format the log message
            message = self.format(record)
            
            # Create log data structure
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
                "source": self.log_source,
                "session_id": self.session_id,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Stream to WebSocket (non-blocking) - only if event loop is running
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.streamer.stream_log(self.session_id, log_data))
                else:
                    # Schedule the coroutine to run when loop becomes available
                    asyncio.ensure_future(self.streamer.stream_log(self.session_id, log_data))
            except RuntimeError:
                # No event loop available, queue the log for later processing
                self.streamer.queue_log(self.session_id, log_data)
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error in WebSocketLogHandler: {e}")


class LogStreamer:
    """Manages log streaming subscriptions and broadcasts logs to WebSocket connections."""
    
    def __init__(self):
        # Track which sessions have log streaming enabled
        # {session_id: {log_source: Set[connection_ids]}}
        self.subscriptions: Dict[str, Dict[str, Set[str]]] = {}
        # Queue for logs when no event loop is available
        self.log_queue: List[Dict[str, Any]] = []
        self.lock = Lock()
    
    def subscribe_to_logs(self, session_id: str, connection_id: str, log_sources: List[str]):
        """Subscribe a WebSocket connection to specific log sources."""
        with self.lock:
            if session_id not in self.subscriptions:
                self.subscriptions[session_id] = {}
            
            for log_source in log_sources:
                if log_source not in self.subscriptions[session_id]:
                    self.subscriptions[session_id][log_source] = set()
                self.subscriptions[session_id][log_source].add(connection_id)
                print(f"🔍 LOG_STREAMER: Subscribed {connection_id} to {log_source} for session {session_id}")
            
            print(f"🔍 LOG_STREAMER: Current subscriptions for {session_id}: {dict(self.subscriptions[session_id])}")
    
    def unsubscribe_from_logs(self, session_id: str, connection_id: str, log_sources: Optional[List[str]] = None):
        """Unsubscribe a WebSocket connection from log sources."""
        with self.lock:
            if session_id not in self.subscriptions:
                return
            
            if log_sources is None:
                # Unsubscribe from all sources
                for log_source in self.subscriptions[session_id]:
                    self.subscriptions[session_id][log_source].discard(connection_id)
            else:
                # Unsubscribe from specific sources
                for log_source in log_sources:
                    if log_source in self.subscriptions[session_id]:
                        self.subscriptions[session_id][log_source].discard(connection_id)
            
            # Clean up empty subscriptions
            self.subscriptions[session_id] = {
                source: connections for source, connections in self.subscriptions[session_id].items()
                if connections
            }
            if not self.subscriptions[session_id]:
                del self.subscriptions[session_id]
    
    def cleanup_connection(self, session_id: str, connection_id: str):
        """Clean up all subscriptions for a disconnected connection."""
        self.unsubscribe_from_logs(session_id, connection_id)
    
    def queue_log(self, session_id: str, log_data: Dict[str, Any]):
        """Queue a log message when no event loop is available."""
        with self.lock:
            self.log_queue.append({
                "session_id": session_id,
                "log_data": log_data,
                "timestamp": datetime.now()
            })
            # Keep queue size reasonable
            if len(self.log_queue) > 1000:
                self.log_queue = self.log_queue[-500:]  # Keep last 500
    
    async def stream_log(self, session_id: str, log_data: Dict[str, Any]):
        """Stream a log message to subscribed WebSocket connections."""
        log_source = log_data.get("source", "unknown")
        
        with self.lock:
            if session_id not in self.subscriptions:
                print(f"🔍 LOG_STREAMER: No subscriptions for session {session_id}")
                return
            
            if log_source not in self.subscriptions[session_id]:
                print(f"🔍 LOG_STREAMER: No subscriptions for log source {log_source} in session {session_id}")
                print(f"🔍 LOG_STREAMER: Available sources: {list(self.subscriptions[session_id].keys())}")
                return
            
            connection_ids = self.subscriptions[session_id][log_source].copy()
        
        if not connection_ids:
            print(f"🔍 LOG_STREAMER: No connections for {log_source} in session {session_id}")
            return
        
        print(f"🔍 LOG_STREAMER: Streaming log from {log_source} to {len(connection_ids)} connections")
        
        # Create WebSocket message
        message = {
            "type": "log_stream",
            "data": log_data
        }
        
        # Broadcast to subscribed connections
        await manager.broadcast_to_session(message, session_id)
    
    def get_available_log_sources(self, session_id: str) -> List[str]:
        """Get list of available log sources for a session."""
        # Standard log sources based on session manager setup
        return [
            "agent",
            "memory_manager", 
            "ollama_general",
            "ollama_digest",
            "ollama_embed",
            "api"  # General API logs
        ]
    
    def get_subscription_status(self, session_id: str) -> Dict[str, List[str]]:
        """Get current subscription status for a session."""
        with self.lock:
            if session_id not in self.subscriptions:
                return {}
            
            return {
                log_source: list(connections)
                for log_source, connections in self.subscriptions[session_id].items()
            }


# Global log streamer instance
log_streamer = LogStreamer() 