"""Simplified Memory Manager for Agent System

Clean, focused implementation with only essential functionality.
Removed obsolete graph processing code and simplified architecture.

Core Features:
- Memory persistence and GUID management (inherited from BaseMemoryManager)
- Digest generation for conversation segmentation
- RAG-enhanced query processing with embeddings
- Simple graph memory integration via queue_writer
- Async processing for digests and embeddings
- Memory compression when needed

Architecture:
- Extends BaseMemoryManager for core persistence
- Uses DigestGenerator for memory analysis and segmentation  
- Uses EmbeddingsManager for semantic search
- Uses RAGManager for context-enhanced queries
- Uses QueueWriter for simple graph memory integration
- Uses MemoryCompressor for automatic memory management
"""

from typing import Any, Dict, Optional, List
import json
import os
import uuid
import asyncio
import logging
from datetime import datetime

from src.utils.logging_config import LoggingConfig
from .base_memory_manager import BaseMemoryManager
from .digest_generator import DigestGenerator
from .memory_compressor import MemoryCompressor
from .data_preprocessor import DataPreprocessor
from .embeddings_manager import EmbeddingsManager
from .rag_manager import RAGManager
from .graph_memory.queue_writer import QueueWriter
from .graph_memory.standalone_graph_queries import StandaloneGraphQueries

# Memory filtering constants
DEFAULT_COMPRESSION_IMPORTANCE_THRESHOLD = 3
DEFAULT_RAG_IMPORTANCE_THRESHOLD = 3
DEFAULT_EMBEDDINGS_IMPORTANCE_THRESHOLD = 3

