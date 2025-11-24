import os
import json
import pytest
import asyncio
from datetime import datetime
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService
from src.utils.logging_config import LoggingConfig
from examples.domain_configs import USER_STORY_CONFIG

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "memory_snapshots")
INPUT_MEMORY_FILE = os.path.join(TEST_DATA_DIR, "agent_memory_for_compression_testing.json")

# Use environment variables with sensible defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Test GUID for logging
TEST_GUID = "memory_compression_test"

@pytest.fixture
def llm_service():
    """Create a real OllamaService instance for integration testing"""
    # Use LoggingConfig for consistent logging
    general_logger = LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "ollama_general",
        log_to_console=False
    )
    digest_logger = LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "ollama_digest",
        log_to_console=False
    )
    embeddings_logger = LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "ollama_embeddings",
        log_to_console=False
    )
    
    # General query service
    general_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.7,
        "stream": False,
        "logger": general_logger
    })
    
    # Digest generation service
    digest_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0,
        "stream": False,
        "logger": digest_logger
    })
    
    # Embeddings service
    embeddings_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "logger": embeddings_logger
    })
    
    return general_service, digest_service, embeddings_service

@pytest.fixture
def memory_manager(llm_service):
    """Create a MemoryManager instance with real LLM service"""
    general_service, digest_service, embeddings_service = llm_service
    
    memory_logger = LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "memory_manager",
        log_to_console=False
    )
    
    manager = MemoryManager(
        memory_guid="memory_compression_test_guid",
        memory_file="memory_compression_test.json",
        domain_config=USER_STORY_CONFIG,
        llm_service=general_service,
        digest_llm_service=digest_service,
        embeddings_llm_service=embeddings_service,
        max_recent_conversation_entries=8,
        importance_threshold=3,
        logger=memory_logger
    )
    return manager

def test_basic_memory_compression(memory_manager):
    """Test basic memory compression functionality"""
    # Check if test data file exists
    if not os.path.exists(INPUT_MEMORY_FILE):
        pytest.skip(f"Test memory file not found at {INPUT_MEMORY_FILE}")
    
    # Load the test memory file
    print(f"Loading test memory from {INPUT_MEMORY_FILE}")
    with open(INPUT_MEMORY_FILE, 'r') as f:
        test_memory = json.load(f)
    
    print(f"Test memory loaded with {len(test_memory.get('conversation_history', []))} conversation entries")
    
    # Initialize memory manager with test data
    # Note: Directly setting memory bypasses some initialization, but is acceptable for testing
    memory_manager.memory = test_memory
    
    # Verify memory is properly loaded
    assert memory_manager.memory is not None, "Memory should be loaded"
    assert "conversation_history" in memory_manager.memory, "Memory should have conversation history"
    assert len(memory_manager.memory["conversation_history"]) > 0, "Memory should have conversation entries"
    
    initial_entry_count = len(memory_manager.memory["conversation_history"])
    
    # Print initial state
    print("\nInitial Memory State:")
    print("=" * 80)
    print(f"Conversation History Entries: {initial_entry_count}")
    print(f"Context Entries: {len(memory_manager.memory.get('context', []))}")
    
    # Print first few conversation entries for verification
    print("\nFirst few conversation entries:")
    for entry in memory_manager.memory["conversation_history"][:2]:
        print(f"Role: {entry.get('role', 'unknown')}")
        print(f"Content: {entry.get('content', '')[:100]}...")
        print()
    
    # Perform memory compression
    print("\nPerforming memory compression...")
    success = memory_manager.update_memory({"operation": "update"})
    print(f"Memory compression result: {success}")
    assert success, "Memory compression should succeed"
    
    # Verify compression occurred
    final_entry_count = len(memory_manager.memory["conversation_history"])
    print(f"\nAfter compression: {final_entry_count} conversation entries")
    
    # Basic assertions
    assert "conversation_history" in memory_manager.memory, "Memory should still have conversation history"
    assert "context" in memory_manager.memory, "Memory should have context after compression"
    assert "metadata" in memory_manager.memory, "Memory should have metadata"
    
    # Compression should reduce or maintain entry count (depending on max_recent_conversation_entries)
    # If we had more than max_recent_conversation_entries, compression should reduce it
    if initial_entry_count > memory_manager.max_recent_conversation_entries:
        assert final_entry_count <= memory_manager.max_recent_conversation_entries, \
            f"Should compress to at most {memory_manager.max_recent_conversation_entries} entries"
    
    # Verify metadata was updated
    metadata = memory_manager.memory.get("metadata", {})
    assert "compression_count" in metadata, "Metadata should track compression count"
    assert metadata["compression_count"] > 0, "Compression count should be incremented"
    assert "updated_at" in metadata, "Metadata should have update timestamp"
    
    print(f"\nCompression completed successfully. Compression count: {metadata.get('compression_count', 0)}")
    print(f"Logs saved to: {LoggingConfig.get_log_base_dir(TEST_GUID)}")

