"""
WebSocket Message Handlers

Handles different types of WebSocket messages and coordinates with the agent system.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket

from ..services.session_manager import SessionManager
from .manager import manager
from .log_streamer import log_streamer

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles WebSocket messages and coordinates with agent system."""
    
    def __init__(self):
        self.message_handlers = {
            "query": self.handle_query,
            "heartbeat": self.handle_heartbeat,
            "get_status": self.handle_get_status,
            "get_memory": self.handle_get_memory,
            "search_memory": self.handle_search_memory,
            "get_graph": self.handle_get_graph,
            "ping": self.handle_ping,
            "subscribe_logs": self.handle_subscribe_logs,
            "unsubscribe_logs": self.handle_unsubscribe_logs,
            "get_log_sources": self.handle_get_log_sources,
        }
    
    async def handle_message(self, websocket: WebSocket, session_id: str, message: Dict[str, Any], session_manager):
        """Route incoming messages to appropriate handlers."""
        try:
            message_type = message.get("type")
            logger.info(f"🔍 ROUTER: Received message type: {message_type} for session {session_id}")
            if not message_type:
                await self.send_error(websocket, "Missing message type")
                return
            
            handler = self.message_handlers.get(message_type)
            if not handler:
                logger.error(f"🔍 ROUTER: Unknown message type: {message_type}")
                await self.send_error(websocket, f"Unknown message type: {message_type}")
                return
            
            logger.info(f"🔍 ROUTER: Routing {message_type} to handler: {handler.__name__}")
            await handler(websocket, session_id, message.get("data", {}), session_manager)
            logger.info(f"🔍 ROUTER: Handler {handler.__name__} completed")
            
        except Exception as e:
            logger.error(f"🔍 ROUTER: Error handling message: {e}")
            await self.send_error(websocket, f"Internal error: {str(e)}")
    
    async def handle_query(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle agent query messages with streaming response."""
        try:
            message = data.get("message")
            if not message:
                await self.send_error(websocket, "Missing message in query")
                return
            
            context = data.get("context", {})
            
            # Get session
            session = await session_manager.get_session(session_id)
            if not session:
                await self.send_error(websocket, f"Session {session_id} not found")
                return
            
            # Send typing indicator
            await manager.send_personal_message({
                "type": "typing_start",
                "data": {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
            # Process message with agent
            try:
                # For now, we'll use the synchronous approach
                # In a future enhancement, we could implement streaming
                response = await session.agent.process_message(message)
                
                # Send response
                await manager.send_personal_message({
                    "type": "query_response",
                    "data": {
                        "message": response,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "partial": False
                    }
                }, websocket)
                
                # Send typing stop
                await manager.send_personal_message({
                    "type": "typing_stop",
                    "data": {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }, websocket)
                
                # Broadcast memory update notification to all session connections
                await manager.broadcast_to_session({
                    "type": "memory_updated",
                    "data": {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "update_type": "conversation_added"
                    }
                }, session_id)
                
            except Exception as e:
                logger.error(f"Error processing agent query: {e}")
                await manager.send_personal_message({
                    "type": "typing_stop",
                    "data": {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }, websocket)
                await self.send_error(websocket, f"Agent processing error: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in query handler: {e}")
            await self.send_error(websocket, f"Query handler error: {str(e)}")
    
    async def handle_heartbeat(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle heartbeat messages to keep connection alive."""
        connection_id = data.get("connection_id")
        if connection_id:
            manager.update_heartbeat(connection_id)
        
        # Send heartbeat response
        await manager.send_personal_message({
            "type": "heartbeat_response",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
        }, websocket)
    
    async def handle_get_status(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle status request messages."""
        logger.info(f"🔍 HANDLER: Handling get_status request for session {session_id}")
        try:
            session = await session_manager.get_session(session_id)
            if not session:
                logger.error(f"🔍 HANDLER: Session {session_id} not found")
                await self.send_error(websocket, f"Session {session_id} not found")
                return
            
            logger.info(f"🔍 HANDLER: Session found, building status data")
            status_data = {
                "session_id": session_id,
                "agent_initialized": session.agent is not None,
                "memory_manager_initialized": session.memory_manager is not None,
                "last_activity": session.last_activity.isoformat(),
                "created_at": session.created_at.isoformat(),
                "config": session.config.dict() if hasattr(session.config, 'dict') else session.config
            }
            
            logger.info(f"🔍 HANDLER: Sending status response: {status_data}")
            await manager.send_personal_message({
                "type": "status_response",
                "data": status_data
            }, websocket)
            logger.info(f"🔍 HANDLER: Status response sent successfully")
            
        except Exception as e:
            logger.error(f"🔍 HANDLER: Error getting status: {e}")
            await self.send_error(websocket, f"Status error: {str(e)}")
    
    async def handle_get_memory(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle memory data request messages."""
        try:
            session = await session_manager.get_session(session_id)
            if not session:
                await self.send_error(websocket, f"Session {session_id} not found")
                return
            
            # Get memory parameters
            memory_type = data.get("type", "conversations")
            limit = data.get("limit", 50)
            offset = data.get("offset", 0)
            
            # Get memory data based on type
            if memory_type == "conversations":
                conversations = session.memory_manager.get_conversation_history()
                # Apply pagination
                total = len(conversations)
                paginated_data = conversations[offset:offset + limit]
                memory_data = {
                    "conversations": paginated_data,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            else:
                memory_data = {"message": f"Memory type '{memory_type}' not yet implemented"}
            
            await manager.send_personal_message({
                "type": "memory_response",
                "data": {
                    "session_id": session_id,
                    "type": memory_type,
                    "data": memory_data,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            await self.send_error(websocket, f"Memory error: {str(e)}")
    
    async def handle_search_memory(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle memory search request messages."""
        try:
            session = await session_manager.get_session(session_id)
            if not session:
                await self.send_error(websocket, f"Session {session_id} not found")
                return
            
            query = data.get("query")
            if not query:
                await self.send_error(websocket, "Missing search query")
                return
            
            # Perform memory search (basic implementation)
            conversations = session.memory_manager.get_conversation_history()
            
            # Simple text search - could be enhanced with embeddings/vector search
            results = []
            for i, conversation in enumerate(conversations):
                if query.lower() in conversation.get("user_message", "").lower() or \
                   query.lower() in conversation.get("agent_response", "").lower():
                    results.append({
                        "index": i,
                        "conversation": conversation,
                        "relevance_score": 1.0  # Placeholder
                    })
            
            await manager.send_personal_message({
                "type": "search_response",
                "data": {
                    "session_id": session_id,
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            await self.send_error(websocket, f"Search error: {str(e)}")
    
    async def handle_get_graph(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle graph data request messages."""
        try:
            session = await session_manager.get_session(session_id)
            if not session:
                await self.send_error(websocket, f"Session {session_id} not found")
                return
            
            format_type = data.get("format", "json")
            include_metadata = data.get("include_metadata", True)
            
            # Check if graph memory is enabled
            if not hasattr(session.memory_manager, 'graph_manager') or \
               session.memory_manager.graph_manager is None:
                graph_data = {
                    "nodes": [],
                    "edges": [],
                    "metadata": {"graph_disabled": True, "message": "Graph memory not enabled"}
                }
            else:
                # Get graph data
                try:
                    graph_data = session.memory_manager.graph_manager.export_graph_data(
                        format=format_type,
                        include_metadata=include_metadata
                    )
                except Exception as e:
                    logger.warning(f"Graph export failed: {e}")
                    graph_data = {
                        "nodes": [],
                        "edges": [],
                        "metadata": {"error": str(e)}
                    }
            
            await manager.send_personal_message({
                "type": "graph_response",
                "data": {
                    "session_id": session_id,
                    "format": format_type,
                    "graph_data": graph_data,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error getting graph: {e}")
            await self.send_error(websocket, f"Graph error: {str(e)}")
    
    async def handle_ping(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle ping messages for connection testing."""
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "message": data.get("message", "pong")
            }
        }, websocket)
    
    async def handle_subscribe_logs(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle log subscription requests."""
        try:
            log_sources = data.get("log_sources", [])
            connection_id = data.get("connection_id")
            
            if not log_sources:
                await self.send_error(websocket, "Missing log_sources in subscribe_logs request")
                return
            
            if not connection_id:
                # Generate a connection ID if not provided
                connection_id = f"{session_id}_{datetime.now().timestamp()}"
            
            # Validate log sources
            available_sources = log_streamer.get_available_log_sources(session_id)
            invalid_sources = [source for source in log_sources if source not in available_sources]
            
            if invalid_sources:
                await self.send_error(websocket, f"Invalid log sources: {invalid_sources}")
                return
            
            # Subscribe to logs
            log_streamer.subscribe_to_logs(session_id, connection_id, log_sources)
            
            # Generate a test log message to verify the system is working
            logger.info(f"Log streaming subscribed for session {session_id}, sources: {log_sources}")
            
            # Send confirmation
            await manager.send_personal_message({
                "type": "logs_subscribed",
                "data": {
                    "session_id": session_id,
                    "connection_id": connection_id,
                    "log_sources": log_sources,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error subscribing to logs: {e}")
            await self.send_error(websocket, f"Log subscription error: {str(e)}")
    
    async def handle_unsubscribe_logs(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle log unsubscription requests."""
        try:
            log_sources = data.get("log_sources")  # None means unsubscribe from all
            connection_id = data.get("connection_id")
            
            if not connection_id:
                await self.send_error(websocket, "Missing connection_id in unsubscribe_logs request")
                return
            
            # Unsubscribe from logs
            log_streamer.unsubscribe_from_logs(session_id, connection_id, log_sources)
            
            # Send confirmation
            await manager.send_personal_message({
                "type": "logs_unsubscribed",
                "data": {
                    "session_id": session_id,
                    "connection_id": connection_id,
                    "log_sources": log_sources or "all",
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error unsubscribing from logs: {e}")
            await self.send_error(websocket, f"Log unsubscription error: {str(e)}")
    
    async def handle_get_log_sources(self, websocket: WebSocket, session_id: str, data: Dict[str, Any], session_manager):
        """Handle get available log sources requests."""
        try:
            available_sources = log_streamer.get_available_log_sources(session_id)
            subscription_status = log_streamer.get_subscription_status(session_id)
            
            await manager.send_personal_message({
                "type": "log_sources_response",
                "data": {
                    "session_id": session_id,
                    "available_sources": available_sources,
                    "subscription_status": subscription_status,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error getting log sources: {e}")
            await self.send_error(websocket, f"Log sources error: {str(e)}")
    
    async def send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to WebSocket client."""
        await manager.send_personal_message({
            "type": "error",
            "data": {
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            }
        }, websocket)


# Global message handler instance
message_handler = MessageHandler() 