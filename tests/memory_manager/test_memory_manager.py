import pytest
import json
import os
from unittest.mock import Mock, patch
from datetime import datetime
from src.memory.memory_manager import MemoryManager


@pytest.fixture
def mock_llm_service():
    return Mock()

@pytest.fixture
def memory_manager(mock_llm_service, tmp_path):
    memory_file = tmp_path / "test_memory.json"
    return MemoryManager(mock_llm_service, str(memory_file))

def test_init(memory_manager):
    assert memory_manager.memory == {}
    assert isinstance(memory_manager.llm, Mock)

def test_create_initial_memory_success(memory_manager, mock_llm_service):
    # Mock response from LLM
    mock_memory = {
        "structured_data": {"test": "data"},
        "knowledge_graph": {"entity1": ["relation", "entity2"]},
        "metadata": {
            "categories": ["test"],
            "timestamp": "2023-01-01T00:00:00",
            "version": "1.0"
        }
    }
    mock_llm_service.generate.return_value = json.dumps(mock_memory)
    
    result = memory_manager.create_initial_memory("test input")
    
    assert result is True
    assert "structured_data" in memory_manager.memory
    assert "knowledge_graph" in memory_manager.memory
    assert "metadata" in memory_manager.memory
    assert "created_at" in memory_manager.memory["metadata"]
    assert "last_updated" in memory_manager.memory["metadata"]

def test_create_initial_memory_failure(memory_manager, mock_llm_service):
    # Mock LLM returning invalid JSON
    mock_llm_service.generate.return_value = "invalid json"
    
    result = memory_manager.create_initial_memory("test input")
    
    assert result is False
    assert memory_manager.memory == {}

def test_query_memory_success(memory_manager, mock_llm_service):
    """Test successful memory query"""
    # Setup mock response
    mock_llm_service.generate.return_value = '{"response": "Test response"}'
    
    # Test query
    result = memory_manager.query_memory('{"user_message": "test query"}')
    
    # Verify response
    assert isinstance(result, dict)
    assert "response" in result
    assert result["response"] == "Test response"
    
    # Verify conversation history was updated
    assert len(memory_manager.memory["conversation_history"]) == 2  # User message + response
    assert memory_manager.memory["conversation_history"][0]["role"] == "user"
    assert memory_manager.memory["conversation_history"][1]["role"] == "assistant"

def test_query_memory_failure(memory_manager, mock_llm_service):
    """Test handling of invalid LLM response"""
    # Setup mock to return invalid JSON
    mock_llm_service.generate.return_value = 'invalid json'
    
    # Test query
    result = memory_manager.query_memory('{"user_message": "test query"}')
    
    # Verify error response
    assert isinstance(result, dict)
    assert "response" in result
    assert "Error processing query" in result["response"]

def test_update_memory_success(memory_manager, mock_llm_service):
    """Test successful memory update"""
    # Setup initial memory state
    memory_manager.memory = {
        "structured_data": {"entities": []},
        "knowledge_graph": {"relationships": []},
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": []
    }
    
    # Setup mock response with valid memory structure
    mock_response = {
        "structured_data": {"entities": []},
        "knowledge_graph": {"relationships": []},
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        }
    }
    mock_llm_service.generate.return_value = json.dumps(mock_response)
    
    # Test update
    result = memory_manager.update_memory('{"new_info": "test"}')
    
    # Verify update was successful
    assert result is True
    assert "structured_data" in memory_manager.memory
    assert "knowledge_graph" in memory_manager.memory
    assert "metadata" in memory_manager.memory

def test_update_memory_failure(memory_manager, mock_llm_service):
    mock_llm_service.generate.return_value = "invalid json"
    
    # Test with reflection operation
    update_context = {
        "operation": "reflect",
        "message": {
            "role": "system",
            "content": "Reflection triggered"
        }
    }
    
    result = memory_manager.update_memory(json.dumps(update_context))
    
    assert result is False

def test_clear_memory(memory_manager):
    # Setup initial memory and file
    memory_manager.memory = {"test": "data"}
    memory_manager.save_memory()
    
    memory_manager.clear_memory()
    
    assert memory_manager.memory == {}
    assert not os.path.exists(memory_manager.memory_file)

def test_save_and_load_memory(memory_manager):
    test_memory = {
        "structured_data": {"test": "data"},
        "knowledge_graph": {},
        "metadata": {"version": "1.0"}
    }
    memory_manager.memory = test_memory
    
    # Save memory
    memory_manager.save_memory()
    
    # Create new instance with same file
    new_manager = MemoryManager(Mock(), memory_manager.memory_file)
    
    assert new_manager.memory == test_memory
