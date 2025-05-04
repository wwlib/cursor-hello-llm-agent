#!/usr/bin/env python3
"""
RAG-Enhanced Memory Example

This example demonstrates integrating RAG (Retrieval Augmented Generation) 
with the memory system to provide enhanced responses by finding semantically 
similar information from past conversations.

The example:
1. Loads conversation history from a test file
2. Sets up MemoryManager, EmbeddingsManager, and RAGManager
3. Processes sample queries with and without RAG enhancement
4. Shows how RAG improves response quality with relevant context
"""

import os
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests
import time

# Add parent directory to path to import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.memory.memory_manager import MemoryManager
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.rag_manager import RAGManager
from src.ai.llm_ollama import OllamaService

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.173:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# File paths
TEST_DATA_DIR = Path("tests/memory_manager/memory_snapshots/rag")
MEMORY_FILE = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162.json"
CONVERSATION_FILE = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162_conversations.json"
OUTPUT_DIR = Path("examples/temp_data")
EMBEDDINGS_FILE = OUTPUT_DIR / "rag_conversation_embeddings.jsonl"
NEW_MEMORY_FILE = OUTPUT_DIR / "rag_memory.json"

def ensure_dir_exists(path: Path):
    """Ensure the directory exists."""
    path.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load test data files."""
    # Check files exist
    if not MEMORY_FILE.exists() or not CONVERSATION_FILE.exists():
        print(f"Error: Required test files not found")
        print(f"Memory file: {MEMORY_FILE} - {'EXISTS' if MEMORY_FILE.exists() else 'MISSING'}")
        print(f"Conversation file: {CONVERSATION_FILE} - {'EXISTS' if CONVERSATION_FILE.exists() else 'MISSING'}")
        return None, None

    # Load memory file
    try:
        with open(MEMORY_FILE, 'r') as f:
            memory_data = json.load(f)
            print(f"Loaded memory data with GUID: {memory_data.get('guid')}")
    except Exception as e:
        print(f"Error loading memory file: {str(e)}")
        memory_data = None

    # Load conversation file
    try:
        with open(CONVERSATION_FILE, 'r') as f:
            conversation_data = json.load(f)
            print(f"Loaded {len(conversation_data.get('entries', []))} conversation entries")
    except Exception as e:
        print(f"Error loading conversation file: {str(e)}")
        conversation_data = None

    return memory_data, conversation_data

def check_ollama_connection():
    """Check if Ollama server is running and accessible.
    
    Returns:
        bool: True if connection is successful
    """
    print(f"\nChecking Ollama server at {OLLAMA_BASE_URL}...")
    
    try:
        # Check server is up
        tags_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if tags_response.status_code != 200:
            print(f"Warning: Ollama responded with status code {tags_response.status_code}")
            return False
            
        # Parse available models
        models_data = tags_response.json()
        available_models = []
        
        # Handle different response formats
        if "models" in models_data:
            available_models = [model.get("name") for model in models_data["models"]]
        elif "models" not in models_data and isinstance(models_data, list):
            # Alternative format
            available_models = [model.get("name") for model in models_data]
        
        print(f"Ollama is running. Available models: {available_models}")
        
        # Test generation model with a simple request
        print(f"\nTesting model '{OLLAMA_MODEL}'...")
        try:
            gen_test = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate", 
                json={"model": OLLAMA_MODEL, "prompt": "test", "stream": False}
            )
            if gen_test.status_code == 200:
                print(f"Success: Model '{OLLAMA_MODEL}' is working.")
            else:
                print(f"Warning: Model '{OLLAMA_MODEL}' test failed with status {gen_test.status_code}.")
                print("You may need to run: ollama pull " + OLLAMA_MODEL)
        except Exception as e:
            print(f"Error testing model '{OLLAMA_MODEL}': {str(e)}")
            
        # Test embedding model
        print(f"\nTesting embedding model '{OLLAMA_EMBED_MODEL}'...")
        try:
            embed_test = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings", 
                json={"model": OLLAMA_EMBED_MODEL, "prompt": "test"}
            )
            if embed_test.status_code == 200:
                print(f"Success: Embedding model '{OLLAMA_EMBED_MODEL}' is working.")
            else:
                print(f"Warning: Embedding model '{OLLAMA_EMBED_MODEL}' test failed with status {embed_test.status_code}.")
                print("You may need to run: ollama pull " + OLLAMA_EMBED_MODEL)
        except Exception as e:
            print(f"Error testing embedding model '{OLLAMA_EMBED_MODEL}': {str(e)}")
        
        return True
            
    except Exception as e:
        print(f"Error connecting to Ollama server: {str(e)}")
        print(f"Please make sure Ollama is running at {OLLAMA_BASE_URL}")
        return False

def setup_managers():
    """Set up the necessary managers for the example."""
    # Ensure output directory exists
    ensure_dir_exists(OUTPUT_DIR)

    # Print configuration for debugging
    print(f"\nConfiguration:")
    print(f"Ollama Base URL: {OLLAMA_BASE_URL}")
    print(f"Ollama Model: {OLLAMA_MODEL}")
    print(f"Ollama Embed Model: {OLLAMA_EMBED_MODEL}")
    
    # Check Ollama connection - already done in run_example function
    
    # Create LLM Service - one for generation, one for embeddings
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "debug": True,
        "debug_file": "rag_example.log",
        "debug_scope": "rag_example",
        "console_output": False
    })
    
    embed_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "debug": True,
        "debug_file": "rag_example_embeddings.log",
        "debug_scope": "rag_embeddings",
        "console_output": False
    })

    # Create Memory Manager with the loaded data
    memory_guid = str(uuid.uuid4())  # Generate new GUID for this example
    memory_manager = MemoryManager(
        memory_file=str(NEW_MEMORY_FILE),
        llm_service=llm_service,
        memory_guid=memory_guid
    )

    # Create Embeddings Manager
    embeddings_manager = EmbeddingsManager(
        embeddings_file=str(EMBEDDINGS_FILE),
        llm_service=embed_service
    )

    # Create RAG Manager
    rag_manager = RAGManager(
        embeddings_manager=embeddings_manager,
        llm_service=llm_service,
        memory_manager=memory_manager
    )

    return memory_manager, embeddings_manager, rag_manager

def initialize_memory(memory_manager, memory_data):
    """Initialize memory with the loaded data."""
    # Create initial memory with system prompt
    system_prompt = """
    You are a helpful AI assistant for a fantasy role-playing game.
    You assist the game master and players with information about the game world,
    character management, and quest tracking.
    """
    
    # Use static memory from loaded data if available
    if memory_data and "static_memory" in memory_data:
        # Get the raw static memory to preserve formatting
        system_prompt = memory_data["static_memory"] 
        
    success = memory_manager.create_initial_memory(system_prompt)
    if success:
        print("Successfully initialized memory")
        
        # If we have context from the original memory, copy it
        if memory_data and "context" in memory_data:
            memory_manager.memory["context"] = memory_data["context"]
            print(f"Copied {len(memory_data['context'])} context entries from original memory")
            memory_manager.save_memory("initialize_with_context")
    else:
        print("Failed to initialize memory")

def initialize_conversation_history(memory_manager, conversation_data):
    """Initialize conversation history from the loaded data."""
    if not conversation_data or "entries" not in conversation_data:
        print("No conversation entries to initialize")
        return False
        
    # Add all conversation entries to history
    entries = conversation_data["entries"]
    for entry in entries:
        memory_manager.add_to_conversation_history(entry)
    
    print(f"Added {len(entries)} entries to conversation history")
    return True

def index_conversations(rag_manager, conversation_data):
    """Index conversations for semantic search."""
    if not conversation_data or "entries" not in conversation_data:
        print("No conversation entries to index")
        return False
        
    # Index all conversation entries
    entries = conversation_data["entries"]
    success = rag_manager.update_indices(entries)
    
    if success:
        print(f"Successfully indexed {len(entries)} conversation entries")
    else:
        print("Failed to index conversation entries")
        
    return success

def process_query(memory_manager, rag_manager, query_text, use_rag=False):
    """Process a query with or without RAG enhancement."""
    print("\n" + "=" * 80)
    print(f"QUERY: {query_text}")
    print(f"Using RAG: {'YES' if use_rag else 'NO'}")
    print("-" * 80)
    
    # Create query context
    if use_rag:
        # Use RAG to enhance the query with relevant historical context
        query_context = rag_manager.enhance_memory_query(query_text)
        print("\nRAG CONTEXT:")
        print(query_context.get("rag_context", "No RAG context available"))
    else:
        # Standard query without RAG
        query_context = {
            "user_message": query_text
        }
    
    # Query memory
    start_time = datetime.now()
    response = memory_manager.query_memory(query_context)
    end_time = datetime.now()
    
    # Display results
    print("\nRESPONSE:")
    print(response)
    print("\nProcessing time:", (end_time - start_time).total_seconds(), "seconds")
    print("=" * 80)
    
    return response

def run_example():
    """Run the RAG integration example."""
    print("RAG-Enhanced Memory Example")
    print("=" * 80)
    
    # Check Ollama connection first
    if not check_ollama_connection():
        print("Error: Cannot connect to Ollama server. Exiting.")
        decision = input("Do you want to continue anyway? (y/n): ")
        if decision.lower() != 'y':
            return
    
    # Load test data
    memory_data, conversation_data = load_data()
    if not memory_data or not conversation_data:
        print("Failed to load required test data")
        return
    
    # Set up managers
    memory_manager, embeddings_manager, rag_manager = setup_managers()
    
    # Initialize memory and conversation history
    initialize_memory(memory_manager, memory_data)
    initialize_conversation_history(memory_manager, conversation_data)
    
    # Index conversations for semantic search
    index_conversations(rag_manager, conversation_data)
    
    # Example queries to test with and without RAG
    test_queries = [
        "Tell me about the ancient ruins",
        "What do I know about the goblins?",
        "How many gold pieces do I have?",
        "What is Elena's current quest?",
        "What settlements are in the Lost Valley?"
    ]
    
    # Process each query with and without RAG
    for query in test_queries:
        # Standard query without RAG
        process_query(memory_manager, rag_manager, query, use_rag=False)
        
        # Enhanced query with RAG
        process_query(memory_manager, rag_manager, query, use_rag=True)

    print_section_header("RAG Enhanced Memory Query Example")
    
    # Sample queries to test
    test_queries = [
        "What reward is being offered for the spider problem?",
        "Tell me about the ancient relics",
        "Who should I talk to about the mines?",
        "What equipment do I need for this quest?"
    ]
    
    # Test each query with and without RAG enhancement
    for query in test_queries:
        print(f"\nQUERY: {query}")
        print("-" * 40)
        
        # First, query without RAG
        print("\nMemory Query WITHOUT RAG enhancement:")
        standard_response = memory_manager.query_memory({"query": query})
        print(standard_response.get("response", "No response generated"))
        
        # Now query with RAG enhancement
        print("\nMemory Query WITH RAG enhancement:")
        
        # Create query context
        query_context = {
            "query": query,
            "domain_instructions": memory_manager.domain_config["domain_instructions"],
            "static_memory": memory_manager.memory.get("static_memory", ""),
            "previous_context": memory_manager.get_formatted_context(),
            "conversation_history": memory_manager.get_formatted_recent_conversations()
        }
        
        # Enhance with RAG
        enhanced_context = rag_manager.enhance_memory_query(query_context)
        
        # Print the RAG context that was added
        print("\nRAG CONTEXT ADDED:")
        print(enhanced_context.get("rag_context", "No RAG context generated"))
        
        # Query with enhanced context
        rag_response = memory_manager.query_memory(enhanced_context)
        print("\nRAG-ENHANCED RESPONSE:")
        print(rag_response.get("response", "No response generated"))
        
        # Short delay between queries
        time.sleep(1)
    
    print_section_header("Example Complete")
    print("\nTemporary files used in this example were saved to:")
    print(f"Memory file: {NEW_MEMORY_FILE}")
    print(f"Embeddings file: {EMBEDDINGS_FILE}")

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_json(data, indent=2):
    """Print JSON in a readable format"""
    print(json.dumps(data, indent=indent))

if __name__ == "__main__":
    run_example() 