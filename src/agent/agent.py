from enum import Enum
from typing import Dict, List, Optional
import json
from datetime import datetime

class AgentPhase(Enum):
    INITIALIZATION = "INITIALIZATION"
    LEARNING = "LEARNING"
    INTERACTION = "INTERACTION"

class Agent:
    def __init__(self, llm_service, memory_manager, domain_name: str = "general", reflection_threshold: int = 10):
        """Initialize the agent with required services.
        
        Args:
            llm_service: Service for LLM operations
            memory_manager: Service for memory operations
            domain_name: Name of the domain (e.g., "dnd_campaign", "user_stories")
            reflection_threshold: Number of conversation turns before triggering reflection (default: 10)
        """
        self.llm = llm_service
        self.memory = memory_manager
        self.domain_name = domain_name
        self.current_phase = AgentPhase.INITIALIZATION
        self.reflection_threshold = reflection_threshold
        print(f"Agent initialized for domain: {domain_name}")
        print(f"Reflection will occur every {reflection_threshold} turns")

    def get_current_phase(self) -> AgentPhase:
        """Get the current agent phase"""
        return self.current_phase

    def get_conversation_history(self) -> list:
        """Get the current conversation history from memory"""
        memory_context = self.memory.get_memory_context()
        return memory_context.get("conversation_history", [])

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response."""
        try:
            # Create query context
            context = {
                "user_message": message
            }
            
            # Query memory for response
            result = self.memory.query_memory(json.dumps(context))
            response = result.get("response", "Error processing message")
            
            # After first message, transition to INTERACTION phase
            if self.current_phase == AgentPhase.INITIALIZATION:
                self.current_phase = AgentPhase.INTERACTION
            
            # Check if we need reflection
            if len(self.get_conversation_history()) >= self.reflection_threshold:
                await self.reflect()
                
            return response
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return "Error processing message"

    async def learn(self, information: str) -> bool:
        """Learn new information and update memory.
        
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
                    self.current_phase = AgentPhase.INTERACTION
                return success
            
            # Update existing memory with new information
            context = {
                "operation": "update",
                "messages": [{
                    "role": "system",
                    "content": information,
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            success = self.memory.update_memory(json.dumps(context))
            if success:
                print("Successfully learned new information")
            else:
                print("Failed to learn new information")
            return success
            
        except Exception as e:
            print(f"Error learning information: {str(e)}")
            return False

    async def reflect(self) -> None:
        """Reflect on recent interactions and update memory accordingly."""
        try:
            print(f"\nReflecting on recent interactions (Current phase: {self.current_phase})")
            
            # Get recent conversation history
            conversation_history = self.get_conversation_history()
            
            # Create reflection context
            context = {
                "operation": "update",
                "messages": conversation_history + [{
                    "role": "system",
                    "content": "Reflection triggered",
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            success = self.memory.update_memory(json.dumps(context))
            if not success:
                print("Failed to complete reflection")
            
        except Exception as e:
            print(f"Error during reflection: {str(e)}")
