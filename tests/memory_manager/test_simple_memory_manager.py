"""Tests for SimpleMemoryManager

Tests the basic functionality of SimpleMemoryManager including:
1. Initialization and file handling
2. Initial memory creation
3. Memory querying
4. Memory updating
5. Memory persistence
"""

import pytest
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from src.memory.simple_memory_manager import SimpleMemoryManager

@pytest.fixture
def mock_llm():
    """Fixture to provide a mock LLM service."""
    mock = Mock()
    mock.generate.return_value = "Test response from LLM"
    return mock

@pytest.fixture
def memory_file(tmp_path):
    """Fixture to provide a temporary memory file path."""
    return str(tmp_path / "test_memory.json")

@pytest.fixture
def initial_data():
    """Fixture to provide test initial data from file."""
    test_dir = Path(__file__).parent
    data_file = test_dir / "test_simple_memory_initial_data.txt"
    with open(data_file, 'r') as f:
        return f.read().strip()

@pytest.fixture
def memory_manager(memory_file, mock_llm):
    """Fixture to provide a SimpleMemoryManager instance."""
    return SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)

def test_initialization_requires_llm(memory_file):
    """Test that SimpleMemoryManager requires an LLM service."""
    with pytest.raises(ValueError, match="llm_service is required"):
        SimpleMemoryManager(memory_file=memory_file)

def test_initialization_with_llm(memory_file, mock_llm):
    """Test basic initialization of SimpleMemoryManager."""
    manager = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    assert manager.memory == {}
    assert manager.memory_file == memory_file
    assert isinstance(manager.domain_config, dict)
    assert manager.llm == mock_llm

def test_create_initial_memory(memory_manager, initial_data):
    """Test creating initial memory structure."""
    success = memory_manager.create_initial_memory(initial_data)
    
    assert success
    assert memory_manager.memory["initial_data"] == initial_data
    assert isinstance(memory_manager.memory["conversation_history"], list)
    assert len(memory_manager.memory["conversation_history"]) == 0
    assert "last_updated" in memory_manager.memory

