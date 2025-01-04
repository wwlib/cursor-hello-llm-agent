from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class MemoryManager:
    # Core prompts that don't change with domain
    QUERY_PROMPT = """You are a memory management system. Your task is to answer queries about the current memory state.

Current Memory State:
{memory_state}

User Query:
{query}

IMPORTANT: You must return ONLY a JSON object with this exact structure:
{{
    "response": "Your natural language response here as a single string"
}}

DO NOT include any other fields or structures in your response.
DO NOT return the memory state or any complex objects.
ONLY return the response object with a single string value."""

    UPDATE_PROMPT = """You are a memory management system. Your task is to incorporate new information into the memory state.

Current Memory State:
{memory_state}

New Information:
{new_data}

Requirements:
1. Preserve existing information unless explicitly contradicted
2. Add new entities and relationships as needed
3. Update existing entities and relationships if new information is provided
4. Maintain consistency with existing data

Return ONLY a valid JSON object with the same structure as the current memory state."""

    def __init__(self, llm_service, memory_file: str = "memory.json", domain_config: dict = None):
        """Initialize the MemoryManager with an LLM service and domain configuration.
        
        Args:
            llm_service: Service for LLM operations
            memory_file: Path to the JSON file for persistent storage
            domain_config: Dictionary containing domain-specific configuration:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
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
            "domain_instructions": {
                "entity_suggestions": [
                    "Consider organizing entities by type (e.g., characters, locations, items)",
                    "Include relevant attributes for each entity type",
                    "Use descriptive names and IDs"
                ],
                "relationship_suggestions": [
                    "Consider key interactions between entities",
                    "Use clear and consistent relationship types",
                    "Track important state changes"
                ]
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
        
        # Include domain-specific instructions if available
        domain_guidance = ""
        if self.domain_config and "domain_instructions" in self.domain_config:
            domain_guidance = "\nDomain-Specific Guidance:\n"
            if "entity_suggestions" in self.domain_config["domain_instructions"]:
                domain_guidance += "\nEntity Organization:\n- " + "\n- ".join(self.domain_config["domain_instructions"]["entity_suggestions"])
            if "relationship_suggestions" in self.domain_config["domain_instructions"]:
                domain_guidance += "\nRelationship Organization:\n- " + "\n- ".join(self.domain_config["domain_instructions"]["relationship_suggestions"])

        create_memory_prompt = f"""You are a memory management system. Your task is to analyze the provided information and create two distinct data structures:

1. structured_data: A catalog of entities (nouns) and their properties
2. knowledge_graph: A collection of relationships (verbs) between entities

Input Data:
{input_data}
{domain_guidance}

Requirements for structured_data:
- Store facts and properties about entities
- Organize entities in a way that makes sense for the domain
- Include all relevant attributes and metadata

Requirements for knowledge_graph:
- Store relationships between entities
- Use clear and consistent relationship types
- Capture important connections and dependencies

