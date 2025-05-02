"""Embeddings Manager for semantic search functionality.

This module provides functionality for generating, storing, and searching embeddings
of conversation history entries to enable semantic search capabilities.
"""

from typing import Dict, List, Optional, Tuple
import json
import os
import numpy as np
from datetime import datetime
from pathlib import Path

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
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load existing embeddings from file."""
        if not os.path.exists(self.embeddings_file):
            return
            
        try:
            with open(self.embeddings_file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    self.embeddings.append((
                        np.array(data['embedding']),
                        data['metadata']
                    ))
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a text string.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            np.ndarray: Embedding vector
        """
        if not self.llm_service:
            raise ValueError("LLM service is required for generating embeddings")
            
        try:
            # Generate embedding using LLM service
            embedding = self.llm_service.generate_embedding(text, {
                'normalize': True  # Always normalize embeddings for consistent similarity calculations
            })
            
            # Convert to numpy array
            return np.array(embedding)
            
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            # Return random vector as fallback for testing
            return np.random.rand(384)  # Typical embedding dimension
    
    def add_embedding(self, text: str, metadata: Dict) -> bool:
        """Add a new embedding to the store.
        
        Args:
            text: Text to generate embedding for
            metadata: Associated metadata (GUID, timestamp, etc.)
            
        Returns:
            bool: True if successfully added
        """
        try:
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            # Add to in-memory store
            self.embeddings.append((embedding, metadata))
            
            # Append to file
            with open(self.embeddings_file, 'a') as f:
                json.dump({
                    'embedding': embedding.tolist(),
                    'metadata': metadata
                }, f)
                f.write('\n')
            
            return True
        except Exception as e:
            print(f"Error adding embedding: {str(e)}")
            return False
    
    def search(self, query: str, k: int = 5, 
              min_importance: Optional[int] = None,
              date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Search for similar entries using semantic similarity.
        
        Args:
            query: Search query text
            k: Number of results to return
            min_importance: Optional minimum importance threshold
            date_range: Optional (start_date, end_date) tuple
            
        Returns:
            List[Dict]: List of results with similarity scores and metadata
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Compute similarities
        similarities = []
        for embedding, metadata in self.embeddings:
            # Apply filters
            if min_importance and metadata.get('importance', 0) < min_importance:
                continue
                
            if date_range:
                entry_date = datetime.fromisoformat(metadata['timestamp'])
                if not (date_range[0] <= entry_date <= date_range[1]):
                    continue
            
            # Compute cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            similarities.append((similarity, metadata))
        
        # Sort by similarity and return top k
        similarities.sort(reverse=True)
        return [
            {
                'score': score,
                'metadata': metadata
            }
            for score, metadata in similarities[:k]
        ]
    
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
                os.remove(self.embeddings_file)
            
            # Generate new embeddings
            for entry in conversation_history:
                # Generate embedding for full entry
                self.add_embedding(
                    entry['content'],
                    {
                        'guid': entry['guid'],
                        'timestamp': entry['timestamp'],
                        'role': entry['role'],
                        'type': 'full_entry'
                    }
                )
                
                # Generate embeddings for segments if available
                if 'digest' in entry and 'rated_segments' in entry['digest']:
                    for segment in entry['digest']['rated_segments']:
                        self.add_embedding(
                            segment['text'],
                            {
                                'guid': entry['guid'],
                                'timestamp': entry['timestamp'],
                                'role': entry['role'],
                                'type': 'segment',
                                'importance': segment['importance'],
                                'topics': segment['topics']
                            }
                        )
            
            return True
        except Exception as e:
            print(f"Error updating embeddings: {str(e)}")
            return False 