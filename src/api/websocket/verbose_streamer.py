"""
WebSocket Verbose Status Streamer

Integrates the VerboseStatusHandler with WebSocket connections to stream
real-time status updates to web clients during agent processing.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .manager import manager
from src.utils.verbose_status import VerboseStatusHandler, get_verbose_handler

logger = logging.getLogger(__name__)


class WebSocketVerboseStreamer:
    """Streams verbose status messages to WebSocket clients."""
    
    def __init__(self):
        self.subscriptions = {}  # {session_id: {connection_id: bool}}
        
    def subscribe_to_verbose_status(self, session_id: str, connection_id: str):
        """Subscribe a WebSocket connection to verbose status updates."""
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = {}
        self.subscriptions[session_id][connection_id] = True
        logger.debug(f"Subscribed {connection_id} to verbose status for session {session_id}")
    
    def unsubscribe_from_verbose_status(self, session_id: str, connection_id: str):
        """Unsubscribe a WebSocket connection from verbose status updates."""
        if session_id in self.subscriptions:
            self.subscriptions[session_id].pop(connection_id, None)
            if not self.subscriptions[session_id]:
                del self.subscriptions[session_id]
        logger.debug(f"Unsubscribed {connection_id} from verbose status for session {session_id}")
    
    def cleanup_connection(self, session_id: str, connection_id: str):
        """Clean up subscriptions for a disconnected connection."""
        self.unsubscribe_from_verbose_status(session_id, connection_id)
    
    async def stream_verbose_message(self, session_id: str, message_data: Dict[str, Any]):
        """Stream a verbose status message to subscribed WebSocket connections."""
        if session_id not in self.subscriptions:
            return
        
        if not self.subscriptions[session_id]:
            return
        
        # Create WebSocket message
        websocket_message = {
            "type": "verbose_status",
            "data": message_data
        }
        
        # Broadcast to subscribed connections in this session
        await manager.broadcast_to_session(websocket_message, session_id)
        logger.debug(f"Streamed verbose message to {len(self.subscriptions[session_id])} connections in session {session_id}")


# Global verbose streamer instance
verbose_streamer = WebSocketVerboseStreamer()


def create_websocket_verbose_handler(session_id: str, enabled: bool = True) -> VerboseStatusHandler:
    """
    Create a VerboseStatusHandler that streams to WebSocket clients.
    
    Args:
        session_id: The session ID for WebSocket routing
        enabled: Whether verbose messages are enabled
        
    Returns:
        VerboseStatusHandler configured for WebSocket streaming
    """
    def websocket_callback(message_data: Dict[str, Any]):
        """Callback to send verbose messages to WebSocket clients."""
        try:
            # Add session context
            message_data["data"]["session_id"] = session_id
            
            # Stream to WebSocket clients (non-blocking)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(verbose_streamer.stream_verbose_message(session_id, message_data["data"]))
                else:
                    asyncio.ensure_future(verbose_streamer.stream_verbose_message(session_id, message_data["data"]))
            except RuntimeError:
                # No event loop available, skip WebSocket streaming
                pass
                
        except Exception as e:
            logger.error(f"Error in WebSocket verbose callback: {e}")
    
    return VerboseStatusHandler(
        enabled=enabled,
        output_handler=print,  # Still print to console
        websocket_callback=websocket_callback
    )


def get_websocket_verbose_handler(session_id: str, enabled: bool = True) -> VerboseStatusHandler:
    """
    Get or create a WebSocket-enabled verbose handler for a session.
    
    This function integrates with the existing get_verbose_handler system
    but adds WebSocket streaming capabilities.
    """
    # Get the existing handler
    handler = get_verbose_handler(enabled)
    
    # Add WebSocket capability if not already present
    if not hasattr(handler, 'websocket_callback') or handler.websocket_callback is None:
        def websocket_callback(message_data: Dict[str, Any]):
            """Callback to send verbose messages to WebSocket clients."""
            try:
                # Add session context
                message_data["data"]["session_id"] = session_id
                
                # Stream to WebSocket clients (non-blocking)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(verbose_streamer.stream_verbose_message(session_id, message_data["data"]))
                    else:
                        asyncio.ensure_future(verbose_streamer.stream_verbose_message(session_id, message_data["data"]))
                except RuntimeError:
                    # No event loop available, skip WebSocket streaming
                    pass
                    
            except Exception as e:
                logger.error(f"Error in WebSocket verbose callback: {e}")
        
        handler.websocket_callback = websocket_callback
    
    return handler


