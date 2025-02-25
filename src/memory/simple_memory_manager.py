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
    
    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, llm_service = None):
        """Initialize the SimpleMemoryManager.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Optional configuration for domain-specific behavior
                         (not used in this implementation but kept for interface consistency)
            llm_service: Service for LLM operations (required for generating responses)
        """
        if llm_service is None:
            raise ValueError("llm_service is required for SimpleMemoryManager")
            
        super().__init__(memory_file, domain_config)
        print(f"\nInitializing SimpleMemoryManager with file: {memory_file}")
        self.llm = llm_service

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
                return True
                
            # Initialize the simplified memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "initial_data": input_data,
                "conversation_history": [],
                "last_updated": now
            }
            
            self.save_memory()
            print("Initial memory created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating memory: {str(e)}")
            return False

    def query_memory(self, query_context: str) -> dict:
        """Process query using LLM to generate response.
        
        Args:
            query_context: JSON string containing query context with user_message
            
        Returns:
            dict: Response from LLM
        """
        try:
            # Parse the query context
            context = json.loads(query_context)
            user_message = context.get("user_message", "")
            
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
            self.save_memory()
            
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

    def update_memory(self, update_context: str) -> bool:
        """Update memory with new information.
        
        In this simple implementation, we just add the messages to history.
        Reflection is not needed since we don't transform memory structure.
        
        Args:
            update_context: JSON string containing update context with messages
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            # Parse the update context
            context = json.loads(update_context)
            
            # Only handle update operations
            if context.get("operation") != "update":
                print("update_memory should only be used for update operations")
                return False
            
            # For simple memory manager, we don't need reflection updates
            # Just return success since memory is already maintained during queries
            return True
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False
