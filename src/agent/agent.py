from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from enum import Enum, auto

class AgentPhase(Enum):
    """Enum representing the different phases of the agent"""
    INITIALIZATION = auto()
    LEARNING = auto()
    INTERACTION = auto()

class Agent:
    """LLM-driven agent with session memory"""

    def __init__(self, llm_service, memory_manager):
        """Initialize the agent with required services.
        
        Args:
            llm_service: Service for LLM operations (used only for direct interactions)
            memory_manager: Service for memory management and LLM operations
        """
        self.llm = llm_service  # Keep for potential direct interactions
        self.memory = memory_manager
        self.current_phase = AgentPhase.INITIALIZATION
        self.conversation_history: List[Dict[str, str]] = []

    def get_current_phase(self) -> AgentPhase:
        """Get the current phase of the agent"""
        return self.current_phase

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history"""
        return self.conversation_history

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response.
        
        Args:
            message: The user's message
            
        Returns:
            str: The agent's response
        """
        try:
            # Create query context
            query_context = {
                "current_phase": self.current_phase.name,
                "recent_messages": self.conversation_history[-5:],
                "user_message": message
            }
            
            # Query memory for response
            result = self.memory.query_memory(json.dumps(query_context))
            
            if not result:
                raise Exception("Failed to get response from memory")
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            self.conversation_history.append({
                "role": "assistant",
                "content": result["response"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Update phase if suggested
            if result.get("suggested_phase"):
                try:
                    self.current_phase = AgentPhase[result["suggested_phase"]]
                except (KeyError, ValueError):
                    pass  # Keep current phase if suggestion is invalid
            
            return result["response"]
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.conversation_history.append({
                "role": "error",
                "content": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            return error_msg

    async def learn(self, information: str) -> bool:
        """Learn new information and update memory.
        
        Args:
            information: New information to learn
            
        Returns:
            bool: True if learning was successful
        """
        try:
            # Set phase to learning
            self.current_phase = AgentPhase.LEARNING

            # Create learning context
            learning_context = {
                "phase": self.current_phase.name,
                "information": information,
                "recent_history": self.conversation_history[-5:]
            }

            # Use memory manager to process and store new information
            success = self.memory.update_memory(json.dumps(learning_context))

            # Add to conversation history
            self.conversation_history.append({
                "role": "system",
                "content": "Learned new information successfully" if success else "Failed to learn new information",
                "timestamp": datetime.now().isoformat()
            })

            return success

        except Exception as e:
            self.conversation_history.append({
                "role": "error",
                "content": f"Error learning information: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            return False

    async def reflect(self) -> bool:
        """Reflect on recent interactions to optimize memory.
        
        Returns:
            bool: True if reflection was successful
        """
        try:
            # Create reflection context
            reflection_context = {
                "operation": "reflect",
                "recent_history": self.conversation_history[-10:]  # Use last 10 messages for reflection
            }
            
            # Use memory manager to process reflection
            success = self.memory.update_memory(json.dumps(reflection_context))
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "system",
                "content": "Completed memory reflection" if success else "Failed to complete reflection",
                "timestamp": datetime.now().isoformat()
            })
            
            return success
            
        except Exception as e:
            self.conversation_history.append({
                "role": "error",
                "content": f"Error during reflection: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            return False
