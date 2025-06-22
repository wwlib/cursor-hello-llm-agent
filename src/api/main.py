"""
FastAPI Application Entry Point

Main application factory and configuration for the Agent System API.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import sessions, agent, memory, graph, websocket
from .services.session_manager import SessionManager
from .middleware.logging import LoggingMiddleware
from .websocket.manager import manager as websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global session manager instance
session_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global session_manager
    
    # Startup
    logger.info("Starting Agent System API...")
    session_manager = SessionManager()
    app.state.session_manager = session_manager
    
    # Start WebSocket heartbeat monitor
    heartbeat_task = asyncio.create_task(websocket_manager.start_heartbeat_monitor())
    logger.info("WebSocket heartbeat monitor started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent System API...")
    
    # Cancel heartbeat task
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    
    if session_manager:
        await session_manager.cleanup()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="Agent System API",
        description="REST API for intelligent agent with memory and graph capabilities",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Include routers
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
    app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
    app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return JSONResponse({
            "status": "healthy",
            "version": "1.0.0",
            "active_sessions": len(session_manager.active_sessions) if session_manager else 0,
            "websocket_connections": websocket_manager.get_connection_count()
        })
    
    # Global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500}
        )
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port) 