Return ONLY a valid JSON object with this structure:
{{
    "structured_data": {{
        // Your organization of entities and their properties
        "entities": []
    }},
    "knowledge_graph": {{
        // Your organization of relationships
        "relationships": []
    }}
}}"""

        try:
            print("Generating memory structure using LLM...")
            llm_response = self.llm.generate(prompt=create_memory_prompt, debug_generate_scope="init_memory")
            
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
                        json_str = json_match.group(0)
                        # Count opening and closing braces
                        open_count = json_str.count('{')
                        close_count = json_str.count('}')
                        # Add missing closing braces if needed
                        if open_count > close_count:
                            json_str += '}' * (open_count - close_count)
                        memory_data = json.loads(json_str)
                        print("Successfully extracted and fixed JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False
            
            # Validate required fields
            required_fields = ["structured_data", "knowledge_graph"]
            for field in required_fields:
                if field not in memory_data:
                    print(f"Missing required field '{field}' in memory data")
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
            return False

    def query_memory(self, query_context: str) -> dict:
        """Query memory with the given context and update memory with the response.

        Args:
            query_context: A JSON string containing the query context

        Returns:
            dict: The query response
        """
        print("\nProcessing memory query...")
        
        try:
            # Parse query context
            context = json.loads(query_context)
            user_message = context.get("user_message", "")
            
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
                messages_to_process = history  # Process all messages
                reflection_success = self._perform_reflection(messages_to_process)
                if reflection_success:
                    # Clear all processed messages
                    self.memory["conversation_history"] = []
                    print("Cleared all messages after successful reflection")

            # Generate response
            print("Generating response using LLM...")
            query_prompt = self.QUERY_PROMPT.format(
                memory_state=json.dumps(self.memory, indent=2),
                query=user_message
            )
            
            response = self.llm.generate(query_prompt)
            
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {str(e)}")
                error_response = {
                    "response": "Error processing query"
                }
                return error_response

            # Validate response structure
            if not isinstance(result, dict) or "response" not in result or not isinstance(result["response"], str):
                print("Invalid response structure - must have 'response' property with string value")
                error_response = {
                    "response": "Error: Invalid response structure from LLM"
                }
                return error_response

            # Add agent's response to conversation history
            if "response" in result:
                self.memory["conversation_history"].append({
                    "role": "assistant",
                    "content": result["response"],
                    "timestamp": datetime.now().isoformat()
                })
                print("Added agent response to history")

            # Save memory after update
            self.save_memory()
            
            return {
                "response": result.get("response", "")
            }

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            return {
                "response": f"Error processing query: {str(e)}"
            }

    def update_memory(self, update_context: str) -> bool:
        """Update memory with new information using LLM.
        
        Args:
            update_context: JSON string containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            print("\nUpdating memory...")
            context = json.loads(update_context)
            
            # Handle reflection operations
            if context.get("operation") == "reflect":
                print("\nProcessing reflection operation...")
                messages_to_process = context.get("messages", [])
                reflection_success = self._perform_reflection(messages_to_process)
                if reflection_success:
                    # Clear only the processed messages from history
                    remaining_messages = [msg for msg in self.memory.get("conversation_history", []) 
                                       if msg not in messages_to_process]
                    self.memory["conversation_history"] = remaining_messages
                    print(f"Cleared processed messages. Remaining: {len(remaining_messages)}")
                return reflection_success

            # Regular memory update
            update_prompt = self.UPDATE_PROMPT.format(
                memory_state=json.dumps(self.memory, indent=2),
                new_data=json.dumps(context, indent=2)
            )

            print("Generating memory update using LLM...")
            llm_response = self.llm.generate(update_prompt, debug_generate_scope="update_memory")
            
            try:
                updated_memory = json.loads(llm_response)
            except json.JSONDecodeError:
                print("Failed to parse LLM response as JSON")
                return False
            
            # Validate required fields
            if not all(field in updated_memory for field in ["structured_data", "knowledge_graph"]):
                print("Missing required fields in updated memory")
                return False
            
            # Preserve conversation history
            conversation_history = self.memory.get("conversation_history", [])
            
            # Update memory with validated data
            self.memory.update(updated_memory)
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Restore conversation history
            self.memory["conversation_history"] = conversation_history
            
            # Save the updated memory
            self.save_memory()
            print("Memory updated successfully")
            return True
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False

    def _extract_schema(self, data: dict) -> dict:
        """Extract schema from existing memory structure."""
        schema = {}
        
        if isinstance(data, dict):
            schema = {k: self._extract_schema(v) for k, v in data.items()}
        elif isinstance(data, list):
            if data:  # If list is not empty, use first item as example
                schema = [self._extract_schema(data[0])]
            else:
                schema = []
        else:
            # For primitive values, store their type
            schema = type(data).__name__
            
        return schema

    def _perform_reflection(self, messages_to_process: list) -> bool:
        """Internal method to perform reflection on a set of messages."""
        print(f"\nReflecting on {len(messages_to_process)} messages...")
        
        # Extract current schema
        current_schema = {
            "structured_data": self._extract_schema(self.memory.get("structured_data", {})),
            "knowledge_graph": self._extract_schema(self.memory.get("knowledge_graph", {}))
        }

        # Extract just the core memory structures
        core_memory = {
            "structured_data": self.memory.get("structured_data", {}),
            "knowledge_graph": self.memory.get("knowledge_graph", {})
        }
        
        reflection_prompt = """You are a memory management system. Your task is to analyze conversations and update the core memory structures with any new information discovered.

Current Memory State (core structures only):
{memory_state}

Recent Conversations to Process:
{messages_to_process}

IMPORTANT: Your task is to:
1. Analyze the conversations above for any new information about entities or relationships
2. Add this information to the appropriate core memory structure while preserving the exact schema:
{schema}

Example entity format must match:
{entity_example}

Example relationship format must match:
{relationship_example}

Rules:
1. PRESERVE all existing data in structured_data and knowledge_graph
2. ADD new information found in conversations while maintaining the schema
3. DO NOT change the structure or format of existing data
4. DO NOT remove or replace existing information unless explicitly contradicted
5. DO NOT include conversation_history or metadata in your response

IMPORTANT: Return ONLY a valid JSON object with structured_data and knowledge_graph.
The response must contain ALL existing entities and relationships PLUS any new ones discovered in conversations."""

        try:
            # Get example entity and relationship from current memory
            entity_example = next(iter(self.memory.get("structured_data", {}).get("entities", [])), None)
            relationship_example = next(iter(self.memory.get("knowledge_graph", {}).get("relationships", [])), None)
            
            # Format the reflection prompt
            prompt = reflection_prompt.format(
                memory_state=json.dumps(core_memory, indent=2),
                messages_to_process=json.dumps(messages_to_process, indent=2),
                schema=json.dumps(current_schema, indent=2),
                entity_example=json.dumps(entity_example, indent=2) if entity_example else "{}",
                relationship_example=json.dumps(relationship_example, indent=2) if relationship_example else "{}"
            )
            
            # Generate reflection update
            print("Generating reflection update using LLM...")
            llm_response = self.llm.generate(prompt, debug_generate_scope="reflect")
            
            try:
                # First try direct JSON parsing
                reflected_memory = json.loads(llm_response)
            except json.JSONDecodeError:
                # If that fails, try to find JSON-like structure
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Count opening and closing braces
                        open_count = json_str.count('{')
                        close_count = json_str.count('}')
                        # Add missing closing braces if needed
                        if open_count > close_count:
                            json_str += '}' * (open_count - close_count)
                        reflected_memory = json.loads(json_str)
                        print("Successfully extracted and fixed JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False
                
            # Validate required fields
            if not all(field in reflected_memory for field in ["structured_data", "knowledge_graph"]):
                print("Missing required fields in reflection update")
                return False
                
            # Preserve conversation history
            conversation_history = self.memory.get("conversation_history", [])
            
            # Update memory with reflection results
            self.memory.update(reflected_memory)
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Restore conversation history
            self.memory["conversation_history"] = conversation_history
            
            # Save the updated memory
            self.save_memory()
            print("Reflection completed successfully")
            return True
            
        except Exception as e:
            print(f"Error during reflection: {str(e)}")
            return False

    def get_memory_context(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
