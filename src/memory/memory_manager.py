from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class MemoryManager:
    def __init__(self, llm_service, memory_file: str = "memory.json", domain_config: dict = None):
        """Initialize the MemoryManager with an LLM service and domain configuration.
        
        Args:
            llm_service: Service for LLM operations
            memory_file: Path to the JSON file for persistent storage
            domain_config: Dictionary containing domain-specific configuration:
                         - schema: The structure for domain-specific data
                         - prompts: Domain-specific prompt templates
        """
        print(f"\nInitializing MemoryManager with file: {memory_file}")
        self.memory_file = memory_file
        self.llm = llm_service
        self.domain_config = domain_config or self._get_default_config()
        self.memory: Dict[str, Any] = {}
        self._load_memory()

    def _get_default_config(self) -> dict:
        """Get the default domain configuration if none provided."""
        return {
            "schema": {
                "structured_data": {
                    "entities": [],     # Generic entities
                    "locations": [],    # Generic locations
                    "activities": []    # Generic activities
                },
                "knowledge_graph": {
                    "entity_relationships": {},
                    "location_relationships": {},
                    "activity_relationships": {}
                }
            },
            "prompts": {
                "create_memory": """You are a helpful assistant that communicates using JSON. 
                Create a structured memory for the following domain information:
                {input_data}
                
                Use this schema:
                {schema}
                
                Return ONLY a valid JSON object with no additional text.""",
                
                "query": """You are a helpful assistant that communicates using JSON.
                Process this query using the current memory state and schema:
                
                Memory State:
                {memory_state}
                
                Schema:
                {schema}
                
                User Query:
                {query}
                
                Return ONLY a valid JSON object with no additional text.""",
                
                "reflect": """You are a helpful assistant that communicates using JSON.
                Analyze these recent interactions and update the knowledge state:
                
                Current State:
                {memory_state}
                
                Recent Messages:
                {messages}
                
                Schema:
                {schema}
                
                Return ONLY a valid JSON object with no additional text."""
            }
        }

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

    def create_initial_memory(self, input_data: str) -> bool:
        """Use LLM to structure initial input data into memory format.
        Only creates new memory if no existing memory is loaded.
        
        Args:
            input_data: Raw input data to be structured
            
        Returns:
            bool: True if memory was created successfully or already exists
        """
        # Skip if memory already exists
        if self.memory:
            print("Memory already exists, skipping initialization")
            return True

        print("\nCreating initial memory structure...")
        create_memory_prompt = self.domain_config["prompts"]["create_memory"].format(
            input_data=input_data,
            schema=json.dumps(self.domain_config["schema"], indent=2)
        )

        try:
            print("Generating memory structure using LLM...")
            # Get structured memory from LLM
            prompt = create_memory_prompt
            llm_response = self.llm.generate(prompt, debug_generate_scope="init_memory")
            
            # Try to extract JSON if there's any extra text
            try:
                # First try direct JSON parsing
                memory_data = json.loads(llm_response)
            except json.JSONDecodeError:
                # If that fails, try to find JSON-like structure
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        memory_data = json.loads(json_match.group(0))
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        print(f"Extracted structure: {json_match.group(0)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    print(f"Raw response: {llm_response}")
                    return False
            
            # Validate required fields
            required_fields = ["structured_data", "knowledge_graph"]
            for field in required_fields:
                if field not in memory_data:
                    print(f"Missing required field '{field}' in memory data")
                    print(f"Received data: {json.dumps(memory_data, indent=2)}")
                    return False
            
            # Initialize metadata and conversation history
            now = datetime.now().isoformat()
            memory_data["metadata"] = {
                "created_at": now,
                "last_updated": now,
                "version": "1.0"
            }
            memory_data["conversation_history"] = []
            
            self.memory = memory_data
            self.save_memory()
            print("Initial memory created and saved successfully")
            return True
            
        except Exception as e:
            print(f"Error creating memory structure: {str(e)}")
            print(f"Full error details: {type(e).__name__}: {str(e)}")
            return False

    def _create_query_prompt(self, context: dict) -> str:
        """Create a prompt for querying memory.

        Args:
            context: The query context containing user message and current phase

        Returns:
            str: The formatted prompt for the LLM
        """
        memory_state = json.dumps(self.memory, indent=2)
        user_message = context.get('user_message', '')
        current_phase = context.get('current_phase', 'INTERACTION')
        
        example_response = '''{
    "response": "Your natural response to the user's question about the world",
    "suggested_phase": "INTERACTION",
    "confidence": 0.9,
    "memory_update": {
        "structured_data": {
            "world": {
                "geography": [],
                "settlements": []
            },
            "npcs": [],
            "events": []
        },
        "knowledge_graph": {
            "npcs": {},
            "settlements": {},
            "events": {}
        }
    }
}'''

        prompt = f"""You are a helpful assistant that communicates using JSON. Your response must be ONLY a valid JSON object with no preamble, explanation, or additional text.

Current Memory State:
{memory_state}

User Message: "{user_message}"
Current Phase: {current_phase}

Your task is to:
1. Generate a natural response to the user's message based on the memory state
2. Suggest the next conversation phase (use "INTERACTION" unless there's a clear reason for another phase)
3. Update the memory with any new information from this interaction

IMPORTANT: Return ONLY a JSON object with this exact structure - no other text or explanation:

{example_response}"""

        return prompt

    def _merge_memory_update(self, memory_update: dict) -> None:
        """Merge memory update with existing memory, preserving existing data.
        
        Args:
            memory_update: New memory data to merge
        """
        if "structured_data" in memory_update:
            # Merge each section of structured data, preserving existing data
            for key in memory_update["structured_data"]:
                if key not in self.memory["structured_data"]:
                    self.memory["structured_data"][key] = memory_update["structured_data"][key]
                elif isinstance(self.memory["structured_data"][key], list):
                    # For lists, append new items avoiding duplicates
                    existing_items = self.memory["structured_data"][key]
                    new_items = memory_update["structured_data"][key]
                    for item in new_items:
                        if item not in existing_items:
                            existing_items.append(item)
                elif isinstance(self.memory["structured_data"][key], dict):
                    # For dictionaries, recursively merge
                    self.memory["structured_data"][key].update(memory_update["structured_data"][key])

        if "knowledge_graph" in memory_update:
            # Merge knowledge graph data, preserving existing relationships
            for key in memory_update["knowledge_graph"]:
                if key not in self.memory["knowledge_graph"]:
                    self.memory["knowledge_graph"][key] = memory_update["knowledge_graph"][key]
                elif isinstance(self.memory["knowledge_graph"][key], dict):
                    # For dictionaries, recursively merge
                    self.memory["knowledge_graph"][key].update(memory_update["knowledge_graph"][key])

    def query_memory(self, query_context: str) -> dict:
        """Query memory with the given context and update memory with the response.

        Args:
            query_context: A JSON string containing the query context

        Returns:
            dict: The query response including suggested phase and confidence
        """
        print("\nProcessing memory query...")
        
        try:
            # Parse query context
            context = json.loads(query_context)
            current_phase = context.get("current_phase", "INTERACTION")
            user_message = context.get("user_message", "")
            
            print(f"Current phase: {current_phase}")
            
            # Initialize conversation history if not present
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
            
            # Add user message to conversation history
            if user_message:
                self.memory["conversation_history"].append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"Added user message to history: {user_message}")

            # Check if reflection is needed (10 messages threshold)
            history = self.memory.get("conversation_history", [])
            if len(history) >= 10:
                print("\nTriggering reflection...")
                messages_to_process = history[-10:]  # Get the last 10 messages
                reflection_success = self._perform_reflection(messages_to_process)
                if reflection_success:
                    # Clear the processed messages
                    self.memory["conversation_history"] = history[:-10]
                    print("Cleared processed messages after successful reflection")

            # Generate response and memory update
            print("Generating response and memory update using LLM...")
            prompt = self._create_query_prompt(context)
            response = self.llm.generate(prompt)
            
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {str(e)}")
                error_response = {
                    "response": "Error processing query",
                    "suggested_phase": "INTERACTION",
                    "confidence": 0.0
                }
                # Add error message to conversation history
                self.memory["conversation_history"].append({
                    "role": "system",
                    "content": f"Error processing query: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                return error_response

            # Add agent's response to conversation history
            if "response" in result:
                self.memory["conversation_history"].append({
                    "role": "assistant",
                    "content": result["response"],
                    "timestamp": datetime.now().isoformat()
                })
                print("Added agent response to history")

            # Update memory with new information
            if "memory_update" in result:
                self._merge_memory_update(result["memory_update"])
                print("Memory updated with new information")
                # Add system message about memory update
                self.memory["conversation_history"].append({
                    "role": "system",
                    "content": "Memory updated with new information",
                    "timestamp": datetime.now().isoformat()
                })

            # Save memory after update
            self.save_memory()
            
            return {
                "response": result.get("response", ""),
                "suggested_phase": result.get("suggested_phase", "INTERACTION"),
                "confidence": result.get("confidence", 0.0)
            }

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            error_response = {
                "response": "Error processing query",
                "suggested_phase": "INTERACTION",
                "confidence": 0.0
            }
            # Add error message to conversation history
            self.memory["conversation_history"].append({
                "role": "system",
                "content": f"Error in query_memory: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            return error_response

    def update_memory(self, update_context: str) -> bool:
        """Update memory with new information using LLM.
        Note: This method is now only used for reflection operations.
        Regular updates are handled directly in query_memory.
        
        Args:
            update_context: JSON string containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            print("\nUpdating memory...")
            context = json.loads(update_context)
            
            # Store existing conversation history and metadata
            existing_history = self.memory.get("conversation_history", [])
            
            # Add new messages if any
            new_message = context.get('message')
            if new_message:
                # Skip updates for system messages that don't contain meaningful information
                if new_message.get('role') == 'system' and new_message.get('content') in [
                    "Learned new information successfully",
                    "Memory updated successfully"
                ]:
                    print("Skipping update for system status message")
                    existing_history.append(new_message)
                    self.memory["conversation_history"] = existing_history
                    return True

                # Only handle reflection operations
                if context.get("operation") == "reflect":
                    print("\nProcessing reflection operation...")
                    recent_messages = existing_history[-10:] if len(existing_history) > 10 else existing_history
                    reflection_success = self._perform_reflection(recent_messages)
                    if reflection_success:
                        # Clear the processed messages
                        existing_history = existing_history[:-len(recent_messages)]
                        print(f"Cleared {len(recent_messages)} messages. Remaining: {len(existing_history)}")
                    return reflection_success
                
                print("Regular updates are now handled in query_memory")
                return True
            
            return True
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            if 'llm_response' in locals():
                print(f"Raw LLM response:\n{llm_response}")
            return False

    def _perform_reflection(self, messages_to_process: list) -> bool:
        """Internal method to perform reflection on a set of messages.
        
        Args:
            messages_to_process: List of messages to reflect on
            
        Returns:
            bool: True if reflection was successful
        """
        print(f"\nReflecting on {len(messages_to_process)} messages...")
        
        reflection_prompt = f"""You are a helpful assistant that communicates using JSON. Your response must be ONLY a valid JSON object with no preamble, explanation, or additional text.

Current Memory State (for context):
{json.dumps(self.memory, indent=2)}

Recent Messages to Process:
{json.dumps(messages_to_process, indent=2)}

Your task is to consolidate and update the memory state:
1. PRESERVE ALL existing information unless explicitly contradicted
2. EXTRACT important facts and information from recent messages
3. UPDATE existing information only if there's clear new information
4. MAINTAIN all important relationships between entities
5. MERGE redundant information while preserving details

RESPOND WITH ONLY THIS JSON STRUCTURE - NO OTHER TEXT:
{{
    "memory_update": {{
        "structured_data": {{
            "world": {{
                "geography": [
                    // Preserve ALL existing geography entries and add new ones
                    // Each entry should have: name, type
                ],
                "settlements": [
                    // Preserve ALL existing settlements and add new ones
                    // Each entry should have: name, location, type
                ]
            }},
            "npcs": [
                // Preserve ALL existing NPCs and add new ones
                // Each entry should have: name, title/role/specialty
            ],
            "events": [
                // Preserve ALL existing events and add new ones
                // Each entry should have: event description and status
            ]
        }},
        "knowledge_graph": {{
            "npcs": {{
                // Preserve ALL existing NPC relationships
                // Add new relationships only for new information
            }},
            "settlements": {{
                // Preserve ALL existing settlement relationships
                // Add new relationships only for new information
            }},
            "events": {{
                // Preserve ALL existing event relationships
                // Add new relationships only for new information
            }}
        }}
    }}
}}"""

        try:
            print("Generating reflection updates using LLM...")
            llm_response = self.llm.generate(reflection_prompt, debug_generate_scope="reflect")
            
            # Try to extract JSON if there's any extra text
            try:
                llm_updates = json.loads(llm_response)
            except json.JSONDecodeError:
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                print(f"Raw LLM response:\n{llm_response}")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        llm_updates = json.loads(json_match.group(0))
                        print("Successfully extracted JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False
            
            # Handle case where memory_update is at top level
            memory_update = llm_updates.get("memory_update", llm_updates)
            
            # Validate required fields
            if "structured_data" not in memory_update or "knowledge_graph" not in memory_update:
                print("Error: Missing required fields in memory update")
                print(f"Received update: {json.dumps(memory_update, indent=2)}")
                return False
            
            # Update memory with validated data
            self.memory["structured_data"] = memory_update["structured_data"]
            self.memory["knowledge_graph"] = memory_update["knowledge_graph"]
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Save the updated memory
            self.save_memory()
            print("Reflection completed and memory updated successfully")
            return True
            
        except Exception as e:
            print(f"Error during reflection: {str(e)}")
            if 'llm_response' in locals():
                print(f"Raw LLM response:\n{llm_response}")
            return False

    def get_memory_context(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
