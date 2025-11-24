"""
API Response Models

Pydantic models for API response validation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class AgentQueryResponse(BaseModel):
    """Response model for agent queries"""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    memory_updates: Optional[List[Dict[str, Any]]] = Field(default=None, description="Memory updates made")
    graph_updates: Optional[List[Dict[str, Any]]] = Field(default=None, description="Graph updates made")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class MemorySearchResponse(BaseModel):
    """Response model for memory search"""
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    relevance_scores: Optional[List[float]] = Field(default=None, description="Relevance scores for results")
    total: int = Field(..., description="Total number of matching results")
    query: str = Field(..., description="Original search query")
    
class MemoryDataResponse(BaseModel):
    """Response model for memory data"""
    data: List[Dict[str, Any]] = Field(..., description="Memory data")
    total: int = Field(..., description="Total number of records")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")

class GraphDataResponse(BaseModel):
    """Response model for graph data"""
    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Graph metadata")
    stats: Optional[Dict[str, Any]] = Field(default=None, description="Graph statistics")

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now) 