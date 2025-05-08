from enum import Enum
from typing import Dict, List, Optional
import json
from datetime import datetime
import asyncio

class AgentPhase(Enum):
    INITIALIZATION = "INITIALIZATION"
    LEARNING = "LEARNING"
    INTERACTION = "INTERACTION"

class Agent:
    def __init__(self, llm_service, memory_manager, domain_name: str = "general"):
        """Initialize the agent with required services.
        
        Args:
            llm_service: Service for LLM operations
            memory_manager: Service for memory operations (should be AsyncMemoryManager)
            domain_name: Name of the domain (e.g., "dnd_campaign", "user_stories")
        """
        self.llm = llm_service
        self.memory = memory_manager
        self.domain_name = domain_name
        self.current_phase = AgentPhase.INITIALIZATION
        print(f"Agent initialized for domain: {domain_name}")
        print(f"Memory management is handled transparently by the MemoryManager")
        
        # Track pending operations
        self._pending_operations = False

    def get_current_phase(self) -> AgentPhase:
        """Get the current agent phase"""
        return self.current_phase

    def get_conversation_history(self) -> list:
        """Get the current conversation history from memory"""
        memory_context = self.memory.get_memory_context()
        return memory_context.get("conversation_history", [])
        
    def has_pending_operations(self) -> bool:
        """Check if there are any pending async operations."""
        if hasattr(self.memory, 'get_pending_operations'):
            pending = self.memory.get_pending_operations()
            return pending["pending_digests"] > 0 or pending["pending_embeddings"] > 0
        return False

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response.
        
        Memory management (compression, etc.) is automatically handled by the MemoryManager.
        Digest generation and embeddings updates happen asynchronously.
        """
        try:
            # Create query context
            query_context = {
                "query": message
            }
            
            # Query memory for response
            response = self.memory.query_memory(query_context)
            
            # After first message, transition to INTERACTION phase
            if self.current_phase == AgentPhase.INITIALIZATION:
                self.current_phase = AgentPhase.INTERACTION
            
            # Return just the string response, not the whole dict
            return response.get("response", str(response))
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return "Error processing message"

    async def learn(self, information: str) -> bool:
        """Learn new information and update memory.
        
        This method handles two types of learning:
        1. Initial learning during INITIALIZATION phase
        2. Ongoing learning during INTERACTION phase
        
        Args:
            information: New information to learn
            
        Returns:
            bool: True if learning was successful
        """
        try:
            print(f"\nLearning new information (Current phase: {self.current_phase})")
            
            # Create initial memory if needed
            if self.current_phase == AgentPhase.INITIALIZATION:
                success = self.memory.create_initial_memory(information)
                if success:
                    print("Initial memory created")
                    self.current_phase = AgentPhase.LEARNING
                return success
            
            # For ongoing learning, use update_memory
            if self.current_phase in [AgentPhase.LEARNING, AgentPhase.INTERACTION]:
                # Add the new information to conversation history
                context = {
                    "operation": "update",
                    "learning_content": information
                }
                
                success = self.memory.update_memory(context)
                if success:
                    print("Successfully learned new information")
                    # Transition to INTERACTION phase if we were in LEARNING
                    if self.current_phase == AgentPhase.LEARNING:
                        self.current_phase = AgentPhase.INTERACTION
                else:
                    print("Failed to learn new information")
                return success
            
            print(f"Unexpected phase for learning: {self.current_phase}")
            return False
            
        except Exception as e:
            print(f"Error learning information: {str(e)}")
            return False
            
    async def wait_for_pending_operations(self) -> None:
        """Wait for all pending async operations to complete."""
        if hasattr(self.memory, 'wait_for_pending_operations'):
            await self.memory.wait_for_pending_operations()