def test_create_initial_memory_persists(memory_manager, memory_file, initial_data):
    """Test that created memory is properly saved to file."""
    memory_manager.create_initial_memory(initial_data)
    
    # Read the file directly
    with open(memory_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data["initial_data"] == initial_data
    assert isinstance(saved_data["conversation_history"], list)
    assert "last_updated" in saved_data

def test_query_memory_adds_messages(memory_manager, mock_llm):
    """Test that querying memory properly adds messages to history."""
    # Setup initial memory
    memory_manager.create_initial_memory("Initial test data")
    
    # Create a query
    query = json.dumps({"user_message": "Test question"})
    response = memory_manager.query_memory(query)
    
    # Verify LLM was called with correct prompt
    mock_llm.generate.assert_called_once()
    prompt_arg = mock_llm.generate.call_args[0][0]
    assert "Initial test data" in prompt_arg
    assert "Test question" in prompt_arg
    
    # Check that both user message and response were added
    history = memory_manager.memory["conversation_history"]
    assert len(history) == 2  # User message + response
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Test question"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Test response from LLM"

def test_query_memory_saves_after_response(memory_manager, memory_file):
    """Test that memory is saved after each query."""
    memory_manager.create_initial_memory("Initial test data")
    query = json.dumps({"user_message": "Test question"})
    memory_manager.query_memory(query)
    
    # Read the file directly
    with open(memory_file, 'r') as f:
        saved_data = json.load(f)
    
    assert len(saved_data["conversation_history"]) == 2
    assert saved_data["conversation_history"][0]["content"] == "Test question"
    assert saved_data["conversation_history"][1]["content"] == "Test response from LLM"

def test_update_memory_no_reflection(memory_manager):
    """Test that update_memory doesn't process reflection updates."""
    memory_manager.create_initial_memory("Initial test data")
    
    # Create update context with reflection
    update_context = json.dumps({
        "operation": "update",
        "messages": [
            {
                "role": "system",
                "content": "Reflection update",
                "timestamp": datetime.now().isoformat()
            }
        ]
    })
    
    success = memory_manager.update_memory(update_context)
    assert success
    # Verify no changes to conversation history
    assert len(memory_manager.memory["conversation_history"]) == 0

def test_clear_memory(memory_manager, memory_file):
    """Test clearing memory and file removal."""
    memory_manager.create_initial_memory("Test data")
    assert os.path.exists(memory_file)
    
    memory_manager.clear_memory()
    assert memory_manager.memory == {}
    assert not os.path.exists(memory_file)

def test_memory_persistence_across_instances(memory_file, mock_llm):
    """Test that memory persists between different instances."""
    # Create and setup first instance
    manager1 = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    manager1.create_initial_memory("Test data")
    query = json.dumps({"user_message": "Test question"})
    manager1.query_memory(query)
    
    # Create second instance and verify data
    manager2 = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    assert manager2.memory["initial_data"] == "Test data"
    assert len(manager2.memory["conversation_history"]) == 2  # User message + response

def test_invalid_json_query(memory_manager):
    """Test handling of invalid JSON in query."""
    memory_manager.create_initial_memory("Test data")
    
    response = memory_manager.query_memory("invalid json")
    assert "response" in response
    assert "Error" in response["response"]

def test_invalid_json_update(memory_manager):
    """Test handling of invalid JSON in update."""
    memory_manager.create_initial_memory("Test data")
    
    success = memory_manager.update_memory("invalid json")
    assert not success

def test_load_existing_valid_memory(memory_file, mock_llm):
    """Test that existing valid memory is loaded and not overwritten."""
    # Create initial memory file
    initial_memory = {
        "initial_data": "test data",
        "conversation_history": [
            {
                "role": "user",
                "content": "test message",
                "timestamp": "2024-01-01T00:00:00"
            }
        ],
        "last_updated": "2024-01-01T00:00:00"
    }
    
    with open(memory_file, 'w') as f:
        json.dump(initial_memory, f)
    
    # Create new manager instance
    manager = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    
    # Try to create new memory - should not overwrite
    result = manager.create_initial_memory("new data")
    
    assert result is True
    assert manager.memory["initial_data"] == "test data"  # Should keep original data
    assert len(manager.memory["conversation_history"]) == 1
    assert manager.memory["conversation_history"][0]["content"] == "test message"

def test_load_existing_invalid_memory(memory_file, mock_llm):
    """Test that invalid memory structure is replaced with new memory."""
    # Create initial memory file with invalid structure
    invalid_memory = {
        "initial_data": "test data",
        # Missing conversation_history and last_updated
    }
    
    with open(memory_file, 'w') as f:
        json.dump(invalid_memory, f)
    
    # Create new manager instance
    manager = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    
    # Try to create new memory - should replace invalid memory
    result = manager.create_initial_memory("new data")
    
    assert result is True
    assert manager.memory["initial_data"] == "new data"  # Should use new data
    assert "conversation_history" in manager.memory
    assert "last_updated" in manager.memory
    assert len(manager.memory["conversation_history"]) == 0

def test_load_existing_partial_memory(memory_file, mock_llm):
    """Test that partially complete memory structure is replaced with new memory."""
    # Create initial memory file with partial structure
    partial_memory = {
        "initial_data": "test data",
        "conversation_history": [],
        # Missing last_updated
    }
    
    with open(memory_file, 'w') as f:
        json.dump(partial_memory, f)
    
    # Create new manager instance
    manager = SimpleMemoryManager(memory_file=memory_file, llm_service=mock_llm)
    
    # Try to create new memory - should replace partial memory
    result = manager.create_initial_memory("new data")
    
    assert result is True
    assert manager.memory["initial_data"] == "new data"  # Should use new data
    assert "conversation_history" in manager.memory
    assert "last_updated" in manager.memory
    assert len(manager.memory["conversation_history"]) == 0 