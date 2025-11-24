"""
Memory Router

API endpoints for memory management and search functionality.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse

from ..models.requests import MemorySearchRequest
from ..models.responses import MemorySearchResponse, MemoryDataResponse
from ..services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

def get_session_manager(request: Request) -> SessionManager:
    """Dependency to get session manager from app state"""
    return request.app.state.session_manager

@router.get("/sessions/{session_id}/memory", response_model=MemoryDataResponse)
async def get_memory_data(
    session_id: str,
    type: Optional[str] = Query(None, description="Memory type filter"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get memory data for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
            
        memory_manager = session.memory_manager
        data = []
        total = 0
        
        if type == "conversations" or type is None:
            # Get conversation data
            conversations = memory_manager.get_conversation_history()
            conversation_data = []
            
            for i, conversation in enumerate(conversations[offset:offset+limit]):
                conversation_data.append({
                    "type": "conversation",
                    "id": i + offset,
                    "content": conversation,
                    "timestamp": session.created_at.isoformat()  # Simplified
                })
            
            data.extend(conversation_data)
            total += len(conversations)
            
        if type == "entities" or type is None:
            # Get entity data if graph memory is available
            if hasattr(memory_manager, 'graph_manager') and memory_manager.graph_manager:
                try:
                    entities = memory_manager.graph_manager.get_all_entities()
                    entity_data = []
                    
                    for entity_id, entity in list(entities.items())[offset:offset+limit]:
                        entity_data.append({
                            "type": "entity",
                            "id": entity_id,
                            "name": entity.name,
                            "entity_type": entity.entity_type,
                            "description": entity.description,
                            "metadata": entity.metadata
                        })
                    
                    data.extend(entity_data)
                    total += len(entities)
                    
                except Exception as e:
                    logger.warning(f"Could not retrieve entities: {e}")
        
        return MemoryDataResponse(
            data=data,
            total=total,
            pagination={
                "limit": limit,
                "offset": offset,
                "has_more": total > offset + limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory data for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory data: {str(e)}")

@router.post("/sessions/{session_id}/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    session_id: str,
    request: MemorySearchRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Search memory for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
            
        memory_manager = session.memory_manager
        
        # Perform memory search using the memory manager's query functionality
        try:
            # Use the memory manager's query method
            search_results = memory_manager.query(
                query=request.query,
                limit=request.limit
            )
            
            # Format results
            results = []
            relevance_scores = []
            
            if isinstance(search_results, dict):
                # If results include context and other information
                if 'context' in search_results:
                    for i, item in enumerate(search_results['context'][:request.limit]):
                        results.append({
                            "type": "context",
                            "content": item,
                            "relevance": 1.0 - (i * 0.1)  # Simple relevance scoring
                        })
                        relevance_scores.append(1.0 - (i * 0.1))
                        
                if 'conversations' in search_results:
                    for i, conversation in enumerate(search_results['conversations'][:request.limit]):
                        results.append({
                            "type": "conversation",
                            "content": conversation,
                            "relevance": 0.8 - (i * 0.1)
                        })
                        relevance_scores.append(0.8 - (i * 0.1))
                        
            elif isinstance(search_results, list):
                # Simple list of results
                for i, result in enumerate(search_results[:request.limit]):
                    results.append({
                        "type": "general",
                        "content": str(result),
                        "relevance": 1.0 - (i * 0.1)
                    })
                    relevance_scores.append(1.0 - (i * 0.1))
            else:
                # Single result
                results.append({
                    "type": "general",
                    "content": str(search_results),
                    "relevance": 1.0
                })
                relevance_scores.append(1.0)
            
            return MemorySearchResponse(
                results=results,
                relevance_scores=relevance_scores,
                total=len(results),
                query=request.query
            )
            
        except Exception as search_error:
            logger.error(f"Memory search error: {search_error}")
            # Return empty results if search fails
            return MemorySearchResponse(
                results=[],
                relevance_scores=[],
                total=0,
                query=request.query
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")

@router.get("/sessions/{session_id}/memory/stats")
async def get_memory_stats(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get memory statistics for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
            
        memory_manager = session.memory_manager
        
        # Get conversation count
        conversation_count = len(memory_manager.get_conversation_history())
        
        # Initialize stats with required fields
        stats = {
            "conversation_count": conversation_count,
            "entity_count": 0,
            "relationship_count": 0,
            "total_memory_size": conversation_count  # Default to conversation count
        }
        
        # Add graph statistics if available
        if hasattr(memory_manager, 'graph_manager') and memory_manager.graph_manager:
            try:
                entities = memory_manager.graph_manager.get_all_entities()
                relationships = memory_manager.graph_manager.get_all_relationships()
                
                stats.update({
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                    "total_memory_size": conversation_count + len(entities) + len(relationships)
                })
            except Exception as e:
                logger.warning(f"Could not get graph stats: {e}")
        
        return JSONResponse(stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory stats for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {str(e)}") 