class MemoryManager(BaseMemoryManager):
    """Simplified LLM-driven memory manager with clean architecture.
    
    Focuses on core functionality without the bloat of obsolete background processing.
    Integrates with standalone graph processing via simple queue writer.
    """

    def __init__(self, memory_guid: str, memory_file: str = "memory.json", 
                 domain_config: Optional[Dict[str, Any]] = None, 
                 llm_service = None, digest_llm_service = None, embeddings_llm_service = None, 
                 max_recent_conversation_entries: int = 8, 
                 importance_threshold: int = DEFAULT_COMPRESSION_IMPORTANCE_THRESHOLD,
                 verbose: bool = False, logger=None, **kwargs):
        """Initialize the MemoryManager with essential services only.
        
        Args:
            memory_guid: Required GUID to identify this memory instance
            memory_file: Path to the JSON file for persistent storage  
            domain_config: Domain-specific configuration
            llm_service: Service for general LLM operations (required)
            digest_llm_service: Service for digest generation (optional, falls back to llm_service)
            embeddings_llm_service: Service for embeddings/RAG (optional, falls back to llm_service)
            max_recent_conversation_entries: Max entries before compression
            importance_threshold: Threshold for segment importance (1-5 scale)
            verbose: Enable verbose status messages
            logger: Optional logger instance
            **kwargs: Additional arguments (ignored for compatibility)
        """
        if llm_service is None:
            raise ValueError("llm_service is required for MemoryManager")
            
        # Initialize base class
        super().__init__(memory_guid, memory_file, domain_config, logger=logger)
        
        # Store LLM services
        self.llm = llm_service
        self.digest_llm = digest_llm_service or llm_service
        self.embeddings_llm = embeddings_llm_service or llm_service
        
        # Initialize verbose handler
        self.verbose = verbose
        if verbose:
            from src.utils.verbose_status import get_verbose_handler
            self.verbose_handler = get_verbose_handler(enabled=True)
        else:
            self.verbose_handler = None
        
        # Configuration
        self.max_recent_conversation_entries = max_recent_conversation_entries
        self.importance_threshold = importance_threshold
        
        # Initialize async operation tracking
        self._pending_digests = {}  # guid -> entry
        self._pending_embeddings = set()  # set of guids
        
        # Load templates
        self._load_templates()
        
        # Initialize core components
        domain_name = self.domain_config.get("domain_name", "general") if self.domain_config else "general"
        self.digest_generator = DigestGenerator(self.digest_llm, domain_name=domain_name, 
                                              domain_config=self.domain_config, logger=logger)
        self.memory_compressor = MemoryCompressor(self.llm, importance_threshold, logger=logger)
        
        # Initialize embeddings manager
        embeddings_file = os.path.splitext(memory_file)[0] + "_embeddings.jsonl"
        self.embeddings_manager = EmbeddingsManager(embeddings_file, self.embeddings_llm, logger=logger)
        
        # Initialize graph memory components (always attempt, fail gracefully)
        self.graph_queue_writer = None
        self.graph_queries = None
        try:
            self._setup_graph_memory_integration()
        except Exception as e:
            self.logger.warning(f"Graph components not available: {e}")
                
        # Initialize RAG manager with optional graph queries
        self.rag_manager = RAGManager(
            llm_service=self.embeddings_llm, 
            embeddings_manager=self.embeddings_manager, 
            graph_queries=self.graph_queries,
            logger=logger
        )
        
        # Ensure memory has a GUID
        self._ensure_memory_guid()
        
        self.logger.debug(f"MemoryManager initialized: max_entries={max_recent_conversation_entries}, "
                         f"importance_threshold={importance_threshold}")

    def _setup_graph_memory_integration(self):
        """Set up simple graph memory integration via queue writer and queries."""
        # Create graph storage path
        memory_dir = os.path.dirname(self.memory_file) or "."
        memory_base = os.path.basename(self.memory_file).split(".")[0]
        graph_storage_path = os.path.join(memory_dir, f"{memory_base}_graph_data")
        os.makedirs(graph_storage_path, exist_ok=True)
        
        # Create logger for graph components
        graph_logger = self._create_graph_logger(memory_dir, memory_base)
        
        # Create embeddings manager for graph memory
        graph_embeddings_file = os.path.join(graph_storage_path, "graph_memory_embeddings.jsonl")
        graph_embeddings_manager = EmbeddingsManager(
            embeddings_file=graph_embeddings_file,
            llm_service=self.embeddings_llm,
            logger=graph_logger
        )
        
        # Initialize simple queue writer for standalone graph process
        self.graph_queue_writer = QueueWriter(
            storage_path=graph_storage_path,
            logger=graph_logger
        )
        
        # Initialize graph queries for reading processed data
        self.graph_queries = StandaloneGraphQueries(
            storage_path=graph_storage_path,
            embeddings_manager=graph_embeddings_manager,
            logger=graph_logger
        )
        
        self.logger.debug(f"Graph memory integration initialized with storage: {graph_storage_path}")

    def _create_graph_logger(self, memory_dir: str, memory_base: str) -> logging.Logger:
        """Create a simple logger for graph operations."""
        graph_logger = LoggingConfig.get_component_file_logger(self.memory_guid, "graph_memory", log_to_console=False)
        return graph_logger

        # logger_name = f"graph_memory.{self.memory_guid}"
        # graph_logger = logging.getLogger(logger_name)
        
        # if graph_logger.handlers:
        #     return graph_logger
            
        # graph_logger.setLevel(logging.DEBUG)
        
        # # Create session logs directory
        # logs_base_dir = self._get_logs_base_dir(memory_dir)
        # session_logs_dir = os.path.join(logs_base_dir, "logs", self.memory_guid)
        # os.makedirs(session_logs_dir, exist_ok=True)
        
        # # Create log file
        # log_file_path = os.path.join(session_logs_dir, "graph_memory.log")
        # file_handler = logging.FileHandler(log_file_path)
        # file_handler.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        # file_handler.setFormatter(formatter)
        # graph_logger.addHandler(file_handler)
        # graph_logger.propagate = False
        
        # return graph_logger

    def _get_logs_base_dir(self, memory_dir: str) -> str:
        """Get the base directory for logs."""
        if memory_dir and memory_dir != ".":
            parent_dir = os.path.dirname(memory_dir)
            if parent_dir and os.path.basename(parent_dir) in ["standard", "simple", "sync"]:
                grandparent_dir = os.path.dirname(parent_dir)
                return grandparent_dir if grandparent_dir else "."
            else:
                return os.path.dirname(memory_dir) if memory_dir != "." else "."
        return "."

    def _ensure_memory_guid(self):
        """Ensure memory has a valid GUID."""
        if not self.memory:
            if not self.memory_guid:
                self.memory_guid = str(uuid.uuid4())
                self.logger.debug(f"Generated new GUID: {self.memory_guid}")
            return
            
        # Use provided GUID, existing GUID, or generate new one
        if self.memory_guid:
            if "guid" in self.memory and self.memory["guid"] != self.memory_guid:
                self.logger.debug(f"Replacing existing memory GUID with provided GUID: {self.memory_guid}")
            self.memory["guid"] = self.memory_guid
        elif "guid" in self.memory:
            self.memory_guid = self.memory["guid"]
            self.logger.debug(f"Using existing memory GUID: {self.memory_guid}")
        else:
            self.memory_guid = str(uuid.uuid4())
            self.memory["guid"] = self.memory_guid
            self.logger.debug(f"Generated new GUID: {self.memory_guid}")

    def _load_templates(self) -> None:
        """Load prompt templates from files."""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = {}
        
        template_files = {"query": "query_memory.prompt"}
        
        for key, filename in template_files.items():
            path = os.path.join(template_dir, filename)
            try:
                with open(path, 'r') as f:
                    self.templates[key] = f.read().strip()
                self.logger.debug(f"Loaded template: {filename}")
            except Exception as e:
                self.logger.error(f"Error loading template {filename}: {str(e)}")
                raise Exception(f"Failed to load template: {filename}")

    def create_initial_memory(self, input_data: str) -> bool:
        """Create initial memory structure from domain data."""
        try:
            # Check if valid memory already exists
            if self.memory and all(key in self.memory for key in ["static_memory", "context", "conversation_history"]):
                self.logger.debug("Valid memory structure already exists")
                self._ensure_memory_guid()
                return True
            
            self.logger.debug("Creating initial memory structure...")

            # Preprocess input data
            if self.verbose_handler:
                with self.verbose_handler.operation("Preprocessing domain data", level=2):
                    data_preprocessor = DataPreprocessor(self.llm)
                    preprocessed_prose, preprocessed_segments = data_preprocessor.preprocess_data(input_data)
            else:
                data_preprocessor = DataPreprocessor(self.llm)
                preprocessed_prose, preprocessed_segments = data_preprocessor.preprocess_data(input_data)

            # Create system entry for initial data
            system_entry = {
                "guid": str(uuid.uuid4()),
                "role": "system",
                "content": input_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate digest
            if self.verbose_handler:
                with self.verbose_handler.operation("Generating digest for domain data", level=2):
                    initial_digest = self.digest_generator.generate_digest(system_entry, segments=preprocessed_segments)
                    system_entry["digest"] = initial_digest
            else:
                initial_digest = self.digest_generator.generate_digest(system_entry, segments=preprocessed_segments)
                system_entry["digest"] = initial_digest
            
            # Create static memory from digest
            static_memory = self._create_static_memory_from_digest(initial_digest)
            
            # Initialize memory structure
            now = datetime.now().isoformat()
            self.memory = {
                "guid": self.memory_guid,
                "memory_type": "standard",
                "static_memory": static_memory,
                "context": [],
                "metadata": {
                    "created_at": now,
                    "updated_at": now,
                    "version": "2.0.0",
                    "domain": self.domain_config.get("name", "general") if self.domain_config else "general"
                },
                "conversation_history": [system_entry]
            }
            
            # Save memory
            self.save_memory("create_initial_memory")
            self.add_to_conversation_history(system_entry)
            
            # Generate embeddings
            if self.verbose_handler:
                with self.verbose_handler.operation("Creating embeddings for semantic search", level=2):
                    self.embeddings_manager.add_new_embeddings([system_entry])
            else:
                self.embeddings_manager.add_new_embeddings([system_entry])

            # Queue graph processing if available
            if self.graph_queue_writer:
                self._queue_graph_processing(system_entry)

            self.logger.debug("Memory created and initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating initial memory: {str(e)}")
            return False

    def _create_static_memory_from_digest(self, digest: Dict[str, Any]) -> str:
        """Create static memory text from digest segments."""
        try:
            rated_segments = digest.get("rated_segments", [])
            if not rated_segments:
                self.logger.debug("No rated segments found in digest")
                return ""
            return "\n".join(segment.get("text", "") for segment in rated_segments)
        except Exception as e:
            self.logger.error(f"Error creating static memory from digest: {str(e)}")
            return ""

    def _queue_graph_processing(self, entry: Dict[str, Any]) -> None:
        """Queue entry for graph processing via queue writer."""
        try:
            if self.verbose_handler:
                self.verbose_handler.status("Queueing knowledge graph processing...", 2)
            
            # Extract text from digest segments if available
            entry_text = entry.get("content", "")
            digest = entry.get("digest", {})
            segments = digest.get("rated_segments", [])
            
            if segments:
                # Use important segments
                important_segments = [
                    seg for seg in segments 
                    if seg.get("importance", 0) >= DEFAULT_RAG_IMPORTANCE_THRESHOLD 
                    and seg.get("memory_worthy", True)
                    and seg.get("type") in ["information", "action"]
                ]
                if important_segments:
                    entry_text = " ".join([seg.get("text", "") for seg in important_segments])
            
            # Queue for processing
            success = self.graph_queue_writer.write_conversation_entry(
                conversation_text=entry_text,
                digest_text=entry.get("content", "")[:500],  # Limited context
                conversation_guid=entry.get("guid", "")
            )
            
            if success:
                self.logger.debug(f"Queued graph processing for entry {entry.get('guid', '')}")
                if self.verbose_handler:
                    self.verbose_handler.success("Graph processing queued", 0.001)
            else:
                self.logger.warning(f"Failed to queue graph processing for entry {entry.get('guid', '')}")
                
        except Exception as e:
            self.logger.error(f"Error queuing graph processing: {e}")

    def query_memory(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Query memory with RAG enhancement."""
        try:
            query = query_context.get("query", "")
            
            # Add user message to history immediately
            user_entry = {
                "guid": str(uuid.uuid4()),
                "role": "user", 
                "content": query,
                "timestamp": datetime.now().isoformat()
            }
            self.add_to_conversation_history(user_entry)
            if "conversation_history" not in self.memory:
                self.memory["conversation_history"] = []
            self.memory["conversation_history"].append(user_entry)
            self.save_memory("add_user_entry")
            
            # Format memory components
            static_memory_text = query_context.get("static_memory", "") or self._get_static_memory_text()
            previous_context_text = query_context.get("previous_context", "") or self._format_context_as_text()
            conversation_history_text = query_context.get("conversation_history", "") or self._format_conversation_history_as_text()
            
            # Get RAG context
            rag_context = query_context.get("rag_context")
            if not rag_context:
                if self.verbose_handler:
                    self.verbose_handler.status("Enhancing query with relevant context (RAG)...", 1)
                enhanced_context = self.rag_manager.enhance_memory_query(query_context)
                rag_context = enhanced_context.get("rag_context", "")
            
            # Get graph context if available
            graph_context = ""
            if self.graph_queries:
                try:
                    if self.verbose_handler:
                        self.verbose_handler.status("Retrieving graph context...", 1)
                    graph_context = self.get_graph_context(query)
                    if graph_context and self.verbose_handler:
                        self.verbose_handler.success("Retrieved graph context", level=2)
                except Exception as e:
                    self.logger.warning(f"Failed to get graph context: {e}")
                    graph_context = ""
            
            # Get domain instructions
            domain_instructions = query_context.get("domain_specific_prompt_instructions", "")
            if not domain_instructions and self.domain_config:
                domain_prompt = self.domain_config.get("domain_specific_prompt_instructions", "")
                domain_instructions = domain_prompt.get("query", "") if isinstance(domain_prompt, dict) else ""
            
            # Create prompt
            prompt = self.templates["query"].format(
                static_memory_text=static_memory_text,
                previous_context_text=previous_context_text,
                conversation_history_text=conversation_history_text,
                query=query,
                domain_specific_prompt_instructions=domain_instructions,
                rag_context=rag_context,
                graph_context=graph_context
            )
            
            # Generate response
            if self.verbose_handler:
                self.verbose_handler.status("Generating response with LLM...", 1)
            llm_response = self.llm.generate(prompt, options={"temperature": 0.7})
            
            # Add agent response to history
            agent_entry = {
                "guid": str(uuid.uuid4()),
                "role": "agent",
                "content": llm_response, 
                "timestamp": datetime.now().isoformat()
            }
            self.add_to_conversation_history(agent_entry)
            self.memory["conversation_history"].append(agent_entry)
            self.save_memory("add_agent_entry")
            
            # Start async processing for both entries
            asyncio.create_task(self._process_entry_async(user_entry))
            asyncio.create_task(self._process_entry_async(agent_entry))
            
            # Check if memory compression is needed
            if len(self.memory["conversation_history"]) > self.max_recent_conversation_entries:
                asyncio.create_task(self._compress_memory_async())
            
            return {"response": llm_response}
            
        except Exception as e:
            self.logger.error(f"Error in query_memory: {str(e)}")
            return {"response": f"Error processing query: {str(e)}", "error": str(e)}

    async def _process_entry_async(self, entry: Dict[str, Any]) -> None:
        """Process entry asynchronously (digest, embeddings, graph)."""
        try:
            # Generate digest if not present
            if "digest" not in entry:
                self.logger.debug(f"Generating digest for {entry['role']} entry...")
                entry["digest"] = self.digest_generator.generate_digest(entry, self.memory)
                
                # Update conversation history file with the digest
                self.update_conversation_history_entry(entry)
                
                # Also update in-memory conversation history
                if "conversation_history" in self.memory:
                    for i, hist_entry in enumerate(self.memory["conversation_history"]):
                        if hist_entry.get("guid") == entry.get("guid"):
                            self.memory["conversation_history"][i] = entry
                            break
                
                self.save_memory("async_digest_generation")
            
            # Update embeddings
            self.logger.debug(f"Updating embeddings for {entry['role']} entry...")
            self.embeddings_manager.add_new_embeddings([entry])
            
            # Queue graph processing if available
            if self.graph_queue_writer:
                await self._queue_graph_processing_async(entry)
                
        except Exception as e:
            self.logger.error(f"Error in async entry processing: {str(e)}")

    async def _queue_graph_processing_async(self, entry: Dict[str, Any]) -> None:
        """Queue graph processing asynchronously."""
        try:
            entry_text = entry.get("content", "")
            digest_text = ""  # Could extract from digest if needed
            conversation_guid = entry.get("guid", "")
            
            success = self.graph_queue_writer.write_conversation_entry(
                conversation_text=entry_text,
                digest_text=digest_text,
                conversation_guid=conversation_guid
            )
            
            if success:
                queue_size = self.graph_queue_writer.get_queue_size()
                self.logger.debug(f"Queued graph processing: entry_guid={conversation_guid}, queue_size={queue_size}")
            else:
                self.logger.warning(f"Failed to queue graph processing for entry {conversation_guid}")
                
        except Exception as e:
            self.logger.error(f"Error queuing async graph processing: {e}")

    async def _compress_memory_async(self) -> None:
        """Compress memory asynchronously when it gets too large."""
        try:
            self.logger.debug("Starting async memory compression...")
            
            conversation_history = self.memory.get("conversation_history", [])
            static_memory = self._get_static_memory_text()
            current_context = self.memory.get("context", [])
            
            compressed_state = await self.memory_compressor.compress_conversation_history_async(
                conversation_history=conversation_history,
                static_memory=static_memory,
                current_context=current_context
            )
            
            # Update memory with compressed state
            self.memory["conversation_history"] = compressed_state.get("conversation_history", conversation_history)
            self.memory["context"] = compressed_state.get("context", current_context)
            
            # Update metadata
            if "compressed_entries" not in self.memory.get("metadata", {}):
                self.memory.setdefault("metadata", {})["compressed_entries"] = []
            compressed_entries = compressed_state.get("compressed_entries", [])
            self.memory["metadata"]["compressed_entries"].extend(compressed_entries)
            self.memory["metadata"]["updated_at"] = datetime.now().isoformat()
            self.memory["metadata"]["compression_count"] = self.memory["metadata"].get("compression_count", 0) + 1
            
            self.save_memory("compress_memory_async")
            self.logger.debug(f"Async memory compression completed. Remaining entries: {len(self.memory['conversation_history'])}")
            
        except Exception as e:
            self.logger.error(f"Error in async memory compression: {str(e)}")

    def update_memory(self, update_context: Dict[str, Any]) -> bool:
        """Update memory by compressing conversation history."""
        try:
            if update_context.get("operation") != "update":
                return False
                
            self.logger.debug("Compressing conversation history...")
            
            conversation_history = self.memory.get("conversation_history", [])
            static_memory = self._get_static_memory_text()
            current_context = self.memory.get("context", [])
            
            compressed_state = self.memory_compressor.compress_conversation_history(
                conversation_history=conversation_history,
                static_memory=static_memory,
                current_context=current_context
            )
            
            # Update memory
            self.memory["conversation_history"] = compressed_state.get("conversation_history", conversation_history)
            self.memory["context"] = compressed_state.get("context", current_context)
            
            # Update metadata
            if "compressed_entries" not in self.memory.get("metadata", {}):
                self.memory.setdefault("metadata", {})["compressed_entries"] = []
            compressed_entries = compressed_state.get("compressed_entries", [])
            self.memory["metadata"]["compressed_entries"].extend(compressed_entries)
            self.memory["metadata"]["updated_at"] = datetime.now().isoformat()
            self.memory["metadata"]["compression_count"] = self.memory["metadata"].get("compression_count", 0) + 1
            
            self.save_memory("compress_conversation_history")
            self.logger.debug(f"Memory compression completed. Remaining entries: {len(self.memory['conversation_history'])}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating memory: {str(e)}")
            return False

    def _get_static_memory_text(self) -> str:
        """Get static memory as text."""
        if "static_memory" not in self.memory:
            return "No static memory available."
        static_memory = self.memory["static_memory"]
        return static_memory if static_memory else "Static memory is empty."

    def _format_context_as_text(self) -> str:
        """Format context as readable text."""
        if "context" not in self.memory or not self.memory["context"]:
            return "No context information available yet."
        
        context = self.memory["context"]
        result = []
        
        if isinstance(context, list):
            for item in context:
                text = item.get("text", "")
                if text:
                    result.append(text)
                    result.append("")
        elif isinstance(context, dict):
            for topic_name, items in context.items():
                result.append(f"TOPIC: {topic_name}")
                for item in items:
                    text = item.get("text", "")
                    attribution = item.get("attribution", "")
                    importance = item.get("importance", 3)
                    importance_str = "*" * importance
                    result.append(f"{importance_str} {text} [{attribution}]")
                result.append("")
        else:
            result.append("Context information available but format not recognized.")
        
        return "\n".join(result)

    def _format_conversation_history_as_text(self) -> str:
        """Format recent conversation history as readable text."""
        if "conversation_history" not in self.memory or not self.memory["conversation_history"]:
            return "No conversation history available."
        
        # Get recent entries
        recent_count = min(4, len(self.memory["conversation_history"]))
        recent_entries = self.memory["conversation_history"][-recent_count:]
        
        result = []
        for entry in recent_entries:
            role = entry.get("role", "unknown").upper()
            
            # Use digest segments if available, otherwise use content
            digest = entry.get("digest", {})
            segments = digest.get("rated_segments", [])
            
            if segments:
                content = " ".join(segment["text"] for segment in segments)
            else:
                content = entry.get("content", "")
                
            result.append(f"[{role}]: {content}")
            result.append("")
        
        return "\n".join(result)

    def get_graph_context(self, query: str, max_entities: int = 5) -> str:
        """Get graph-based context for a query using StandaloneGraphQueries."""
        if not self.graph_queries:
            return ""
        
        try:
            # Query for relevant context
            context_results = self.graph_queries.query_for_context(query, max_results=max_entities)
            
            if not context_results:
                return ""
            
            # Format context
            context_lines = ["Relevant entities and relationships:"]
            
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
                
                # Add relationships
                if connections:
                    for conn in connections[:3]:
                        rel_type = conn.get("relationship", "related_to")
                        target = conn.get("target", "")
                        if target:
                            context_lines.append(f"  - {rel_type} {target}")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            self.logger.warning(f"Error getting graph context: {e}")
            return ""

    # Async operation tracking methods for compatibility with agent
    def has_pending_operations(self) -> bool:
        """Check if there are pending async operations (agent-visible only)."""
        return bool(self._pending_digests or self._pending_embeddings)

    def get_pending_operations(self) -> Dict[str, Any]:
        """Get information about pending operations (agent-visible only)."""
        return {
            "pending_digests": len(self._pending_digests),
            "pending_embeddings": len(self._pending_embeddings)
        }

    async def wait_for_pending_operations(self, timeout: float = 60.0) -> None:
        """Wait for pending operations to complete (agent-visible only)."""
        start_time = asyncio.get_event_loop().time()
        
        while self._pending_digests or self._pending_embeddings:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                self.logger.warning(f"Timeout waiting for pending operations after {timeout}s")
                break
            await asyncio.sleep(0.2)

    # Optional methods for compatibility with agent_usage_example.py
    def get_graph_processing_status(self) -> Dict[str, Any]:
        """Get simple graph processing status."""
        if not self.graph_queue_writer:
            return {"available": False, "message": "Graph processing not available"}
        
        try:
            queue_size = self.graph_queue_writer.get_queue_size()
            return {
                "available": True,
                "queue_size": queue_size,
                "status": "active" if queue_size > 0 else "idle"
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def process_background_graph_queue(self, max_tasks: int = 1) -> Dict[str, Any]:
        """Compatibility method for manual graph processing - not implemented in simplified version."""
        return {
            "processed": 0,
            "message": "Background graph processing handled by standalone process"
        }