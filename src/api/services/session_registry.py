"""
Session Registry Service

Manages a persistent registry of all agent sessions, enabling session discovery,
restoration, and lifecycle management.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class SessionState(str, Enum):
    """Session state enumeration"""
    ACTIVE = "active"       # Currently loaded in memory
    DORMANT = "dormant"     # Persisted to disk, can be restored
    ARCHIVED = "archived"   # Old sessions requiring full initialization
    EXPIRED = "expired"     # Sessions that can be cleaned up

@dataclass
class SessionRegistryEntry:
    """Registry entry for a session"""
    session_id: str
    user_id: Optional[str]
    domain: str
    enable_graph: bool
    created_at: str  # ISO format
    last_activity: str  # ISO format
    state: SessionState
    memory_path: str
    conversation_count: int = 0
    memory_size_mb: float = 0.0
    last_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionRegistryEntry':
        """Create from dictionary"""
        # Handle enum conversion
        if isinstance(data.get('state'), str):
            data['state'] = SessionState(data['state'])
        return cls(**data)
    
    def is_recent(self, hours: int = 24) -> bool:
        """Check if session had recent activity"""
        try:
            last_activity = datetime.fromisoformat(self.last_activity.replace('Z', '+00:00'))
            return (datetime.now() - last_activity.replace(tzinfo=None)) < timedelta(hours=hours)
        except Exception:
            return False
    
    def get_age_days(self) -> int:
        """Get session age in days"""
        try:
            created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            return (datetime.now() - created.replace(tzinfo=None)).days
        except Exception:
            return 0

class SessionRegistry:
    """Manages the persistent registry of agent sessions"""
    
    def __init__(self, base_memory_dir: str = "agent_memories"):
        self.base_memory_dir = base_memory_dir
        self.standard_memory_dir = os.path.join(base_memory_dir, "standard")
        self.registry_file = os.path.join(self.standard_memory_dir, "session_registry.json")
        
        # Ensure directories exist
        os.makedirs(self.standard_memory_dir, exist_ok=True)
        
        self.sessions: Dict[str, SessionRegistryEntry] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load registry from disk or create if it doesn't exist"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    
                # Load sessions from registry
                for session_id, session_data in data.get('sessions', {}).items():
                    try:
                        self.sessions[session_id] = SessionRegistryEntry.from_dict(session_data)
                    except Exception as e:
                        logger.warning(f"Failed to load session {session_id} from registry: {e}")
                        
                logger.info(f"Loaded {len(self.sessions)} sessions from registry")
                
            except Exception as e:
                logger.error(f"Failed to load session registry: {e}")
                self.sessions = {}
        else:
            logger.info("No existing session registry found, will create new one")
            self.sessions = {}
    
    def _save_registry(self) -> bool:
        """Save registry to disk"""
        try:
            registry_data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_sessions": len(self.sessions)
                },
                "sessions": {
                    session_id: entry.to_dict() 
                    for session_id, entry in self.sessions.items()
                }
            }
            
            # Create backup if registry exists
            if os.path.exists(self.registry_file):
                backup_file = f"{self.registry_file}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.registry_file, backup_file)
            
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            logger.debug(f"Saved session registry with {len(self.sessions)} sessions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session registry: {e}")
            return False
    
    def scan_existing_sessions(self) -> int:
        """Scan the filesystem for existing session directories and build registry"""
        if not os.path.exists(self.standard_memory_dir):
            logger.warning(f"Standard memory directory does not exist: {self.standard_memory_dir}")
            return 0
        
        scanned_count = 0
        new_sessions = 0
        
        # Scan for session directories (UUIDs)
        for item in os.listdir(self.standard_memory_dir):
            session_path = os.path.join(self.standard_memory_dir, item)
            
            # Skip files and non-UUID directories
            if not os.path.isdir(session_path) or item == "session_registry.json":
                continue
            
            # Check if it looks like a session ID (UUID format)
            # Relaxing this
            # if not self._is_uuid_format(item):
            #     continue

            # Check to see if the item (folder name) is the same as the guid in the agent_memory.json file
            agent_memory_file = os.path.join(session_path, "agent_memory.json")
            if os.path.exists(agent_memory_file):
                with open(agent_memory_file, 'r') as f:
                    agent_memory_data = json.load(f)
                    guid = agent_memory_data.get('guid', '')
                    if guid != item:
                        continue
            
            scanned_count += 1
            
            # Skip if already in registry
            if item in self.sessions:
                continue
            
            # Try to extract session information
            session_entry = self._extract_session_info(item, session_path)
            if session_entry:
                self.sessions[item] = session_entry
                new_sessions += 1
                logger.info(f"Added session to registry: {item}")
        
        if new_sessions > 0:
            self._save_registry()
            logger.info(f"Scanned {scanned_count} session directories, added {new_sessions} new sessions to registry")
        else:
            logger.info(f"Scanned {scanned_count} session directories, no new sessions found")
        
        return new_sessions
    
    def _is_uuid_format(self, text: str) -> bool:
        """Check if text looks like a UUID"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, text, re.IGNORECASE))
    
    def _extract_session_info(self, session_id: str, session_path: str) -> Optional[SessionRegistryEntry]:
        """Extract session information from filesystem"""
        try:
            memory_file = os.path.join(session_path, "agent_memory.json")
            conversations_file = os.path.join(session_path, "agent_memory_conversations.json")
            
            # Default values
            domain = "unknown"
            enable_graph = False
            created_at = datetime.now().isoformat()
            last_activity = datetime.now().isoformat()
            conversation_count = 0
            memory_size_mb = 0.0
            last_message = ""
            
            # Extract info from memory file if it exists
            if os.path.exists(memory_file):
                try:
                    with open(memory_file, 'r') as f:
                        memory_data = json.load(f)
                    
                    # Extract domain from metadata
                    metadata = memory_data.get('metadata', {})
                    domain = metadata.get('domain', 'unknown')
                    
                    # Check if graph memory was enabled
                    enable_graph = os.path.exists(os.path.join(session_path, "agent_memory_graph_data"))
                    
                    # Get file modification time as last activity
                    last_activity = datetime.fromtimestamp(os.path.getmtime(memory_file)).isoformat()
                    
                    # Get memory file size
                    memory_size_mb = os.path.getsize(memory_file) / (1024 * 1024)
                    
                except Exception as e:
                    logger.warning(f"Could not read memory file for session {session_id}: {e}")
            
            # Extract conversation info
            if os.path.exists(conversations_file):
                try:
                    with open(conversations_file, 'r') as f:
                        conversations_data = json.load(f)
                    
                    conversation_history = conversations_data.get('conversation_history', [])
                    conversation_count = len(conversation_history)
                    
                    # Get last user message
                    for entry in reversed(conversation_history):
                        if entry.get('role') == 'user':
                            last_message = entry.get('content', '')[:100]  # First 100 chars
                            break
                    
                    # Use conversation file modification time if more recent
                    conv_last_activity = datetime.fromtimestamp(os.path.getmtime(conversations_file)).isoformat()
                    if conv_last_activity > last_activity:
                        last_activity = conv_last_activity
                    
                except Exception as e:
                    logger.warning(f"Could not read conversations file for session {session_id}: {e}")
            
            # Get directory creation time as created_at
            try:
                created_at = datetime.fromtimestamp(os.path.getctime(session_path)).isoformat()
            except Exception:
                pass
            
            return SessionRegistryEntry(
                session_id=session_id,
                user_id=None,  # We don't have user info in the files
                domain=domain,
                enable_graph=enable_graph,
                created_at=created_at,
                last_activity=last_activity,
                state=SessionState.DORMANT,  # All scanned sessions start as dormant
                memory_path=session_path,
                conversation_count=conversation_count,
                memory_size_mb=memory_size_mb,
                last_message=last_message
            )
            
        except Exception as e:
            logger.error(f"Failed to extract session info for {session_id}: {e}")
            return None
    
    def add_session(self, session_id: str, user_id: Optional[str], domain: str, 
                   enable_graph: bool, memory_path: str) -> bool:
        """Add a new session to the registry"""
        try:
            entry = SessionRegistryEntry(
                session_id=session_id,
                user_id=user_id,
                domain=domain,
                enable_graph=enable_graph,
                created_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                state=SessionState.ACTIVE,
                memory_path=memory_path
            )
            
            self.sessions[session_id] = entry
            self._save_registry()
            logger.info(f"Added new session to registry: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add session to registry: {e}")
            return False
    
    def update_session_activity(self, session_id: str, conversation_count: int = None, 
                               last_message: str = None) -> bool:
        """Update session activity and metadata"""
        if session_id not in self.sessions:
            return False
        
        try:
            entry = self.sessions[session_id]
            entry.last_activity = datetime.now().isoformat()
            
            if conversation_count is not None:
                entry.conversation_count = conversation_count
            
            if last_message is not None:
                entry.last_message = last_message[:100]  # Truncate to 100 chars
            
            self._save_registry()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            return False
    
    def set_session_state(self, session_id: str, state: SessionState) -> bool:
        """Set session state"""
        if session_id not in self.sessions:
            return False
        
        try:
            self.sessions[session_id].state = state
            self._save_registry()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set session state: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[SessionRegistryEntry]:
        """Get session entry by ID"""
        return self.sessions.get(session_id)
    
    def get_sessions_by_state(self, state: SessionState) -> List[SessionRegistryEntry]:
        """Get all sessions with a specific state"""
        return [entry for entry in self.sessions.values() if entry.state == state]
    
    def get_recent_sessions(self, hours: int = 24) -> List[SessionRegistryEntry]:
        """Get sessions with recent activity"""
        return [entry for entry in self.sessions.values() if entry.is_recent(hours)]
    
    def get_all_sessions(self) -> List[SessionRegistryEntry]:
        """Get all sessions sorted by last activity (most recent first)"""
        return sorted(
            self.sessions.values(), 
            key=lambda x: x.last_activity, 
            reverse=True
        )
    
    def archive_old_sessions(self, days_old: int = 30) -> int:
        """Archive sessions older than specified days"""
        archived_count = 0
        
        for entry in self.sessions.values():
            if entry.state != SessionState.ARCHIVED and entry.get_age_days() > days_old:
                entry.state = SessionState.ARCHIVED
                archived_count += 1
        
        if archived_count > 0:
            self._save_registry()
            logger.info(f"Archived {archived_count} old sessions")
        
        return archived_count
    
    def remove_session(self, session_id: str) -> bool:
        """Remove session from registry"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_registry()
            logger.info(f"Removed session from registry: {session_id}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            "total_sessions": len(self.sessions),
            "by_state": {},
            "recent_sessions": len(self.get_recent_sessions()),
            "total_conversations": sum(entry.conversation_count for entry in self.sessions.values()),
            "total_memory_mb": sum(entry.memory_size_mb for entry in self.sessions.values())
        }
        
        for state in SessionState:
            stats["by_state"][state.value] = len(self.get_sessions_by_state(state))
        
        return stats
