"""
Performance Tracking System

Provides comprehensive timing and performance measurement capabilities
for the agent system to identify bottlenecks and optimize operations.
"""

import time
import logging
import json
import os
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import threading


@dataclass
class OperationTiming:
    """Data class for storing operation timing information"""
    operation_name: str
    operation_id: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = None
    parent_operation_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class PerformanceTracker:
    """
    Track timing and performance metrics across the agent system.
    
    Features:
    - Hierarchical operation tracking with parent-child relationships
    - Thread-safe operation tracking
    - Automatic performance data persistence
    - Context manager for easy operation timing
    - Performance summary generation
    """
    
    def __init__(self, session_id: str, logs_dir: str = None, logger: Optional[logging.Logger] = None):
        self.session_id = session_id
        self.logger = logger or logging.getLogger(__name__)

        self.logs_dir = logs_dir
        if self.logs_dir is None:
            self.logs_dir = os.path.join("logs", self.session_id)
            os.makedirs(self.logs_dir, exist_ok=True)
        # Thread-safe storage for operations
        self._lock = threading.Lock()
        self._active_operations: Dict[str, OperationTiming] = {}
        self._completed_operations: List[OperationTiming] = []
        self._operation_stack: List[str] = []  # Stack for nested operations
        
        # Performance data file
        self._setup_performance_logging()
        
        # Load existing performance data if available
        self._load_existing_performance_data()
        
    def _setup_performance_logging(self):
        """Setup performance data logging to file"""
        try:            
            # Performance data file
            self.performance_file = os.path.join(self.logs_dir, "performance_data.jsonl")
            
            # Performance summary file
            self.performance_summary_file = os.path.join(self.logs_dir, "performance_summary.json")
            
            self.logger.debug(f"Performance tracking initialized for session {self.session_id}")
            self.logger.debug(f"Performance data file: {self.performance_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not setup performance logging: {e}")
            self.performance_file = None
            self.performance_summary_file = None
    
    def performance_file_exists(self) -> bool:
        """Check if the performance data file exists"""
        return self.performance_file and os.path.exists(self.performance_file)
    
    def performance_summary_file_exists(self) -> bool:
        """Check if the performance summary file exists"""
        return self.performance_summary_file and os.path.exists(self.performance_summary_file)

    def _load_existing_performance_data(self):
        """Load existing performance data from file if it exists"""
        if not self.performance_file or not os.path.exists(self.performance_file):
            return
            
        try:
            with self._lock:
                with open(self.performance_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            operation_data = json.loads(line)
                            operation_timing = OperationTiming(
                                operation_name=operation_data.get("operation_name", ""),
                                operation_id=operation_data.get("operation_id", ""),
                                start_time=operation_data.get("start_time", 0),
                                end_time=operation_data.get("end_time"),
                                duration_seconds=operation_data.get("duration_seconds"),
                                metadata=operation_data.get("metadata", {}),
                                parent_operation_id=operation_data.get("parent_operation_id"),
                                session_id=operation_data.get("session_id"),
                                timestamp=operation_data.get("timestamp")
                            )
                            self._completed_operations.append(operation_timing)
                            
            self.logger.debug(f"Loaded {len(self._completed_operations)} existing performance operations")
            
        except Exception as e:
            self.logger.warning(f"Error loading existing performance data: {e}")
    
    @contextmanager
    def track_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to track operation timing with hierarchical support.
        
        Args:
            operation_name: Name of the operation being tracked
            metadata: Optional metadata to associate with the operation
            
        Yields:
            operation_id: Unique identifier for this operation
        """
        start_time = time.perf_counter()
        operation_id = f"{operation_name}_{int(start_time * 1000000)}"  # Microsecond precision
        
        # Determine parent operation
        parent_id = None
        with self._lock:
            if self._operation_stack:
                parent_id = self._operation_stack[-1]
            self._operation_stack.append(operation_id)
        
        # Create operation timing record
        operation_timing = OperationTiming(
            operation_name=operation_name,
            operation_id=operation_id,
            start_time=start_time,
            metadata=metadata or {},
            parent_operation_id=parent_id,
            session_id=self.session_id
        )
        
        with self._lock:
            self._active_operations[operation_id] = operation_timing
        
        # Log operation start
        indent = "  " * (len(self._operation_stack) - 1) if self._operation_stack else ""
        self.logger.info(f"PERF_START: {indent}{operation_name} ({operation_id})")
        
        try:
            yield operation_id
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # Complete the operation timing
            operation_timing.end_time = end_time
            operation_timing.duration_seconds = duration
            
            with self._lock:
                # Move from active to completed
                self._active_operations.pop(operation_id, None)
                self._completed_operations.append(operation_timing)
                
                # Remove from operation stack
                if self._operation_stack and self._operation_stack[-1] == operation_id:
                    self._operation_stack.pop()
            
            # Log operation completion
            indent = "  " * len(self._operation_stack) if self._operation_stack else ""
            self.logger.info(f"PERF_END: {indent}{operation_name} ({operation_id}) - {duration:.3f}s")
            
            # Save performance data
            self._save_operation_data(operation_timing)
    
    def _save_operation_data(self, operation_timing: OperationTiming):
        """Save individual operation data to file"""
        if not self.performance_file:
            return
            
        try:
            with open(self.performance_file, 'a') as f:
                f.write(json.dumps(asdict(operation_timing)) + '\n')
        except Exception as e:
            self.logger.warning(f"Could not save performance data: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance summary.
        
        Returns:
            Dictionary containing performance metrics and analysis
        """
        with self._lock:
            completed_ops = self._completed_operations.copy()
            active_ops = list(self._active_operations.values())
        
        if not completed_ops:
            return {
                "session_id": self.session_id,
                "total_operations": 0,
                "active_operations": len(active_ops),
                "message": "No completed operations yet"
            }
        
        # Calculate basic statistics
        total_operations = len(completed_ops)
        total_time = sum(op.duration_seconds for op in completed_ops if op.duration_seconds)
        
        # Group operations by name
        operations_by_name = {}
        for op in completed_ops:
            name = op.operation_name
            if name not in operations_by_name:
                operations_by_name[name] = []
            operations_by_name[name].append(op)
        
        # Calculate statistics per operation type
        operation_stats = {}
        for name, ops in operations_by_name.items():
            durations = [op.duration_seconds for op in ops if op.duration_seconds]
            if durations:
                operation_stats[name] = {
                    "count": len(ops),
                    "total_time": sum(durations),
                    "average_time": sum(durations) / len(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                    "percentage_of_total": (sum(durations) / total_time) * 100 if total_time > 0 else 0
                }
        
        # Find top-level operations (no parent)
        top_level_ops = [op for op in completed_ops if op.parent_operation_id is None]
        
        # Create hierarchical operation tree for the most recent top-level operation
        operation_tree = None
        if top_level_ops:
            latest_top_level = max(top_level_ops, key=lambda x: x.start_time)
            operation_tree = self._build_operation_tree(latest_top_level, completed_ops)
        
        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_operations": total_operations,
            "active_operations": len(active_ops),
            "total_time_seconds": total_time,
            "operation_statistics": operation_stats,
            "latest_operation_tree": operation_tree,
            "top_operations_by_time": sorted(
                operation_stats.items(), 
                key=lambda x: x[1]["total_time"], 
                reverse=True
            )[:10]
        }
        
        return summary
    
    def _build_operation_tree(self, root_op: OperationTiming, all_ops: List[OperationTiming]) -> Dict[str, Any]:
        """Build hierarchical tree of operations starting from root operation"""
        tree = {
            "operation_name": root_op.operation_name,
            "operation_id": root_op.operation_id,
            "duration_seconds": root_op.duration_seconds,
            "metadata": root_op.metadata,
            "children": []
        }
        
        # Find child operations
        child_ops = [op for op in all_ops if op.parent_operation_id == root_op.operation_id]
        child_ops.sort(key=lambda x: x.start_time)
        
        for child_op in child_ops:
            child_tree = self._build_operation_tree(child_op, all_ops)
            tree["children"].append(child_tree)
        
        return tree
    
    def save_performance_summary(self):
        """Save performance summary to file"""
        if not self.performance_summary_file:
            return
            
        try:
            summary = self.get_performance_summary()
            with open(self.performance_summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Performance summary saved to {self.performance_summary_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not save performance summary: {e}")
    
    def print_performance_report(self):
        """Print a formatted performance report to the console"""
        summary = self.get_performance_summary()
        
        print("\n" + "="*80)
        print(f"PERFORMANCE REPORT - Session: {self.session_id}")
        print("="*80)
        
        if summary.get("total_operations", 0) == 0:
            print("No completed operations to report.")
            return
        
        print(f"Total Operations: {summary['total_operations']}")
        print(f"Active Operations: {summary['active_operations']}")
        print(f"Total Time: {summary['total_time_seconds']:.3f} seconds")
        
        print("\nTOP OPERATIONS BY TIME:")
        print("-" * 50)
        for op_name, stats in summary.get("top_operations_by_time", [])[:5]:
            print(f"{op_name:30} {stats['total_time']:8.3f}s ({stats['percentage_of_total']:5.1f}%) x{stats['count']}")
        
        if summary.get("latest_operation_tree"):
            print("\nLATEST OPERATION BREAKDOWN:")
            print("-" * 50)
            self._print_operation_tree(summary["latest_operation_tree"], indent=0)
        
        print("="*80)
    
    def _print_operation_tree(self, tree: Dict[str, Any], indent: int = 0):
        """Print operation tree in a hierarchical format"""
        prefix = "  " * indent
        duration = tree.get("duration_seconds", 0)
        
        # Add metadata info if available
        metadata_str = ""
        if tree.get("metadata"):
            metadata = tree["metadata"]
            if "prompt_length" in metadata:
                metadata_str = f" (prompt: {metadata['prompt_length']} chars)"
            elif "llm_tokens" in metadata:
                metadata_str = f" (tokens: {metadata['llm_tokens']})"
        
        print(f"{prefix}{tree['operation_name']:30} {duration:8.3f}s{metadata_str}")
        
        for child in tree.get("children", []):
            self._print_operation_tree(child, indent + 1)


# Global performance tracker registry for easy access
_performance_trackers: Dict[str, PerformanceTracker] = {}
_tracker_lock = threading.Lock()


def get_performance_tracker(session_id: str, logs_dir: str = None, logger: Optional[logging.Logger] = None) -> PerformanceTracker:
    """
    Get or create a performance tracker for a session.
    
    Args:
        session_id: Session identifier
        logger: Optional logger instance
        
    Returns:
        PerformanceTracker instance for the session
    """
    with _tracker_lock:
        if session_id not in _performance_trackers:
            _performance_trackers[session_id] = PerformanceTracker(session_id, logs_dir=logs_dir, logger=logger)
        return _performance_trackers[session_id]


def cleanup_performance_tracker(session_id: str):
    """Clean up performance tracker for a session"""
    with _tracker_lock:
        if session_id in _performance_trackers:
            tracker = _performance_trackers.pop(session_id)
            tracker.save_performance_summary()
