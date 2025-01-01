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
    # Setup initial memory
    memory_manager.memory = {
        "structured_data": {"test": "data"},
        "knowledge_graph": {}
    }
    
    # Create test query context
    query_context = {
        "current_phase": "INTERACTION",
        "recent_messages": [
            {"role": "user", "content": "test message"}
        ],
        "user_message": "test query"
    }
    
    # Mock LLM response with new format
    mock_response = {
        "response": "Test response",
        "new_information": {"test": "new_data"},
        "suggested_phase": "INTERACTION",
        "confidence": 0.9
    }
    mock_llm_service.generate.return_value = json.dumps(mock_response)
    
    result = memory_manager.query_memory(json.dumps(query_context))
    
    assert result == mock_response
    assert "response" in result
    assert "new_information" in result
    assert "suggested_phase" in result
    assert "confidence" in result

def test_query_memory_failure(memory_manager, mock_llm_service):
    mock_llm_service.generate.return_value = "invalid json"
    
    result = memory_manager.query_memory(json.dumps({"user_message": "test"}))
    
    assert result["response"] == "Error processing query"
    assert result["confidence"] == 0.0
    assert result["suggested_phase"] is None

def test_update_memory_success(memory_manager, mock_llm_service):
    # Setup initial memory
    initial_memory = {
        "structured_data": {"test": "data"},
        "knowledge_graph": {},
        "metadata": {
            "version": "1.0",
            "last_updated": "2023-01-01T00:00:00"
        }
    }
    memory_manager.memory = initial_memory
    
    # Create test update context
    update_context = {
        "phase": "LEARNING",
        "information": "new test data",
        "recent_history": [
            {"role": "user", "content": "test message"}
        ]
    }
    
    # Mock updated memory response
    updated_memory = {
        "structured_data": {"test": "updated"},
        "knowledge_graph": {},
        "metadata": {
            "version": "1.0"
        }
    }
    mock_llm_service.generate.return_value = json.dumps(updated_memory)
    
    result = memory_manager.update_memory(json.dumps(update_context))
    
    assert result is True
    assert memory_manager.memory["structured_data"]["test"] == "updated"
    assert "last_updated" in memory_manager.memory["metadata"]

def test_update_memory_reflection(memory_manager, mock_llm_service):
    """Test memory update with reflection operation"""
    # Setup initial memory
    memory_manager.memory = {
        "structured_data": {"test": "data"},
        "knowledge_graph": {},
        "metadata": {"version": "1.0"}
    }
    
    # Create reflection context
    reflection_context = {
        "phase": "INTERACTION",
        "recent_history": [{"role": "user", "content": "test"}],
        "operation": "reflect"
    }
    
    # Mock reflection response
    reflection_result = {
        "structured_data": {"test": "reflected"},
        "knowledge_graph": {},
        "metadata": {"version": "1.0"}
    }
    mock_llm_service.generate.return_value = json.dumps(reflection_result)
    
    result = memory_manager.update_memory(json.dumps(reflection_context))
    
    assert result is True
    assert memory_manager.memory["structured_data"]["test"] == "reflected"
    assert "last_updated" in memory_manager.memory["metadata"]

def test_update_memory_failure(memory_manager, mock_llm_service):
    mock_llm_service.generate.return_value = "invalid json"
    
    result = memory_manager.update_memory(json.dumps({"information": "test"}))
    
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
