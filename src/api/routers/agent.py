"""
Agent Router

API endpoints for agent interaction and query processing.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..models.requests import AgentQueryRequest
from ..models.responses import AgentQueryResponse
from ..services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

def get_session_manager(request: Request) -> SessionManager:
    """Dependency to get session manager from app state"""
    return request.app.state.session_manager

@router.post("/sessions/{session_id}/query", response_model=AgentQueryResponse)
async def query_agent(
    session_id: str,
    request: AgentQueryRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Send a query to the agent"""
    try:
        # Get the session
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.agent:
            raise HTTPException(status_code=500, detail="Agent not initialized for session")
            
        # Process the query through the agent
        try:
            # Call the agent's process_message method
            response = await session.agent.process_message(request.message)
            
            # Track memory and graph updates (simplified for now)
            memory_updates = []
            graph_updates = []
            
            # Check if memory manager has recent updates
            if session.memory_manager:
                # This is a simplified approach - in a real implementation,
                # we'd track what specifically changed during this query
                memory_updates.append({
                    "type": "conversation_added",
                    "timestamp": session.last_activity.isoformat()
                })
                
                # Check for graph updates if graph memory is enabled
                if hasattr(session.memory_manager, 'graph_manager'):
                    graph_updates.append({
                        "type": "entities_updated",
                        "timestamp": session.last_activity.isoformat()
                    })
            
            return AgentQueryResponse(
                response=response,
                session_id=session_id,
                memory_updates=memory_updates if memory_updates else None,
                graph_updates=graph_updates if graph_updates else None,
                metadata={
                    "query_length": len(request.message),
                    "response_length": len(response),
                    "context_provided": bool(request.context)
                }
            )
            
        except Exception as agent_error:
            logger.error(f"Agent processing error for session {session_id}: {agent_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Agent processing failed: {str(agent_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process query for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.get("/sessions/{session_id}/status")
async def get_agent_status(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get the status of the agent for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return JSONResponse({
            "session_id": session_id,
            "agent_initialized": session.agent is not None,
            "memory_manager_initialized": session.memory_manager is not None,
            "session_status": session.status.value,
            "last_activity": session.last_activity.isoformat(),
            "config": {
                "domain": session.config.domain,
                "enable_graph": session.config.enable_graph,
                "max_memory_size": session.config.max_memory_size
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}") 