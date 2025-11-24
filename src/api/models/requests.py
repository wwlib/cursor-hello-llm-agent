"""
API Request Models

Pydantic models for API request validation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class AgentQueryRequest(BaseModel):
    """Request model for agent queries"""
    message: str = Field(..., description="Message to send to the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for the query")
    stream: bool = Field(default=False, description="Enable streaming response")

class MemorySearchRequest(BaseModel):
    """Request model for memory search"""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    limit: int = Field(default=10, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")

class MemoryQueryParams(BaseModel):
    """Query parameters for memory endpoints"""
    type: Optional[str] = Field(default=None, description="Memory type filter")
    limit: int = Field(default=50, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")

class GraphQueryParams(BaseModel):
    """Query parameters for graph endpoints"""
    format: str = Field(default="json", description="Response format (json|d3)")
    include_metadata: bool = Field(default=True, description="Include metadata in response")
    node_limit: Optional[int] = Field(default=None, description="Maximum number of nodes")
    edge_limit: Optional[int] = Field(default=None, description="Maximum number of edges") 