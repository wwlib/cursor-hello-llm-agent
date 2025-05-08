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
from .memory_compressor import MemoryCompressor
from .data_preprocessor import DataPreprocessor
from .embeddings_manager import EmbeddingsManager
from .rag_manager import RAGManager

class MemoryManager(BaseMemoryManager):
    """LLM-driven memory manager implementation.
    
    Extends BaseMemoryManager to provide LLM-driven memory operations with domain-specific configuration.
    """

    def __init__(self, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, 
                 llm_service = None, digest_llm_service = None, embeddings_llm_service = None, memory_guid: str = None, 
                 max_recent_conversation_entries: int = 8, importance_threshold: int = 3):
        """Initialize the MemoryManager with LLM service instances and domain configuration.
        
        Args:
            memory_file: Path to the JSON file for persistent storage
            domain_config: Dictionary containing domain-specific configuration:
                         - schema: Domain-specific entity types and properties
                         - relationships: Domain-specific relationship types
                         - prompts: Domain-specific prompt templates
            llm_service: Service for general LLM operations (required)
            digest_llm_service: Service for digest generation (optional, falls back to llm_service)
            embeddings_llm_service: Service for embeddings/RAG (optional, falls back to llm_service)
            memory_guid: Optional GUID to identify this memory instance. If not provided, 
                       a new one will be generated or loaded from existing file.
            max_recent_conversation_entries: Maximum number of recent conversation entries to keep before compression
            importance_threshold: Threshold for segment importance (1-5 scale) to keep during compression
        """
        if llm_service is None:
            raise ValueError("llm_service is required for MemoryManager")
            
        # Pass memory_guid to the parent constructor
        super().__init__(memory_file, domain_config, memory_guid)
        print(f"\nInitializing MemoryManager with file: {memory_file}")
        self.llm = llm_service
        self.digest_llm = digest_llm_service or llm_service
        self.embeddings_llm = embeddings_llm_service or llm_service
        self._load_templates()
        
        # Initialize DigestGenerator with dedicated LLM service
        self.digest_generator = DigestGenerator(self.digest_llm)
        print("Initialized DigestGenerator")
        
        # Initialize MemoryCompressor (uses general LLM)
        self.memory_compressor = MemoryCompressor(self.llm, importance_threshold)
        print("Initialized MemoryCompressor")
        
        # Initialize EmbeddingsManager and RAGManager with dedicated embeddings LLM service
        embeddings_file = os.path.splitext(memory_file)[0] + "_embeddings.jsonl"
        self.embeddings_manager = EmbeddingsManager(embeddings_file, self.embeddings_llm)
        self.rag_manager = RAGManager(self.embeddings_llm, self.embeddings_manager)
        print("Initialized EmbeddingsManager and RAGManager")
        print(f"Embeddings file: {embeddings_file}")
        
        # Ensure memory has a GUID
        self._ensure_memory_guid()
        
        # Configurable memory parameters
        self.max_recent_conversation_entries = max_recent_conversation_entries
        self.importance_threshold = importance_threshold
        print(f"Memory configuration: max_recent_conversation_entries={max_recent_conversation_entries}, importance_threshold={importance_threshold}")

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
                "query": "",
                "update": ""
            }
        }

    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = {}
        
        template_files = {
            "query": "query_memory.prompt"
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
        
        The initial data is processed through the DigestGenerator to create a structured
        markdown representation of the static knowledge.
        """
        try:
            # Check if we have valid existing memory
            if self.memory and all(key in self.memory for key in ["static_memory", "context", "conversation_history"]):
                print("Valid memory structure already exists, skipping initialization")
                # Ensure GUID exists even for pre-existing memories
                self._ensure_memory_guid()
                return True

            print("\nCreating initial memory structure...")

            # Use DataPreprocessor to segment the input data
            data_preprocessor = DataPreprocessor(self.llm)
            preprocessed_segments = data_preprocessor.preprocess_data(input_data)
            print(f"Preprocessed segments: {preprocessed_segments}")

            # Create system entry for initial data
            system_entry = {
                "guid": str(uuid.uuid4()),
                "role": "system",
                "content": input_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate digest for initial data using pre-segmented content
            print("Generating digest for initial data with pre-segmented content...")
            initial_digest = self.digest_generator.generate_digest(system_entry, segments=preprocessed_segments)
            system_entry["digest"] = initial_digest
                        
            # Create static memory from digest
            static_memory = self._create_static_memory_from_digest(initial_digest)
            
            # Initialize complete memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "guid": self.memory_guid,            # Use the GUID we already have or just generated
                "memory_type": "standard",           # Explicitly mark this as a standard memory type
                "static_memory": static_memory,      # Markdown formatted static knowledge
                "context": [],                       # Organized important information by topic
                "metadata": {
                    "created_at": now,
                    "updated_at": now,
                    "version": "2.0.0",
                    "domain": self.domain_config.get("name", "general") if self.domain_config else "general"
                },
                "conversation_history": [system_entry]  # Include initial entries in history
            }
            
            # Save memory to file
            self.save_memory("create_initial_memory")
            
            # Also add to conversation history file
            self.add_to_conversation_history(system_entry)
            
            # Generate and save embeddings for the initial system entry
            self.embeddings_manager.update_indices([system_entry])

            print("Memory created and initialized with static knowledge")
            return True
        except Exception as e:
            print(f"Error creating initial memory: {str(e)}")
            return False

    def _create_static_memory_from_digest(self, digest: Dict[str, Any]) -> str:
        """Create static memory text from a digest by concatenating rated segments."""
        try:
            rated_segments = digest.get("rated_segments", [])
            
            if not rated_segments:
                print("Warning: No rated segments found in digest, using empty static memory")
                return ""
            
            return "\n".join(segment.get("text", "") for segment in rated_segments)
            
        except Exception as e:
            print(f"Error creating static memory from digest: {str(e)}")
            return ""

    def _get_initial_segments_text(self) -> str:
        """Concatenate the rated segments from the initial system entry for use in prompts."""
        if "conversation_history" not in self.memory or not self.memory["conversation_history"]:
            return ""
        initial_entry = self.memory["conversation_history"][0]
        digest = initial_entry.get("digest", {})
        rated_segments = digest.get("rated_segments", [])
        if not rated_segments:
            return initial_entry.get("content", "")
        # Concatenate all segment texts, separated by newlines
        return "\n".join(seg.get("text", "") for seg in rated_segments if seg.get("text"))

    def query_memory(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Query memory with the given context.
        
        Args:
            query_context: Dictionary containing query context:
                           - query: The query text
                           - domain_instructions: Optional domain-specific instructions
                           - rag_context: Optional RAG-enhanced context
                           
        Returns:
            Dict[str, Any]: Response with the LLM's answer
        """
        try:
            print("\nQuerying memory...")
            
            # Extract query text
            query = query_context.get("query", "")

            # Add user message to history and trigger embedding/indexing
            if query:
                user_entry = {
                    "guid": str(uuid.uuid4()),
                    "role": "user",
                    "content": query,
                    "timestamp": datetime.now().isoformat()
                }
                self.add_conversation_entry(user_entry)
            
            # Use concatenated initial segments for static memory in prompts
            static_memory_text = query_context.get("static_memory", "") or self._get_initial_segments_text() or self._format_static_memory_as_text()
            
            # Format context as text (use provided or get from memory)
            previous_context_text = query_context.get("previous_context", "") or self._format_context_as_text()
            
            # Format recent conversation history as text (use provided or get from memory)
            conversation_history_text = query_context.get("conversation_history", "") or self._format_conversation_history_as_text()
            
            # Get or generate RAG context
            rag_context = query_context.get("rag_context")
            if not rag_context:
                enhanced_context = self.rag_manager.enhance_memory_query(query_context)
                rag_context = enhanced_context.get("rag_context", "")
                if rag_context:
                    print("Using RAG-enhanced context for memory query (auto-generated)")
            else:
                print("Using RAG-enhanced context for memory query (provided)")
            
            # Get domain-specific instructions (use provided or get from config)
            domain_specific_prompt_instructions = query_context.get("domain_specific_prompt_instructions", "")
            domain_specific_query_prompt_instructions = domain_specific_prompt_instructions
            if not domain_specific_prompt_instructions and self.domain_config:
                domain_specific_prompt_instructions = self.domain_config.get("domain_specific_prompt_instructions", "")
                domain_specific_query_prompt_instructions = domain_specific_prompt_instructions.get("query", "") if isinstance(domain_specific_prompt_instructions, dict) else ""
            
            # Create prompt with formatted text
            prompt = self.templates["query"].format(
                static_memory_text=static_memory_text,
                previous_context_text=previous_context_text,
                conversation_history_text=conversation_history_text,
                query=query,
                domain_specific_prompt_instructions=domain_specific_query_prompt_instructions,
                rag_context=rag_context  # Include RAG context in the prompt
            )
            
            # Get response from LLM
            print("Generating response using LLM...")
            llm_response = self.llm.generate(
                prompt,
                options={"temperature": 0.7}
            )
            
            # Add agent response to history and trigger embedding/indexing
            agent_entry = {
                "guid": str(uuid.uuid4()),
                "role": "agent",
                "content": llm_response,
                "timestamp": datetime.now().isoformat()
            }
            self.add_conversation_entry(agent_entry)

            # Save to persist memory updates
            self.save_memory("query_memory")
            
            # Check if we should compress memory based on number of conversations
            conversation_entries = len(self.memory["conversation_history"])
            if conversation_entries > self.max_recent_conversation_entries:
                print(f"Memory has {conversation_entries} conversations, compressing...")
                self.update_memory({"operation": "update"})
            
            return {"response": llm_response}

        except Exception as e:
            print(f"Error in query_memory: {str(e)}")
            return {"response": f"Error processing query: {str(e)}", "error": str(e)}

    def _format_static_memory_as_text(self) -> str:
        """Format static memory as readable text."""
        if "static_memory" not in self.memory:
            return "No static memory available."
            
        static_memory = self.memory["static_memory"]
        if not static_memory:
            return "Static memory is empty."
        
        # Static memory is now stored as markdown, so we can return it directly
        return static_memory
    
    def get_formatted_context(self) -> str:
        """Get formatted context text for external use (e.g., RAG)."""
        return self._format_context_as_text()
        
    def _format_context_as_text(self) -> str:
        """Format context as readable text instead of JSON."""
        if "context" not in self.memory or not self.memory["context"]:
            return "No context information available yet."
        
        context = self.memory["context"]
        result = []
        
        # Handle context as a list (newer format)
        if isinstance(context, list):
            for item in context:
                # Each item is a context entry with text and guids
                text = item.get("text", "")
                guids = item.get("guids", [])
                
                # Add formatted text
                if text:
                    result.append(text)
                    result.append("")  # Empty line between entries
        
        # Handle context as a dictionary (older format)
        elif isinstance(context, dict):
            for topic_name, items in context.items():
                result.append(f"TOPIC: {topic_name}")
                for item in items:
                    text = item.get("text", "")
                    attribution = item.get("attribution", "")
                    importance = item.get("importance", 3)
                    importance_str = "*" * importance  # Visualize importance with asterisks
                    result.append(f"{importance_str} {text} [{attribution}]")
                result.append("")  # Empty line between topics
        
        # Add message for unrecognized format
        else:
            result.append("Context information available but format not recognized.")
        
        return "\n".join(result)
    
    def get_formatted_recent_conversations(self) -> str:
        """Get formatted recent conversation history for external use (e.g., RAG)."""
        return self._format_conversation_history_as_text()
        
    def _format_conversation_history_as_text(self) -> str:
        """Format recent conversation history as readable text using digest segments."""
        if "conversation_history" not in self.memory or not self.memory["conversation_history"]:
            return "No conversation history available."
        
        # Get only the most recent conversation entries
        recent_count = min(4, len(self.memory["conversation_history"]))  # Last 2 exchanges
        recent_entries = self.memory["conversation_history"][-recent_count:]
        
        result = []
        for entry in recent_entries:
            role = entry.get("role", "unknown").upper()
            
            # Get segments from digest if available
            digest = entry.get("digest", {})
            segments = digest.get("rated_segments", [])
            
            if segments:
                # Use concatenated segments
                content = " ".join(segment["text"] for segment in segments)
            else:
                # Fallback to original content if no digest/segments
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
            # Get current memory state
            conversation_history = self.memory.get("conversation_history", [])
            # Use concatenated initial segments for static memory in compression
            static_memory = self._get_initial_segments_text() or self.memory.get("static_memory", "")
            current_context = self.memory.get("context", [])
            
            # Use MemoryCompressor to compress the conversation history
            compressed_state = self.memory_compressor.compress_conversation_history(
                conversation_history=conversation_history,
                static_memory=static_memory,
                current_context=current_context
            )
            
            # Update memory with compressed state
            self.memory["conversation_history"] = compressed_state.get("conversation_history", conversation_history)
            self.memory["context"] = compressed_state.get("context", current_context)
            
            # Update the compressed entries tracker
            if "compressed_entries" not in self.memory["metadata"]:
                self.memory["metadata"]["compressed_entries"] = []
            # Defensive: ensure it's a list
            if not isinstance(self.memory["metadata"]["compressed_entries"], list):
                self.memory["metadata"]["compressed_entries"] = []
            compressed_entries = compressed_state.get("compressed_entries", [])
            self.memory["metadata"]["compressed_entries"].extend(compressed_entries)
            
            # Update metadata
            self.memory["metadata"]["updated_at"] = datetime.now().isoformat()
            self.memory["metadata"]["compression_count"] = self.memory["metadata"].get("compression_count", 0) + 1
            
            # Save to persist memory updates
            self.save_memory("compress_conversation_history")
            
            print(f"Compressed conversation history. Remaining entries: {len(self.memory['conversation_history'])}")
            return True
            
        except Exception as e:
            print(f"Error compressing conversation history: {str(e)}")
            return False
            
    def add_conversation_entry(self, entry: Dict[str, Any]) -> bool:
        """Add a conversation entry with automatic digest generation.
        
        Args:
            entry: Dictionary containing the conversation entry:
                  - guid: Optional unique identifier (will be generated if missing)
                  - role: Role (e.g., "user", "agent", "system")
                  - content: Entry content text
                  - timestamp: Optional timestamp (will be generated if missing)
                  
        Returns:
            bool: True if the entry was added successfully
        """
        try:
            # Ensure basic fields exist
            if "content" not in entry:
                print("Error: Conversation entry must have 'content'")
                return False
                
            if "role" not in entry:
                print("Error: Conversation entry must have 'role'")
                return False
                
            # Ensure GUID
            if "guid" not in entry:
                entry["guid"] = str(uuid.uuid4())
                
            # Ensure timestamp
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.now().isoformat()
                
            # Generate digest if not already present
            if "digest" not in entry:
                print(f"Generating digest for {entry['role']} entry...")
                entry["digest"] = self.digest_generator.generate_digest(entry, self.memory)
                
            # Add to conversation history file and memory
            self.add_to_conversation_history(entry)
            
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
                
            self.memory["conversation_history"].append(entry)
            print(f"Added {entry['role']} entry to conversation history")
            
            # Save to persist memory updates
            self.save_memory("add_conversation_entry")
            
            # Update RAG/embeddings indices for the new entry
            self.embeddings_manager.update_indices([entry])

            return True
            
        except Exception as e:
            print(f"Error adding conversation entry: {str(e)}")
            return False
            
    def update_memory_with_conversations(self) -> bool:
        """Update memory with current conversation history.
        
        This method processes the conversation history to extract important information
        and update the memory context.
        
        Returns:
            bool: True if memory was updated successfully
        """
        try:
            # Check if we need to compress based on conversation count
            conversation_entries = len(self.memory.get("conversation_history", []))
            if conversation_entries > self.max_recent_conversation_entries:
                print(f"Memory has {conversation_entries} conversations, compressing...")
                return self.update_memory({"operation": "update"})
            else:
                print(f"Memory has only {conversation_entries} conversations, compression not needed yet")
                return True
        except Exception as e:
            print(f"Error updating memory with conversations: {str(e)}")
            return False
