"""
Session Manager Service

Manages agent sessions, lifecycle, and multi-tenant access patterns.
"""

import uuid
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from threading import Lock
from pathlib import Path

from ..models.sessions import SessionInfo, SessionStatus, SessionConfig
from ...agent.agent import Agent
from ...memory.memory_manager import MemoryManager
from ...ai.llm_ollama import OllamaService

logger = logging.getLogger(__name__)

# Constants for directory structure (matching agent_usage_example.py)
BASE_MEMORY_DIR = "agent_memories"
MEMORY_FILE_PREFIX = "agent_memory"
BASE_LOGS_DIR = "logs"

class AgentSession:
    """Represents an active agent session"""
    
    def __init__(self, session_id: str, user_id: Optional[str], config: SessionConfig):
        self.session_id = session_id
        self.user_id = user_id
        self.config = config
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.status = SessionStatus.ACTIVE
        
        # Initialize agent and memory manager
        self._agent: Optional[Agent] = None
        self._memory_manager: Optional[MemoryManager] = None
        self._lock = Lock()
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session has expired"""
        return (datetime.now() - self.last_activity).total_seconds() > timeout_seconds
        
    def get_memory_dir(self, memory_type: str = "standard") -> str:
        """Get the directory path for a specific memory manager type"""
        # Use absolute path to ensure files are created in the correct location
        current_dir = os.getcwd()
        dir_path = os.path.join(current_dir, BASE_MEMORY_DIR, memory_type)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def get_memory_filename(self, memory_type: str = "standard") -> str:
        """Generate a memory filename based on memory manager type and session GUID"""
        # Create memory directory for this type if it doesn't exist
        memory_dir = self.get_memory_dir(memory_type)
        
        # Create GUID directory if it doesn't exist
        guid_dir = os.path.join(memory_dir, self.session_id)
        os.makedirs(guid_dir, exist_ok=True)
        file_path = os.path.join(guid_dir, f"{MEMORY_FILE_PREFIX}.json")
        return file_path

    def setup_session_logging(self) -> Dict[str, str]:
        """Set up logging directories and files for this session"""
        # Create logs directory structure
        logs_dir = BASE_LOGS_DIR
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create GUID-specific logs directory
        guid_logs_dir = os.path.join(logs_dir, self.session_id)
        os.makedirs(guid_logs_dir, exist_ok=True)
        
        # Define log file paths
        log_files = {
            'ollama_general': os.path.join(guid_logs_dir, "ollama_general.log"),
            'ollama_digest': os.path.join(guid_logs_dir, "ollama_digest.log"),
            'ollama_embed': os.path.join(guid_logs_dir, "ollama_embed.log"),
            'memory_manager': os.path.join(guid_logs_dir, "memory_manager.log"),
            'agent': os.path.join(guid_logs_dir, "agent.log")
        }
        
        return log_files
        
    async def initialize_agent(self):
        """Initialize the agent for this session"""
        
        with self._lock:
            if self._agent is None:
                try:
                    # Set up logging and data paths
                    log_files = self.setup_session_logging()
                    
                    # Get memory file path using the same structure as agent_usage_example
                    memory_type = "standard"  # Default to standard for now
                    memory_file = self.get_memory_filename(memory_type)
                    
                    # Ensure the memory file directory exists
                    memory_file_dir = os.path.dirname(memory_file)
                    os.makedirs(memory_file_dir, exist_ok=True)
                    
                    # Debug logging to session log directory
                    debug_log_path = os.path.join(os.path.dirname(log_files['agent']), "debug_memory_file.log")
                    with open(debug_log_path, "w") as f:
                        f.write(f"Session ID: {self.session_id}\n")
                        f.write(f"Memory file path: {memory_file}\n")
                        f.write(f"Memory file dir: {memory_file_dir}\n")
                        f.write(f"Memory file is absolute: {os.path.isabs(memory_file)}\n")
                        f.write(f"Current working directory: {os.getcwd()}\n")
                    
                    # Create LLM service for this session
                    # Use environment variables or defaults
                    
                    # Create separate OllamaService instances for different purposes (like agent_usage_example)
                    general_llm_service = OllamaService({
                        'base_url': os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                        'model': self.config.llm_model or os.getenv("OLLAMA_MODEL", "llama2"),
                        'temperature': 0.7,
                        'stream': False,
                        'debug': os.getenv("DEV_MODE", "false").lower() == "true",
                        'debug_file': log_files['ollama_general'],
                        'debug_scope': f"session_{self.session_id}_general",
                        'console_output': False
                    })
                    
                    # Digest generation service
                    digest_llm_service = OllamaService({
                        'base_url': os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                        'model': self.config.llm_model or os.getenv("OLLAMA_MODEL", "llama2"),
                        'temperature': 0,
                        'stream': False,
                        'debug': os.getenv("DEV_MODE", "false").lower() == "true",
                        'debug_file': log_files['ollama_digest'],
                        'debug_scope': f"session_{self.session_id}_digest",
                        'console_output': False
                    })
                    
                    # Embeddings service
                    embeddings_llm_service = OllamaService({
                        'base_url': os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                        'model': os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
                        'debug': False,
                        'debug_file': log_files['ollama_embed']
                    })
                    
                    # Set up memory manager logging
                    memory_manager_logger = logging.getLogger(f"memory_manager.session_{self.session_id}")
                    memory_manager_logger.setLevel(logging.DEBUG)
                    memory_manager_log_handler = logging.FileHandler(log_files['memory_manager'])
                    memory_manager_log_handler.setLevel(logging.DEBUG)
                    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
                    memory_manager_log_handler.setFormatter(formatter)
                    memory_manager_logger.addHandler(memory_manager_log_handler)
                    
                    # Create memory manager with session-specific GUID, LLM service, and proper file path
                    debug_info = f"""
