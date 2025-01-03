from enum import Enum
from typing import Dict, List, Optional
import json
from datetime import datetime

class AgentPhase(Enum):
    INITIALIZATION = "INITIALIZATION"
    LEARNING = "LEARNING"
    INTERACTION = "INTERACTION"

class Agent:
    def __init__(self, llm_service, memory_manager):
        """Initialize the agent with required services.
        
        Args:
            llm_service: Service for LLM operations
            memory_manager: Service for memory operations
        """
        self.llm = llm_service
        self.memory = memory_manager
        self.current_phase = AgentPhase.INITIALIZATION
        print(f"Agent initialized in {self.current_phase} phase")

    def get_current_phase(self) -> AgentPhase:
        """Get the current agent phase"""
        return self.current_phase

    def get_conversation_history(self) -> list:
        """Get the current conversation history from memory"""
        memory_context = self.memory.get_memory_context()
        return memory_context.get("conversation_history", [])

    async def process_message(self, message: str) -> str:
        """Process a user message and update agent state.
        
        Args:
            message: The user's message
            
        Returns:
            str: The agent's response
        """
        try:
            print(f"\nProcessing message (Current phase: {self.current_phase})")
            
            # Create query context
            context = {
                "current_phase": self.current_phase.name,
                "user_message": message
            }
            
            # Query memory and get response
            result = self.memory.query_memory(json.dumps(context))
            if not result:
                print("Failed to generate response")
                return None
            
            # Handle phase transition if suggested
            suggested_phase = result.get("suggested_phase", "INTERACTION")
            if suggested_phase not in AgentPhase.__members__:
                print(f"Invalid phase suggestion: {suggested_phase}, defaulting to INTERACTION")
                suggested_phase = "INTERACTION"
            
            if suggested_phase != self.current_phase.name:
                print(f"Transitioning from {self.current_phase} to {suggested_phase}")
                self.current_phase = AgentPhase[suggested_phase]
            
            return result["response"]
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"

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
                    print("Initial memory created, transitioning to LEARNING phase")
                    self.current_phase = AgentPhase.LEARNING
                    print("Transitioning to INTERACTION phase")
                    self.current_phase = AgentPhase.INTERACTION
                return success
            
            # Update existing memory
            context = {
                "phase": self.current_phase.name,
                "information": information,
                "recent_history": self.get_conversation_history()
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
            
            # Create reflection context
            context = {
                "operation": "reflect",
                "message": {
                    "role": "system",
                    "content": "Reflection triggered",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            success = self.memory.update_memory(json.dumps(context))
            if not success:
                print("Failed to complete reflection")
            
        except Exception as e:
            print(f"Error during reflection: {str(e)}")
