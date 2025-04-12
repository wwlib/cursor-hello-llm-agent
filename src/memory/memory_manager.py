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
from .base_memory_manager import BaseMemoryManager

class MemoryManager(BaseMemoryManager):
    """LLM-driven memory manager implementation.
    
    Extends BaseMemoryManager to provide LLM-driven memory operations with domain-specific configuration.
    """

    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, llm_service = None):
        """Initialize the MemoryManager with an LLM service and domain configuration.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Dictionary containing domain-specific configuration:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
                         - prompts: Domain-specific prompt templates
            llm_service: Service for LLM operations (required for this implementation)
        """
        if llm_service is None:
            raise ValueError("llm_service is required for MemoryManager")
            
        super().__init__(memory_file, domain_config)
        print(f"\nInitializing MemoryManager with file: {memory_file}")
        self.llm = llm_service
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

    def create_initial_memory(self, input_data: str) -> bool:
        """Use LLM to structure initial input data into memory format.
        
        The LLM is free to choose the internal structure of static_memory and working_memory
        based on what makes sense for the domain. We only validate the top-level structure.
        """
        # Check if we have valid existing memory
        if self.memory and all(key in self.memory for key in ["original_data", "static_memory", "working_memory", "metadata", "conversation_history"]):
            print("Valid memory structure already exists, skipping initialization")
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
            
            # Print the prompt to debug format placeholders
            print(f"DEBUG - FORMATTED PROMPT (first 200 chars):\n{prompt[:200]}...")
            print(f"DEBUG - FORMATTED PROMPT (last 200 chars):\n{prompt[-200:]}...")
            
            llm_response = self.llm.generate(prompt)
            
            # Print the response to debug
            print(f"DEBUG - LLM RESPONSE (first 200 chars):\n{llm_response[:200]}...")
            print(f"DEBUG - LLM RESPONSE (last 200 chars):\n{llm_response[-200:]}...")
            
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

            # Validate knowledge_graph structure
            static_knowledge_graph = static_memory["knowledge_graph"]
            if "simple_facts" not in static_knowledge_graph or "relationships" not in static_knowledge_graph:
                print("knowledge_graph must contain simple_facts and relationships")
                return False

            if not isinstance(static_knowledge_graph["simple_facts"], list) or not isinstance(static_knowledge_graph["relationships"], list):
                print("simple_facts and relationships must be lists")
                return False

            # Validate simple_facts structure
            for fact in static_knowledge_graph["simple_facts"]:
                if not isinstance(fact, dict):
                    print("Each fact must be a dictionary")
                    return False
                required_fields = ["key", "value", "context"]
                if not all(field in fact for field in required_fields):
                    print(f"Fact missing required fields: {required_fields}")
                    return False

            # Validate relationship structure
            for relationship in static_knowledge_graph["relationships"]:
                if not isinstance(relationship, dict):
                    print("Each relationship must be a dictionary")
                    return False
                required_fields = ["subject", "predicate", "object", "context"]
                if not all(field in relationship for field in required_fields):
                    print(f"Relationship missing required fields: {required_fields}")
                    return False
            
            # Initialize complete memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "original_data": input_data,  # Store the original raw input data
                "static_memory": static_memory,
                "working_memory": {
                    "structured_data": {
                        "entities": []  # Empty list for entities
                    },
                    "knowledge_graph": {
                        "simple_facts": [],  # For natural language facts
                        "relationships": []  # For explicit subject-predicate-object relationships
                    }
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
            print(f"Full error: {repr(e)}")
            return False

    def query_memory(self, query_context: Dict[str, Any]) -> dict:
        """Query memory with the given context."""
        try:
            print("\nQuerying memory...")
            print(query_context)
            
            # Add user message to history
            user_message = query_context.get("user_message", "")
            if user_message:
                self.memory["conversation_history"].append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"Added user message to history: {user_message}")
            
            # Extract original data for the template
            original_data = self.memory.get("original_data", "")
            
            prompt = self.templates["query"].format(
                memory_state=json.dumps(self.memory, indent=2),
                query=user_message,
                original_data=original_data
            )
            
            # Get response from LLM
            print("Generating response using LLM...")
            llm_response = self.llm.generate(prompt)
            
            try:
                result = json.loads(llm_response)
            except json.JSONDecodeError:
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                        result = json.loads(json_str)
                        print("Successfully extracted and fixed JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False

            if not isinstance(result, dict) or "response" not in result:
                print("Invalid response structure - must have 'response' property")
                return {"response": "Error: Invalid response structure from LLM"}

            # Add assistant response to history with digest information
            self.memory["conversation_history"].append({
                "role": "assistant",
                "content": result["response"],
                "digest": result.get("digest", {}),  # Store the digest information
                "timestamp": datetime.now().isoformat()
            })
            print("Added assistant response to history")

            # Save to persist conversation history
            self.save_memory()
            
            return {"response": result["response"]}

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            return {"response": f"Error processing query: {str(e)}"}

    def update_memory(self, update_context: Dict[str, Any]) -> bool:
        """Update memory with new information using LLM.
        Only used for updating memory operations to minimize LLM calls.
        
        Args:
            update_context: Dictionary containing update context
            
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            print("\nUpdating memory...")
            
            # Only handle updating memory operations
            if update_context.get("operation") != "update":
                print("update_memory should only be used for updating memory operations")
                return False

            print("\nProcessing update memory operation...")            
            return self._perform_update_memory()
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False

    def _perform_update_memory(self) -> bool:
        """Internal method to perform update memory on a set of messages."""
        try:
            print("\nProcessing messages for memory update...")
                        
            # Generate prompt for memory update
            prompt = self.templates["update"].format(
                memory_state=json.dumps(self.memory, indent=2)
            )
            
            # Get response from LLM
            print("Generating memory update using LLM...")
            llm_response = self.llm.generate(prompt)
            
            try:
                result = json.loads(llm_response)
            except json.JSONDecodeError:
                import re
                print("Failed to parse direct JSON, attempting to extract JSON structure...")
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                        result = json.loads(json_str)
                        print("Successfully extracted and fixed JSON structure")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing extracted JSON structure: {str(e)}")
                        return False
                else:
                    print("Could not find JSON structure in LLM response")
                    return False

            if not isinstance(result, dict) or "working_memory" not in result:
                print("Invalid response structure - must have 'working_memory' property")
                return False

            # Extract and validate working memory
            working_memory = result["working_memory"]
            
            if not isinstance(working_memory, dict):
                print("working_memory must be a dictionary")
                return False

            if "structured_data" not in working_memory or "knowledge_graph" not in working_memory:
                print("working_memory must contain structured_data and knowledge_graph")
                return False

            # Validate structured_data
            structured_data = working_memory["structured_data"]
            if not isinstance(structured_data, dict):
                print("structured_data must be a dictionary")
                return False

            if "entities" not in structured_data:
                print("structured_data must contain entities")
                return False

            if not isinstance(structured_data["entities"], list):
                print("entities must be a list")
                return False

            # Validate knowledge_graph
            knowledge_graph = working_memory["knowledge_graph"]
            
            if not isinstance(knowledge_graph, dict):
                print("knowledge_graph must be a dictionary")
                return False

            if "simple_facts" not in knowledge_graph or "relationships" not in knowledge_graph:
                print("knowledge_graph must contain simple_facts and relationships")
                return False

            if not isinstance(knowledge_graph["simple_facts"], list) or not isinstance(knowledge_graph["relationships"], list):
                print("simple_facts and relationships must be lists")
                return False

            # Validate simple_facts structure
            for fact in knowledge_graph["simple_facts"]:
                if not isinstance(fact, dict):
                    print("Each fact must be a dictionary")
                    return False
                required_fields = ["key", "value", "context", "source"]
                if not all(field in fact for field in required_fields):
                    print(f"Fact missing required fields: {required_fields}")
                    return False

            # Validate relationship structure
            for relationship in knowledge_graph["relationships"]:
                if not isinstance(relationship, dict):
                    print("Each relationship must be a dictionary")
                    return False
                required_fields = ["subject", "predicate", "object", "context", "source"]
                if not all(field in relationship for field in required_fields):
                    print(f"Relationship missing required fields: {required_fields}")
                    return False

            # Update working memory
            self.memory["working_memory"] = working_memory
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Clear conversation history after successful update
            self.memory["conversation_history"] = []
            
            # Save the updated memory
            self.save_memory()
            print("Memory updated and saved successfully")
            return True
            
        except Exception as e:
            print(f"Error in _perform_update_memory: {str(e)}")
            return False

