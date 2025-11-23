"""Base Memory Manager for Agent System

This module defines the abstract base class for memory management implementations.
All concrete memory managers should inherit from this class and implement its abstract methods.

Design Principles::

    1. Separation of Concerns
       - Core memory persistence functionality in base class
       - Specific memory operations defined as abstract methods
       - Concrete implementations provide domain-specific logic

    2. Common Interface
       - All memory managers share the same public interface
       - Implementation details can vary while maintaining consistent API
       - Makes memory managers interchangeable in the agent system
"""

from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
import json
import os
import uuid
from datetime import datetime
import logging

class BaseMemoryManager(ABC):
    """Abstract base class for memory management implementations.
    
    Provides core functionality for memory persistence and defines interface
    for memory operations. Concrete implementations must implement all abstract methods.
    """
    
    def __init__(self, memory_guid: str, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, logger=None):
        """Initialize the base memory manager.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Optional configuration for domain-specific behavior:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
                         - prompts: Domain-specific prompt templates
            memory_guid: Required GUID to identify this memory instance
            logger: Optional logger instance for logging
        """
        self.memory_file = memory_file
        self.domain_config = domain_config or {}
        # Store the provided memory_guid (may be None)
        self.memory_guid = memory_guid
        # Store the logger instance, or get a default logger for this module
        self.logger = logger or logging.getLogger(__name__)
        self.memory: Dict[str, Any] = self._load_memory()
        # Initialize conversation history file path based on memory file
        self._init_conversation_history_file()

    def _init_conversation_history_file(self):
        """Initialize the conversation history file path based on memory file."""
        # Determine memory directory and base filename
        memory_dir = os.path.dirname(self.memory_file) or "."
        memory_base = os.path.basename(self.memory_file).split(".")[0]
        
        # Create conversation history file name based on memory file
        self.conversation_history_file = os.path.join(memory_dir, f"{memory_base}_conversations.json")
        self.logger.debug(f"Conversation history file: {self.conversation_history_file}")
        
        # Initialize conversation history structure if it doesn't exist
        if not os.path.exists(self.conversation_history_file):
            self._initialize_conversation_history()
        
    def _initialize_conversation_history(self):
        """Create initial conversation history file structure."""
        # Create initial structure with memory GUID
        conversation_data = {
            "memory_file_guid": self.memory_guid or "",  # Will be updated when memory GUID is set
            "entries": []
        }
        
        # Save to file
        try:
            with open(self.conversation_history_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
            self.logger.debug(f"Created new conversation history file: {self.conversation_history_file}")
        except Exception as e:
            self.logger.error(f"Error creating conversation history file: {str(e)}")
            
    def _load_conversation_history(self) -> Dict[str, Any]:
        """Load conversation history from file."""
        try:
            if os.path.exists(self.conversation_history_file):
                with open(self.conversation_history_file, 'r') as f:
                    conversation_data = json.load(f)
                    
                # Ensure the memory GUID matches
                if self.memory_guid and conversation_data.get("memory_file_guid") != self.memory_guid:
                    self.logger.debug(f"Warning: Conversation history GUID mismatch. Expected {self.memory_guid}, found {conversation_data.get('memory_file_guid')}")
                    # Update the GUID to match current memory
                    conversation_data["memory_file_guid"] = self.memory_guid
                    self._save_conversation_history(conversation_data)
                    
                return conversation_data
            else:
                return self._initialize_conversation_history()
        except Exception as e:
            self.logger.error(f"Error loading conversation history: {str(e)}")
            return {"memory_file_guid": self.memory_guid or "", "entries": []}
            
    def _save_conversation_history(self, conversation_data: Dict[str, Any]) -> bool:
        """Save conversation history to file."""
        try:
            # Ensure memory GUID is set in conversation history
            if self.memory_guid:
                conversation_data["memory_file_guid"] = self.memory_guid
                
            with open(self.conversation_history_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving conversation history: {str(e)}")
            return False
            
    def add_to_conversation_history(self, entry: Dict[str, Any]) -> bool:
        """Add an entry to the conversation history.
        
        Args:
            entry: Dictionary containing the conversation entry with role, content, etc.
            
        Returns:
            bool: True if entry was added successfully
        """
        try:
            # Load current conversation history
            conversation_data = self._load_conversation_history()
            
            # Add entry to history
            conversation_data["entries"].append(entry)
            
            # Save updated history
            return self._save_conversation_history(conversation_data)
        except Exception as e:
            self.logger.error(f"Error adding to conversation history: {str(e)}")
            return False
            
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the full conversation history.
        
        Returns:
            list: List of conversation entries
        """
        try:
            conversation_data = self._load_conversation_history()
            return conversation_data.get("entries", [])
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    def update_conversation_history_entry(self, entry: Dict[str, Any]) -> bool:
        """Update an existing entry in the conversation history (e.g., when digest is added).
        
        Args:
            entry: Dictionary containing the conversation entry with updated fields (e.g., digest)
            
        Returns:
            bool: True if entry was updated successfully
        """
        try:
            entry_guid = entry.get("guid")
            if not entry_guid:
                self.logger.warning("Cannot update conversation history entry without guid")
                return False
            
            # Load current conversation history
            conversation_data = self._load_conversation_history()
            entries = conversation_data.get("entries", [])
            
            # Find and update the entry
            updated = False
            for i, existing_entry in enumerate(entries):
                if existing_entry.get("guid") == entry_guid:
                    # Update the entry with new fields (e.g., digest)
                    entries[i].update(entry)
                    updated = True
                    break
            
            if not updated:
                self.logger.warning(f"Entry with guid {entry_guid} not found in conversation history")
                return False
            
            # Save updated history
            conversation_data["entries"] = entries
            return self._save_conversation_history(conversation_data)
        except Exception as e:
            self.logger.error(f"Error updating conversation history entry: {str(e)}")
            return False

    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    memory_data = json.load(f)
                    # If memory already has a GUID and we weren't given one
                    if "guid" in memory_data and not self.memory_guid:
                        self.memory_guid = memory_data["guid"]
                        self.logger.debug(f"Loaded memory with existing GUID: {self.memory_guid}")
                self.logger.debug("Memory loaded from file")
                return memory_data
            else:
                self.logger.debug("Memory file not found, will create new memory")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading memory: {str(e)}")
            return {}

    def save_memory(self, operation_name: str = "unknown") -> bool:
        """Save memory to file."""
        try:
            # Backup existing file if it exists
            if os.path.exists(self.memory_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{os.path.splitext(self.memory_file)[0]}_bak_{timestamp}{os.path.splitext(self.memory_file)[1]}"
                os.rename(self.memory_file, backup_file)
                self.logger.debug(f"Backup created: {backup_file}")
            
            # Ensure memory has current GUID
            if self.memory_guid and self.memory:
                self.memory["guid"] = self.memory_guid

            if "metadata" not in self.memory:
                self.memory["metadata"] = {}
            self.memory["metadata"]["saved_during"] = operation_name
            
            # Write updated memory to file
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
            self.logger.debug(f"Memory saved after '{operation_name}' operation")
            return True
        except Exception as e:
            self.logger.error(f"Error saving memory: {str(e)}")
            return False

    def get_memory(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)

    def _extract_schema(self, data: dict) -> dict:
        """Extract schema from existing memory structure."""
        schema = {}
        
        if isinstance(data, dict):
            schema = {k: self._extract_schema(v) for k, v in data.items()}
        elif isinstance(data, list):
            if data:  # If list is not empty, use first item as example
                schema = [self._extract_schema(data[0])]
            else:
                schema = []
        else:
            # For primitive values, store their type
            schema = type(data).__name__
            
        return schema

    @abstractmethod
    def create_initial_memory(self, input_data: str) -> bool:
        """Create initial memory structure from input data.
        
        Args:
            input_data: Initial data to structure into memory format
            
        Returns:
            bool: True if memory was created successfully
        """
        pass

    @abstractmethod
    def query_memory(self, query_context: Dict[str, Any]) -> dict:
        """Query memory with the given context.
        
        Args:
            query_context: Dictionary containing query context
            
        Returns:
            dict: Query response
        """
        pass

    @abstractmethod
    def update_memory(self, update_context: Dict[str, Any]) -> bool:
        """Update memory with new information.
        
        Args:
            update_context: Dictionary containing update information
            
        Returns:
            bool: True if memory was updated successfully
        """
        pass

    def get_memory_guid(self) -> Optional[str]:
        """Get the GUID of the current memory file.
        
        Returns:
            str: The memory GUID if available, None otherwise
        """
        return self.memory_guid
    
    def has_pending_operations(self) -> bool:
        """Check if there are any pending async operations.
        
        Returns:
            bool: True if there are pending operations
        """
        return False  # Default implementation for synchronous managers
    
    def get_pending_operations(self) -> Dict[str, Any]:
        """Get information about pending async operations.
        
        Returns:
            Dict with counts of pending digests, embeddings, and graph updates
        """
        return {
            "pending_digests": 0,
            "pending_embeddings": 0,
            "pending_graph_updates": 0
        }  # Default implementation for synchronous managers
    
    def get_graph_context(self, query: str, max_entities: int = 5) -> str:
        """Get graph-based context for a query.
        
        Args:
            query: The query to find relevant graph context for
            max_entities: Maximum number of entities to include in context
            
        Returns:
            str: Formatted graph context string
        """
        return ""  # Default implementation returns empty context
