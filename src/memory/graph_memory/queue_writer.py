"""
Queue Writer for Standalone GraphManager

Handles writing conversation entries to the queue file for processing by
the standalone GraphManager process.
"""

import json
import os
import time
import filelock
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class QueueWriter:
    """Writes conversation entries to queue file for standalone GraphManager."""
    
    def __init__(self, storage_path: str, logger: Optional[logging.Logger] = None):
        """Initialize queue writer.
        
        Args:
            storage_path: Path to graph storage directory
            logger: Optional logger instance
        """
        self.storage_path = storage_path
        self.queue_file = os.path.join(storage_path, "conversation_queue.jsonl")
        self.lock_file = self.queue_file + ".lock"
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
    
    def write_conversation_entry(self, conversation_text: str, digest_text: str = "",
                               conversation_guid: str = None, importance: int = None,
                               memory_worthy: bool = None, segment_type: str = None,
                               topics: list = None) -> bool:
        """Write a conversation entry to the queue.
        
        Args:
            conversation_text: Full conversation text
            digest_text: Digest/summary of conversation
            conversation_guid: Unique identifier for conversation
            importance: Importance rating from digest
            memory_worthy: Whether segment is memory worthy
            segment_type: Type of segment (information, action, query, command)
            topics: List of topics from digest
            
        Returns:
            True if successfully written, False otherwise
        """
        try:
            entry = {
                "conversation_text": conversation_text,
                "digest_text": digest_text,
                "conversation_guid": conversation_guid,
                "queued_at": datetime.now().isoformat(),
                "timestamp": time.time()
            }
            
            # Add digest metadata if available
            if importance is not None:
                entry["importance"] = importance
            if memory_worthy is not None:
                entry["memory_worthy"] = memory_worthy
            if segment_type is not None:
                entry["type"] = segment_type
            if topics is not None:
                entry["topics"] = topics
            
            # Write with file locking
            with filelock.FileLock(self.lock_file, timeout=10):
                with open(self.queue_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')
                    f.flush()
            
            self.logger.debug(f"Queued conversation entry: {conversation_guid}")
            return True
            
        except filelock.Timeout:
            self.logger.error("Timeout acquiring lock for queue write")
            return False
        except Exception as e:
            self.logger.error(f"Error writing to queue: {e}")
            return False
    
    def get_queue_size(self) -> int:
        """Get approximate number of entries in queue."""
        try:
            if not os.path.exists(self.queue_file):
                return 0
            
            with filelock.FileLock(self.lock_file, timeout=5):
                with open(self.queue_file, 'r') as f:
                    return sum(1 for line in f if line.strip())
        except filelock.Timeout:
            self.logger.warning("Timeout acquiring lock for queue size check")
            return -1
        except Exception as e:
            self.logger.error(f"Error checking queue size: {e}")
            return -1
    
    def clear_queue(self) -> bool:
        """Clear all entries from queue (for testing/cleanup)."""
        try:
            with filelock.FileLock(self.lock_file, timeout=10):
                if os.path.exists(self.queue_file):
                    os.truncate(self.queue_file, 0)
            
            self.logger.info("Cleared conversation queue")
            return True
        except filelock.Timeout:
            self.logger.error("Timeout acquiring lock for queue clear")
            return False
        except Exception as e:
            self.logger.error(f"Error clearing queue: {e}")
            return False