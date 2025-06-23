"""
Session Data Models

Pydantic models for session management and agent state.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    ERROR = "error"

class SessionConfig(BaseModel):
    """Session configuration model"""
    domain: str = Field(default="dnd", description="Domain configuration (e.g., 'dnd', 'lab_assistant', 'user_story')")
    llm_model: Optional[str] = Field(default=None, description="LLM model to use")
    embed_model: Optional[str] = Field(default=None, description="Embedding model to use")
    max_memory_size: int = Field(default=1000, description="Maximum memory entries")
    enable_graph: bool = Field(default=True, description="Enable graph memory features")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration options")
    
    @validator('domain')
    def validate_domain(cls, v):
        """Validate that the domain is available"""
        try:
            from ..configs import get_available_domains, get_default_domain
            available_domains = get_available_domains()
            if v not in available_domains and available_domains:
                # Log warning but allow it - SessionManager will handle fallback
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Domain '{v}' not in available domains {available_domains}, will fallback to default")
        except ImportError:
            # If configs not available, skip validation
            pass
        return v

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