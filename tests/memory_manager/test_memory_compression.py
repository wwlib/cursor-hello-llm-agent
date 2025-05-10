import os
import json
import pytest
from datetime import datetime
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "memory_snapshots")
INPUT_MEMORY_FILE = os.path.join(TEST_DATA_DIR, "agent_memory_for_compression_testing.json")

# LLM Service Configuration
LLM_CONFIG = {
    "base_url": "http://192.168.1.173:11434",  # Update this to your Ollama server URL
    "model": "gemma3",  # Update this to your preferred model
    "temperature": 0.7,
    "stream": False,
    "debug": True,
    "debug_scope": "memory_compression_test",
    "console_output": False
}

@pytest.fixture
def llm_service():
    """Create a real OllamaService instance for integration testing"""
    # Create logs directory structure
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "memory_compression_test"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    # Create separate debug files for each service
    general_debug_file = os.path.join(guid_logs_dir, "general.log")
    digest_debug_file = os.path.join(guid_logs_dir, "digest.log")
    embed_debug_file = os.path.join(guid_logs_dir, "embed.log")
    
    # Update config with debug files
    config = LLM_CONFIG.copy()
    config["debug_file"] = general_debug_file
    
    service = OllamaService(config)
    return service

@pytest.fixture
def memory_manager(llm_service):
    """Create a MemoryManager instance with real LLM service"""
    manager = MemoryManager(
        memory_guid="memory_compression_test_guid",
        memory_file="memory_compression_test",
        llm_service=llm_service,
        max_recent_conversation_entries=8,  # Keep only 2 most recent entries
        importance_threshold=3  # Keep segments with importance >= 3
    )
    return manager

def test_basic_memory_compression(memory_manager):
    """Test basic memory compression functionality"""
    # Load the test memory file
    print(f"Loading test memory from {INPUT_MEMORY_FILE}")
    with open(INPUT_MEMORY_FILE, 'r') as f:
        test_memory = json.load(f)
    
    print(f"Test memory loaded with {len(test_memory['conversation_history'])} conversation entries")
    
    # Initialize memory manager with test data
    memory_manager.memory = test_memory
    
    # Verify memory is properly loaded
    assert memory_manager.memory is not None, "Memory should be loaded"
    assert "conversation_history" in memory_manager.memory, "Memory should have conversation history"
    assert len(memory_manager.memory["conversation_history"]) > 0, "Memory should have conversation entries"
    
    # Print initial state
    print("\nInitial Memory State:")
    print("=" * 80)
    print(f"Conversation History Entries: {len(memory_manager.memory['conversation_history'])}")
    print(f"Context Entries: {len(memory_manager.memory.get('context', {}))}")
    
    # Print first few conversation entries for verification
    print("\nFirst few conversation entries:")
    for entry in memory_manager.memory["conversation_history"][:2]:
        print(f"Role: {entry['role']}")
        print(f"Content: {entry['content'][:100]}...")
        print()
    
    # Perform memory compression
    print("\nPerforming memory compression...")
    success = memory_manager.update_memory({"operation": "update"})
    print(f"Memory compression result: {success}")
    assert success, "Memory compression should succeed"
    
    # # Print compressed state
    # print("\nCompressed Memory State:")
    # print("=" * 80)
    # print(f"Conversation History Entries: {len(memory_manager.memory['conversation_history'])}")
    # print(f"Context Entries: {len(memory_manager.memory['context'])}")
    
    # # Print compressed content
    # print("\nCompressed Content:")
    # print("=" * 80)
    # for topic, entries in memory_manager.memory['context'].items():
    #     print(f"\nTopic: {topic}")
    #     print("-" * 40)
    #     for entry in entries:
    #         print(f"Importance: {entry['importance']}")
    #         print(f"Text: {entry['text']}")
    #         print(f"Source GUIDs: {entry['source_guids']}")
    #         print()
    
    # # Basic assertions
    # assert "context" in memory_manager.memory, "Memory should have context after compression"
    # assert "compressed_entries" in memory_manager.memory, "Memory should track compressed entries"
    # assert len(memory_manager.memory["conversation_history"]) <= 8, "Should keep only recent entries"
    
    # # Verify context structure
    # context = memory_manager.memory["context"]
    # for topic, entries in context.items():
    #     assert len(entries) > 0, f"Topic {topic} should have entries"
    #     for entry in entries:
    #         assert "text" in entry, "Entry should have text"
    #         assert "importance" in entry, "Entry should have importance"
    #         assert "source_guids" in entry, "Entry should have source GUIDs"
    #         assert entry["importance"] >= 3, "Entry should meet importance threshold"

