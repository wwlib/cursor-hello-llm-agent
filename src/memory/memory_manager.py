"""Memory Manager for Agent System

Design Principles:
1. Flexible Schema Design
   - Only the top-level structure (static_memory, working_memory, metadata, conversation_history) is fixed
   - The internal structure of static_memory and working_memory should be determined by the LLM based on the domain
   - Domain-specific schemas are provided as suggestions, not requirements
   
2. Domain-Driven Design
   - Domain-specific guidance is provided through domain_config
   - This includes both prompt instructions and schema suggestions
   - The LLM should use these as guidance to create an appropriate structure for the domain
   
3. Memory Organization
   - static_memory: Contains foundational, unchanging information about the domain
   - working_memory: Contains dynamic information learned during interactions
   - Both sections' internal structure is flexible and domain-dependent
   
4. Memory Update Process
   - Periodically analyzes conversation history to update working_memory
   - Uses domain-specific guidance to determine what information to extract
   - Updates working_memory structure based on the domain's needs

Usage:
    memory_manager = MemoryManager(
        llm_service=llm_service,
        memory_file="memory.json",
        domain_config={
            "domain_specific_prompt_instructions": {
                "create_memory": "Domain-specific guidance for memory creation",
                "query": "Domain-specific guidance for queries",
                "update": "Domain-specific guidance for updating memory"
            },
            "domain_specific_schema_suggestions": {
                // Flexible schema suggestions for the domain
            }
        }
    )
"""

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
        self._load_templates()

    def _get_default_config(self) -> dict:
        """Get the default domain configuration if none provided."""
        return {
            "domain_specific_prompt_instructions:": {
                "create_memory": "",
                "query": "",
                "update": ""
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
        
        The LLM is free to choose the internal structure of static_memory and working_memory
        based on what makes sense for the domain. We only validate the top-level structure.
        """
        if self.memory:
            print("Memory already exists, skipping initialization")
            return True

        print("\nCreating initial memory structure...")
    
        # Include domain-specific instructions if available
        domain_guidance = ""
        if self.domain_config and "domain_specific_prompt_instructions" in self.domain_config:
            domain_guidance = "\nDomain-Specific Guidance:\n"
            create_memory_instructions = self.domain_config["domain_specific_prompt_instructions"]["create_memory"]
            domain_guidance += create_memory_instructions

        if self.domain_config and "domain_specific_schema_suggestions" in self.domain_config:
            domain_guidance += "\n\nDomain-Specific Schema Suggestions:\n"
            schema_suggestions = self.domain_config["domain_specific_schema_suggestions"]
            domain_guidance += json.dumps(schema_suggestions, indent=2)
            
        try:
            print("Generating memory structure using LLM...")
            prompt = self.templates["create"].format(
                input_data=input_data,
                domain_guidance=domain_guidance
            )
            llm_response = self.llm.generate(prompt)
            
            try:
                memory_data = json.loads(llm_response)
            except json.JSONDecodeError:
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                        memory_data = json.loads(json_str)
                        print("Successfully extracted and fixed JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False

            # Validate only the top-level structure
            if "static_memory" not in memory_data:
                print("Missing static_memory in LLM response")
                return False
                
            static_memory = memory_data["static_memory"]
            if not isinstance(static_memory, dict):
                print("static_memory must be a dictionary")
                return False
                
            if "structured_data" not in static_memory or "knowledge_graph" not in static_memory:
                print("static_memory must contain structured_data and knowledge_graph")
                return False
                
            if not isinstance(static_memory["structured_data"], dict) or not isinstance(static_memory["knowledge_graph"], dict):
                print("structured_data and knowledge_graph must be dictionaries")
                return False
            
            # Initialize complete memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "static_memory": static_memory,
                "working_memory": {
                    "structured_data": {},  # Empty but matching structure will be filled by LLM
                    "knowledge_graph": {}   # Empty but matching structure will be filled by LLM
                },
                "metadata": {
                    "created_at": now,
                    "last_updated": now,
                    "version": "1.0"
                },
                "conversation_history": []
            }
            
            self.save_memory()
            print("Initial memory created and saved successfully")
            return True
            
        except Exception as e:
            print(f"Error creating memory structure: {str(e)}")
            return False

    def query_memory(self, query_context: str) -> dict:
        """Query memory with the given context."""
        print("\nProcessing memory query...")
        
        try:
            context = json.loads(query_context)
            user_message = context.get("user_message", "")
            
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
            
            # Add user message to history
            if user_message:
                self.memory["conversation_history"].append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"Added user message to history: {user_message}")

            # Check if we need updating memory
            history = self.memory.get("conversation_history", [])
            if len(history) >= 3:  # Trigger updating memory after 3 messages
                print("\nTriggering updating memory...")
                update_memory_success = self._perform_update_memory(history)
                if update_memory_success:
                    # Clear only if updating memory was successful
                    self.memory["conversation_history"] = []
                    print("Cleared conversation history after successful updating memory")

            # Generate response using LLM
            print("Generating response using LLM...")
            prompt = self.templates["query"].format(
                memory_state=json.dumps(self.memory, indent=2),
                query=user_message
            )
            
            response = self.llm.generate(prompt)
            
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {str(e)}")
                return {"response": "Error processing query"}

            if not isinstance(result, dict) or "response" not in result:
                print("Invalid response structure - must have 'response' property")
                return {"response": "Error: Invalid response structure from LLM"}

            # Add assistant response to history
            self.memory["conversation_history"].append({
                "role": "assistant",
                "content": result["response"],
                "timestamp": datetime.now().isoformat()
            })
            print("Added assistant response to history")

            # Save to persist conversation history
            self.save_memory()
            
            return {"response": result["response"]}

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            return {"response": f"Error processing query: {str(e)}"}

    def update_memory(self, update_context: str) -> bool:
        """Update memory with new information using LLM.
        Only used for updating memory operations to minimize LLM calls.
        
        Args:
            update_context: JSON string containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            print("\nUpdating memory...")
            context = json.loads(update_context)
            
            # Only handle updating memory operations
            if context.get("operation") != "update":
                print("update_memory should only be used for updating memory operations")
                return False

            print("\nProcessing update memory operation...")
            messages_to_process = context.get("messages", [])
            return self._perform_update_memory(messages_to_process)
            
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

    def _perform_update_memory(self, messages_to_process: list) -> bool:
        """Internal method to perform update memory on a set of messages."""
        if not messages_to_process:
            print("No messages to update with")
            return False
            
        print(f"\nUpdating memory with {len(messages_to_process)} messages...")
        
        try:
            # Get examples from current memory if available
            entity_example = next(iter(self.memory.get("static_memory", {}).get("structured_data", {}).get("entities", [])), {})
            relationship_example = next(iter(self.memory.get("static_memory", {}).get("knowledge_graph", {}).get("relationships", [])), {})
            
            # Prepare updating memory prompt
            prompt = self.templates["update"].format(
                memory_state=json.dumps(self.memory, indent=2),
                messages_to_process=json.dumps(messages_to_process, indent=2),
                entity_example=json.dumps(entity_example, indent=2),
                relationship_example=json.dumps(relationship_example, indent=2)
            )
            
            print("Generating updated memory using LLM...")
            llm_response = self.llm.generate(prompt)
            
            try:
                # First try direct JSON parsing
                updated_memory = json.loads(llm_response)
            except json.JSONDecodeError:
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                # Try to find JSON structure in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if not json_match:
                    print("Could not find JSON structure in LLM response")
                    return False
                    
                try:
                    # Clean up and parse the extracted JSON
                    json_str = json_match.group(0)
                    # Remove any markdown code block markers
                    json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                    updated_memory = json.loads(json_str)
                    print("Successfully extracted and parsed JSON structure")
                except json.JSONDecodeError as e:
                    print(f"Error parsing extracted JSON structure: {str(e)}")
                    return False
            
            # Validate the updated memory structure
            if "working_memory" not in updated_memory:
                print("Missing working_memory in update memory response")
                return False
                
            working_memory = updated_memory["working_memory"]
            if not all(field in working_memory for field in ["structured_data", "knowledge_graph"]):
                print("Missing required fields in working_memory")
                return False
                
            # Update only the working memory section
            self.memory["working_memory"] = working_memory
            
            # Update metadata timestamp
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Save the updated memory
            self.save_memory()
            print("Memory updated successfully")
            return True
            
        except Exception as e:
            print(f"Error during update memory: {str(e)}")
            return False

    def get_memory_context(self) -> Dict[str, Any]:
        """Return the entire memory state"""
        return self.memory

    def clear_memory(self) -> None:
        """Clear all stored memory"""
        self.memory = {}
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)

    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = {}
        
        template_files = {
            "create": "create_memory.prompt",
            "query": "query_memory.prompt",
            "update": "update_memory.prompt"
        }
        
        for key, filename in template_files.items():
            path = os.path.join(template_dir, filename)
            try:
                with open(path, 'r') as f:
                    self.templates[key] = f.read().strip()
                print(f"Loaded template: {filename}")
            except Exception as e:
                print(f"Error loading template {filename}: {str(e)}")
                # Raise an exception if the template cannot be loaded
                raise Exception(f"Failed to load template: {filename}")
