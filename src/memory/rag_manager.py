"""RAG (Retrieval Augmented Generation) Manager for enhanced memory retrieval.

This module implements RAG capabilities to improve the LLM-driven Agent's memory access
and response generation. RAG combines the power of semantic search with LLM generation
to provide more accurate, contextually relevant responses.

Key Features:
1. Semantic Search Integration
   - Uses embeddings to find relevant conversation history entries
   - Supports both full-text and segment-level search
   - Enables finding related information across different conversations

2. Context Enhancement
   - Retrieves relevant historical context for current queries
   - Combines static memory with dynamic conversation history
   - Provides better continuity across multiple interactions

3. Memory Augmentation
   - Enhances LLM responses with retrieved context
   - Maintains conversation coherence
   - Reduces hallucination by grounding responses in actual history

Implementation Strategy:

1. Memory Indexing
   - Index both static memory and conversation history
   - Generate embeddings for:
     * Full conversation entries
     * Individual segments from digests
     * Topics and key concepts
   - Maintain separate indices for different types of content

2. Retrieval Process
   - Convert user query to embedding
   - Search across all indices for relevant content
   - Rank results by relevance and recency
   - Apply importance filtering
   - Return top-k most relevant entries

3. Context Assembly
   - Combine retrieved content with current context
   - Format for optimal LLM consumption
   - Maintain source attribution
   - Handle overlapping/redundant information

4. Response Generation
   - Use retrieved context to enhance LLM prompts
   - Ensure responses are grounded in actual history
   - Maintain conversation flow and coherence
   - Track which retrieved content influenced the response

5. Performance Optimization
   - Implement caching for frequent queries
   - Use batch processing for embedding generation
   - Maintain efficient index structures
   - Support incremental updates

Integration Points:

1. MemoryManager Integration
   - Hook into memory update process
   - Index new content as it's added
   - Maintain consistency with memory compression
   - Support memory reconstruction from indices

2. LLM Service Integration
   - Enhance prompts with retrieved context
   - Track which retrieved content influenced responses
   - Support different retrieval strategies for different types of queries

3. Conversation History Integration
   - Index new conversation entries
   - Support temporal queries (e.g., "what did we discuss last week?")
   - Enable finding related conversations

4. Domain-Specific Customization
   - Support domain-specific retrieval strategies
   - Allow custom importance weighting
   - Enable specialized indexing for domain concepts

Usage Example:
```python
# Initialize RAG Manager
rag_manager = RAGManager(
    embeddings_manager=embeddings_manager,
    llm_service=llm_service,
    memory_manager=memory_manager
)

# Query with RAG enhancement
response = rag_manager.query(
    query="What did we discuss about the mountain troll?",
    context={
        "importance_threshold": 3,
        "max_results": 5,
        "include_static_memory": True
    }
)
```

Future Enhancements:
1. Multi-hop Retrieval
   - Chain multiple retrieval steps
   - Follow references between related content
   - Build knowledge graphs from retrieved content

2. Active Learning
   - Track which retrieved content was useful
   - Improve retrieval based on feedback
   - Adapt to user's information needs

3. Temporal Reasoning
   - Track how information evolves over time
   - Handle conflicting or outdated information
   - Support temporal queries

4. Cross-Conversation Analysis
   - Identify patterns across conversations
   - Build topic hierarchies
   - Support meta-level queries about conversation history
"""

from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime
import os
import logging

