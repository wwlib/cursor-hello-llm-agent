"""
Background Graph Processor

Configurable background processing system for graph memory updates.
Allows graph memory to be processed asynchronously without blocking user interactions,
while still providing enhanced context when available.

Key Features:
- Configurable processing frequency and batch sizes
- Priority-based processing queue
- Real-time status monitoring
- Graceful degradation when processing is behind
- Performance metrics and optimization
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from collections import deque, defaultdict


class ProcessingPriority(Enum):
    """Priority levels for graph processing tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class GraphProcessingTask:
    """Represents a single graph processing task."""
    entry_id: str
    entry_data: Dict[str, Any]
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    processing_mode: str = "balanced"  # speed, balanced, comprehensive


@dataclass
class ProcessingStats:
    """Statistics for graph processing performance."""
    total_processed: int = 0
    total_failed: int = 0
    average_processing_time: float = 0.0
    queue_size: int = 0
    last_processing_time: Optional[float] = None
    processing_rate: float = 0.0  # tasks per minute
    backlog_age: float = 0.0  # age of oldest unprocessed task


class BackgroundGraphProcessor:
    """Configurable background processor for graph memory updates.
    
    This processor manages a queue of graph processing tasks and processes them
    in the background according to configurable schedules and priorities.
    
    Features:
    - Configurable processing frequency (every N seconds)
    - Batch processing with configurable batch sizes
    - Priority-based task scheduling
    - Real-time performance monitoring
    - Graceful handling of processing delays
    - Status callbacks for monitoring
    """
    
    def __init__(self, 
                 graph_manager,
                 processing_frequency: float = 30.0,  # seconds between processing cycles
                 batch_size: int = 5,
                 max_queue_size: int = 100,
                 enable_priority_processing: bool = True,
                 status_callback: Optional[Callable] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the background graph processor.
        
        Args:
            graph_manager: GraphManager instance for processing tasks
            processing_frequency: Seconds between processing cycles (default: 30)
            batch_size: Maximum tasks to process in one batch (default: 5)
            max_queue_size: Maximum tasks to keep in queue (default: 100)
            enable_priority_processing: Whether to use priority-based scheduling
            status_callback: Optional callback for status updates
            logger: Logger instance for debugging
        """
        self.graph_manager = graph_manager
        self.processing_frequency = processing_frequency
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.enable_priority_processing = enable_priority_processing
        self.status_callback = status_callback
        self.logger = logger or logging.getLogger(__name__)
        
        # Processing state
        self._task_queue = deque()
        self._processing_stats = ProcessingStats()
        self._is_running = False
        self._processing_task = None
        self._lock = threading.Lock()
        
        # Configuration
        self._processing_modes = {
            "speed": {"batch_size": 10, "timeout": 5.0},
            "balanced": {"batch_size": 5, "timeout": 15.0},
            "comprehensive": {"batch_size": 3, "timeout": 30.0}
        }
        
        # Performance tracking
        self._processing_times = deque(maxlen=100)  # Keep last 100 processing times
        self._last_processing_cycle = 0.0
        
        self.logger.info(f"Initialized BackgroundGraphProcessor: "
                        f"frequency={processing_frequency}s, batch_size={batch_size}, "
                        f"max_queue={max_queue_size}")
    
    def start(self) -> None:
        """Start the background processing loop."""
        if self._is_running:
            self.logger.warning("Background processor is already running")
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        self.logger.info("Started background graph processing")
        
        if self.status_callback:
            self.status_callback("started", {"frequency": self.processing_frequency})
    
    def stop(self) -> None:
        """Stop the background processing loop."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
        
        self.logger.info("Stopped background graph processing")
        
        if self.status_callback:
            self.status_callback("stopped", {"queue_size": len(self._task_queue)})
    
    def add_task(self, 
                 entry_id: str, 
                 entry_data: Dict[str, Any],
                 priority: ProcessingPriority = ProcessingPriority.NORMAL,
                 processing_mode: str = "balanced") -> bool:
        """
        Add a graph processing task to the queue.
        
        Args:
            entry_id: Unique identifier for the entry
            entry_data: Entry data to process
            priority: Processing priority
            processing_mode: Processing mode (speed, balanced, comprehensive)
            
        Returns:
            True if task was added, False if queue is full
        """
        with self._lock:
            if len(self._task_queue) >= self.max_queue_size:
                self.logger.warning(f"Task queue full ({self.max_queue_size}), dropping task {entry_id}")
                return False
            
            task = GraphProcessingTask(
                entry_id=entry_id,
                entry_data=entry_data,
                priority=priority,
                processing_mode=processing_mode
            )
            
            if self.enable_priority_processing:
                # Insert task based on priority
                inserted = False
                for i, existing_task in enumerate(self._task_queue):
                    if task.priority.value > existing_task.priority.value:
                        self._task_queue.insert(i, task)
                        inserted = True
                        break
                
                if not inserted:
                    self._task_queue.append(task)
            else:
                self._task_queue.append(task)
            
            self.logger.debug(f"Added task {entry_id} with priority {priority.name}")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        with self._lock:
            current_time = time.time()
            
            # Calculate backlog age
            backlog_age = 0.0
            if self._task_queue:
                oldest_task = self._task_queue[0]
                backlog_age = current_time - oldest_task.created_at
            
            # Calculate processing rate
            processing_rate = 0.0
            if self._processing_times:
                recent_times = [t for t in self._processing_times if current_time - t < 300]  # Last 5 minutes
                processing_rate = len(recent_times) / 5.0  # tasks per minute
            
            return {
                "is_running": self._is_running,
                "queue_size": len(self._task_queue),
                "total_processed": self._processing_stats.total_processed,
                "total_failed": self._processing_stats.total_failed,
                "average_processing_time": self._processing_stats.average_processing_time,
                "processing_rate": processing_rate,
                "backlog_age": backlog_age,
                "last_processing_time": self._processing_stats.last_processing_time,
                "processing_frequency": self.processing_frequency,
                "batch_size": self.batch_size
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get detailed queue status information."""
        with self._lock:
            priority_counts = defaultdict(int)
            mode_counts = defaultdict(int)
            
            for task in self._task_queue:
                priority_counts[task.priority.name] += 1
                mode_counts[task.processing_mode] += 1
            
            return {
                "total_tasks": len(self._task_queue),
                "priority_distribution": dict(priority_counts),
                "mode_distribution": dict(mode_counts),
                "oldest_task_age": (
                    time.time() - self._task_queue[0].created_at 
                    if self._task_queue else 0.0
                )
            }
    
    async def _processing_loop(self) -> None:
        """Main processing loop that runs in the background."""
        self.logger.info("Started background processing loop")
        
        while self._is_running:
            try:
                start_time = time.time()
                
                # Process available tasks
                processed_count = await self._process_batch()
                
                if processed_count > 0:
                    self.logger.debug(f"Processed {processed_count} tasks in background")
                
                # Update statistics
                self._update_stats(processed_count, time.time() - start_time)
                
                # Wait for next processing cycle
                await asyncio.sleep(self.processing_frequency)
                
            except asyncio.CancelledError:
                self.logger.info("Background processing loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in background processing loop: {e}")
                await asyncio.sleep(min(self.processing_frequency, 10.0))  # Shorter sleep on error
    
    async def _process_batch(self) -> int:
        """Process a batch of tasks from the queue."""
        if not self._task_queue:
            return 0
        
        # Get tasks to process
        tasks_to_process = []
        with self._lock:
            batch_size = min(self.batch_size, len(self._task_queue))
            for _ in range(batch_size):
                if self._task_queue:
                    tasks_to_process.append(self._task_queue.popleft())
        
        if not tasks_to_process:
            return 0
        
        # Process tasks
        processed_count = 0
        for task in tasks_to_process:
            try:
                success = await self._process_single_task(task)
                if success:
                    processed_count += 1
                    self._processing_stats.total_processed += 1
                else:
                    # Retry logic
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        with self._lock:
                            self._task_queue.append(task)  # Re-queue for retry
                        self.logger.warning(f"Retrying task {task.entry_id} (attempt {task.retry_count})")
                    else:
                        self._processing_stats.total_failed += 1
                        self.logger.error(f"Failed to process task {task.entry_id} after {task.max_retries} retries")
                
            except Exception as e:
                self.logger.error(f"Error processing task {task.entry_id}: {e}")
                self._processing_stats.total_failed += 1
        
        return processed_count
    
    async def _process_single_task(self, task: GraphProcessingTask) -> bool:
        """Process a single graph processing task."""
        try:
            # Get processing configuration for this mode
            mode_config = self._processing_modes.get(task.processing_mode, self._processing_modes["balanced"])
            
            # Process with timeout
            processing_start = time.time()
            
            # Use the GraphManager's conversation processing method
            # Extract conversation text and digest from entry data
            conversation_text = task.entry_data.get("content", "")
            digest_text = task.entry_data.get("digest", {}).get("summary", "") if isinstance(task.entry_data.get("digest"), dict) else ""
            conversation_guid = task.entry_data.get("guid", "")
            
            # Process the conversation entry using GraphManager's method
            # This method handles all the entity extraction and relationship processing
            results = self.graph_manager.process_conversation_entry_with_resolver(
                conversation_text=conversation_text,
                digest_text=digest_text,
                conversation_guid=conversation_guid
            )
            
            # Log the results
            if results and not results.get("error"):
                entities_count = len(results.get("entities", []))
                relationships_count = len(results.get("relationships", []))
                self.logger.debug(f"Graph processing completed: {entities_count} entities, {relationships_count} relationships")
            else:
                self.logger.warning(f"Graph processing failed: {results.get('error', 'Unknown error')}")
            
            processing_time = time.time() - processing_start
            
            # Track processing time
            self._processing_times.append(time.time())
            
            self.logger.debug(f"Processed task {task.entry_id} in {processing_time:.2f}s "
                            f"(mode: {task.processing_mode})")
            
            return True
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Task {task.entry_id} timed out after {mode_config['timeout']}s")
            return False
        except Exception as e:
            self.logger.error(f"Error processing task {task.entry_id}: {e}")
            return False
    
    def _update_stats(self, processed_count: int, cycle_time: float) -> None:
        """Update processing statistics."""
        if processed_count > 0:
            self._processing_stats.last_processing_time = time.time()
            
            # Update average processing time
            if self._processing_times:
                recent_times = list(self._processing_times)[-processed_count:]
                avg_time = sum(recent_times) / len(recent_times) if recent_times else 0.0
                self._processing_stats.average_processing_time = avg_time
    
    def configure(self, 
                  processing_frequency: Optional[float] = None,
                  batch_size: Optional[int] = None,
                  max_queue_size: Optional[int] = None) -> None:
        """
        Update processor configuration.
        
        Args:
            processing_frequency: New processing frequency in seconds
            batch_size: New batch size
            max_queue_size: New maximum queue size
        """
        if processing_frequency is not None:
            self.processing_frequency = processing_frequency
            self.logger.info(f"Updated processing frequency to {processing_frequency}s")
        
        if batch_size is not None:
            self.batch_size = batch_size
            self.logger.info(f"Updated batch size to {batch_size}")
        
        if max_queue_size is not None:
            self.max_queue_size = max_queue_size
            self.logger.info(f"Updated max queue size to {max_queue_size}")
        
        if self.status_callback:
            self.status_callback("configured", self.get_stats())
    
    def clear_queue(self) -> int:
        """Clear all pending tasks from the queue."""
        with self._lock:
            cleared_count = len(self._task_queue)
            self._task_queue.clear()
            self.logger.info(f"Cleared {cleared_count} tasks from queue")
            return cleared_count
    
    def get_processing_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration for a specific processing mode."""
        return self._processing_modes.get(mode, self._processing_modes["balanced"])
    
    def set_processing_mode_config(self, mode: str, config: Dict[str, Any]) -> None:
        """Update configuration for a specific processing mode."""
        self._processing_modes[mode] = config
        self.logger.info(f"Updated {mode} mode configuration: {config}")
