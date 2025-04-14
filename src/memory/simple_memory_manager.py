"""Simple Memory Manager Implementation

A straightforward implementation of BaseMemoryManager that simply accumulates data
without any LLM-based transformation. Useful for testing and simple use cases.

Key Features:
1. Stores initial data directly
2. Accumulates all messages in conversation history
3. Uses LLM for generating responses to queries
4. Simple, flat memory structure
"""

from typing import Any, Dict, Optional
import json
import uuid
from datetime import datetime
from .base_memory_manager import BaseMemoryManager

class SimpleMemoryManager(BaseMemoryManager):
    """Simple implementation of memory manager that accumulates data without transformation.
    
    This implementation:
    - Stores initial data as-is
    - Keeps all messages in conversation_history
    - Uses LLM for generating responses to queries
    - Uses simplified memory structure
    """
    
    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, llm_service = None, memory_guid: str = None):
        """Initialize the SimpleMemoryManager.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Optional configuration for domain-specific behavior
                         (not used in this implementation but kept for interface consistency)
            llm_service: Service for LLM operations (required for generating responses)
            memory_guid: Optional GUID to identify this memory instance. If not provided, 
                       a new one will be generated or loaded from existing file.
        """
        if llm_service is None:
            raise ValueError("llm_service is required for SimpleMemoryManager")
        
        # Pass memory_guid to the parent constructor
        super().__init__(memory_file, domain_config, memory_guid)
        print(f"\nInitializing SimpleMemoryManager with file: {memory_file}")
        self.llm = llm_service
        
        # Ensure memory has a GUID
        self._ensure_memory_guid()
        
    def _ensure_memory_guid(self):
        """Ensure that the memory has a GUID, prioritizing the provided GUID if available."""
        # If memory doesn't exist yet, we'll handle this when creating memory
        if not self.memory:
            # Make sure we have a GUID, generating one if needed
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                print(f"Generated new GUID: {self.memory_guid} for memory file that will be created")
            return
            
        # Priority order for GUID:
        # 1. GUID provided at initialization (self.memory_guid from constructor)
        # 2. GUID in existing memory file (self.memory["guid"])
        # 3. Generate a new GUID if neither exists
        
        # If we already have a GUID from initialization, use it
        if self.memory_guid:
            # Force the memory to use our provided GUID, overriding any existing GUID
            if "guid" in self.memory and self.memory["guid"] != self.memory_guid:
                print(f"Replacing existing memory GUID: {self.memory['guid']} with provided GUID: {self.memory_guid}")
            
            # Set the GUID in memory
            self.memory["guid"] = self.memory_guid
            print(f"Using provided GUID for memory: {self.memory_guid}")
            # self.save_memory()
        # If no GUID was provided but one exists in memory, use that
        elif "guid" in self.memory:
            self.memory_guid = self.memory["guid"]
            print(f"Using existing memory GUID: {self.memory_guid}")
        # If no GUID was provided and none exists in memory, generate a new one
        else:
            self.memory_guid = str(uuid.uuid4())
            self.memory["guid"] = self.memory_guid
            print(f"Generated new GUID for memory: {self.memory_guid}")
            # self.save_memory()

    def create_initial_memory(self, input_data: str) -> bool:
        """Store initial input data.
        
        Args:
            input_data: Initial data to store
            
        Returns:
            bool: True if memory was created successfully
        """
        try:
            # Check if we have valid existing memory
            if self.memory and all(key in self.memory for key in ["initial_data", "conversation_history", "last_updated"]):
                print("Valid memory structure already exists, skipping initialization")
                # Ensure GUID exists even for pre-existing memories
                self._ensure_memory_guid()
                return True
            
            # Use existing GUID if it was provided or already generated, only generate a new one as a last resort
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                print(f"Generated new GUID for memory: {self.memory_guid}")
            else:
                print(f"Using existing GUID for memory: {self.memory_guid}")
            
            # Initialize the simplified memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "guid": self.memory_guid,      # Use the GUID we already have or just generated
                "memory_type": "simple",       # Explicitly mark this as a simple memory type
                "initial_data": input_data,
                "conversation_history": [],
                "last_updated": now
            }
            
            self.save_memory("create_initial_memory:simple")
            print(f"Initial memory created with GUID: {self.memory_guid} and type: simple")
            return True
            
        except Exception as e:
            print(f"Error creating memory: {str(e)}")
            return False

    def query_memory(self, query_context: Dict[str, Any]) -> dict:
        """Process query using LLM to generate response.
        
        Args:
            query_context: Dictionary containing query context with user_message
            
        Returns:
            dict: Response from LLM
        """
        try:
            # Get user message from context
            user_message = query_context.get("user_message", "")
            
            # Add user message to history
            if user_message:
                self.memory["conversation_history"].append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Create prompt for LLM that includes all context
            prompt = f"""Given this context:

Initial Data:
{self.memory["initial_data"]}

Conversation History ({len(self.memory["conversation_history"])} messages):
{self._format_conversation_history()}

Latest User Message: {user_message}

Please provide a helpful response based on all available context."""
            
            # Get response from LLM
            print("Generating response using LLM...")
            llm_response = self.llm.generate(prompt)
            
            # Add response to history
            self.memory["conversation_history"].append({
                "role": "assistant",
                "content": llm_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update timestamp and save
            self.memory["last_updated"] = datetime.now().isoformat()
            self.save_memory("query_memory:simple")
            
            return {"response": llm_response}
            
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            return {"response": f"Error processing query: {str(e)}"}

    def _format_conversation_history(self) -> str:
        """Format conversation history for LLM prompt."""
        formatted = ""
        for msg in self.memory["conversation_history"]:
            formatted += f"\n[{msg['role']}] {msg['content']}"
        return formatted

    def update_memory(self, update_context: Dict[str, Any]) -> bool:
        """Update memory with new information.
        
        In this simple implementation, we just add the messages to history.
        Reflection is not needed since we don't transform memory structure.
        
        Args:
            update_context: Dictionary containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            # Only handle update operations
            if update_context.get("operation") != "update":
                print("update_memory should only be used for update operations")
                return False
            
            # For simple memory manager, we don't need reflection updates
            # Just return success since memory is already maintained during queries
            return True
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False
