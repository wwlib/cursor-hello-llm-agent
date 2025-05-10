"""Memory Compressor for Agent System

This module provides functionality for compressing conversation history into a more
efficient memory format while preserving important information.

Design Principles:
1. Separation of Concerns
   - Memory compression logic is isolated from memory management
   - Clear interface for compression operations
   - Configurable compression parameters

2. Efficient Compression
   - Processes conversations in natural turns (user + agent pairs)
   - Maintains conversation context and flow
   - Preserves important information while reducing redundancy

3. Quality Control
   - Uses LLM with temperature=0 for deterministic results
   - Properly handles Unicode and special characters
   - Maintains traceability with source GUIDs
"""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime
import logging

class MemoryCompressor:
    """Handles compression of conversation history into efficient memory format."""
    
    def __init__(self, llm_service, importance_threshold: int = 3, logger=None):
        """Initialize the MemoryCompressor.
        
        Args:
            llm_service: Service for LLM operations
            importance_threshold: Minimum importance score (1-5) to keep segments
            logger: Logger instance for logging
        """
        self.llm = llm_service
        self.importance_threshold = importance_threshold
        self.logger = logger or logging.getLogger(__name__)
        self._load_templates()
        
    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        import os
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        try:
            with open(os.path.join(template_dir, "compress_memory.prompt"), 'r') as f:
                self.compress_template = f.read().strip()
            print("Loaded compression template")
        except Exception as e:
            print(f"Error loading compression template: {str(e)}")
            raise Exception("Failed to load compression template")
            
    def compress_conversation_history(self, 
                                    conversation_history: List[Dict[str, Any]],
                                    static_memory: str,
                                    current_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compress conversation history into efficient memory format.
        
        Args:
            conversation_history: List of conversation entries to compress
            static_memory: Current static memory content
            current_context: Current context entries
            
        Returns:
            dict: Updated memory state with compressed information
        """
        try:
            if not conversation_history:
                print("No entries to compress")
                return {"context": current_context, "conversation_history": []}
            
            print(f"Found {len(conversation_history)} entries to compress")
            
            # Process entries in turns (user + agent pairs)
            turns = []
            current_turn = []
            
            for entry in conversation_history:
                current_turn.append(entry)
                
                # If we have a complete turn (user + agent) or this is the last entry
                if len(current_turn) == 2 or entry == conversation_history[-1]:
                    turns.append(current_turn)
                    current_turn = []
            
            print(f"Split into {len(turns)} turns")
            
            # Process each turn
            new_context = current_context.copy() if current_context else []
            
            for turn in turns:
                # Extract important segments from this turn
                important_segments = []
                
                for entry in turn:
                    # Process digest if available
                    if "digest" in entry and "rated_segments" in entry["digest"]:
                        print(f"Processing digest for entry {entry.get('guid')}")
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
                                    "source_guid": entry.get("guid")
                                })
                    else:
                        print(f"No digest found for entry {entry.get('guid')}")
                
                if important_segments:
                    # Transform segments into simple markdown format
                    markdown_segments = []
                    for segment in important_segments:
                        role = segment.get("role", "unknown").upper()
                        markdown_segments.append(f"[{role}]: {segment['text']}")
                    
                    # Join segments with newlines
                    important_segments_text = "\n".join(markdown_segments)
                    
                    # Use LLM to organize important segments by topic
                    prompt = self.compress_template.format(
                        important_segments_text=important_segments_text,
                        previous_context_text=json.dumps(current_context, indent=2),
                        static_memory_text=static_memory
                    )
                    
                    print("Sending compression prompt to LLM...")
                    # Call LLM to organize segments with temperature=0 for deterministic results
                    llm_response = self.llm.generate(prompt, options={"temperature": 0}, debug_generate_scope="memory_compression")
                    print("Received response from LLM")
                    
                    # Create a new context entry with the markdown text and source GUIDs
                    context_entry = {
                        "text": llm_response,
                        "guids": [entry.get("guid") for entry in turn if entry.get("guid")]
                    }
                    
                    # Add the new context entry
                    new_context.append(context_entry)
                    print("Added new context entry with compressed information")
            
            # Collect GUIDs of all compressed entries
            all_compressed_guids = []
            for turn in turns:
                for entry in turn:
                    if entry.get('guid'):
                        all_compressed_guids.append(entry['guid'])

            # Return updated memory state
            return {
                "context": new_context,
                "conversation_history": [],  # Clear conversation history after compression
                "metadata": {
                    "last_compressed": datetime.now().isoformat(),
                    "compressed_entries": all_compressed_guids,
                    "compressed_entry_count": len(all_compressed_guids)
                }
            }
            
        except Exception as e:
            print(f"Error in compress_conversation_history: {str(e)}")
            return {"context": current_context, "conversation_history": conversation_history} 