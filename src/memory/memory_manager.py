"""Memory Manager for Agent System

Design Principles::

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

Usage::

    memory_manager = MemoryManager(
        memory_guid=guid,
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
from .graph_memory import AltGraphManager as GraphManager
import asyncio
import logging

# Memory filtering constants
DEFAULT_COMPRESSION_IMPORTANCE_THRESHOLD = 3
DEFAULT_RAG_IMPORTANCE_THRESHOLD = 3  # Standardized to match compression
DEFAULT_EMBEDDINGS_IMPORTANCE_THRESHOLD = 3  # Only embed important segments

class MemoryManager(BaseMemoryManager):
    """LLM-driven memory manager implementation.
    
    Extends BaseMemoryManager to provide LLM-driven memory operations with domain-specific configuration.
    """

    def __init__(self, memory_guid: str, memory_file: str = "memory.json", domain_config: Optional[Dict[str, Any]] = None, 
                 llm_service = None, digest_llm_service = None, embeddings_llm_service = None, 
                 max_recent_conversation_entries: int = 8, importance_threshold: int = DEFAULT_COMPRESSION_IMPORTANCE_THRESHOLD, 
                 enable_graph_memory: bool = True, logger=None):
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
            memory_guid: Required GUID to identify this memory instance.
            max_recent_conversation_entries: Maximum number of recent conversation entries to keep before compression
            importance_threshold: Threshold for segment importance (1-5 scale) to keep during compression
            enable_graph_memory: Whether to enable graph memory functionality (default: True)
            logger: Optional logger instance for this MemoryManager
        """
        if llm_service is None:
            raise ValueError("llm_service is required for MemoryManager")
            
        # Pass memory_guid and logger to the parent constructor
        super().__init__(memory_guid, memory_file, domain_config, logger=logger)
        self.logger.debug(f"\nInitializing MemoryManager with file: {memory_file}")
        self.llm = llm_service
        self.digest_llm = digest_llm_service or llm_service
        self.embeddings_llm = embeddings_llm_service or llm_service
        self._load_templates()
        
        # Initialize DigestGenerator with dedicated LLM service and domain config
        domain_name = self.domain_config.get("domain_name", "general") if self.domain_config else "general"
        self.logger.debug(f"Initializing DigestGenerator for domain: {domain_name}")
        self.digest_generator = DigestGenerator(self.digest_llm, domain_name=domain_name, domain_config=self.domain_config, logger=logger)
        
        # Initialize MemoryCompressor (uses general LLM)
        self.memory_compressor = MemoryCompressor(self.llm, importance_threshold, logger=logger)
        self.logger.debug("Initialized MemoryCompressor")
        
        # Initialize EmbeddingsManager first
        embeddings_file = os.path.splitext(memory_file)[0] + "_embeddings.jsonl"
        self.embeddings_manager = EmbeddingsManager(embeddings_file, self.embeddings_llm, logger=logger)
        self.logger.debug("Initialized EmbeddingsManager")
        self.logger.debug(f"Embeddings file: {embeddings_file}")
        
        # Initialize GraphManager if enabled
        self.enable_graph_memory = enable_graph_memory
        self.graph_manager = None
        if enable_graph_memory:
            try:
                # Create graph storage path based on memory file
                memory_dir = os.path.dirname(memory_file) or "."
                memory_base = os.path.basename(memory_file).split(".")[0]
                graph_storage_path = os.path.join(memory_dir, f"{memory_base}_graph_data")
                graph_embeddings_file = os.path.join(graph_storage_path, "graph_memory_embeddings.jsonl")
                
                # Create directory for graph storage
                os.makedirs(graph_storage_path, exist_ok=True)
                
                # Create dedicated logger for graph manager
                graph_logger = self._create_graph_manager_logger(memory_dir, memory_base)
                
                # Get similarity threshold from domain config
                similarity_threshold = 0.8
                if self.domain_config and "graph_memory_config" in self.domain_config:
                    similarity_threshold = self.domain_config["graph_memory_config"].get("similarity_threshold", 0.8)
                
                # Create separate embeddings manager for graph memory
                graph_embeddings_file = os.path.join(graph_storage_path, "graph_memory_embeddings.jsonl")
                graph_embeddings_manager = EmbeddingsManager(
                    embeddings_file=graph_embeddings_file,
                    llm_service=self.embeddings_llm,
                    logger=graph_logger  # Use dedicated graph logger
                )
                
                self.graph_manager = GraphManager(
                    storage_path=graph_storage_path,
                    embeddings_manager=graph_embeddings_manager,
                    similarity_threshold=similarity_threshold,
                    logger=graph_logger,  # Use dedicated graph logger
                    llm_service=self.llm,  # Use general LLM service (gemma3) for entity extraction
                    embeddings_llm_service=self.embeddings_llm,  # Use embeddings LLM service (mxbai-embed-large)
                    domain_config=self.domain_config
                )
                self.logger.debug(f"Initialized GraphManager with storage: {graph_storage_path}")
                graph_logger.debug(f"Graph memory logger initialized for memory: {memory_base}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GraphManager: {e}. Graph memory disabled.")
                self.enable_graph_memory = False
                self.graph_manager = None
        
        # Initialize RAGManager with optional graph manager
        self.rag_manager = RAGManager(
            llm_service=self.embeddings_llm, 
            embeddings_manager=self.embeddings_manager, 
            graph_manager=self.graph_manager,
            logger=logger
        )
        self.logger.debug("Initialized RAGManager with graph integration")
        
        # Ensure memory has a GUID
        self._ensure_memory_guid()
        
        # Configurable memory parameters
        self.max_recent_conversation_entries = max_recent_conversation_entries
        self.importance_threshold = importance_threshold
        self.logger.debug(f"Memory configuration: max_recent_conversation_entries={max_recent_conversation_entries}, importance_threshold={importance_threshold}, graph_memory={enable_graph_memory}")

    def _ensure_memory_guid(self):
        """Ensure that the memory has a GUID, prioritizing the provided GUID if available."""
        # If memory doesn't exist yet, we'll handle this when creating memory
        if not self.memory:
            # Make sure we have a GUID, generating one if needed
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                self.logger.debug(f"Generated new GUID: {self.memory_guid} for memory file that will be created")
            return
            
        # Priority order for GUID:
        # 1. GUID provided at initialization (self.memory_guid from constructor)
        # 2. GUID in existing memory file (self.memory["guid"])
        # 3. Generate a new GUID if neither exists
        
        # If we already have a GUID from initialization, use it
        if self.memory_guid:
            # Force the memory to use our provided GUID, overriding any existing GUID
            if "guid" in self.memory and self.memory["guid"] != self.memory_guid:
                self.logger.debug(f"Replacing existing memory GUID: {self.memory['guid']} with provided GUID: {self.memory_guid}")
            
            # Set the GUID in memory
            self.memory["guid"] = self.memory_guid
            self.logger.debug(f"Using provided GUID for memory: {self.memory_guid}")
        # If no GUID was provided but one exists in memory, use that
        elif "guid" in self.memory:
            self.memory_guid = self.memory["guid"]
            self.logger.debug(f"Using existing memory GUID: {self.memory_guid}")
        # If no GUID was provided and none exists in memory, generate a new one
        else:
            self.memory_guid = str(uuid.uuid4())
            self.memory["guid"] = self.memory_guid
            self.logger.debug(f"Generated new GUID for memory: {self.memory_guid}")

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
                self.logger.debug(f"Loaded template: {filename}")
            except Exception as e:
                self.logger.error(f"Error loading template {filename}: {str(e)}")
                # Raise an exception if the template cannot be loaded
                raise Exception(f"Failed to load template: {filename}")

    def create_initial_memory(self, input_data: str) -> bool:
        self.logger.debug(f"[DEBUG] create_initial_memory: memory_file={self.memory_file}, current self.memory={json.dumps(self.memory, indent=2)}")
        try:
            # Check if we have valid existing memory
            if self.memory and all(key in self.memory for key in ["static_memory", "context", "conversation_history"]):
                self.logger.debug("Valid memory structure already exists, skipping initialization")
                # Ensure GUID exists even for pre-existing memories
                self._ensure_memory_guid()
                return True
            self.logger.debug("Creating initial memory structure...")

            # Use DataPreprocessor to segment the input data
            data_preprocessor = DataPreprocessor(self.llm)
            preprocessed_prose, preprocessed_segments = data_preprocessor.preprocess_data(input_data)
            self.logger.debug(f"Preprocessed segments: {preprocessed_segments}")

            # Create system entry for initial data
            system_entry = {
                "guid": str(uuid.uuid4()),
                "role": "system",
                "content": input_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate digest for initial data using pre-segmented content
            self.logger.debug("Generating digest for initial data with pre-segmented content...")
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
            self.embeddings_manager.add_new_embeddings([system_entry])

            # Process static memory with graph memory system if enabled
            if self.enable_graph_memory and self.graph_manager:
                self.logger.debug("Processing static memory for graph memory...")
                self._process_initial_graph_memory(system_entry)

            self.logger.debug("Memory created and initialized with static knowledge")
            return True
        except Exception as e:
            self.logger.error(f"Error creating initial memory: {str(e)}")
            return False

    def _create_static_memory_from_digest(self, digest: Dict[str, Any]) -> str:
        """Create static memory text from a digest by concatenating rated segments."""
        try:
            rated_segments = digest.get("rated_segments", [])
            
            if not rated_segments:
                self.logger.debug("Warning: No rated segments found in digest, using empty static memory")
                return ""
            
            return "\n".join(segment.get("text", "") for segment in rated_segments)
            
        except Exception as e:
            self.logger.error(f"Error creating static memory from digest: {str(e)}")
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

    def _create_graph_manager_logger(self, memory_dir: str, memory_base: str) -> logging.Logger:
        """Create a dedicated logger for graph manager operations.
        
        Args:
            memory_dir: Directory where the memory file is located
            memory_base: Base name of the memory file (without extension) - kept for compatibility
            
        Returns:
            Logger instance configured for graph memory operations
        """
        # Create logger name based on memory GUID for session-specific logging
        logger_name = f"graph_memory.{self.memory_guid}"
        graph_logger = logging.getLogger(logger_name)
        
        # Avoid duplicate handlers if logger already exists
        if graph_logger.handlers:
            return graph_logger
            
        # Set logger level
        graph_logger.setLevel(logging.DEBUG)
        
        # Create session-specific logs directory (same pattern as agent_usage_example.py)
        if memory_dir and memory_dir != ".":
            # For GUID-specific memories, use the parent directory to create logs
            parent_dir = os.path.dirname(memory_dir)
            if parent_dir and os.path.basename(parent_dir) in ["standard", "simple", "sync"]:
                # We're in agent_memories/standard/guid_dir structure
                logs_base_dir = os.path.dirname(os.path.dirname(parent_dir))  # Go up to project root
            else:
                # We're in a direct memory directory
                logs_base_dir = os.path.dirname(memory_dir) if memory_dir != "." else "."
        else:
            # Default to current directory
            logs_base_dir = "."
            
        # Create session-specific logs directory using memory GUID
        session_logs_dir = os.path.join(logs_base_dir, "logs", self.memory_guid)
        os.makedirs(session_logs_dir, exist_ok=True)
        
        # Create graph manager log file in the session directory
        log_file_path = os.path.join(session_logs_dir, "graph_manager.log")
        
        # Create file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        graph_logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs in parent loggers
        graph_logger.propagate = False
        
        self.logger.debug(f"Created graph memory logger: {logger_name} -> {log_file_path}")
        
        return graph_logger

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
            self.logger.debug("Querying memory...")
            
            # Extract query text
            query = query_context.get("query", "")

            # Add user message to history immediately
            if query:
                user_entry = {
                    "guid": str(uuid.uuid4()),
                    "role": "user",
                    "content": query,
                    "timestamp": datetime.now().isoformat()
                }
                # Add to conversation history file and memory immediately
                self.add_to_conversation_history(user_entry)
                if "conversation_history" not in self.memory:
                    self.memory["conversation_history"] = []
                self.memory["conversation_history"].append(user_entry)
                self.save_memory("add_user_entry")
            
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
                    self.logger.debug("Using RAG-enhanced context for memory query (auto-generated)")
            else:
                self.logger.debug("Using RAG-enhanced context for memory query (provided)")
            
            # Get graph context if enabled
            graph_context = ""
            if self.enable_graph_memory and self.graph_manager:
                try:
                    graph_context = self.get_graph_context(query)
                    if graph_context:
                        self.logger.debug("Added graph context to memory query")
                except Exception as e:
                    self.logger.warning(f"Failed to get graph context: {e}")
                    graph_context = ""
            
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
                rag_context=rag_context,  # Include RAG context in the prompt
                graph_context=graph_context  # Include graph context in the prompt
            )
            
            # Get response from LLM
            self.logger.debug("Generating response using LLM...")
            llm_response = self.llm.generate(
                prompt,
                options={"temperature": 0.7}
            )
            
            # Start background processing for user entry and agent response
            if query:
                # Start background processing for user entry
                asyncio.create_task(self._process_entry_async(user_entry))
            
            # Create agent entry
            agent_entry = {
                "guid": str(uuid.uuid4()),
                "role": "agent",
                "content": llm_response,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add agent response to history immediately
            self.add_to_conversation_history(agent_entry)
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
            self.memory["conversation_history"].append(agent_entry)
            self.save_memory("add_agent_entry")
            
            # Start background processing for agent entry
            asyncio.create_task(self._process_entry_async(agent_entry))
            
            # Check if we should compress memory based on number of conversations
            conversation_entries = len(self.memory["conversation_history"])
            if conversation_entries > self.max_recent_conversation_entries:
                self.logger.debug(f"Memory has {conversation_entries} conversations, scheduling compression...")
                asyncio.create_task(self._compress_memory_async())
            
            return {"response": llm_response}

        except Exception as e:
            self.logger.error(f"Error in query_memory: {str(e)}")
            return {"response": f"Error processing query: {str(e)}", "error": str(e)}
            
    async def _process_entry_async(self, entry: Dict[str, Any]) -> None:
        """Process a conversation entry asynchronously (digest generation, embeddings, and graph updates)."""
        try:
            # Generate digest if not already present
            if "digest" not in entry:
                self.logger.debug(f"Generating digest for {entry['role']} entry...")
                entry["digest"] = self.digest_generator.generate_digest(entry, self.memory)
                
                # Update conversation history file with the digest
                self._update_conversation_history_entry(entry)
                
                self.save_memory("async_digest_generation")
            
            # Update embeddings
            self.logger.debug(f"Updating embeddings for {entry['role']} entry...")
            self.embeddings_manager.add_new_embeddings([entry])
            
            # Update graph memory if enabled
            if self.enable_graph_memory and self.graph_manager:
                try:
                    await self._update_graph_memory_async(entry)
                except Exception as e:
                    self.logger.warning(f"Error updating graph memory: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in async entry processing: {str(e)}")
    
    async def _update_graph_memory_async(self, entry: Dict[str, Any]) -> None:
        """Update graph memory with entities and relationships from a conversation entry."""
        try:
            self.logger.debug(f"Updating graph memory for {entry['role']} entry...")
            
            # Check if we're using AltGraphManager and if it has EntityResolver
            if (hasattr(self.graph_manager, 'process_conversation_entry_with_resolver') and 
                hasattr(self.graph_manager, 'alt_entity_resolver') and 
                self.graph_manager.alt_entity_resolver):
                # Use conversation-level processing with EntityResolver for AltGraphManager
                await self._update_graph_memory_conversation_level(entry)
            else:
                # Use segment-based processing for regular GraphManager
                await self._update_graph_memory_segment_based(entry)
                
        except Exception as e:
            self.logger.error(f"Error updating graph memory: {e}")
    
    async def _update_graph_memory_conversation_level(self, entry: Dict[str, Any]) -> None:
        """Update graph memory using conversation-level processing (for AltGraphManager with EntityResolver)."""
        try:
            # Get full conversation text and digest
            conversation_text = entry.get("content", "")
            digest = entry.get("digest", {})
            digest_text = ""
            
            # Build digest text from important segments
            segments = digest.get("rated_segments", [])
            important_segments = [
                seg for seg in segments 
                if seg.get("importance", 0) >= DEFAULT_RAG_IMPORTANCE_THRESHOLD 
                and seg.get("memory_worthy", True)
                and seg.get("type") in ["information", "action"]
            ]
            
            if important_segments:
                digest_text = " ".join([seg.get("text", "") for seg in important_segments])
            
            if not conversation_text and not digest_text:
                self.logger.debug("No conversation or digest text, skipping graph update")
                return
            
            # Process using AltGraphManager with EntityResolver
            self.logger.debug("Processing conversation with AltGraphManager EntityResolver")
            results = self.graph_manager.process_conversation_entry_with_resolver(
                conversation_text=conversation_text,
                digest_text=digest_text,
                conversation_guid=entry.get("guid")
            )
            
            # Log results
            stats = results.get("stats", {})
            self.logger.info(f"Graph update completed - entities: {stats.get('entities_new', 0)} new, "
                           f"{stats.get('entities_existing', 0)} existing, "
                           f"relationships: {stats.get('relationships_extracted', 0)}")
            
        except Exception as e:
            self.logger.error(f"Error in conversation-level graph update: {e}")
    
    async def _update_graph_memory_segment_based(self, entry: Dict[str, Any]) -> None:
        """Update graph memory using segment-based processing (for regular GraphManager)."""
        try:
            # Get segments from digest
            digest = entry.get("digest", {})
            segments = digest.get("rated_segments", [])
            
            if not segments:
                self.logger.debug("No segments found in digest, skipping graph update")
                return
            
            # Filter for important segments
            important_segments = [
                seg for seg in segments 
                if seg.get("importance", 0) >= DEFAULT_RAG_IMPORTANCE_THRESHOLD 
                and seg.get("memory_worthy", True)
                and seg.get("type") in ["information", "action"]
            ]
            
            if not important_segments:
                self.logger.debug("No important segments found, skipping graph update")
                return
            
            # Process all segments together for better entity and relationship extraction
            all_segment_entities = []
            segments_with_entities = []
            
            # First pass: Extract entities from all segments
            for i, segment in enumerate(important_segments):
                segment_text = segment.get("text", "")
                if segment_text:
                    # Extract and resolve entities from the segment using EntityResolver
                    # This automatically handles adding/updating nodes with smart duplicate detection
                    entities = self.graph_manager.extract_and_resolve_entities_from_segments([{
                        "text": segment_text,
                        "importance": segment.get("importance", 0),
                        "type": segment.get("type", "information"),
                        "memory_worthy": segment.get("memory_worthy", True),
                        "topics": segment.get("topics", []),
                        "conversation_guid": entry.get("guid")
                    }])
                    
                    # Note: entities are already added/updated in extract_and_resolve_entities_from_segments
                    # The returned entities include resolution information for relationship extraction
                    
                    # Store segment with its entities for relationship extraction
                    if entities:
                        segment_with_entities = {
                            "id": f"seg_{i}",
                            "text": segment_text,
                            "entities": entities,
                            "importance": segment.get("importance", 0),
                            "type": segment.get("type", "information")
                        }
                        segments_with_entities.append(segment_with_entities)
                        all_segment_entities.extend(entities)
            
            # Second pass: Extract relationships across all segments if we have multiple entities
            if len(all_segment_entities) > 1 and segments_with_entities:
                try:
                    relationships = self.graph_manager.extract_relationships_from_segments(segments_with_entities)
                    
                    # Add relationships to graph
                    for rel in relationships:
                        # Find evidence from the segments
                        evidence = ""
                        for seg in segments_with_entities:
                            if any(entity.get("name") == rel.get("from_entity") for entity in seg.get("entities", [])) and \
                               any(entity.get("name") == rel.get("to_entity") for entity in seg.get("entities", [])):
                                evidence = seg.get("text", "")
                                break
                        
                        self.graph_manager.add_edge(
                            from_node=rel.get("from_entity", ""),
                            to_node=rel.get("to_entity", ""),
                            relationship_type=rel.get("relationship", "related_to"),
                            evidence=evidence or "Cross-segment relationship",
                            confidence=rel.get("confidence", 0.5)
                        )
                except Exception as e:
                    self.logger.warning(f"Error extracting relationships: {e}")
            
            self.logger.debug(f"Updated graph memory with {len(important_segments)} segments")
            
        except Exception as e:
            self.logger.error(f"Error in segment-based graph update: {e}")
    
    def _process_initial_graph_memory(self, system_entry: Dict[str, Any]) -> None:
        """Process initial system entry for graph memory during memory creation.
        
        This is a synchronous version of the graph memory processing specifically 
        for the initial static memory that contains domain knowledge.
        
        Args:
            system_entry: The initial system entry containing static memory content
        """
        try:
            self.logger.debug("Processing initial system entry for graph memory...")
            
            # Get segments from digest
            digest = system_entry.get("digest", {})
            segments = digest.get("rated_segments", [])
            
            if not segments:
                self.logger.debug("No segments found in initial digest, skipping initial graph processing")
                return
            
            # Filter for important segments (same criteria as async processing)
            important_segments = [
                seg for seg in segments 
                if seg.get("importance", 0) >= DEFAULT_RAG_IMPORTANCE_THRESHOLD 
                and seg.get("memory_worthy", True)
                and seg.get("type") in ["information", "action"]
            ]
            
            if not important_segments:
                self.logger.debug("No important segments found in initial content, skipping graph processing")
                return
            
            self.logger.debug(f"Processing {len(important_segments)} important segments for initial graph memory")
            
            # Process all segments together for better entity and relationship extraction
            all_segment_entities = []
            segments_with_entities = []
            
            # First pass: Extract entities from all segments
            for i, segment in enumerate(important_segments):
                segment_text = segment.get("text", "")
                if segment_text:
                    # Extract entities from the segment
                    entities = self.graph_manager.extract_entities_from_segments([{
                        "text": segment_text,
                        "importance": segment.get("importance", 0),
                        "type": segment.get("type", "information"),
                        "memory_worthy": segment.get("memory_worthy", True),
                        "topics": segment.get("topics", [])
                    }])
                    
                    # Add entities to graph (with automatic similarity matching)
                    for entity in entities:
                        # For initial memory, no conversation GUID is available
                        entity_attributes = entity.get("attributes", {}).copy()
                        
                        self.graph_manager.add_or_update_node(
                            name=entity.get("name", ""),
                            node_type=entity.get("type", "concept"),
                            description=entity.get("description", ""),
                            **entity_attributes
                        )
                    
                    # Store segment with its entities for relationship extraction
                    if entities:
                        segment_with_entities = {
                            "id": f"seg_{i}",
                            "text": segment_text,
                            "entities": entities,
                            "importance": segment.get("importance", 0),
                            "type": segment.get("type", "information")
                        }
                        segments_with_entities.append(segment_with_entities)
                        all_segment_entities.extend(entities)
            
            # Second pass: Extract relationships across all segments if we have multiple entities
            if len(all_segment_entities) > 1 and segments_with_entities:
                try:
                    relationships = self.graph_manager.extract_relationships_from_segments(segments_with_entities)
                    
                    # Add relationships to graph
                    for rel in relationships:
                        # Find evidence from the segments
                        evidence = ""
                        for seg in segments_with_entities:
                            if any(entity.get("name") == rel.get("from_entity") for entity in seg.get("entities", [])) and \
                               any(entity.get("name") == rel.get("to_entity") for entity in seg.get("entities", [])):
                                evidence = seg.get("text", "")
                                break
                        
                        self.graph_manager.add_edge(
                            from_node=rel.get("from_entity", ""),
                            to_node=rel.get("to_entity", ""),
                            relationship_type=rel.get("relationship_type", "related_to"),
                            confidence=rel.get("confidence", 0.5),
                            evidence=evidence
                        )
                    
                    self.logger.debug(f"Added {len(relationships)} relationships from initial static memory")
                    
                except Exception as e:
                    self.logger.error(f"Error extracting relationships from initial segments: {str(e)}")
            
            # Save graph state
            self.graph_manager.save_graph()
            
            self.logger.debug(f"Initial graph memory processing complete: {len(all_segment_entities)} entities processed")
            
        except Exception as e:
            self.logger.error(f"Error processing initial graph memory: {str(e)}")
            
    async def _compress_memory_async(self) -> None:
        """Compress memory asynchronously."""
        try:
            self.logger.debug("Starting async memory compression...")
            self._compress_conversation_history()
        except Exception as e:
            self.logger.error(f"Error in async memory compression: {str(e)}")

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
            self.logger.debug("Updating memory...")
            
            # Only handle updating memory operations
            if update_context.get("operation") != "update":
                self.logger.debug("update_memory should only be used for updating memory operations")
                return False

            self.logger.debug("Compressing conversation history...")            
            return self._compress_conversation_history()
            
        except Exception as e:
            self.logger.error(f"Error updating memory: {str(e)}")
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
            
            self.logger.debug(f"Compressed conversation history. Remaining entries: {len(self.memory['conversation_history'])}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error compressing conversation history: {str(e)}")
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
                self.logger.error("Error: Conversation entry must have 'content'")
                return False
                
            if "role" not in entry:
                self.logger.error("Error: Conversation entry must have 'role'")
                return False
                
            # Ensure GUID
            if "guid" not in entry:
                entry["guid"] = str(uuid.uuid4())
                
            # Ensure timestamp
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.now().isoformat()
                
            # Generate digest if not already present
            if "digest" not in entry:
                self.logger.debug(f"Generating digest for {entry['role']} entry...")
                entry["digest"] = self.digest_generator.generate_digest(entry, self.memory)
                
            # Add to conversation history file and memory
            self.add_to_conversation_history(entry)
            
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
                
            self.memory["conversation_history"].append(entry)
            self.logger.debug(f"Added {entry['role']} entry to conversation history")
            
            # Save to persist memory updates
            self.save_memory("add_conversation_entry")
            
            # Update RAG/embeddings indices for the new entry
            self.embeddings_manager.add_new_embeddings([entry])

            return True
            
        except Exception as e:
            self.logger.error(f"Error adding conversation entry: {str(e)}")
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
                self.logger.debug(f"Memory has {conversation_entries} conversations, compressing...")
                return self.update_memory({"operation": "update"})
            else:
                self.logger.debug(f"Memory has only {conversation_entries} conversations, compression not needed yet")
                return True
        except Exception as e:
            self.logger.error(f"Error updating memory with conversations: {str(e)}")
            return False
    
    def get_graph_context(self, query: str, max_entities: int = 5) -> str:
        """Get graph-based context for a query.
        
        Args:
            query: The query to find relevant graph context for
            max_entities: Maximum number of entities to include in context
            
        Returns:
            str: Formatted graph context string
        """
        if not self.enable_graph_memory or not self.graph_manager:
            return ""
        
        try:
            # Query the graph for relevant context
            context_results = self.graph_manager.query_for_context(query, max_results=max_entities)
            
            if not context_results:
                return ""
            
            # Format graph context for the prompt
            context_lines = []
            context_lines.append("Relevant entities and relationships:")
            
            for result in context_results:
                entity_name = result.get("name", "Unknown")
                entity_type = result.get("type", "unknown")
                description = result.get("description", "")
                connections = result.get("connections", [])
                
                # Add entity info
                entity_line = f"• {entity_name} ({entity_type})"
                if description:
                    entity_line += f": {description}"
                context_lines.append(entity_line)
                
                # Add key relationships
                if connections:
                    for conn in connections[:3]:  # Limit to top 3 connections
                        rel_type = conn.get("relationship", "related_to")
                        target = conn.get("target", "")
                        if target:
                            context_lines.append(f"  - {rel_type} {target}")
                
            return "\n".join(context_lines)
            
        except Exception as e:
            self.logger.warning(f"Error getting graph context: {e}")
            return ""

class AsyncMemoryManager(MemoryManager):
    """Asynchronous version of MemoryManager that handles digest generation and embeddings updates asynchronously."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_digests = {}  # guid -> entry
        self._pending_embeddings = set()  # set of guids
        self._pending_graph_updates = set()  # set of guids
        
    async def add_conversation_entry(self, entry: Dict[str, Any]) -> bool:
        """Add a conversation entry with asynchronous digest generation and embeddings update.
        
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
                self.logger.error("Error: Conversation entry must have 'content'")
                return False
                
            if "role" not in entry:
                self.logger.error("Error: Conversation entry must have 'role'")
                return False
                
            # Ensure GUID
            if "guid" not in entry:
                entry["guid"] = str(uuid.uuid4())
                
            # Ensure timestamp
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.now().isoformat()
            
            # Add to conversation history file and memory immediately
            self.add_to_conversation_history(entry)
            
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
                
            self.memory["conversation_history"].append(entry)
            self.logger.debug(f"Added {entry['role']} entry to conversation history")
            
            # Save to persist memory updates
            self.save_memory("add_conversation_entry")
            
            # Start async digest generation if not already present
            if "digest" not in entry:
                self.logger.debug(f"Starting async digest generation for {entry['role']} entry...")
                self._pending_digests[entry["guid"]] = entry
                asyncio.create_task(self._generate_digest_async(entry))
            else:
                # If digest exists, start embeddings and graph updates
                self._pending_embeddings.add(entry["guid"])
                if self.enable_graph_memory and self.graph_manager:
                    self._pending_graph_updates.add(entry["guid"])
                asyncio.create_task(self._update_embeddings_async(entry))

            return True
            
        except Exception as e:
            self.logger.error(f"Error adding conversation entry: {str(e)}")
            return False
    
    async def _generate_digest_async(self, entry: Dict[str, Any]) -> None:
        """Asynchronously generate digest for an entry."""
        try:
            # Generate digest
            entry["digest"] = self.digest_generator.generate_digest(entry, self.memory)
            
            # Update conversation history file with the digest
            self._update_conversation_history_entry(entry)
            
            # Remove from pending digests
            self._pending_digests.pop(entry["guid"], None)
            
            # Start embeddings and graph updates
            self._pending_embeddings.add(entry["guid"])
            if self.enable_graph_memory and self.graph_manager:
                self._pending_graph_updates.add(entry["guid"])
            await self._update_embeddings_async(entry)
            
            # Save memory to persist the digest
            self.save_memory("async_digest_generation")
            
        except Exception as e:
            self.logger.error(f"Error in async digest generation: {str(e)}")
    
    def _update_conversation_history_entry(self, entry: Dict[str, Any]) -> bool:
        """Update an existing entry in the conversation history file.
        
        Args:
            entry: Updated conversation entry with digest
            
        Returns:
            bool: True if entry was updated successfully
        """
        try:
            # Load current conversation history
            conversation_data = self._load_conversation_history()
            
            # Find and update the entry by GUID
            entry_guid = entry.get("guid")
            if not entry_guid:
                self.logger.error("Cannot update conversation history entry without GUID")
                return False
                
            # Find the entry to update
            updated = False
            for i, existing_entry in enumerate(conversation_data["entries"]):
                if existing_entry.get("guid") == entry_guid:
                    conversation_data["entries"][i] = entry
                    updated = True
                    break
            
            if not updated:
                self.logger.warning(f"Could not find conversation history entry with GUID {entry_guid} to update")
                return False
            
            # Save updated history
            success = self._save_conversation_history(conversation_data)
            if success:
                self.logger.debug(f"Updated conversation history entry {entry_guid} with digest")
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating conversation history entry: {str(e)}")
            return False
    
    async def _update_embeddings_async(self, entry: Dict[str, Any]) -> None:
        """Asynchronously update embeddings and graph memory for an entry."""
        try:
            # Update embeddings
            self.embeddings_manager.add_new_embeddings([entry])
            
            # Remove from pending embeddings
            self._pending_embeddings.discard(entry["guid"])
            
            # Update graph memory if enabled
            if self.enable_graph_memory and self.graph_manager and entry["guid"] in self._pending_graph_updates:
                await self._update_graph_memory_async(entry)
                self._pending_graph_updates.discard(entry["guid"])
            
        except Exception as e:
            self.logger.error(f"Error in async embeddings/graph update: {str(e)}")
    
    def get_pending_operations(self) -> Dict[str, Any]:
        """Get information about pending async operations.
        
        Returns:
            Dict with counts of pending digests, embeddings, and graph updates
        """
        return {
            "pending_digests": len(self._pending_digests),
            "pending_embeddings": len(self._pending_embeddings),
            "pending_graph_updates": len(self._pending_graph_updates)
        }
    
    def has_pending_operations(self) -> bool:
        """Check if there are any pending async operations.
        
        Returns:
            bool: True if there are pending operations
        """
        return bool(self._pending_digests or self._pending_embeddings or self._pending_graph_updates)
    
    async def wait_for_pending_operations(self) -> None:
        """Wait for all pending async operations to complete."""
        while self._pending_digests or self._pending_embeddings or self._pending_graph_updates:
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
