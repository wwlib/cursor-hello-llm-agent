"""Memory Manager for Agent System

Design Principles:
1. Flexible Memory Design
   - Maintains conversation history with importance-rated segments
   - Uses these rated segments for memory compression over time
   
2. Domain-Driven Design
   - Domain-specific guidance is provided through domain_config
   - The LLM should use these as guidance to remember important information
   
3. Memory Organization
   - static_memory: Contains foundational, unchanging information about the domain
   - conversation_history: Contains full conversation with important segments rated
   - context: Contains compressed important information organized by topic
   
4. Memory Update Process
   - Periodically compresses conversation history to retain only important segments
   - Organizes important information by topics for better retrieval
   - Balances completeness with efficiency

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

from typing import Any, Dict, Optional, List
import json
import os
import re
import uuid
from datetime import datetime
from .base_memory_manager import BaseMemoryManager
from .digest_generator import DigestGenerator

class MemoryManager(BaseMemoryManager):
    """LLM-driven memory manager implementation.
    
    Extends BaseMemoryManager to provide LLM-driven memory operations with domain-specific configuration.
    """

    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, 
                 llm_service = None, memory_guid: str = None, max_recent_conversations: int = 10, 
                 importance_threshold: int = 3):
        """Initialize the MemoryManager with an LLM service and domain configuration.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Dictionary containing domain-specific configuration:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
                         - prompts: Domain-specific prompt templates
            llm_service: Service for LLM operations (required for this implementation)
            memory_guid: Optional GUID to identify this memory instance. If not provided, 
                       a new one will be generated or loaded from existing file.
            max_recent_conversations: Maximum number of recent conversations to keep before compression
            importance_threshold: Threshold for segment importance (1-5 scale) to keep during compression
        """
        if llm_service is None:
            raise ValueError("llm_service is required for MemoryManager")
            
        # Pass memory_guid to the parent constructor
        super().__init__(memory_file, domain_config, memory_guid)
        print(f"\nInitializing MemoryManager with file: {memory_file}")
        self.llm = llm_service
        self._load_templates()
        
        # Initialize DigestGenerator
        self.digest_generator = DigestGenerator(llm_service)
        print("Initialized DigestGenerator")
        
        # Ensure memory has a GUID
        self._ensure_memory_guid()
        
        # Configurable memory parameters
        self.max_recent_conversations = max_recent_conversations
        self.importance_threshold = importance_threshold
        print(f"Memory configuration: max_recent_conversations={max_recent_conversations}, importance_threshold={importance_threshold}")

    def _ensure_memory_guid(self):
        """Ensure that the memory has a GUID, prioritizing the provided GUID if available."""
        # If memory doesn't exist yet, we'll handle this when creating memory
        if not self.memory:
            # Make sure we have a GUID, generating one if needed
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                print(f"Generated new GUID: {self.memory_guid} for memory file that will be created")
            return
            
        # Priority order for GUID:
        # 1. GUID provided at initialization (self.memory_guid from constructor)
        # 2. GUID in existing memory file (self.memory["guid"])
        # 3. Generate a new GUID if neither exists
        
        # If we already have a GUID from initialization, use it
        if self.memory_guid:
            # Force the memory to use our provided GUID, overriding any existing GUID
            if "guid" in self.memory and self.memory["guid"] != self.memory_guid:
                print(f"Replacing existing memory GUID: {self.memory['guid']} with provided GUID: {self.memory_guid}")
            
            # Set the GUID in memory
            self.memory["guid"] = self.memory_guid
            print(f"Using provided GUID for memory: {self.memory_guid}")
            # self.save_memory()
        # If no GUID was provided but one exists in memory, use that
        elif "guid" in self.memory:
            self.memory_guid = self.memory["guid"]
            print(f"Using existing memory GUID: {self.memory_guid}")
        # If no GUID was provided and none exists in memory, generate a new one
        else:
            self.memory_guid = str(uuid.uuid4())
            self.memory["guid"] = self.memory_guid
            print(f"Generated new GUID for memory: {self.memory_guid}")
            # self.save_memory()

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
            "update": "update_memory.prompt",
            "compress": "compress_memory.prompt"
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
        
        The LLM is free to choose the internal structure of static_memory
        based on what makes sense for the domain.
        """
        # Check if we have valid existing memory
        if self.memory and all(key in self.memory for key in ["initial_data", "static_memory", "context", "conversation_history"]):
            print("Valid memory structure already exists, skipping initialization")
            # Ensure GUID exists even for pre-existing memories
            self._ensure_memory_guid()
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
            
            # Use existing GUID if it was provided or already generated, only generate a new one as a last resort
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                print(f"Generated new GUID for memory: {self.memory_guid}")
            else:
                print(f"Using existing GUID for memory: {self.memory_guid}")
            
            # Initialize complete memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "guid": self.memory_guid,            # Use the GUID we already have or just generated
                "memory_type": "standard",           # Explicitly mark this as a standard memory type
                "initial_data": input_data,         # Store the initial raw input data
                "static_memory": memory_data["static_memory"],
                "context": {},                       # Organized important information by topic
                "metadata": {
                    "created_at": now,
                    "last_updated": now,
                    "version": "1.0"
                },
                "conversation_history": []
            }
            
            self.save_memory("create_initial_memory")
            print(f"Initial memory created with GUID: {self.memory_guid} and type: standard")
            return True
            
        except Exception as e:
            print(f"Error creating memory structure: {str(e)}")
            print(f"Full error: {repr(e)}")
            return False

    def query_memory(self, query_context: Dict[str, Any]) -> str:
        """Query memory with the given context."""
        try:
            print("\nQuerying memory...")
            
            # Add user message to history
            user_message = query_context.get("user_message", "")
            if user_message:
                # Create user message entry with GUID
                user_entry = {
                    "guid": str(uuid.uuid4()),
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Generate digest for user message
                print("Generating digest for user message...")
                user_digest = self.digest_generator.generate_digest(user_entry, self.memory)
                user_entry["digest"] = user_digest
                
                # Add to both conversation history file and memory
                self.add_to_conversation_history(user_entry)
                self.memory["conversation_history"].append(user_entry)
                print(f"Added user message to history with digest: {user_message}")
            
            # Format static memory as text
            static_memory_text = self._format_static_memory_as_text()
            
            # Format context as text
            context_text = self._format_context_as_text()
            
            # Format recent conversation history as text
            conversation_history_text = self._format_conversation_history_as_text()
            
            # Get domain-specific instructions
            domain_instructions = ""
            if self.domain_config and "domain_specific_prompt_instructions" in self.domain_config:
                domain_instructions = self.domain_config["domain_specific_prompt_instructions"].get("query", "")
            
            # Create prompt with formatted text
            prompt = self.templates["query"].format(
                static_memory_text=static_memory_text,
                context_text=context_text,
                conversation_history_text=conversation_history_text,
                query=user_message,
                domain_instructions=domain_instructions
            )
            
            # Get response from LLM
            print("Generating response using LLM...")
            llm_response = self.llm.generate(prompt)
            
            # Create assistant entry with GUID
            assistant_entry = {
                "guid": str(uuid.uuid4()),
                "role": "assistant",
                "content": llm_response,
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate digest for assistant response
            print("Generating digest for assistant response...")
            assistant_digest = self.digest_generator.generate_digest(assistant_entry, self.memory)
            assistant_entry["digest"] = assistant_digest
            
            # Add to both conversation history file and memory
            self.add_to_conversation_history(assistant_entry)
            self.memory["conversation_history"].append(assistant_entry)
            print("Added assistant response to history with digest")

            # Save to persist memory updates
            self.save_memory("query_memory")
            
            # Check if we should compress memory based on number of conversations
            conversation_count = len(self.memory["conversation_history"]) // 2  # Each conversation is a user-assistant pair
            if conversation_count > self.max_recent_conversations:
                print(f"Memory has {conversation_count} conversations, compressing...")
                self.update_memory({"operation": "update"})
            
            return llm_response

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            return f"Error processing query: {str(e)}"

    def _format_static_memory_as_text(self) -> str:
        """Format static memory as readable text instead of JSON."""
        if "static_memory" not in self.memory:
            return "No static memory available."
            
        static_memory = self.memory["static_memory"]
        if "topics" not in static_memory:
            return f"Static memory available but not in topic format: {json.dumps(static_memory, indent=2)}"
        
        result = []
        for topic_name, segments in static_memory["topics"].items():
            result.append(f"TOPIC: {topic_name}")
            for segment in segments:
                importance = segment.get("importance", 3)
                importance_str = "*" * importance  # Visualize importance with asterisks
                text = segment.get("text", "")
                result.append(f"{importance_str} {text}")
            result.append("")  # Empty line between topics
        
        return "\n".join(result)
    
    def _format_context_as_text(self) -> str:
        """Format context as readable text instead of JSON."""
        if "context" not in self.memory or not self.memory["context"]:
            return "No context information available yet."
        
        result = []
        for topic_name, items in self.memory["context"].items():
            result.append(f"TOPIC: {topic_name}")
            for item in items:
                text = item.get("text", "")
                attribution = item.get("attribution", "")
                importance = item.get("importance", 3)
                importance_str = "*" * importance  # Visualize importance with asterisks
                result.append(f"{importance_str} {text} [{attribution}]")
            result.append("")  # Empty line between topics
        
        return "\n".join(result)
    
    def _format_conversation_history_as_text(self) -> str:
        """Format recent conversation history as readable text."""
        if "conversation_history" not in self.memory or not self.memory["conversation_history"]:
            return "No conversation history available."
        
        # Get only the most recent conversation entries
        recent_count = min(4, len(self.memory["conversation_history"]))  # Last 2 exchanges
        recent_entries = self.memory["conversation_history"][-recent_count:]
        
        result = []
        for entry in recent_entries:
            role = entry.get("role", "unknown").upper()
            content = entry.get("content", "")
            result.append(f"[{role}]: {content}")
            result.append("")  # Empty line between entries
        
        return "\n".join(result)

    def update_memory(self, update_context: Dict[str, Any]) -> bool:
        """Update memory by compressing conversation history to keep only important segments.
        
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

            print("\nCompressing conversation history...")            
            return self._compress_conversation_history()
            
        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False

    def _compress_conversation_history(self) -> bool:
        """Compress conversation history by keeping only important segments and updating context."""
        try:
            # Check if we have enough conversations to compress
            if len(self.memory["conversation_history"]) < (self.max_recent_conversations * 2):
                print(f"Not enough conversations to compress (need {self.max_recent_conversations * 2}, have {len(self.memory['conversation_history'])})")
                return False
            
            # Find conversation entries to compress (all except most recent MAX_RECENT_CONVERSATIONS)
            keep_recent = self.max_recent_conversations * 2  # Each conversation has user and assistant messages
            entries_to_compress = self.memory["conversation_history"][:-keep_recent]
            
            if not entries_to_compress:
                print("No entries to compress")
                return False
            
            # Extract important segments from entries to compress
            important_segments = []
            compressed_guids = []  # Keep track of compressed entry GUIDs
            
            for entry in entries_to_compress:
                # Store GUID of compressed entry for reference
                entry_guid = entry.get("guid")
                if entry_guid:
                    compressed_guids.append(entry_guid)
                    
                # Process digest if available
                if "digest" in entry and "rated_segments" in entry["digest"]:
                    # Filter segments by importance
                    for segment in entry["digest"]["rated_segments"]:
                        if segment.get("importance", 0) >= self.importance_threshold:
                            # Include role and timestamp with the segment
                            important_segments.append({
                                "text": segment["text"],
                                "importance": segment["importance"],
                                "topics": segment.get("topics", []),
                                "role": entry["role"],
                                "timestamp": entry["timestamp"],
                                "source_guid": entry_guid  # Link back to original entry
                            })
            
            print(f"Extracted {len(important_segments)} important segments from {len(entries_to_compress)} entries")
            
            # If we have important segments, update the context
            if important_segments:
                # Use LLM to organize important segments by topic
                prompt = self.templates["compress"].format(
                    important_segments=json.dumps(important_segments, indent=2),
                    existing_context=json.dumps(self.memory.get("context", {}), indent=2)
                )
                
                # Call LLM to organize segments
                llm_response = self.llm.generate(prompt)
                
                try:
                    updated_context = json.loads(llm_response)
                    if not isinstance(updated_context, dict):
                        print("Invalid context format returned from LLM, must be a dictionary")
                        return False
                    
                    # Update the context
                    self.memory["context"] = updated_context
                    print("Updated memory context with organized important segments")
                except json.JSONDecodeError:
                    # Try to extract JSON if it's embedded in markdown or other text
                    json_match = re.search(r'\{[\s\S]*\}', llm_response)
                    if json_match:
                        try:
                            json_str = json_match.group(0)
                            # Remove any markdown code block markers
                            json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                            updated_context = json.loads(json_str)
                            
                            if not isinstance(updated_context, dict):
                                print("Invalid context format returned from LLM, must be a dictionary")
                                return False
                            
                            # Update the context
                            self.memory["context"] = updated_context
                            print("Updated memory context with organized important segments")
                        except json.JSONDecodeError as e:
                            print(f"Error parsing extracted JSON context: {str(e)}")
                            return False
                    else:
                        print("Could not extract context JSON from LLM response")
                        return False
            
            # Keep only the most recent conversations in memory
            self.memory["conversation_history"] = self.memory["conversation_history"][-keep_recent:]
            
            # Add a record of compressed entries
            if "compressed_entries" not in self.memory:
                self.memory["compressed_entries"] = []
            
            # Record this compression operation
            self.memory["compressed_entries"].append({
                "timestamp": datetime.now().isoformat(),
                "entry_guids": compressed_guids,
                "count": len(compressed_guids)
            })
            
            print(f"Compressed memory to keep {keep_recent} recent messages")
            
            # Update metadata
            self.memory["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Save the updated memory
            self.save_memory("compress_memory")
            print("Memory compressed and saved successfully")
            return True
            
        except Exception as e:
            print(f"Error in _compress_conversation_history: {str(e)}")
            return False
