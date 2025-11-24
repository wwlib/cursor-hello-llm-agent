#!/usr/bin/env python3
"""
Standalone GraphManager Process

A standalone background process for handling computationally intensive graph operations
(entity/relationship extraction, embeddings). Runs independently from the main agent
for improved responsiveness.

Key Features:
- File-based communication via conversation_queue.jsonl
- Processes conversation entries asynchronously
- Atomic updates to graph files
- Error recovery and crash resilience
- Graceful shutdown handling
"""

import asyncio
import json
import os
import sys
import argparse
import logging
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import filelock

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.graph_memory.graph_manager import GraphManager
from examples.domain_configs import CONFIG_MAP


class StandaloneGraphManager:
    """Standalone GraphManager process for background graph operations."""
    
    def __init__(self, storage_path: str, domain_config: Dict[str, Any], 
                 llm_service, embeddings_manager):
        """Initialize standalone GraphManager.
        
        Args:
            storage_path: Directory path for graph storage
            domain_config: Domain-specific configuration
            llm_service: LLM service instance
            embeddings_manager: Embeddings manager instance
        """
        self.storage_path = storage_path
        self.domain_config = domain_config
        self.llm_service = llm_service
        self.embeddings_manager = embeddings_manager
        
        # File paths
        self.queue_file = os.path.join(storage_path, "conversation_queue.jsonl")
        self.lock_file = self.queue_file + ".lock"
        self.metadata_file = os.path.join(storage_path, "graph_metadata.json")
        
        # Processing state
        self.is_running = False
        self.last_processed_guid = None
        self.processed_count = 0
        
        # Setup logging
        self.setup_logging()
        
        # Initialize GraphManager
        self.graph_manager = GraphManager(
            storage_path=storage_path,
            embeddings_manager=embeddings_manager,
            llm_service=llm_service,
            domain_config=domain_config,
            logger=self.logger,
            memory_guid="standalone"
        )
        
        self.logger.info(f"Initialized StandaloneGraphManager with storage: {storage_path}")
    
    def setup_logging(self):
        """Setup dedicated logging for standalone process."""
        log_file = os.path.join(self.storage_path, "graph_manager.log")
        
        # Create logger
        self.logger = logging.getLogger("standalone_graph_manager")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.propagate = False
    
    def load_processing_state(self) -> Dict[str, Any]:
        """Load processing state for recovery."""
        try:
            processing_state_file = os.path.join(self.storage_path, "processing_state.json")
            if os.path.exists(processing_state_file):
                with open(processing_state_file, 'r') as f:
                    state = json.load(f)
                self.last_processed_guid = state.get("last_processed_guid")
                self.processed_count = state.get("processed_count", 0)
                self.logger.info(f"Loaded processing state: last_guid={self.last_processed_guid}, count={self.processed_count}")
                return state
        except Exception as e:
            self.logger.warning(f"Could not load processing state: {e}")
        
        return {
            "last_processed_guid": None,
            "processed_count": 0,
            "started_at": datetime.now().isoformat()
        }
    
    def save_processing_state(self):
        """Save processing state separately from graph metadata."""
        try:
            processing_state_file = os.path.join(self.storage_path, "processing_state.json")
            processing_state = {
                "last_processed_guid": self.last_processed_guid,
                "processed_count": self.processed_count,
                "last_updated": datetime.now().isoformat()
            }
            
            # Atomic write
            temp_file = processing_state_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(processing_state, f, indent=2)
            os.rename(temp_file, processing_state_file)
            
            self.logger.debug(f"Saved processing state: processed {self.processed_count} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to save processing state: {e}")
    
    def read_queue_entries(self) -> list:
        """Read conversation queue entries from file."""
        entries = []
        
        if not os.path.exists(self.queue_file):
            return entries
        
        try:
            with filelock.FileLock(self.lock_file, timeout=10):
                with open(self.queue_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                entries.append(entry)
                            except json.JSONDecodeError as e:
                                self.logger.warning(f"Invalid JSON in queue: {e}")
                                continue
        except filelock.Timeout:
            self.logger.warning("Could not acquire lock for reading queue")
        except Exception as e:
            self.logger.error(f"Error reading queue: {e}")
        
        return entries
    
    def clear_processed_entries(self, processed_guids: list):
        """Remove processed entries from queue file."""
        if not processed_guids:
            return
        
        try:
            with filelock.FileLock(self.lock_file, timeout=10):
                # Read all entries
                remaining_entries = []
                if os.path.exists(self.queue_file):
                    with open(self.queue_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    entry = json.loads(line)
                                    if entry.get("conversation_guid") not in processed_guids:
                                        remaining_entries.append(entry)
                                except json.JSONDecodeError:
                                    continue
                
                # Write remaining entries back
                with open(self.queue_file, 'w') as f:
                    for entry in remaining_entries:
                        f.write(json.dumps(entry) + '\n')
                
                self.logger.debug(f"Cleared {len(processed_guids)} processed entries from queue")
                
        except filelock.Timeout:
            self.logger.warning("Could not acquire lock for clearing queue")
        except Exception as e:
            self.logger.error(f"Error clearing queue: {e}")
    
    async def process_queue_batch(self, max_batch_size: int = 5) -> int:
        """Process a batch of queue entries."""
        entries = self.read_queue_entries()
        
        if not entries:
            return 0
        
        # Filter out already processed entries if we have recovery info
        if self.last_processed_guid:
            # Find the index of last processed entry
            last_index = -1
            for i, entry in enumerate(entries):
                if entry.get("conversation_guid") == self.last_processed_guid:
                    last_index = i
                    break
            
            if last_index >= 0:
                entries = entries[last_index + 1:]
        
        if not entries:
            return 0
        
        # Process batch
        batch = entries[:max_batch_size]
        processed_guids = []
        
        self.logger.info(f"Processing batch of {len(batch)} entries")
        
        for entry in batch:
            try:
                conversation_guid = entry.get("conversation_guid")
                conversation_text = entry.get("conversation_text", "")
                digest_text = entry.get("digest_text", "")
                
                self.logger.debug(f"Processing conversation: {conversation_guid}")
                
                # Process with GraphManager
                result = await self.graph_manager.process_conversation_entry_with_resolver_async(
                    conversation_text=conversation_text,
                    digest_text=digest_text,
                    conversation_guid=conversation_guid
                )
                
                if result and not result.get("error"):
                    entities_count = len(result.get("entities", []))
                    relationships_count = len(result.get("relationships", []))
                    self.logger.info(f"Processed {conversation_guid}: {entities_count} entities, {relationships_count} relationships")
                    
                    processed_guids.append(conversation_guid)
                    self.last_processed_guid = conversation_guid
                    self.processed_count += 1
                else:
                    self.logger.error(f"Failed to process {conversation_guid}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.logger.error(f"Error processing entry: {e}")
                # Continue processing other entries
                continue
        
        # Clear processed entries from queue
        self.clear_processed_entries(processed_guids)
        
        # Save graph metadata (total_nodes, total_edges) via GraphManager
        if processed_guids:
            await self.graph_manager._save_graph_async()
        
        # Save processing state separately
        self.save_processing_state()
        
        return len(processed_guids)
    
    async def run(self):
        """Main processing loop."""
        self.logger.info("Starting standalone GraphManager process")
        self.is_running = True
        
        # Load metadata for recovery
        self.load_processing_state()
        
        try:
            while self.is_running:
                try:
                    processed_count = await self.process_queue_batch()
                    
                    if processed_count > 0:
                        self.logger.debug(f"Processed {processed_count} entries")
                        # Continue processing without delay if there might be more
                        continue
                    else:
                        # No entries to process, wait before checking again
                        await asyncio.sleep(2.0)
                        
                except asyncio.CancelledError:
                    self.logger.info("Processing cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Error in processing loop: {e}")
                    await asyncio.sleep(5.0)  # Wait before retrying
        
        finally:
            self.is_running = False
            self.save_processing_state()
            self.logger.info("Standalone GraphManager process stopped")
    
    def stop(self):
        """Stop the processing loop."""
        self.logger.info("Stopping standalone GraphManager process")
        self.is_running = False


def setup_signal_handlers(standalone_manager):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        standalone_manager.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Standalone GraphManager Process")
    parser.add_argument("--storage-path", required=True, help="Path to graph storage directory")
    parser.add_argument("--config", default="dnd", choices=CONFIG_MAP.keys(), 
                       help="Domain configuration to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Validate storage path
    if not os.path.exists(args.storage_path):
        print(f"Error: Storage path does not exist: {args.storage_path}")
        sys.exit(1)
    
    # Get domain config
    domain_config = CONFIG_MAP.get(args.config)
    if not domain_config:
        print(f"Error: Unknown configuration: {args.config}")
        sys.exit(1)
    
    print(f"Starting GraphManager process with config: {args.config}")
    print(f"Storage path: {args.storage_path}")
    
    try:
        # Initialize LLM service
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "gemma3")
        embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
        
        llm_config = {
            "base_url": base_url,
            "model": model,
            "temperature": 0.1,
            "stream": False,
            "debug": args.verbose,
            "console_output": False
        }
        
        llm_service = OllamaService(llm_config)
        
        # Initialize embeddings manager
        embeddings_config = {
            "base_url": base_url,
            "model": embed_model,
            "debug": args.verbose,
            "console_output": False
        }
        
        embeddings_llm_service = OllamaService(embeddings_config)
        
        # Create embeddings file path
        embeddings_file = os.path.join(args.storage_path, "graph_memory_embeddings.jsonl")
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=embeddings_llm_service
        )
        
        # Initialize standalone manager
        standalone_manager = StandaloneGraphManager(
            storage_path=args.storage_path,
            domain_config=domain_config,
            llm_service=llm_service,
            embeddings_manager=embeddings_manager
        )
        
        # Setup signal handlers
        setup_signal_handlers(standalone_manager)
        
        # Run the process
        asyncio.run(standalone_manager.run())
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()