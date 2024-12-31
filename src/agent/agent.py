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
            llm_service: Service for LLM operations
            memory_manager: Service for memory management
        """
        self.llm = llm_service
        self.memory = memory_manager
        self.current_phase = AgentPhase.INITIALIZATION
        self.conversation_history: List[Dict[str, str]] = []

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response.
        
        Args:
            message: The user's input message
            
        Returns:
            str: The agent's response
        """
        # Add message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # Get memory context
        memory_context = self.memory.get_memory_context()

        # Create response prompt
        response_prompt = f"""
Context:
{json.dumps(memory_context, indent=2)}

Current Phase: {self.current_phase.name}
Previous Messages: {json.dumps(self.conversation_history[-5:], indent=2)}

User Message: {message}

Generate a response that:
1. Uses relevant information from memory
2. Maintains consistency with previous interactions
3. Advances the current phase appropriately
4. Identifies any new information to be stored

Response should be in-character and appropriate for the current phase.

Return your response in JSON format:
{{
    "response": "Your response here",
    "new_information": {{
        // Any new information to be stored
    }},
    "suggested_phase": "current or next phase name"
}}
"""

        # Generate response using LLM
        try:
            llm_response = self.llm.generate(response_prompt)
            response_data = json.loads(llm_response)

            # Update memory if there's new information
            if response_data.get("new_information"):
                self.memory.update_memory(json.dumps(response_data["new_information"]))

            # Update phase if suggested
            suggested_phase = response_data.get("suggested_phase")
            if suggested_phase and hasattr(AgentPhase, suggested_phase):
                self.current_phase = getattr(AgentPhase, suggested_phase)

            # Add response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_data["response"],
                "timestamp": datetime.now().isoformat()
            })

            return response_data["response"]

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

            # Create learning prompt
            learn_prompt = f"""
Current Memory State:
{json.dumps(self.memory.get_memory_context(), indent=2)}

New Information to Learn:
{information}

Analyze this information and return a JSON object containing:
1. Structured data to be added to memory
2. Any new relationships for the knowledge graph
3. Suggested updates to existing memory

Return in JSON format suitable for memory update.
"""

            # Process with LLM
            llm_response = self.llm.generate(learn_prompt)
            processed_data = json.loads(llm_response)

            # Update memory
            success = self.memory.update_memory(json.dumps(processed_data))

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

    async def reflect(self) -> None:
        """Periodic reflection to optimize memory."""
        try:
            # Create reflection prompt
            reflection_prompt = f"""
Current Memory State:
{json.dumps(self.memory.get_memory_context(), indent=2)}

Recent Interactions:
{json.dumps(self.conversation_history[-10:], indent=2)}

Analyze the current memory state and recent interactions to:
1. Identify important patterns or relationships
2. Suggest memory structure optimizations
3. Highlight key information for future reference

Return analysis and suggested updates in JSON format.
"""

            # Process with LLM
            llm_response = self.llm.generate(reflection_prompt)
            reflection_data = json.loads(llm_response)

            # Update memory with reflection insights
            self.memory.update_memory(json.dumps(reflection_data))

            # Add reflection to history
            self.conversation_history.append({
                "role": "system",
                "content": "Completed memory reflection and optimization",
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            self.conversation_history.append({
                "role": "error",
                "content": f"Error during reflection: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history.
        
        Returns:
            List[Dict[str, str]]: List of conversation messages
        """
        return self.conversation_history

    def get_current_phase(self) -> AgentPhase:
        """Get the current phase of the agent.
        
        Returns:
            AgentPhase: Current phase enum value
        """
        return self.current_phase
