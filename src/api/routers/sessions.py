"""
Sessions Router

API endpoints for session management and lifecycle.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..models.sessions import (
    CreateSessionRequest, CreateSessionResponse, SessionInfo, 
    SessionListResponse, DeleteSessionResponse
)
from ..services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

def get_session_manager(request: Request) -> SessionManager:
    """Dependency to get session manager from app state"""
    return request.app.state.session_manager

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a new agent session"""
    try:
        session_id = await session_manager.create_session(
            config=request.config,
            user_id=request.user_id
        )
        
        return CreateSessionResponse(
            session_id=session_id,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get information about a specific session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return SessionInfo(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            created_at=session.created_at,
            last_activity=session.last_activity,
            config=session.config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Delete a session"""
    try:
        success = await session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return DeleteSessionResponse(
            status="success",
            message=f"Session {session_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = None,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """List active sessions"""
    try:
        sessions = session_manager.list_sessions(user_id=user_id)
        
        return SessionListResponse(
            sessions=sessions,
            total=len(sessions)
        )
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.post("/sessions/cleanup")
async def cleanup_expired_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Manually trigger cleanup of expired sessions"""
    try:
        await session_manager.cleanup_expired_sessions()
        
        return JSONResponse({
            "status": "success",
            "message": "Expired sessions cleaned up",
            "active_sessions": session_manager.get_session_count()
        })
        
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}") 