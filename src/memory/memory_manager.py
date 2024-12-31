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
            bool: True if memory was created successfully, False otherwise
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
}

Important: Return ONLY the JSON object, with no additional explanation or text."""

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
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error creating memory structure: {str(e)}")
            return False

    def query_memory(self, query: str) -> Dict[str, Any]:
        """Query the memory using LLM to find relevant information.
        
        Args:
            query: The query string to search memory with
            
        Returns:
            Dict containing the query response
        """
        query_prompt = f"""
Given this memory context: {json.dumps(self.memory)}
And this query: {query}
Provide a response using the stored information.

Return your response as a JSON object with this structure:
{{
    "response": "Your detailed response here",
    "relevant_data": {{
        // The specific data points used from memory
    }},
    "confidence": 0.0 to 1.0
}}"""

        try:
            llm_response = self.llm.generate(query_prompt)
            return json.loads(llm_response)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error querying memory: {str(e)}")
            return {
                "response": "Error processing query",
                "relevant_data": {},
                "confidence": 0.0
            }

    def update_memory(self, new_data: str) -> bool:
        """Update memory with new information using LLM.
        
        Args:
            new_data: New information to incorporate into memory
            
        Returns:
            bool: True if memory was updated successfully, False otherwise
        """
        update_prompt = f"""
Given this memory context: {json.dumps(self.memory)}
And this new information: {new_data}
Return updated JSON structures that incorporate the new information.

Use the same structure as the input memory. Preserve existing information unless it conflicts with new data."""

        try:
            llm_response = self.llm.generate(update_prompt)
            updated_memory = json.loads(llm_response)
            
            # Update metadata
            updated_memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.memory = updated_memory
            self.save_memory()
            return True
        except (json.JSONDecodeError, Exception) as e:
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
