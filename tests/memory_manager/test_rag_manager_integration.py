"""Integration tests for the RAGManager class with actual LLM calls."""

import pytest
import os
import json
import numpy as np
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

from src.memory.rag_manager import RAGManager
from src.memory.embeddings_manager import EmbeddingsManager
from src.ai.llm_ollama import OllamaService

# Test data paths - memory snapshots from a DND game
TEST_DATA_DIR = Path("tests/memory_manager/memory_snapshots/rag")
TEST_MEMORY_PATH = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162.json"
TEST_CONVERSATIONS_PATH = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162_conversations.json"

# Configure Ollama connection
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3")

# Development settings for temp files
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")
DEV_TEMP_DIR = Path("tests/test_files/tmp")

def clear_file(file_path):
    """Ensure the file exists and is empty to start with a clean state.
    
    This helps prevent test interference when running in DEV_MODE.
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create or truncate the file to ensure it's empty
    with open(file_path, 'w') as f:
        pass
    
    print(f"Cleared file for testing: {file_path}")

@pytest.fixture
def llm_service():
    """Create an instance of OllamaService for testing."""
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_LLM_MODEL,
        "debug": True,
        "debug_scope": "test_rag_manager",
        "console_output": True
    })

@pytest.fixture
def embeddings_service():
    """Create an instance of OllamaService for embeddings."""
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "debug": True,
        "debug_scope": "test_embeddings_manager",
        "console_output": True
    })
    
@pytest.fixture
def temp_embeddings_file():
    """Create a temporary embeddings file for testing."""
    if DEV_MODE:
        # Create the dev temp directory if it doesn't exist
        DEV_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"embeddings_test_{timestamp}.jsonl"
        temp_path = DEV_TEMP_DIR / filename
        
        # Create the file
        temp_path.touch()
        print(f"[DEV MODE] Created test file at: {temp_path}")
        
        yield str(temp_path)
        
        # In dev mode, we don't delete the file
        print(f"[DEV MODE] Keeping test file for inspection: {temp_path}")
    else:
        # Standard tempfile behavior for normal test runs
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as temp_file:
            temp_path = temp_file.name
            print(f"Created temporary embeddings file: {temp_path}")
        
        yield temp_path
        
        # Clean up after test
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"Removed temporary file: {temp_path}")

@pytest.fixture
def test_conversation_data():
    """Load test conversation data from the snapshot file."""
    if not TEST_CONVERSATIONS_PATH.exists():
        pytest.skip(f"Test conversation data not found at {TEST_CONVERSATIONS_PATH}")
        
    with open(TEST_CONVERSATIONS_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture
def test_memory_data():
    """Load test memory data from the snapshot file."""
    if not TEST_MEMORY_PATH.exists():
        pytest.skip(f"Test memory data not found at {TEST_MEMORY_PATH}")
        
    with open(TEST_MEMORY_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture
def embeddings_manager(embeddings_service, temp_embeddings_file, test_conversation_data):
    """Create and initialize an EmbeddingsManager with test data."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    # Create manager
    manager = EmbeddingsManager(temp_embeddings_file, embeddings_service)
    
    # Get conversation entries
    entries = test_conversation_data.get("entries", [])
    if not entries:
        pytest.skip("No entries found in test conversation data")
    
    # Update embeddings from this history
    success = manager.update_embeddings(entries)
    if not success:
        pytest.skip("Failed to update embeddings")
    
    return manager

@pytest.fixture
def rag_manager(llm_service, embeddings_manager):
    """Create a RAGManager instance for testing."""
    return RAGManager(llm_service, embeddings_manager)

def test_rag_manager_init(llm_service, embeddings_manager):
    """Test that the RAGManager initializes correctly."""
    manager = RAGManager(llm_service, embeddings_manager)
    assert manager.llm_service == llm_service
    assert manager.embeddings_manager == embeddings_manager

