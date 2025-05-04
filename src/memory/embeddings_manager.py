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

class EmbeddingsManager:
    """Manages embeddings for conversation history entries to enable semantic search.
    
    The EmbeddingsManager handles:
    1. Generating embeddings for conversation entries
    2. Storing embeddings persistently
    3. Loading embeddings for search
    4. Adding new embeddings
    5. Performing semantic search
    
    Basic Approach:
    
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
    
    def __init__(self, embeddings_file: str, llm_service=None):
        """Initialize the EmbeddingsManager.
        
        Args:
            embeddings_file: Path to the JSONL file for storing embeddings
            llm_service: Optional LLM service for generating embeddings
        """
        self.embeddings_file = embeddings_file
        self.llm_service = llm_service
        self.embeddings = []  # List of (embedding, metadata) tuples
        self.logger = logging.getLogger("embeddings_manager")
        
        # Initialize embeddings file directory if it doesn't exist
        embeddings_dir = os.path.dirname(embeddings_file)
        if embeddings_dir and not os.path.exists(embeddings_dir):
            os.makedirs(embeddings_dir, exist_ok=True)
            
        # Load existing embeddings
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load existing embeddings from file."""
        if not os.path.exists(self.embeddings_file):
            self.logger.info(f"Embeddings file {self.embeddings_file} does not exist, starting with empty embeddings.")
            return
            
        try:
            with open(self.embeddings_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        if 'embedding' not in data or 'metadata' not in data:
                            self.logger.warning(f"Line {line_num} in embeddings file is missing required fields.")
                            continue
                            
                        self.embeddings.append((
                            np.array(data['embedding']),
                            data['metadata']
                        ))
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse line {line_num} in embeddings file.")
                        continue
                        
            self.logger.info(f"Loaded {len(self.embeddings)} embeddings from {self.embeddings_file}")
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
        normalize = options.get('normalize', True)
            
        try:
            # Generate embedding using LLM service
            embedding = self.llm_service.generate_embedding(text, options)
            
            # Convert to numpy array
            embedding_array = np.array(embedding)
            
            # Normalize if requested (though LLM service should already do this)
            if normalize and options.get('normalize', True):
                norm = np.linalg.norm(embedding_array)
                if norm > 0:
                    embedding_array = embedding_array / norm
                    
            return embedding_array
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def add_embedding(self, text: str, metadata: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> bool:
        """Add a new embedding to the store.
        
        Args:
            text: Text to generate embedding for
            metadata: Associated metadata (GUID, timestamp, etc.)
            options: Optional dictionary with embedding options
            
        Returns:
            bool: True if successfully added
        """
        try:
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
            
            self.logger.info(f"Added embedding for text: '{text[:30]}...' with GUID: {metadata.get('guid', 'unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding embedding: {str(e)}")
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
        # Get query embedding
        if isinstance(query, str):
            try:
                query_embedding = self.generate_embedding(query)
            except Exception as e:
                self.logger.error(f"Error generating embedding for query: {str(e)}")
                return []
        else:
            query_embedding = query
        
        # Compute similarities
        similarities = []
        for embedding, metadata in self.embeddings:
            # Apply filters
            if min_importance and metadata.get('importance', 0) < min_importance:
                continue
                
            if date_range and 'timestamp' in metadata:
                try:
                    entry_date = datetime.fromisoformat(metadata['timestamp'])
                    if not (date_range[0] <= entry_date <= date_range[1]):
                        continue
                except (ValueError, TypeError):
                    # Skip entries with invalid timestamps
                    continue
            
            # Compute cosine similarity
            similarity = self.calculate_similarity(query_embedding, embedding)
            similarities.append((similarity, metadata))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Return top k results
        results = [
            {
                'score': float(score),  # Convert from numpy to Python float
                'metadata': metadata
            }
            for score, metadata in similarities[:k]
        ]
        
        self.logger.info(f"Search found {len(results)} results out of {len(similarities)} total embeddings")
        return results
    
    def update_embeddings(self, conversation_history: List[Dict]) -> bool:
        """Update embeddings for conversation history entries.
        
        Args:
            conversation_history: List of conversation entries
            
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
                    self.logger.info(f"Created backup of embeddings file: {backup_path}")
                except OSError:
                    self.logger.warning(f"Could not create backup of embeddings file")
            
            # Create a new embeddings file
            with open(self.embeddings_file, 'w'):
                pass  # Just create an empty file
            
            # Generate new embeddings
            success_count = 0
            total_count = 0
            
            for entry in conversation_history:
                total_count += 1
                
                # Generate embedding for full entry
                if self.add_embedding(
                    entry.get('content', ''),
                    {
                        'guid': entry.get('guid', ''),
                        'timestamp': entry.get('timestamp', datetime.now().isoformat()),
                        'role': entry.get('role', 'unknown'),
                        'type': 'full_entry'
                    }
                ):
                    success_count += 1
                
                # Generate embeddings for segments if available
                if 'digest' in entry and 'rated_segments' in entry['digest']:
                    for segment in entry['digest']['rated_segments']:
                        total_count += 1
                        if self.add_embedding(
                            segment.get('text', ''),
                            {
                                'guid': entry.get('guid', ''),
                                'timestamp': entry.get('timestamp', datetime.now().isoformat()),
                                'role': entry.get('role', 'unknown'),
                                'type': 'segment',
                                'importance': segment.get('importance', 3),
                                'topics': segment.get('topics', [])
                            }
                        ):
                            success_count += 1
            
            self.logger.info(f"Updated embeddings: {success_count}/{total_count} successful")
            return success_count > 0
        except Exception as e:
            self.logger.error(f"Error updating embeddings: {str(e)}")
            return False 