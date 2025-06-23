"""
Graph Router

API endpoints for graph data access and visualization.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse

from ..models.responses import GraphDataResponse
from ..services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

def get_session_manager(request: Request) -> SessionManager:
    """Dependency to get session manager from app state"""
    return request.app.state.session_manager

@router.get("/sessions/{session_id}/graph", response_model=GraphDataResponse)
async def get_graph_data(
    session_id: str,
    format: str = Query("json", description="Response format (json|d3)"),
    include_metadata: bool = Query(True, description="Include metadata in response"),
    node_limit: Optional[int] = Query(None, description="Maximum number of nodes"),
    edge_limit: Optional[int] = Query(None, description="Maximum number of edges"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get graph data for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not session.memory_manager:
            raise HTTPException(status_code=500, detail="Memory manager not initialized")
            
        # Check if graph memory is available
        if not hasattr(session.memory_manager, 'graph_manager') or not session.memory_manager.graph_manager:
            return GraphDataResponse(
                nodes=[],
                edges=[],
                metadata={"message": "Graph memory not enabled for this session"},
                stats={"nodes": 0, "edges": 0}
            )
            
        graph_manager = session.memory_manager.graph_manager
        
        try:
            # Get entities (nodes) and relationships (edges) from graph manager
            entities = graph_manager.nodes  # Dictionary of entity_id -> GraphNode
            relationships = graph_manager.edges  # List of GraphEdge objects
            
            # Convert entities to nodes
            nodes = []
            for entity_id, entity in entities.items():
                if node_limit and len(nodes) >= node_limit:
                    break
                    
                node_data = {
                    "id": entity_id,
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description
                }
                
                if include_metadata:
                    node_data["metadata"] = getattr(entity, 'attributes', {})
                    
                # Format for D3 if requested
                if format == "d3":
                    node_data["group"] = hash(entity.entity_type) % 10  # Simple grouping
                    
                nodes.append(node_data)
            
            # Convert relationships to edges
            edges = []
            for relationship in relationships:
                if edge_limit and len(edges) >= edge_limit:
                    break
                    
                edge_data = {
                    "id": relationship.id,
                    "source": relationship.from_node_id,
                    "target": relationship.to_node_id,
                    "type": relationship.relationship,
                    "description": getattr(relationship, 'evidence', relationship.relationship)
                }
                
                if include_metadata:
                    edge_data["metadata"] = {
                        "confidence": getattr(relationship, 'confidence', 1.0),
                        "created_at": getattr(relationship, 'created_at', ''),
                        "updated_at": getattr(relationship, 'updated_at', '')
                    }
                    
                # Format for D3 if requested
                if format == "d3":
                    edge_data["value"] = relationship.strength if hasattr(relationship, 'strength') else 1
                    
                edges.append(edge_data)
            
            # Prepare metadata
            metadata = None
            if include_metadata:
                metadata = {
                    "session_id": session_id,
                    "graph_type": "entity_relationship",
                    "format": format,
                    "generated_at": session.last_activity.isoformat(),
                    "config": {
                        "domain": session.config.domain,
                        "node_limit": node_limit,
                        "edge_limit": edge_limit
                    }
                }
            
            # Calculate stats
            stats = {
                "nodes": len(nodes),
                "edges": len(edges),
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "truncated": {
                    "nodes": node_limit and len(entities) > node_limit,
                    "edges": edge_limit and len(relationships) > edge_limit
                }
            }
            
            return GraphDataResponse(
                nodes=nodes,
                edges=edges,
                metadata=metadata,
                stats=stats
            )
            
        except Exception as graph_error:
            logger.error(f"Graph data error: {graph_error}")
            return GraphDataResponse(
                nodes=[],
                edges=[],
                metadata={"error": f"Failed to retrieve graph data: {str(graph_error)}"},
                stats={"nodes": 0, "edges": 0}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph data for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get graph data: {str(e)}")

@router.get("/sessions/{session_id}/graph/entity/{entity_id}")
async def get_entity_details(
    session_id: str,
    entity_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get details for a specific entity"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not hasattr(session.memory_manager, 'graph_manager') or not session.memory_manager.graph_manager:
            raise HTTPException(status_code=404, detail="Graph memory not available")
            
        graph_manager = session.memory_manager.graph_manager
        
        # Get entity
        entities = graph_manager.nodes
        if entity_id not in entities:
            raise HTTPException(status_code=404, detail="Entity not found")
            
        entity = entities[entity_id]
        
        # Get relationships for this entity
        relationships = graph_manager.edges
        entity_relationships = []
        
        for relationship in relationships:
            if relationship.from_node_id == entity_id or relationship.to_node_id == entity_id:
                entity_relationships.append({
                    "id": relationship.id,
                    "type": relationship.relationship,
                    "description": getattr(relationship, 'evidence', relationship.relationship),
                    "source": relationship.from_node_id,
                    "target": relationship.to_node_id,
                    "is_source": relationship.from_node_id == entity_id
                })
        
        return JSONResponse({
            "entity": {
                "id": entity_id,
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description,
                "metadata": entity.metadata
            },
            "relationships": entity_relationships,
            "relationship_count": len(entity_relationships)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity details for {entity_id} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get entity details: {str(e)}")

@router.get("/sessions/{session_id}/graph/stats")
async def get_graph_stats(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get detailed graph statistics"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if not hasattr(session.memory_manager, 'graph_manager') or not session.memory_manager.graph_manager:
            return JSONResponse({
                "session_id": session_id,
                "graph_enabled": False,
                "message": "Graph memory not available for this session"
            })
            
        graph_manager = session.memory_manager.graph_manager
        
        try:
            entities = graph_manager.nodes
            relationships = graph_manager.edges
            
            # Count entity types
            entity_types = {}
            for entity in entities.values():
                entity_type = entity.type
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            # Count relationship types
            relationship_types = {}
            for relationship in relationships:
                rel_type = relationship.relationship
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        
            return JSONResponse({
                "session_id": session_id,
                "graph_enabled": True,
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "graph_density": len(relationships) / max(len(entities), 1),
                "last_updated": session.last_activity.isoformat()
            })
            
        except Exception as graph_error:
            logger.error(f"Graph stats error: {graph_error}")
            return JSONResponse({
                "session_id": session_id,
                "graph_enabled": True,
                "error": f"Failed to calculate graph stats: {str(graph_error)}"
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph stats for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {str(e)}") 