"""Embeddings Manager for semantic search functionality.

This module provides functionality for generating, storing, and searching embeddings
of conversation history entries to enable semantic search capabilities.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import json
import os
import numpy as np
from datetime import datetime
from pathlib import Path
import logging
import traceback

# Standard importance threshold for embeddings generation
DEFAULT_EMBEDDINGS_IMPORTANCE_THRESHOLD = 3

# Define which segment types should be embedded for search
EMBEDDINGS_RELEVANT_TYPES = ["information", "action"]  # Exclude queries and commands

class EmbeddingsManager:
    """Manages embeddings for conversation history entries to enable semantic search.
    
    The EmbeddingsManager handles:
    1. Generating embeddings for conversation entries
    2. Storing embeddings persistently
    3. Loading embeddings for search
    4. Adding new embeddings
    5. Performing semantic search
    
    Basic Approach::
    
        1. Generating Embeddings:
           - Use a local embedding model (e.g., all-MiniLM-L6-v2) for efficiency
           - Generate embeddings for:
             * Full conversation entry text
             * Individual segments from digests
             * Topics and key concepts
           - Store metadata with each embedding (entry GUID, timestamp, etc.)
        
        2. Saving Embeddings:
           - Store in JSONL format for easy appending and reading
           - Each line contains:
             * embedding: vector as list of floats
             * metadata: entry GUID, timestamp, text, etc.
             * source: whether from full entry or segment
           - Keep embeddings file in sync with conversation history
        
        3. Loading Embeddings:
           - Load embeddings file at initialization
           - Maintain in-memory index for quick search
           - Handle missing or corrupted embeddings gracefully
           - Support incremental loading for large histories
        
        4. Adding New Embeddings:
           - Generate embeddings for new conversation entries
           - Append to embeddings file
           - Update in-memory index
           - Handle duplicates and updates
        
        5. Semantic Search:
           - Convert query to embedding
           - Compute cosine similarity with all stored embeddings
           - Return top-k most similar entries
           - Support filtering by:
             * date range
             * importance threshold
             * specific topics
           - Return both similarity scores and full entry data
    """
    
    def __init__(self, embeddings_file: str, llm_service=None, logger=None):
        """Initialize the EmbeddingsManager.
        
        Args:
            embeddings_file: Path to the JSONL file for storing embeddings
            llm_service: Optional LLM service for generating embeddings
            logger: Optional logger instance
        """
        self.embeddings_file = embeddings_file
        self.llm_service = llm_service
        self.embeddings = []  # List of (embedding, metadata) tuples
        self.embedding_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize embeddings file directory if it doesn't exist
        embeddings_dir = os.path.dirname(embeddings_file)
        if embeddings_dir and not os.path.exists(embeddings_dir):
            os.makedirs(embeddings_dir, exist_ok=True)
            
        # Load existing embeddings
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load existing embeddings from file."""
        if not os.path.exists(self.embeddings_file):
            self.logger.debug(f"Embeddings file {self.embeddings_file} does not exist, starting with empty embeddings.")
            return
            
        try:
            with open(self.embeddings_file, 'r') as f:
                count = 0
                error_count = 0
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        if 'embedding' not in data:
                            self.logger.debug(f"Line {line_num} in embeddings file is missing 'embedding' field.")
                            error_count += 1
                            continue
                            
                        # Ensure metadata exists (create empty if not)
                        if 'metadata' not in data:
                            self.logger.debug(f"Line {line_num} in embeddings file is missing 'metadata' field, creating empty.")
                            data['metadata'] = {}
                            
                        # Add the text to metadata if it's in the main data but not in metadata
                        if 'text' in data and 'text' not in data['metadata']:
                            data['metadata']['text'] = data['text']
                            
                        self.embeddings.append((
                            np.array(data['embedding']),
                            data['metadata']
                        ))
                        count += 1
                    except json.JSONDecodeError:
                        self.logger.debug(f"Failed to parse line {line_num} in embeddings file.")
                        error_count += 1
                        continue
                    except Exception as e:
                        self.logger.debug(f"Error processing line {line_num}: {str(e)}")
                        error_count += 1
                        continue
                        
            self.logger.debug(f"Loaded {count} embeddings from {self.embeddings_file} ({error_count} errors)")
        except Exception as e:
            self.logger.error(f"Error loading embeddings: {str(e)}")
    
    def generate_embedding(self, text: str, options: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Generate embedding for a text string.
        
        Args:
            text: Text to generate embedding for
            options: Optional dictionary with embedding options:
                - model: Specific embedding model to use (default: whatever the LLM service uses)
                - normalize: Whether to normalize the embedding vector (default: True)
                
        Returns:
            np.ndarray: Embedding vector
            
        Raises:
            ValueError: If LLM service is not available or text is empty
        """
        if not self.llm_service:
            raise ValueError("LLM service is required for generating embeddings")
            
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
            
        options = options or {}
        # Always set the embedding model
        options = {**options, "model": self.embedding_model}
        normalize = options.get('normalize', True)
            
        try:
            # Generate embedding using LLM service
            embedding = self.llm_service.generate_embedding(text, options)
            
            # Convert to numpy array
            embedding_array = np.array(embedding)
            
            # Normalize if requested (though LLM service should already do this)
            # Ensure normalize is a boolean to avoid numpy array ambiguity
            should_normalize = bool(normalize) and bool(options.get('normalize', True))
            if should_normalize:
                norm = np.linalg.norm(embedding_array)
                if norm > 0:
                    embedding_array = embedding_array / norm
                    
            return embedding_array
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def _extract_text(self, item: Union[Dict[str, Any], str]) -> str:
        """Extract text content from various possible formats.
        
        Args:
            item: Dictionary or string containing text
            
        Returns:
            str: Extracted text
        """
        # If already a string, return it
        if isinstance(item, str):
            return item
            
        # If it's a dictionary, try various fields
        if isinstance(item, dict):
            # Try common text field names
            for field in ['text', 'content', 'segment_text']:
                if field in item and item[field]:
                    return item[field]
                    
            # Check metadata if present
            if 'metadata' in item and isinstance(item['metadata'], dict):
                for field in ['text', 'content', 'segment_text']:
                    if field in item['metadata'] and item['metadata'][field]:
                        return item['metadata'][field]
        
        # If we get here, we couldn't find any text
        self.logger.debug(f"Could not extract text from item: {item}")
        return ""
    
    def add_embedding(self, text_or_item: Union[str, Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None, options: Optional[Dict[str, Any]] = None) -> bool:
        """Add a new embedding to the store.
        
        Args:
            text_or_item: Text to generate embedding for or dictionary with text/'content' field
            metadata: Associated metadata (GUID, timestamp, etc.) - optional if text_or_item is a dictionary with metadata
            options: Optional dictionary with embedding options
            
        Returns:
            bool: True if successfully added
        """
        try:
            # Extract text and metadata
            if isinstance(text_or_item, str):
                text = text_or_item
                metadata = metadata or {}
            else:
                # Extract text from dictionary
                text = self._extract_text(text_or_item)
                
                # If metadata wasn't provided but exists in the item, use that
                if metadata is None and isinstance(text_or_item, dict):
                    if 'metadata' in text_or_item:
                        metadata = text_or_item['metadata']
                    else:
                        # Use the item itself as metadata
                        metadata = text_or_item
            
            # Ensure we have text to embed
            if not text or not text.strip():
                self.logger.debug("Cannot add embedding for empty text")
                return False
                
            # Ensure metadata is a dictionary
            if metadata is None:
                metadata = {}
                
            # Store text in metadata if not already there
            if 'text' not in metadata:
                metadata['text'] = text[:1000]  # Limit text size for storage
            
            # Generate embedding
            embedding = self.generate_embedding(text, options)
            
            # Add to in-memory store
            self.embeddings.append((embedding, metadata))
            
            # Append to file - create file if it doesn't exist
            file_mode = 'a' if os.path.exists(self.embeddings_file) else 'w'
            with open(self.embeddings_file, file_mode) as f:
                json.dump({
                    'embedding': embedding.tolist(),
                    'metadata': metadata,
                    'text': text[:100] + '...' if len(text) > 100 else text  # Store text preview for debugging
                }, f)
                f.write('\n')
            
            guid = metadata.get('guid', 'unknown')
            text_preview = text[:30] + '...' if len(text) > 30 else text
            self.logger.debug(f"Added embedding for text: '{text_preview}' with GUID: {guid}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding embedding: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score between -1 and 1
        """
        # Ensure embeddings are normalized for accurate cosine similarity
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 > 0:
            embedding1 = embedding1 / norm1
        if norm2 > 0:
            embedding2 = embedding2 / norm2
            
        return np.dot(embedding1, embedding2)
    
    def search(self, query: Union[str, np.ndarray], k: int = 5, 
              min_importance: Optional[int] = None,
              date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Search for similar entries using semantic similarity.
        
        Args:
            query: Search query text or embedding vector
            k: Number of results to return
            min_importance: Optional minimum importance threshold
            date_range: Optional (start_date, end_date) tuple
            
        Returns:
            List[Dict]: List of results with similarity scores and metadata
        """
        if not self.embeddings:
            self.logger.debug("RAG_SEARCH: No embeddings available for search")
            return []
            
        try:
            # Log search parameters
            query_text = query if isinstance(query, str) else f"<embedding_vector_len_{len(query)}>"
            self.logger.debug(f"RAG_SEARCH: Starting search for query: '{query_text}'")
            self.logger.debug(f"RAG_SEARCH: Parameters - k={k}, min_importance={min_importance}, date_range={date_range}")
            self.logger.debug(f"RAG_SEARCH: Total embeddings available: {len(self.embeddings)}")
            
            # Get query embedding
            if isinstance(query, str):
                try:
                    self.logger.debug(f"RAG_SEARCH: Generating embedding for query text")
                    query_embedding = self.generate_embedding(query)
                    self.logger.debug(f"RAG_SEARCH: Generated query embedding with dimension: {len(query_embedding)}")
                except Exception as e:
                    self.logger.error(f"RAG_SEARCH: Error generating embedding for query: {str(e)}")
                    return []
            else:
                query_embedding = query
                self.logger.debug(f"RAG_SEARCH: Using provided embedding vector with dimension: {len(query_embedding)}")
            
            # Compute similarities
            similarities = []
            filtered_count = 0
            processed_count = 0
            
            for embedding, metadata in self.embeddings:
                try:
                    processed_count += 1
                    
                    # Apply filters
                    if min_importance is not None:
                        importance = metadata.get('importance', 0)
                        if importance < min_importance:
                            filtered_count += 1
                            continue
                            
                    if date_range and 'timestamp' in metadata:
                        try:
                            entry_date = datetime.fromisoformat(metadata['timestamp'])
                            if not (date_range[0] <= entry_date <= date_range[1]):
                                filtered_count += 1
                                continue
                        except (ValueError, TypeError):
                            # Skip entries with invalid timestamps
                            filtered_count += 1
                            continue
                    
                    # Compute cosine similarity
                    similarity = self.calculate_similarity(query_embedding, embedding)
                    
                    # Extract text from metadata for convenience
                    text = metadata.get('text', '')
                    if not text and 'content' in metadata:
                        text = metadata['content']
                        
                    # Create a copy of metadata to avoid modifying the original
                    result_metadata = metadata.copy()
                    
                    # Add the entry to results
                    similarities.append((
                        similarity, 
                        text,
                        result_metadata
                    ))
                except Exception as e:
                    self.logger.debug(f"RAG_SEARCH: Error processing embedding {processed_count}: {str(e)}")
                    continue
            
            self.logger.debug(f"RAG_SEARCH: Processed {processed_count} embeddings, filtered out {filtered_count}, kept {len(similarities)} for ranking")
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[0], reverse=True)
            
            # Log top similarities before truncating
            if similarities:
                self.logger.debug(f"RAG_SEARCH: Top similarity scores: {[f'{s[0]:.4f}' for s in similarities[:min(10, len(similarities))]]}")
            
            # Return top k results
            results = [
                {
                    'score': float(score),  # Convert from numpy to Python float
                    'text': text,
                    'metadata': metadata
                }
                for score, text, metadata in similarities[:k]
            ]
            
            # Log detailed results
            self.logger.debug(f"RAG_SEARCH: Returning {len(results)} results out of {len(similarities)} candidates")
            for i, result in enumerate(results):
                text_preview = result['text'][:100] + "..." if len(result['text']) > 100 else result['text']
                entity_info = ""
                if 'entity_id' in result['metadata']:
                    entity_info = f" [entity_id: {result['metadata']['entity_id']}]"
                if 'entity_name' in result['metadata']:
                    entity_info += f" [entity_name: {result['metadata']['entity_name']}]"
                if 'entity_type' in result['metadata']:
                    entity_info += f" [entity_type: {result['metadata']['entity_type']}]"
                
                self.logger.debug(f"RAG_SEARCH: Result {i+1}: score={result['score']:.4f}{entity_info}")
                self.logger.debug(f"RAG_SEARCH: Result {i+1} text: '{text_preview}'")
            
            return results
            
        except Exception as e:
            self.logger.error(f"RAG_SEARCH: Error in search: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []
    
    def deduplicate_embeddings_file(self):
        """Remove redundant embeddings with identical text from the embeddings file. Returns the number of embeddings removed."""
        if not os.path.exists(self.embeddings_file):
            self.logger.debug("Embeddings file does not exist, skipping deduplication.")
            return 0

        seen_texts = set()
        deduped = []
        original_count = 0
        try:
            with open(self.embeddings_file, "r") as infile:
                for line in infile:
                    original_count += 1
                    try:
                        data = json.loads(line)
                        meta = data.get("metadata", {})
                        text = meta.get("text") or data.get("text")
                        if text is not None:
                            text_key = text.strip()
                            if text_key not in seen_texts:
                                seen_texts.add(text_key)
                                deduped.append(data)
                    except Exception as e:
                        self.logger.debug(f"Error parsing line during deduplication: {e}")

            # Overwrite the file with deduplicated entries
            with open(self.embeddings_file, "w") as outfile:
                for item in deduped:
                    json.dump(item, outfile)
                    outfile.write("\n")

            removed_count = original_count - len(deduped)
            self.logger.info(f"Deduplicated embeddings file: {len(deduped)} unique texts remain. {removed_count} embeddings removed.")
            return removed_count
        except Exception as e:
            self.logger.error(f"Error during embeddings deduplication: {e}")
            return 0

    def update_embeddings(self, conversation_entries: List[Dict]) -> bool:
        """Update embeddings for conversation history entries.
        
        Args:
            conversation_entries: List of conversation entries
            
        Returns:
            bool: True if successfully updated
        """
        try:
            # Clear existing embeddings
            self.embeddings = []
            if os.path.exists(self.embeddings_file):
                # Create a backup of the existing file
                backup_path = f"{self.embeddings_file}.bak"
                try:
                    os.rename(self.embeddings_file, backup_path)
                    self.logger.debug(f"Created backup of embeddings file: {backup_path}")
                except OSError:
                    self.logger.error(f"Could not create backup of embeddings file")
            
            # Create a new embeddings file
            with open(self.embeddings_file, 'w'):
                pass  # Just create an empty file
            
            # Generate new embeddings
            success_count = 0
            total_count = 0
            
            for entry in conversation_entries:
                # Only embed rated_segments from digest
                if 'digest' in entry and 'rated_segments' in entry['digest']:
                    segments = entry['digest']['rated_segments']
                    self.logger.debug(f"Processing {len(segments)} segments for entry {entry.get('guid', str(total_count))}")
                    for i, segment in enumerate(segments):
                        if 'text' not in segment or not segment['text']:
                            self.logger.debug(f"Skipping segment {i} without text in entry {entry.get('guid', str(total_count))}")
                            continue
                        
                        # Skip segments below importance threshold
                        importance = segment.get('importance', 3)
                        if importance < DEFAULT_EMBEDDINGS_IMPORTANCE_THRESHOLD:
                            self.logger.debug(f"Skipping segment {i} with low importance ({importance}) in entry {entry.get('guid', str(total_count))}")
                            continue
                        
                        # Skip segments with irrelevant types
                        segment_type = segment.get('type', 'information')
                        if segment_type not in EMBEDDINGS_RELEVANT_TYPES:
                            self.logger.debug(f"Skipping segment {i} with irrelevant type ({segment_type}) in entry {entry.get('guid', str(total_count))}")
                            continue
                            
                        total_count += 1
                        # Create segment metadata
                        segment_metadata = {
                            'guid': entry.get('guid', str(total_count)),
                            'timestamp': entry.get('timestamp', datetime.now().isoformat()),
                            'role': entry.get('role', 'unknown'),
                            'type': 'segment',
                            'importance': segment.get('importance', 3),
                            'topics': segment.get('topics', []),
                            'segment_index': i,
                            'text': segment.get('text', '')
                        }
                        if self.add_embedding(segment.get('text', ''), segment_metadata):
                            success_count += 1
            
            self.logger.debug(f"Updated embeddings: {success_count}/{total_count} successful")
            # Deduplicate after batch update
            removed_count = self.deduplicate_embeddings_file()
            self.logger.info(f"Deduplication complete: {removed_count} redundant embeddings removed.")
            return success_count > 0
        except Exception as e:
            self.logger.error(f"Error updating embeddings: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _existing_embedding_keys(self):
        """Return a set of (guid, type, segment_index) for all current embeddings."""
        keys = set()
        for _, metadata in self.embeddings:
            guid = metadata.get('guid')
            typ = metadata.get('type', 'full_entry')
            segment_index = metadata.get('segment_index') if typ == 'segment' else None
            keys.add((guid, typ, segment_index))
        return keys
    
    def add_embeddings_for_entry(self, entry: Dict) -> int:
        """Add embeddings for a single conversation entry and its segments, skipping duplicates.
        Returns the number of new embeddings added."""
        added = 0
        existing_keys = self._existing_embedding_keys()
        guid = entry.get('guid')
        timestamp = entry.get('timestamp', datetime.now().isoformat())
        role = entry.get('role', 'unknown')
        # Add segment embeddings if present
        if 'digest' in entry and 'rated_segments' in entry['digest']:
            segments = entry['digest']['rated_segments']
            for i, segment in enumerate(segments):
                if 'text' not in segment or not segment['text']:
                    continue
                
                # Skip segments below importance threshold
                importance = segment.get('importance', 3)
                if importance < DEFAULT_EMBEDDINGS_IMPORTANCE_THRESHOLD:
                    continue
                
                # Skip segments with irrelevant types
                segment_type = segment.get('type', 'information')
                if segment_type not in EMBEDDINGS_RELEVANT_TYPES:
                    continue
                    
                key = (guid, 'segment', i)
                if key in existing_keys:
                    continue
                segment_metadata = {
                    'guid': guid,
                    'timestamp': timestamp,
                    'role': role,
                    'type': 'segment',
                    'importance': segment.get('importance', 3),
                    'topics': segment.get('topics', []),
                    'segment_index': i,
                    'text': segment.get('text', '')
                }
                if self.add_embedding(segment.get('text', ''), segment_metadata):
                    added += 1
        return added
    
    def add_new_embeddings(self, new_entries: List[Dict]) -> bool:
        """Incrementally add embeddings for new conversation entries only."""
        total_added = 0
        for entry in new_entries:
            total_added += self.add_embeddings_for_entry(entry)
        self.logger.debug(f"Incremental embedding update: {total_added} new embeddings added.")
        return total_added > 0 