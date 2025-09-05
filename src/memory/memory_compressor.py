"""Memory Compressor for Agent System

This module provides functionality for compressing conversation history into a more
efficient memory format while preserving important information.

Design Principles::

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

# Define which segment types should be included in compressed memory context
CONTEXT_RELEVANT_TYPES = ["information", "action"]  # Exclude old queries and commands

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
            self.logger.debug("Loaded compression template")
        except Exception as e:
            self.logger.error(f"Error loading compression template: {str(e)}")
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
                self.logger.debug("No entries to compress")
                return {"context": current_context, "conversation_history": []}
            
            self.logger.debug(f"Found {len(conversation_history)} entries to compress")
            
            # Process entries in turns (user + agent pairs)
            turns = []
            current_turn = []
            
            for entry in conversation_history:
                current_turn.append(entry)
                
                # If we have a complete turn (user + agent) or this is the last entry
                if len(current_turn) == 2 or entry == conversation_history[-1]:
                    turns.append(current_turn)
                    current_turn = []
            
            self.logger.debug(f"Split into {len(turns)} turns")
            
            # Process each turn
            new_context = current_context.copy() if current_context else []
            
            for turn in turns:
                # Extract important segments from this turn
                important_segments = []
                
                for entry in turn:
                    # Process digest if available
                    if "digest" in entry and "rated_segments" in entry["digest"]:
                        self.logger.debug(f"Processing digest for entry {entry.get('guid')}")
                        # Filter segments by importance and type
                        for segment in entry["digest"]["rated_segments"]:
                            segment_type = segment.get("type", "information")
                            if (segment.get("importance", 0) >= self.importance_threshold and 
                                segment_type in CONTEXT_RELEVANT_TYPES):
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
                        self.logger.debug(f"No digest found for entry {entry.get('guid')}")
                
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
                    
                    self.logger.debug("Sending compression prompt to LLM...")
                    # Call LLM to organize segments with temperature=0 for deterministic results
                    llm_response = self.llm.generate(prompt, options={"temperature": 0}, debug_generate_scope="memory_compression")
                    self.logger.debug("Received response from LLM")
                    
                    # Check if the response indicates no new information
                    if llm_response.strip() == "NO_NEW_INFORMATION":
                        self.logger.debug("No new information found in this turn, skipping context creation")
                        continue
                    
                    # Clean the response and check if it's actually meaningful
                    cleaned_response = llm_response.strip()
                    if len(cleaned_response) < 10:  # Very short responses are likely not meaningful
                        self.logger.debug("Response too short to be meaningful, skipping")
                        continue
                    
                    # Create a new context entry with the cleaned text and source GUIDs
                    context_entry = {
                        "text": cleaned_response,
                        "guids": [entry.get("guid") for entry in turn if entry.get("guid")]
                    }
                    
                    # Add the new context entry
                    new_context.append(context_entry)
                    self.logger.debug("Added new context entry with compressed information")
            
            # Collect GUIDs of all compressed entries
            all_compressed_guids = []
            for turn in turns:
                for entry in turn:
                    if entry.get('guid'):
                        all_compressed_guids.append(entry['guid'])

            # Consolidate similar context entries to prevent redundancy buildup
            consolidated_context = self._consolidate_context_entries(new_context)

            # Return updated memory state
            return {
                "context": consolidated_context,
                "conversation_history": [],  # Clear conversation history after compression
                "metadata": {
                    "last_compressed": datetime.now().isoformat(),
                    "compressed_entries": all_compressed_guids,
                    "compressed_entry_count": len(all_compressed_guids),
                    "original_context_count": len(new_context),
                    "consolidated_context_count": len(consolidated_context)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in compress_conversation_history: {str(e)}")
            return {"context": current_context, "conversation_history": conversation_history}
    
    def _consolidate_context_entries(self, context_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Consolidate similar context entries to prevent redundancy buildup.
        
        Args:
            context_entries: List of context entries to consolidate
            
        Returns:
            List of consolidated context entries
        """
        if len(context_entries) <= 1:
            return context_entries
        
        try:
            # Group similar entries for potential consolidation
            consolidated = []
            processed_indices = set()
            
            for i, entry in enumerate(context_entries):
                if i in processed_indices:
                    continue
                
                entry_text = entry.get("text", "").strip()
                if not entry_text:
                    continue
                
                # Look for similar entries to consolidate
                similar_entries = [entry]
                similar_indices = {i}
                
                for j, other_entry in enumerate(context_entries[i+1:], start=i+1):
                    if j in processed_indices:
                        continue
                    
                    other_text = other_entry.get("text", "").strip()
                    if not other_text:
                        continue
                    
                    # Check for significant overlap (simple similarity check)
                    if self._entries_are_similar(entry_text, other_text):
                        similar_entries.append(other_entry)
                        similar_indices.add(j)
                
                # Mark all similar entries as processed
                processed_indices.update(similar_indices)
                
                # If we found similar entries, consolidate them
                if len(similar_entries) > 1:
                    self.logger.debug(f"Consolidating {len(similar_entries)} similar context entries")
                    consolidated_entry = self._merge_similar_entries(similar_entries)
                    consolidated.append(consolidated_entry)
                else:
                    # Keep the entry as-is
                    consolidated.append(entry)
            
            self.logger.debug(f"Context consolidation: {len(context_entries)} -> {len(consolidated)} entries")
            return consolidated
            
        except Exception as e:
            self.logger.error(f"Error in context consolidation: {str(e)}")
            return context_entries
    
    def _entries_are_similar(self, text1: str, text2: str, threshold: float = 0.35) -> bool:
        """Check if two context entries are similar enough to consolidate.
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if entries are similar enough to consolidate
        """
        try:
            # Simple word-based similarity check
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return False
            
            # Calculate Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            similarity = intersection / union if union > 0 else 0
            return similarity >= threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating text similarity: {str(e)}")
            return False
    
    def _merge_similar_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge similar context entries into a single consolidated entry.
        
        Args:
            entries: List of similar entries to merge
            
        Returns:
            Consolidated context entry
        """
        try:
            # Combine all GUIDs
            all_guids = []
            for entry in entries:
                guids = entry.get("guids", [])
                if isinstance(guids, list):
                    all_guids.extend(guids)
                elif guids:  # Single GUID
                    all_guids.append(guids)
            
            # Remove duplicates while preserving order
            unique_guids = []
            seen = set()
            for guid in all_guids:
                if guid not in seen:
                    unique_guids.append(guid)
                    seen.add(guid)
            
            # Use the most comprehensive text (longest one, assuming it has the most information)
            texts = [entry.get("text", "") for entry in entries]
            consolidated_text = max(texts, key=len) if texts else ""
            
            return {
                "text": consolidated_text,
                "guids": unique_guids
            }
            
        except Exception as e:
            self.logger.error(f"Error merging context entries: {str(e)}")
            # Return the first entry as fallback
            return entries[0] if entries else {"text": "", "guids": []}
    
    async def compress_conversation_history_async(self, 
                                    conversation_history: List[Dict[str, Any]],
                                    static_memory: str,
                                    current_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compress conversation history into efficient memory format asynchronously.
        
        This method is identical to compress_conversation_history but uses async LLM calls
        to prevent blocking the event loop during long compression operations.
        
        Args:
            conversation_history: List of conversation entries to compress
            static_memory: Current static memory content
            current_context: Current context entries
            
        Returns:
            dict: Updated memory state with compressed information
        """
        try:
            if not conversation_history:
                self.logger.debug("No entries to compress")
                return {"context": current_context, "conversation_history": []}
            
            self.logger.debug(f"Found {len(conversation_history)} entries to compress")
            
            # Process entries in turns (user + agent pairs)
            turns = []
            current_turn = []
            
            for entry in conversation_history:
                current_turn.append(entry)
                
                # If we have a complete turn (user + agent) or this is the last entry
                if len(current_turn) == 2 or entry == conversation_history[-1]:
                    turns.append(current_turn)
                    current_turn = []
            
            self.logger.debug(f"Split into {len(turns)} turns")
            
            # Process each turn
            new_context = current_context.copy() if current_context else []
            all_compressed_guids = []
            
            for turn in turns:
                # Extract important segments from this turn
                important_segments = []
                
                for entry in turn:
                    # Process digest if available
                    if "digest" in entry and "rated_segments" in entry["digest"]:
                        self.logger.debug(f"Processing digest for entry {entry.get('guid')}")
                        # Filter segments by importance and type
                        for segment in entry["digest"]["rated_segments"]:
                            segment_type = segment.get("type", "information")
                            if (segment.get("importance", 0) >= self.importance_threshold and 
                                segment_type in CONTEXT_RELEVANT_TYPES):
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
                        self.logger.debug(f"No digest found for entry {entry.get('guid')}")
                
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
                    
                    self.logger.debug("Sending compression prompt to LLM async...")
                    # Call LLM asynchronously to organize segments with temperature=0 for deterministic results
                    llm_response = await self.llm.generate_async(prompt, options={"temperature": 0}, debug_generate_scope="memory_compression_async")
                    self.logger.debug("Received response from LLM async")
                    
                    # Check if the response indicates no new information
                    if llm_response.strip() == "NO_NEW_INFORMATION":
                        self.logger.debug("No new information found in this turn, skipping context creation")
                        continue
                    
                    # Clean the response and check if it's actually meaningful
                    cleaned_response = llm_response.strip()
                    if len(cleaned_response) < 10:  # Very short responses are likely not meaningful
                        self.logger.debug("Response too short to be meaningful, skipping")
                        continue
                    
                    # Create a new context entry with the cleaned text and source GUIDs
                    context_entry = {
                        "text": cleaned_response,
                        "timestamp": datetime.now().isoformat(),
                        "source_guids": [entry.get("guid") for entry in turn if entry.get("guid")]
                    }
                    
                    new_context.append(context_entry)
                    self.logger.debug(f"Added compressed context entry from turn with {len(turn)} entries")
                
                # Track GUIDs from this turn
                for entry in turn:
                    if entry.get("guid"):
                        all_compressed_guids.append(entry["guid"])
            
            # Consolidate context entries to prevent buildup
            consolidated_context = self._consolidate_context_entries(new_context)
            
            self.logger.debug(f"Async compression complete: {len(consolidated_context)} consolidated context entries, {len(all_compressed_guids)} entries compressed")
            
            return {
                "context": consolidated_context,
                "conversation_history": [],  # Clear conversation history after compression
                "metadata": {
                    "last_compressed": datetime.now().isoformat(),
                    "compressed_entries": all_compressed_guids,
                    "compressed_entry_count": len(all_compressed_guids),
                    "original_context_count": len(new_context),
                    "consolidated_context_count": len(consolidated_context)
                }
            }
                
        except Exception as e:
            self.logger.error(f"Error during async compression: {str(e)}")
            return {"context": current_context, "conversation_history": conversation_history} 