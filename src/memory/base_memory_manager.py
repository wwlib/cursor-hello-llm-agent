"""Base Memory Manager for Agent System

This module defines the abstract base class for memory management implementations.
All concrete memory managers should inherit from this class and implement its abstract methods.

Design Principles:
1. Separation of Concerns
   - Core memory persistence functionality in base class
   - Specific memory operations defined as abstract methods
   - Concrete implementations provide domain-specific logic

2. Common Interface
   - All memory managers share the same public interface
   - Implementation details can vary while maintaining consistent API
   - Makes memory managers interchangeable in the agent system
"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import json
import os
import uuid
from datetime import datetime

class BaseMemoryManager(ABC):
    """Abstract base class for memory management implementations.
    
    Provides core functionality for memory persistence and defines interface
    for memory operations. Concrete implementations must implement all abstract methods.
    """
    
    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None):
        """Initialize the base memory manager.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Optional configuration for domain-specific behavior:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
                         - prompts: Domain-specific prompt templates
        """
        self.memory_file = memory_file
        self.domain_config = domain_config or {}
        self.memory: Dict[str, Any] = {}
        # The memory_guid attribute will be set by implementations
        self.memory_guid = None
        self._load_memory()

    def _load_memory(self) -> None:
        """Load memory from JSON file if it exists"""
        if os.path.exists(self.memory_file):
            print(f"Loading existing memory from {self.memory_file}")
            with open(self.memory_file, 'r') as f:
                self.memory = json.load(f)
            print("Memory loaded successfully")
        else:
            print("No existing memory file found")

    def save_memory(self) -> None:
        """Save current memory state to JSON file and create a backup.
        Backups are created with incrementing numbers (e.g. memory_bak_1.json)."""
        print(f"\nSaving memory to {self.memory_file}")
        
        try:
            # Create backup with incrementing number
            base_path = os.path.splitext(self.memory_file)[0]
            backup_num = 1
            while os.path.exists(f"{base_path}_bak_{backup_num}.json"):
                backup_num += 1
            backup_file = f"{base_path}_bak_{backup_num}.json"
            
            # Save current memory to both files
            for file_path in [self.memory_file, backup_file]:
                with open(file_path, 'w') as f:
                    json.dump(self.memory, f, indent=2)
            
            print(f"Memory saved successfully with backup: {backup_file}")
            
        except Exception as e:
            print(f"Error saving memory: {str(e)}")
            # Try to at least save the main file
            try:
                with open(self.memory_file, 'w') as f:
                    json.dump(self.memory, f, indent=2)
                print("Memory saved to main file despite backup error")
            except Exception as e2:
                print(f"Critical error: Failed to save memory: {str(e2)}")
                raise

    def get_memory_context(self) -> Dict[str, Any]:
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
