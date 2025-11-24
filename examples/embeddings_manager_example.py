#!/usr/bin/env python3
"""
EmbeddingsManager Example - Semantic Search in Conversation History

This example demonstrates how to use the EmbeddingsManager to:
1. Generate embeddings for conversation history entries
2. Store these embeddings persistently
3. Perform semantic search to find related conversations

This shows how RAG (Retrieval Augmented Generation) can be implemented
to enhance the agent's memory by finding contextually relevant information.
"""

import os
import json
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add parent directory to path to import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.utils.logging_config import LoggingConfig
from src.memory.embeddings_manager import EmbeddingsManager
from src.ai.llm_ollama import OllamaService

# Configuration - use environment variables with sensible defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Use a fixed example GUID for this standalone example
EXAMPLE_GUID = "embeddings_manager_example"

# File paths
TEST_DATA_DIR = Path("tests/memory_manager/memory_snapshots/rag")
CONVERSATION_FILE = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162_conversations.json"
OUTPUT_DIR = Path("examples/temp_data")
EMBEDDINGS_FILE = OUTPUT_DIR / "conversation_embeddings.jsonl"

def ensure_dir_exists(path: Path):
    """Ensure the directory exists."""
    path.mkdir(parents=True, exist_ok=True)

def load_conversation_history(file_path: Path) -> List[Dict[str, Any]]:
    """Load conversation history from JSON file.
    
    Args:
        file_path: Path to the conversation history JSON file
        
    Returns:
        List of conversation entries
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Extract entries from the conversation data
        if isinstance(data, dict) and "entries" in data:
            return data["entries"]
        else:
            print(f"Unexpected data format in {file_path}")
            return []
    except Exception as e:
        print(f"Error loading conversation history: {str(e)}")
        return []

def format_conversation_entry(entry: Dict[str, Any]) -> str:
    """Format a conversation entry for display.
    
    Args:
        entry: Conversation entry dictionary
        
    Returns:
        Formatted string representation
    """
    role = entry.get("role", "unknown").upper()
    content = entry.get("content", "").strip()
    timestamp = entry.get("timestamp", "")
    
    # Format timestamp if present
    date_str = ""
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            date_str = timestamp
    
    # Truncate content if too long
    if len(content) > 100:
        content = content[:97] + "..."
    
    return f"[{role}] ({date_str}): {content}"

def generate_and_store_embeddings(conversation_entries: List[Dict[str, Any]]) -> EmbeddingsManager:
    """Generate and store embeddings for all conversation entries.
    
    Args:
        conversation_entries: List of conversation entries
        
    Returns:
        Initialized EmbeddingsManager with stored embeddings
    """
    print("\nInitializing LLM service and embeddings manager...")
    
    # Set up logging using LoggingConfig
    llm_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "ollama_embeddings",
        log_to_console=False
    )
    embeddings_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "embeddings_manager",
        log_to_console=False
    )
    
    # Initialize LLM service with proper logging
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "logger": llm_logger
    })
    
    # Initialize embeddings manager with logger
    embeddings_manager = EmbeddingsManager(
        str(EMBEDDINGS_FILE),
        llm_service,
        logger=embeddings_logger
    )
    
    # Check if we need to generate embeddings
    if len(embeddings_manager.embeddings) > 0:
        print(f"Found {len(embeddings_manager.embeddings)} existing embeddings")
        return embeddings_manager
    
    print(f"Generating embeddings for conversation entries...")
    
    # Count of embeddings to be generated
    segment_count = 0
    entry_count = 0
    
    # Custom approach instead of update_embeddings to ensure full segment text is stored
    for entry in conversation_entries:
        entry_count += 1
        entry_guid = entry.get("guid", "")
        timestamp = entry.get("timestamp", datetime.now().isoformat())
        role = entry.get("role", "unknown")
        
        # Generate embedding for full entry
        if entry.get("content"):
            embeddings_manager.add_embedding(
                entry.get("content", ""),
                {
                    "guid": entry_guid,
                    "timestamp": timestamp,
                    "role": role,
                    "type": "full_entry"
                }
            )
        
        # Process digest segments if available
        if "digest" in entry and "rated_segments" in entry["digest"]:
            segments = entry["digest"]["rated_segments"]
            
            for i, segment in enumerate(segments):
                segment_count += 1
                segment_text = segment.get("text", "")
                
                if not segment_text:
                    continue
                
                # Store embedding with full segment text and metadata
                embeddings_manager.add_embedding(
                    segment_text,
                    {
                        "guid": entry_guid,
                        "timestamp": timestamp,
                        "role": role,
                        "type": "segment",
                        "segment_index": i,
                        "segment_text": segment_text,  # Store the full segment text
                        "importance": segment.get("importance", 3),
                        "topics": segment.get("topics", []),
                        "segment_type": segment.get("type", "information")
                    }
                )
    
    total_embeddings = len(embeddings_manager.embeddings)
    print(f"Successfully generated and stored {total_embeddings} embeddings:")
    print(f"- {entry_count} full entry embeddings")
    print(f"- {segment_count} segment embeddings")
    
    return embeddings_manager

def search_conversations(embeddings_manager: EmbeddingsManager, query: str, k: int = 5) -> List[Dict]:
    """Search for the most similar conversation entries.
    
    Args:
        embeddings_manager: EmbeddingsManager with stored embeddings
        query: Search query text
        k: Number of results to return
        
    Returns:
        List of search results with similarity scores and metadata
    """
    print(f"\nSearching for: '{query}'")
    
    try:
        # Perform search
        results = embeddings_manager.search(query, k=k)
        
        if not results:
            print("No matching results found")
            return []
            
        print(f"Found {len(results)} matching results")
        return results
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return []

def display_search_results(results: List[Dict], conversation_entries: List[Dict[str, Any]]):
    """Display search results with content and similarity scores.
    
    Args:
        results: Search results from embeddings_manager.search()
        conversation_entries: Original conversation entries
    """
    if not results:
        return
    
    print("\nSearch Results:")
    print("-" * 80)
    
    # Create a lookup table for faster access
    entry_lookup = {entry.get("guid", ""): entry for entry in conversation_entries}
    
    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        metadata = result.get("metadata", {})
        guid = metadata.get("guid", "")
        type_info = metadata.get("type", "unknown")
        
        print(f"\n{i}. MATCH (Score: {score:.4f}, Type: {type_info})")
        print("-" * 40)
        
        # If this is a segment match, show the full segment text from metadata
        if type_info == "segment":
            # Use the stored segment_text from metadata
            segment_text = metadata.get("segment_text", "")
            if not segment_text and "text" in metadata:
                # Fallback to text field if segment_text is not available
                segment_text = metadata.get("text", "")
                
            print(f"MATCHED SEGMENT: \"{segment_text}\"")
            
            # Show segment type if available
            segment_type = metadata.get("segment_type", "")
            if segment_type:
                print(f"TYPE: {segment_type}")
            
            # Show topics if available
            if "topics" in metadata and metadata["topics"]:
                topics = ", ".join(metadata["topics"])
                print(f"TOPICS: {topics}")
                
            # Show importance if available
            if "importance" in metadata:
                importance = metadata["importance"]
                stars = "*" * importance
                print(f"IMPORTANCE: {importance}/5 {stars}")
                
            # Show which entry it came from
            entry = entry_lookup.get(guid, {})
            role = entry.get("role", "unknown").upper()
            timestamp = entry.get("timestamp", "")
            
            # Format timestamp
            date_str = format_timestamp(timestamp)
            print(f"FROM: [{role}] ({date_str})")
            
            # Show the segment index if available
            if "segment_index" in metadata:
                print(f"SEGMENT INDEX: {metadata['segment_index']}")
        else:
            # For full entry matches, show the full entry
            entry = entry_lookup.get(guid, {})
            role = entry.get("role", "unknown").upper()
            content = entry.get("content", "").strip()
            timestamp = entry.get("timestamp", "")
            
            # Format timestamp
            date_str = format_timestamp(timestamp)
            print(f"[{role}] ({date_str}):")
            print(f"{content}")
            
        print(f"GUID: {guid}")
        print("-" * 80)

def format_timestamp(timestamp: str) -> str:
    """Format a timestamp string for display.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Formatted date/time string for display
    """
    if not timestamp:
        return ""
        
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp

def explain_rag_integration():
    """Explain how this example relates to RAG integration in the memory system."""
    print("\nRAG Integration Explanation:")
    print("-" * 80)
    print("This example demonstrates a key component of RAG (Retrieval Augmented Generation):")
    print("1. When the agent receives a user query, it can use semantic search to find")
    print("   relevant historical conversations instead of relying only on recent history.")
    print("2. These relevant conversations provide better context for the LLM to generate")
    print("   more accurate and contextually appropriate responses.")
    print("3. The similarity scores help determine which historical entries are most")
    print("   relevant to include in the limited context window.")
    print()
    print("Integration with query_memory.prompt would involve:")
    print("1. Using the user's query to find semantically similar past conversations")
    print("2. Adding the most relevant ones to the RECENT_CONVERSATION_HISTORY section")
    print("3. This gives the LLM access to relevant historical context that might not")
    print("   be in the most recent conversations or in the compressed memory.")
    print("-" * 80)

def run_interactive_demo(embeddings_manager: EmbeddingsManager, conversation_entries: List[Dict[str, Any]]):
    """Run an interactive demo allowing the user to search the conversation history.
    
    Args:
        embeddings_manager: EmbeddingsManager with stored embeddings
        conversation_entries: Original conversation entries
    """
    print("\nInteractive Semantic Search Demo")
    print("Enter search queries to find similar conversations, or 'exit' to quit.")
    
    while True:
        query = input("\nSearch query: ").strip()
        
        if query.lower() in ("exit", "quit"):
            break
            
        if not query:
            continue
            
        results = search_conversations(embeddings_manager, query)
        display_search_results(results, conversation_entries)

def main():
    """Main function demonstrating embeddings generation and semantic search."""
    print("EmbeddingsManager Example - Semantic Search in Conversation History")
    print(f"Using Ollama at {OLLAMA_BASE_URL} with model {OLLAMA_EMBED_MODEL}")
    
    # Ensure output directory exists
    ensure_dir_exists(OUTPUT_DIR)
    
    # Check if conversation file exists
    if not CONVERSATION_FILE.exists():
        print(f"Error: Conversation file not found at {CONVERSATION_FILE}")
        print(f"Please ensure the test data file exists.")
        return
    
    # Load conversation history
    conversation_entries = load_conversation_history(CONVERSATION_FILE)
    if not conversation_entries:
        print("No conversation entries found")
        return
        
    print(f"Loaded {len(conversation_entries)} conversation entries")
    
    # Generate and store embeddings
    embeddings_manager = generate_and_store_embeddings(conversation_entries)
    
    # Show example searches
    example_queries = [
        "Tell me about the Lost Valley",
        "What quest is available?",
        "How can I earn gold?",
        "Information about the goblins",
        "Where are the ancient ruins located?"
    ]
    
    print("\nExample Searches:")
    for query in example_queries:
        results = search_conversations(embeddings_manager, query)
        display_search_results(results, conversation_entries)
    
    # Explain RAG integration
    explain_rag_integration()
    
    # Run interactive demo
    run_interactive_demo(embeddings_manager, conversation_entries)
    
    print(f"\nLogs saved to: {LoggingConfig.get_log_base_dir(EXAMPLE_GUID)}")
    print(f"Embeddings saved to: {EMBEDDINGS_FILE}")

if __name__ == "__main__":
    main()