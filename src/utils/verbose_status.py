"""
Verbose Status Handler

Provides timing and status messages for CLI and potentially WebSocket clients.
Shows users what operations are happening and how long they take.
"""

import time
import threading
import json
from typing import Optional, Callable, Dict, Any
from contextlib import contextmanager
from datetime import datetime


class VerboseStatusHandler:
    """
    Handle verbose status messages with timing information.
    
    Features:
    - Context manager for operation timing
    - Thread-safe status updates
    - Configurable output handlers (CLI, WebSocket, etc.)
    - Hierarchical operation tracking
    """
    
    def __init__(self, enabled: bool = True, output_handler: Optional[Callable[[str], None]] = None, websocket_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the verbose status handler.
        
        Args:
            enabled: Whether verbose messages are enabled
            output_handler: Function to handle output messages (defaults to print)
            websocket_callback: Optional callback for WebSocket message streaming
        """
        self.enabled = enabled
        self.websocket_callback = websocket_callback
        self.output_handler = output_handler or print
        self._lock = threading.Lock()
        self._operation_stack = []
        
    def set_enabled(self, enabled: bool):
        """Enable or disable verbose messages."""
        with self._lock:
            self.enabled = enabled
    
    def _send_websocket_message(self, message_type: str, message: str, level: int = 0, duration: Optional[float] = None):
        """Send a message to WebSocket clients if callback is configured."""
        if self.websocket_callback:
            try:
                websocket_data = {
                    "type": "verbose_status",
                    "data": {
                        "message_type": message_type,  # "status", "success", "warning", "error"
                        "message": message,
                        "level": level,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat(),
                        "operation_stack": [op[0] for op in self._operation_stack] if self._operation_stack else []
                    }
                }
                self.websocket_callback(websocket_data)
            except Exception as e:
                # Don't let WebSocket errors break the verbose handler
                print(f"Error sending WebSocket message: {e}")
    
    def set_output_handler(self, handler: Callable[[str], None]):
        """Set the output handler for messages."""
        with self._lock:
            self.output_handler = handler
    
    def status(self, message: str, level: int = 0):
        """
        Send a status message.
        
        Args:
            message: The status message
            level: Indentation level for hierarchical display
        """
        if not self.enabled:
            return
            
        with self._lock:
            indent = "  " * level
            formatted_message = f"🔄 {indent}{message}"
            self.output_handler(formatted_message)
            self._send_websocket_message("status", message, level)
    
    def success(self, message: str, duration: Optional[float] = None, level: int = 0):
        """
        Send a success message with optional timing.
        
        Args:
            message: The success message
            duration: Optional duration in seconds
            level: Indentation level for hierarchical display
        """
        if not self.enabled:
            return
            
        with self._lock:
            indent = "  " * level
            if duration is not None:
                formatted_message = f"✅ {indent}{message} ({duration:.2f}s)"
            else:
                formatted_message = f"✅ {indent}{message}"
            self.output_handler(formatted_message)
            self._send_websocket_message("success", message, level, duration)
    
    def warning(self, message: str, level: int = 0):
        """
        Send a warning message.
        
        Args:
            message: The warning message
            level: Indentation level for hierarchical display
        """
        if not self.enabled:
            return
            
        with self._lock:
            indent = "  " * level
            formatted_message = f"⚠️  {indent}{message}"
            self.output_handler(formatted_message)
            self._send_websocket_message("warning", message, level)
    
    def error(self, message: str, level: int = 0):
        """
        Send an error message.
        
        Args:
            message: The error message
            level: Indentation level for hierarchical display
        """
        if not self.enabled:
            return
            
        with self._lock:
            indent = "  " * level
            formatted_message = f"❌ {indent}{message}"
            self.output_handler(formatted_message)
            self._send_websocket_message("error", message, level)
    
    @contextmanager
    def operation(self, operation_name: str, level: int = 0, show_start: bool = True, show_elapsed: bool = True):
        """
        Context manager for timed operations.
        
        Args:
            operation_name: Name of the operation
            level: Indentation level
            show_start: Whether to show the start message
            show_elapsed: Whether to show elapsed time in start message
            
        Yields:
            VerboseStatusHandler: Self for nested operations
        """
        if not self.enabled:
            yield self
            return
        
        start_time = time.time()
        
        if show_start:
            self.status(f"{operation_name}...", level)
        
        # Track operation stack for nested operations
        with self._lock:
            self._operation_stack.append((operation_name, start_time))
            current_level = len(self._operation_stack) - 1
        
        try:
            yield self
        except Exception as e:
            duration = time.time() - start_time
            self.error(f"Failed {operation_name}: {str(e)} ({duration:.2f}s)", level)
            raise
        finally:
            duration = time.time() - start_time
            self.success(f"{operation_name}", duration, level)
            
            with self._lock:
                if self._operation_stack and self._operation_stack[-1][0] == operation_name:
                    self._operation_stack.pop()
    
    def get_operation_elapsed(self) -> float:
        """Get elapsed time for the current operation."""
        with self._lock:
            if self._operation_stack:
                _, start_time = self._operation_stack[-1]
                return time.time() - start_time
            return 0.0
    
    def get_current_level(self) -> int:
        """Get the current nesting level for operations."""
        with self._lock:
            return len(self._operation_stack)


# Global instance
_global_verbose_handler = None

def get_verbose_handler(enabled: bool = True, output_handler: Optional[Callable[[str], None]] = None) -> VerboseStatusHandler:
    """Get or create the global verbose status handler."""
    global _global_verbose_handler
    if _global_verbose_handler is None:
        _global_verbose_handler = VerboseStatusHandler(enabled, output_handler)
    else:
        if output_handler:
            _global_verbose_handler.set_output_handler(output_handler)
        _global_verbose_handler.set_enabled(enabled)
    return _global_verbose_handler

def set_verbose_enabled(enabled: bool):
    """Enable or disable verbose messages globally."""
    handler = get_verbose_handler()
    handler.set_enabled(enabled)

# Convenience functions for common operations
def status(message: str, level: int = 0):
    """Send a status message."""
    handler = get_verbose_handler()
    handler.status(message, level)

def success(message: str, duration: Optional[float] = None, level: int = 0):
    """Send a success message."""
    handler = get_verbose_handler()
    handler.success(message, duration, level)

def warning(message: str, level: int = 0):
    """Send a warning message."""
    handler = get_verbose_handler()
    handler.warning(message, level)

def error(message: str, level: int = 0):
    """Send an error message."""
    handler = get_verbose_handler()
    handler.error(message, level)

@contextmanager
def operation(operation_name: str, level: int = 0, show_start: bool = True, show_elapsed: bool = True):
    """Context manager for timed operations."""
    handler = get_verbose_handler()
    with handler.operation(operation_name, level, show_start, show_elapsed) as h:
        yield h
