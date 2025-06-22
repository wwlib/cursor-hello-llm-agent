"""
Session Data Models

Pydantic models for session management and agent state.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    ERROR = "error"

class SessionConfig(BaseModel):
    """Session configuration model"""
    domain: str = Field(default="general", description="Domain configuration (e.g., 'dnd', 'general')")
    llm_model: Optional[str] = Field(default=None, description="LLM model to use")
    embed_model: Optional[str] = Field(default=None, description="Embedding model to use")
    max_memory_size: int = Field(default=1000, description="Maximum memory entries")
    enable_graph: bool = Field(default=True, description="Enable graph memory features")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration options")

class CreateSessionRequest(BaseModel):
    """Request model for creating a new session"""
    config: SessionConfig = Field(default_factory=SessionConfig)
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    user_id: Optional[str]
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    config: SessionConfig
    
class CreateSessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str
    status: str
    message: str = "Session created successfully"

class SessionListResponse(BaseModel):
    """Response model for listing sessions"""
    sessions: list[SessionInfo]
    total: int
    
class DeleteSessionResponse(BaseModel):
    """Response model for session deletion"""
    status: str
    message: str 