class RAGManager:
    """Manages Retrieval Augmented Generation for enhancing memory queries.
    
    The RAGManager integrates with EmbeddingsManager to provide semantic search
    capabilities and context enhancement for memory queries. It:
    
    1. Performs semantic searches for relevant context
    2. Formats search results into context for memory queries
    3. Integrates with the memory system to enhance queries with relevant context
    4. Handles updates to the embeddings indices
    
    This enables agents to retrieve contextually relevant information from
    conversation history based on semantic similarity rather than just
    recency or exact keyword matches.
    """
    
    def __init__(self, llm_service, embeddings_manager, logger=None):
        """Initialize the RAGManager.
        
        Args:
            llm_service: Service for LLM operations
            embeddings_manager: Manager for embeddings and semantic search
            logger: Optional logger instance
        """
        self.llm_service = llm_service
        self.embeddings_manager = embeddings_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def query(self, query_text: str, limit: int = 5, min_importance: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query for semantically relevant context.
        
        Args:
            query_text: The text query to find relevant context for
            limit: Maximum number of results to return (default: 5)
            min_importance: Minimum importance level (1-5) for results
            
        Returns:
            List of relevant context items with text, score, and metadata
        """
        try:
            self.logger.debug(f"Querying for: '{query_text}' (limit={limit}, min_importance={min_importance})")
            
            # Get search results
            search_results = self.embeddings_manager.search(query_text, k=limit*2, min_importance=min_importance)
            self.logger.debug(f"Search returned {len(search_results)} raw results")
            
            # Transform results to include the text
            enhanced_results = []
            for i, result in enumerate(search_results):
                # Get the metadata
                metadata = result.get("metadata", {})
                score = result.get("score", 0)
                
                # Extract text from various possible locations
                text = None
                
                # Try to get text directly from result
                if "text" in result:
                    text = result["text"]
                # Try to get from metadata
                elif "text" in metadata:
                    text = metadata["text"]
                # For segments, check if segment text exists
                elif "segment_text" in metadata:
                    text = metadata["segment_text"]
                # For full entries, use content
                elif "content" in metadata:
                    text = metadata["content"]
                
                # Skip results without text
                if not text:
                    self.logger.debug(f"Skipping result {i} - no text found")
                    continue
                
                # Prepare the enhanced result
                enhanced_result = {
                    "score": score,
                    "text": text,
                    "metadata": metadata
                }
                
                enhanced_results.append(enhanced_result)
                self.logger.debug(f"Added result {i}: score={score:.4f}, text='{text[:50]}...'")
            
            # Sort by score (highest first) and limit
            enhanced_results.sort(key=lambda x: x["score"], reverse=True)
            results = enhanced_results[:limit]
            
            self.logger.debug(f"Returning {len(results)} processed results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in RAG query: {str(e)}")
            return []
    
    def format_enhanced_context(self, query_text: str, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into a structured context for memory enhancement.
        
        Args:
            query_text: Original query text (for reference)
            search_results: Results from semantic search
            
        Returns:
            Formatted context string for inclusion in memory query
        """
        if not search_results:
            self.logger.debug("No search results to format as context")
            return ""
        
        # Start with header
        context = "SEMANTICALLY_RELEVANT_CONTEXT (Information specifically related to your query):\n\n"
        
        # Add each result with its importance level
        for i, result in enumerate(search_results):
            # Get importance level (default to 3 if not specified)
            importance = result.get("metadata", {}).get("importance", 3)
            # Get topics if available
            topics = result.get("metadata", {}).get("topics", [])
            
            # Format the result
            topics_str = f" (Topics: {', '.join(topics)})" if topics else ""
            context += f"[!{importance}] {result['text']}{topics_str}\n\n"
        
        self.logger.debug(f"Generated context with {len(search_results)} items")
        return context
    
    def enhance_memory_query(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a memory query with semantically relevant context.
        
        Args:
            query_context: Dictionary containing original query context:
                           - query: The query text
                           - domain_specific_prompt_instructions: Domain-specific instructions
                           - static_memory: Static memory text
                           - previous_context: Previous context text
                           - conversation_history: Recent conversation history
                           
        Returns:
            Enhanced query context with RAG context added
        """
        # Make a copy of the original context to avoid modifying it
        enhanced_context = query_context.copy()
        
        try:
            # Extract the query text
            query_text = query_context.get("query", "")
            self.logger.debug(f"Enhancing memory query: '{query_text}'")
            
            # Search for relevant content
            search_results = self.query(
                query_text,
                limit=5,
                min_importance=2  # Only include moderately important content and above
            )
            
            # Format the results as context
            if search_results:
                rag_context = self.format_enhanced_context(query_text, search_results)
                enhanced_context["rag_context"] = rag_context
                self.logger.debug(f"Added RAG context of length {len(rag_context)}")
            else:
                enhanced_context["rag_context"] = ""
                self.logger.debug("No relevant context found for query")
            
            return enhanced_context
            
        except Exception as e:
            self.logger.error(f"Error enhancing memory query: {str(e)}")
            enhanced_context["rag_context"] = ""
            return enhanced_context
    
    # Embedding/indexing is now fully delegated to EmbeddingsManager.
    # For incremental updates, use self.embeddings_manager.update_indices(new_entries)
    # For full reindexing, use self.embeddings_manager.update_embeddings(conversation_entries)
    
    def _format_context_as_text(self, context) -> str:
        """Format context items as text for inclusion in prompts.
        
        Handles both list and dictionary formats.
        
        Args:
            context: Context items to format (list or dict)
            
        Returns:
            Formatted text representation
        """
        if not context:
            return ""
            
        # Handle list format
        if isinstance(context, list):
            formatted_items = []
            for item in context:
                if isinstance(item, dict) and "text" in item:
                    # Format with importance if available
                    importance = item.get("importance", 3)
                    formatted_items.append(f"[!{importance}] {item['text']}")
                elif isinstance(item, str):
                    formatted_items.append(item)
            
            return "\n\n".join(formatted_items)
            
        # Handle dictionary format
        elif isinstance(context, dict):
            # Either use the items or text field
            if "items" in context:
                return self._format_context_as_text(context["items"])
            elif "text" in context:
                return context["text"]
            else:
                # Try to convert the whole dict to string
                try:
                    return str(context)
                except:
                    return ""
        
        # Handle string or other formats
        return str(context)
