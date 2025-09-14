"""
Simple Graph Processor

Event-driven background processing system for graph memory updates.
Processes tasks immediately when the system has capacity, with no artificial delays
or complex configuration.

Key Features:
- Event-driven processing (no polling/frequency)
- Simple concurrency control
- Immediate processing when system is idle
- All operations are fully async and non-blocking
"""

import asyncio
import time
from typing import Dict, Any, Optional
import logging


class SimpleGraphProcessor:
    """Simple event-driven processor for graph memory updates.
    
    Processes tasks immediately when the system has capacity, with simple
    concurrency control and no artificial delays.
    
    Features:
    - Event-driven processing (no polling)
    - Simple concurrency limits
    - Immediate processing when idle
    - Full async operation
    """
    
    def __init__(self, 
                 graph_manager,
                 max_concurrent_tasks: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the simple graph processor.
        
        Args:
            graph_manager: GraphManager instance for processing tasks
            max_concurrent_tasks: Maximum concurrent processing tasks (default: 3)
            logger: Logger instance for debugging
        """
        self.graph_manager = graph_manager
        self.max_concurrent_tasks = max_concurrent_tasks
        self.logger = logger or logging.getLogger(__name__)
        
        # Processing state
        self._task_queue = asyncio.Queue()
        self._active_tasks = set()
        self._is_running = False
        self._processor_task = None
        
        # Statistics
        self._total_processed = 0
        self._total_failed = 0
        self._processing_times = []
        
        self.logger.info(f"Initialized SimpleGraphProcessor: "
                        f"max_concurrent_tasks={max_concurrent_tasks}")
    
    async def start(self) -> None:
        """Start the background processing loop."""
        if self._is_running:
            self.logger.warning("Simple processor is already running")
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_continuously())
        self.logger.info("Started simple graph processing")
    
    async def stop(self) -> None:
        """Stop the background processing loop."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active tasks to complete
        while self._active_tasks:
            await asyncio.sleep(0.1)
        
        self.logger.info("Stopped simple graph processing")
    
    def _write_verbose_log(self, message: str):
        """Write verbose log message to graph storage directory if available."""
        try:
            if self.graph_manager and hasattr(self.graph_manager, '_write_verbose_graph_log'):
                self.graph_manager._write_verbose_graph_log(message)
            else:
                # Fallback to regular logger if graph manager not available
                self.logger.debug(message)
        except Exception as e:
            # Don't fail the main operation if logging fails
            self.logger.debug(f"Failed to write verbose log: {e}")
    
    async def add_task(self, 
                       conversation_text: str,
                       digest_text: str = "",
                       conversation_guid: str = None) -> None:
        """
        Add a graph processing task to the queue for immediate processing.
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            conversation_guid: GUID for tracking conversation mentions
        """
        self._write_verbose_log(f"[BACKGROUND_PROCESSOR] add_task called with GUID: {conversation_guid}")
        
        task_data = {
            "conversation_text": conversation_text,
            "digest_text": digest_text,
            "conversation_guid": conversation_guid,
            "queued_at": time.time()
        }
        
        self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Putting task in queue, current queue size: {self._task_queue.qsize()}")
        await self._task_queue.put(task_data)
        self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Task queued, new queue size: {self._task_queue.qsize()}")
        self.logger.debug(f"Queued graph processing task for conversation {conversation_guid or 'unknown'}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return {
            "is_running": self._is_running,
            "queue_size": self._task_queue.qsize(),
            "active_tasks": len(self._active_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "average_processing_time": (
                sum(self._processing_times) / len(self._processing_times) 
                if self._processing_times else 0.0
            )
        }
    
    async def _process_continuously(self) -> None:
        """Main processing loop that processes tasks as they arrive."""
        self.logger.info("Started continuous processing loop")
        self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Starting continuous processing loop, is_running: {self._is_running}")
        
        while self._is_running:
            try:
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Waiting for task, queue size: {self._task_queue.qsize()}")
                
                # Wait for a task to become available
                task_data = await self._task_queue.get()
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Got task from queue: {task_data.get('conversation_guid', 'unknown')}")
                
                # Wait for an available slot if at max concurrency
                while len(self._active_tasks) >= self.max_concurrent_tasks:
                    self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Waiting for available slot, active: {len(self._active_tasks)}, max: {self.max_concurrent_tasks}")
                    await asyncio.sleep(0.1)
                
                # Start processing immediately
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Starting task processing")
                processing_task = asyncio.create_task(self._process_task(task_data))
                self._active_tasks.add(processing_task)
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Task started, active tasks: {len(self._active_tasks)}")
                
                # Clean up completed tasks
                processing_task.add_done_callback(self._cleanup_task)
                
            except asyncio.CancelledError:
                self.logger.info("Continuous processing loop cancelled")
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Continuous processing loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in continuous processing loop: {e}")
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] ERROR in continuous processing loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    def _cleanup_task(self, task):
        """Clean up completed task and update statistics."""
        self._active_tasks.discard(task)
        
        # Update statistics based on task result
        try:
            # Task completed successfully if no exception
            task.result()  # This will raise if task failed
            self._total_processed += 1
        except Exception:
            self._total_failed += 1
    
    async def _process_task(self, task_data: Dict[str, Any]) -> None:
        """Process a single graph processing task."""
        start_time = time.time()
        conversation_guid = task_data.get("conversation_guid", "unknown")
        
        try:
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] _process_task starting for GUID: {conversation_guid}")
            
            # Extract task data
            conversation_text = task_data.get("conversation_text", "")
            digest_text = task_data.get("digest_text", "")
            
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Calling graph_manager.process_conversation_entry_with_resolver_async")
            
            # Process using GraphManager's async method with timeout to prevent hanging
            results = await asyncio.wait_for(
                self.graph_manager.process_conversation_entry_with_resolver_async(
                    conversation_text=conversation_text,
                    digest_text=digest_text,
                    conversation_guid=conversation_guid
                ), 
                timeout=300.0  # 5 minute timeout
            )
            
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Graph manager processing completed")
            
            # Log results
            if results and not results.get("error"):
                entities_count = len(results.get("entities", []))
                relationships_count = len(results.get("relationships", []))
                self.logger.debug(f"Graph processing completed: {entities_count} entities, {relationships_count} relationships")
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Success: {entities_count} entities, {relationships_count} relationships")
            else:
                self.logger.warning(f"Graph processing failed: {results.get('error', 'Unknown error')}")
                self._write_verbose_log(f"[BACKGROUND_PROCESSOR] ERROR: {results.get('error', 'Unknown error')}")
                raise Exception(f"Graph processing failed: {results.get('error', 'Unknown error')}")
            
            # Track processing time
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] Task completed successfully in {processing_time:.2f}s")
            
            # Keep only recent processing times (last 100)
            if len(self._processing_times) > 100:
                self._processing_times.pop(0)
            
            self.logger.debug(f"Processed graph task in {processing_time:.2f}s")
            
        except asyncio.TimeoutError:
            self.logger.error(f"Graph processing timed out for GUID: {conversation_guid} after 5 minutes")
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] TIMEOUT ERROR for GUID: {conversation_guid}")
            raise  # Re-raise so cleanup_task can track the failure
        except Exception as e:
            self.logger.error(f"Error processing graph task for GUID {conversation_guid}: {e}")
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] ERROR for GUID {conversation_guid}: {e}")
            import traceback
            self._write_verbose_log(f"[BACKGROUND_PROCESSOR] ERROR TRACEBACK: {traceback.format_exc()}")
            raise  # Re-raise so cleanup_task can track the failure
