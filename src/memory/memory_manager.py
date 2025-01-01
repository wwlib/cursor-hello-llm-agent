from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class MemoryManager:
    def __init__(self, llm_service, memory_file: str = "memory.json"):
        """Initialize the MemoryManager with an LLM service and optional memory file path.
        
        Args:
            llm_service: Service for LLM operations
            memory_file: Path to the JSON file for persistent storage
        """
        self.memory_file = memory_file
        self.llm = llm_service
        self.memory: Dict[str, Any] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        """Load memory from JSON file if it exists"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                self.memory = json.load(f)

    def save_memory(self) -> None:
        """Save current memory state to JSON file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)

    def create_initial_memory(self, input_data: str) -> bool:
        """Use LLM to structure initial input data into memory format.
        
        Args:
            input_data: Raw input data to be structured
            
        Returns:
            bool: True if memory was created successfully
        """
        create_memory_prompt = """
You are a memory management system. Your task is to analyze the provided information and create two organized data structures:

1. A structured_data JSON object to store key facts and details
2. A knowledge_graph JSON object to map relationships between entities

Input Data:
{INPUT_DATA}

Requirements:
- Structure the data in a way that will be useful for the specific domain
- Include all relevant information from the input
- Create meaningful relationships in the knowledge graph
- Use consistent naming and structure that can be extended in future updates
- Include metadata about data categories to help with future queries

Return only a valid JSON object with this structure:
{
    "structured_data": {
        // Your structured organization of the facts and details
    },
    "knowledge_graph": {
        // Your graph of relationships between entities
    },
    "metadata": {
        "categories": [],
        "timestamp": "",
        "version": "1.0"
    }
}"""

        try:
            # Get structured memory from LLM
            prompt = create_memory_prompt.replace("{INPUT_DATA}", input_data)
            llm_response = self.llm.generate(prompt)
            memory_data = json.loads(llm_response)
            
            # Add system metadata
            memory_data["metadata"]["created_at"] = datetime.now().isoformat()
            memory_data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.memory = memory_data
            self.save_memory()
            return True
        except Exception as e:
            print(f"Error creating memory structure: {str(e)}")
            return False

    def query_memory(self, query_context: str) -> Dict[str, Any]:
        """Query the memory using LLM to find relevant information and generate response.
        
        Args:
            query_context: JSON string containing query context (phase, history, message)
            
        Returns:
            Dict containing the response, new information, and suggested phase
        """
        try:
            context = json.loads(query_context)
            
            query_prompt = f"""
Context:
{json.dumps(self.memory, indent=2)}

Current Phase: {context.get('current_phase', 'UNKNOWN')}
Previous Messages: {json.dumps(context.get('recent_messages', []), indent=2)}

User Message: {context.get('user_message', '')}

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
    "suggested_phase": "current or next phase name",
    "confidence": 0.0 to 1.0
}}"""

            llm_response = self.llm.generate(query_prompt)
            response_data = json.loads(llm_response)
            
            # If there's new information, update memory
            if response_data.get("new_information"):
                self.update_memory(json.dumps(response_data["new_information"]))
            
            return response_data
            
        except Exception as e:
            print(f"Error querying memory: {str(e)}")
            return {
                "response": "Error processing query",
                "new_information": {},
                "suggested_phase": None,
                "confidence": 0.0
            }

    def update_memory(self, update_context: str) -> bool:
        """Update memory with new information using LLM.
        
        Args:
            update_context: JSON string containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            context = json.loads(update_context)
            
            # Handle different types of updates
            if context.get("operation") == "reflect":
                update_prompt = f"""
Current Memory State:
{json.dumps(self.memory, indent=2)}

Recent Interactions:
{json.dumps(context.get('recent_history', []), indent=2)}

Analyze the current memory state and recent interactions to:
1. Identify important patterns or relationships
2. Suggest memory structure optimizations
3. Highlight key information for future reference

Return analysis and suggested updates in JSON format suitable for memory update."""

            else:  # Standard update or learning
                update_prompt = f"""
Current Memory State:
{json.dumps(self.memory, indent=2)}

Phase: {context.get('phase', 'UNKNOWN')}
New Information: {context.get('information', '{}')}
Recent History: {json.dumps(context.get('recent_history', []), indent=2)}

Analyze this information and return a JSON object containing:
1. Updated structured data
2. New or modified relationships for the knowledge graph
3. Any necessary changes to existing memory

Return in JSON format suitable for memory update."""

            llm_response = self.llm.generate(update_prompt)
            updated_memory = json.loads(llm_response)
            
            # Update metadata
            updated_memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.memory = updated_memory
            self.save_memory()
            return True
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False

    def get_memory_context(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