SessionManager Debug Info for {self.session_id}:
- Memory file path: {memory_file}
- Memory file exists: {os.path.exists(memory_file)}
- Memory file directory: {os.path.dirname(memory_file)}
- Memory file directory exists: {os.path.exists(os.path.dirname(memory_file))}
- Current working directory: {os.getcwd()}
"""
                    logger.info(debug_info)
                    
                    # Also write to a debug file for easier inspection
                    with open("session_manager_debug.log", "a") as f:
                        f.write(f"{datetime.now()}: {debug_info}\n")
                    
                    self._memory_manager = MemoryManager(
                        memory_guid=self.session_id,
                        memory_file=memory_file,  # Use the properly structured file path
                        llm_service=general_llm_service,
                        max_recent_conversation_entries=4,
                        digest_llm_service=digest_llm_service,
                        embeddings_llm_service=embeddings_llm_service,
                        logger=memory_manager_logger
                    )
                    
                    # Set up agent logging
                    agent_logger = logging.getLogger(f"agent.session_{self.session_id}")
                    agent_logger.setLevel(logging.DEBUG)
                    agent_handler = logging.FileHandler(log_files['agent'])
                    agent_handler.setFormatter(formatter)
                    agent_logger.addHandler(agent_handler)
                    
                    # Create agent with the memory manager and LLM service
                    self._agent = Agent(
                        llm_service=general_llm_service,
                        memory_manager=self._memory_manager,
                        domain_name=self.config.domain,
                        logger=agent_logger
                    )
                    
                    logger.info(f"Initialized agent for session {self.session_id}")
                    logger.info(f"Memory file: {memory_file}")
                    logger.info(f"Log files: {log_files}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize agent for session {self.session_id}: {e}")
                    self.status = SessionStatus.ERROR
                    raise
                    
    @property
    def agent(self) -> Optional[Agent]:
        """Get the agent instance"""
        return self._agent
        
    @property
    def memory_manager(self) -> Optional[MemoryManager]:
        """Get the memory manager instance"""
        return self._memory_manager
        
    async def cleanup(self):
        """Clean up session resources"""
        with self._lock:
            if self._memory_manager:
                # Save any pending memory state
                try:
                    # Save conversation history properly
                    conversation_data = self._memory_manager._load_conversation_history()
                    self._memory_manager._save_conversation_history(conversation_data)
                except Exception as e:
                    logger.error(f"Error saving conversations for session {self.session_id}: {e}")
                    
            self.status = SessionStatus.INACTIVE
            logger.info(f"Cleaned up session {self.session_id}")

class SessionManager:
    """Manages multiple agent sessions"""
    
    def __init__(self, max_sessions: int = 100, session_timeout: int = 3600):
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.active_sessions: Dict[str, AgentSession] = {}
        self._lock = Lock()
        
        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
    def _start_cleanup_task(self):
        """Start background task for session cleanup"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            logger.warning("No event loop available for automatic session cleanup")
            
    async def _periodic_cleanup(self):
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                
    async def create_session(self, config: SessionConfig, user_id: Optional[str] = None) -> str:
        """Create a new agent session"""
        
        with self._lock:
            # Check session limit
            if len(self.active_sessions) >= self.max_sessions:
                # Try to clean up expired sessions first
                await self.cleanup_expired_sessions()
                
                if len(self.active_sessions) >= self.max_sessions:
                    raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session
            session = AgentSession(session_id, user_id, config)
            self.active_sessions[session_id] = session
            
            logger.info(f"Created session {session_id} for user {user_id}")
            
        # Initialize agent (outside lock to avoid blocking)
        await session.initialize_agent()
        
        return session_id
        
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get an existing session"""
        with self._lock:
            session = self.active_sessions.get(session_id)
            if session:
                if session.is_expired(self.session_timeout):
                    # Session expired, remove it
                    await self._remove_session(session_id)
                    return None
                else:
                    session.update_activity()
            return session
            
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            return await self._remove_session(session_id)
            
    async def _remove_session(self, session_id: str) -> bool:
        """Remove a session (internal method, assumes lock is held)"""
        session = self.active_sessions.get(session_id)
        if session:
            await session.cleanup()
            del self.active_sessions[session_id]
            logger.info(f"Removed session {session_id}")
            return True
        return False
        
    async def cleanup_expired_sessions(self):
        """Clean up all expired sessions"""
        expired_sessions = []
        
        with self._lock:
            for session_id, session in self.active_sessions.items():
                if session.is_expired(self.session_timeout):
                    expired_sessions.append(session_id)
                    
        for session_id in expired_sessions:
            await self._remove_session(session_id)
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
    def list_sessions(self, user_id: Optional[str] = None) -> List[SessionInfo]:
        """List active sessions"""
        with self._lock:
            sessions = []
            for session in self.active_sessions.values():
                if user_id is None or session.user_id == user_id:
                    sessions.append(SessionInfo(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        status=session.status,
                        created_at=session.created_at,
                        last_activity=session.last_activity,
                        config=session.config
                    ))
            return sessions
            
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        with self._lock:
            return len(self.active_sessions)
            
    async def cleanup(self):
        """Clean up all resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        # Clean up all sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self._remove_session(session_id)
            
        logger.info("Session manager cleanup complete") 