def test_query(rag_manager):
    """Test querying for relevant context."""
    # Basic query
    query = "What do I know about spiders?"
    results = rag_manager.query(query, limit=3)
    
    # Check structure
    assert isinstance(results, list)
    assert len(results) <= 3
    
    if results:
        # Verify result structure
        assert "score" in results[0]
        assert "text" in results[0]
        assert "metadata" in results[0]
        
        # Check scores are in descending order
        scores = [r["score"] for r in results]
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

def test_format_enhanced_context(rag_manager):
    """Test formatting relevant results as context."""
    # Sample query and mock results
    query = "What do I know about treasure?"
    mock_results = [
        {
            "score": 0.92,
            "text": "The village has offered a reward of 1000 gold coins.",
            "metadata": {
                "importance": 5,
                "topics": ["treasure", "quest"],
                "guid": "test-guid-1"
            }
        },
        {
            "score": 0.85,
            "text": "Captain Silas mentioned ancient relics might be found in the caves.",
            "metadata": {
                "importance": 4,
                "topics": ["treasure", "caves"],
                "guid": "test-guid-2"
            }
        }
    ]
    
    # Format context
    context = rag_manager.format_enhanced_context(query, mock_results)
    
    # Check that context is a non-empty string
    assert isinstance(context, str)
    assert len(context.strip()) > 0
    
    # Check that context includes our relevant information
    assert "gold coins" in context
    assert "ancient relics" in context
    
    # Check that importance indicators are included
    assert "[!5]" in context or "**" in context  # Importance indicators

def test_enhance_memory_query(rag_manager, test_memory_data):
    """Test enhancing a memory query with RAG context."""
    # Basic query
    query_context = {
        "query": "What rewards are offered for completing quests?",
        "domain_instructions": "You are a helpful assistant",
        "static_memory": test_memory_data.get("static_memory", ""),
        "conversation_history": "User: What rewards can I earn?\nAgent: Let me check my memory."
    }
    
    # Enhance with RAG
    enhanced_context = rag_manager.enhance_memory_query(query_context)
    
    # Check that the enhanced context includes the RAG section
    assert "SEMANTICALLY_RELEVANT_CONTEXT" in enhanced_context.get("rag_context", "")
    
    # All other fields should be preserved
    assert enhanced_context["query"] == query_context["query"]
    assert enhanced_context["domain_instructions"] == query_context["domain_instructions"]
    assert enhanced_context["static_memory"] == query_context["static_memory"]

@pytest.mark.skipif(not TEST_CONVERSATIONS_PATH.exists(), 
                    reason=f"Test conversation data not found at {TEST_CONVERSATIONS_PATH}")
def test_index_memory(rag_manager, test_conversation_data):
    """Test indexing memory with the RAG manager."""
    # Get conversation entries
    entries = test_conversation_data.get("entries", [])
    assert len(entries) > 0, "No entries found in test conversation data"
    
    # Create a tiny subset for testing
    test_entries = entries[:2]
    
    # Index memory
    success = rag_manager.index_memory(test_entries)
    assert success is True
    
    # Test a query after indexing
    query = "What information do we have?"
    results = rag_manager.query(query, limit=2)
    
    # Check that results were returned
    assert isinstance(results, list)
    assert len(results) > 0

def test_update_indices(rag_manager, test_conversation_data):
    """Test updating indices with new conversation entries."""
    # Get conversation entries
    entries = test_conversation_data.get("entries", [])
    assert len(entries) > 0, "No entries found in test conversation data"
    
    # Create a tiny subset for testing
    test_entries = entries[:1]
    
    # Update indices with subset
    success = rag_manager.update_indices(test_entries)
    assert success is True
    
    # Test a query after updating indices
    query = "What was recently discussed?"
    results = rag_manager.query(query, limit=2)
    
    # Check that results were returned
    assert isinstance(results, list)
    assert len(results) > 0
