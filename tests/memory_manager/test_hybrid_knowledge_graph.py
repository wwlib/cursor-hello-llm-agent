import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock
from src.memory.memory_manager import MemoryManager

@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    mock_service = Mock()
    mock_service.generate = Mock()
    return mock_service

@pytest.fixture
def memory_manager(mock_llm_service, tmp_path):
    """Fixture to provide a memory manager instance."""
    memory_file = tmp_path / "test_memory.json"
    manager = MemoryManager(
        memory_file=str(memory_file),
        domain_config={},
        llm_service=mock_llm_service
    )
    return manager

def test_create_initial_memory_with_hybrid_graph(memory_manager, mock_llm_service):
    """Test creating initial memory with hybrid knowledge graph structure."""
    # Create the response
    response = json.dumps({
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "initial_entity_1",
                        "type": "test_type",
                        "name": "Initial Entity",
                        "features": ["initial_feature"],
                        "description": "Initial description"
                    }
                ]
            },
            "knowledge_graph": {
                "simple_facts": [
                    {
                        "key": "initial_fact",
                        "value": "This is an initial fact",
                        "context": "Initial context"
                    }
                ],
                "relationships": [
                    {
                        "subject": "initial_entity_1",
                        "predicate": "HAS_FEATURE",
                        "object": "initial_feature",
                        "context": "Initial relationship"
                    }
                ]
            }
        },
        "working_memory": {
            "structured_data": {
                "entities": []
            },
            "knowledge_graph": {
                "simple_facts": [],
                "relationships": []
            }
        },
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    })
    
    # Set up the mock to return the response
    mock_llm_service.generate.return_value = response
    
    # Run the test
    result = memory_manager.create_initial_memory("test input")
    assert result is True
    
    # Verify the mock was called
    mock_llm_service.generate.assert_called_once()
    
    # Verify memory structure
    memory = memory_manager.memory
    assert "static_memory" in memory
    assert "working_memory" in memory
    assert "structured_data" in memory["static_memory"]
    assert "knowledge_graph" in memory["static_memory"]
    assert "simple_facts" in memory["static_memory"]["knowledge_graph"]
    assert "relationships" in memory["static_memory"]["knowledge_graph"]

    # Verify initial data
    static_entities = memory["static_memory"]["structured_data"]["entities"]
    assert len(static_entities) == 1
    assert static_entities[0]["identifier"] == "initial_entity_1"

    static_facts = memory["static_memory"]["knowledge_graph"]["simple_facts"]
    assert len(static_facts) == 1
    assert static_facts[0]["key"] == "initial_fact"

    static_relationships = memory["static_memory"]["knowledge_graph"]["relationships"]
    assert len(static_relationships) == 1
    assert static_relationships[0]["subject"] == "initial_entity_1"

def test_update_memory_with_hybrid_graph(memory_manager, mock_llm_service):
    """Test updating memory with hybrid knowledge graph structure."""
    # Setup initial memory
    initial_memory = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "static_entity_1",
                        "type": "test_type",
                        "name": "Static Entity",
                        "features": ["static_feature"],
                        "description": "Static description"
                    }
                ]
            },
            "knowledge_graph": {
                "simple_facts": [
                    {
                        "key": "static_fact",
                        "value": "This is a static fact",
                        "context": "Static context"
                    }
                ],
                "relationships": [
                    {
                        "subject": "static_entity_1",
                        "predicate": "HAS_FEATURE",
                        "object": "static_feature",
                        "context": "Static relationship"
                    }
                ]
            }
        },
        "working_memory": {
            "structured_data": {
                "entities": []
            },
            "knowledge_graph": {
                "simple_facts": [],
                "relationships": []
            }
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": []
    }
    memory_manager.memory = initial_memory

    # Create the mock response
    response = json.dumps({
        "working_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "new_entity_1",
                        "type": "test_type",
                        "name": "New Entity",
                        "features": ["new_feature"],
                        "description": "New description"
                    }
                ]
            },
            "knowledge_graph": {
                "simple_facts": [
                    {
                        "key": "new_fact",
                        "value": "This is a new fact",
                        "context": "New context"
                    }
                ],
                "relationships": [
                    {
                        "subject": "new_entity_1",
                        "predicate": "HAS_FEATURE",
                        "object": "new_feature",
                        "context": "New relationship"
                    }
                ]
            }
        }
    })
    
    # Set up the mock to return the response
    mock_llm_service.generate.return_value = response

    # Test memory update
    update_context = {
        "operation": "update",
        "messages": [
            {
                "role": "user",
                "content": "Test message 1",
                "timestamp": "2024-01-01T00:00:01"
            },
            {
                "role": "assistant",
                "content": "Test response 1",
                "timestamp": "2024-01-01T00:00:02"
            }
        ]
    }
    result = memory_manager.update_memory(json.dumps(update_context))
    assert result is True
    
    # Verify the mock was called
    mock_llm_service.generate.assert_called_once()

    # Verify update was successful
    memory = memory_manager.memory
    assert "working_memory" in memory
    assert "structured_data" in memory["working_memory"]
    assert "knowledge_graph" in memory["working_memory"]

    # Verify working memory updates
    working_entities = memory["working_memory"]["structured_data"]["entities"]
    assert len(working_entities) == 1
    assert working_entities[0]["identifier"] == "new_entity_1"

    working_facts = memory["working_memory"]["knowledge_graph"]["simple_facts"]
    assert len(working_facts) == 1
    assert working_facts[0]["key"] == "new_fact"

    working_relationships = memory["working_memory"]["knowledge_graph"]["relationships"]
    assert len(working_relationships) == 1
    assert working_relationships[0]["subject"] == "new_entity_1"

    # Verify static memory remains unchanged
    static_entities = memory["static_memory"]["structured_data"]["entities"]
    assert len(static_entities) == 1
    assert static_entities[0]["identifier"] == "static_entity_1"

    static_facts = memory["static_memory"]["knowledge_graph"]["simple_facts"]
    assert len(static_facts) == 1
    assert static_facts[0]["key"] == "static_fact"

    static_relationships = memory["static_memory"]["knowledge_graph"]["relationships"]
    assert len(static_relationships) == 1
    assert static_relationships[0]["subject"] == "static_entity_1"

def test_validate_hybrid_graph_structure(memory_manager, mock_llm_service):
    """Test validation of hybrid knowledge graph structure."""
    # Test with missing simple_facts
    mock_response = json.dumps({
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        }
    })
    mock_llm_service.generate.return_value = mock_response
    
    result = memory_manager.update_memory(json.dumps({"operation": "update", "messages": []}))
    assert result is False

    # Test with invalid simple_facts format
    mock_response = json.dumps({
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {
                "simple_facts": [{"identifier": "test"}],
                "relationships": []
            }
        }
    })
    mock_llm_service.generate.return_value = mock_response
    
    result = memory_manager.update_memory(json.dumps({"operation": "update", "messages": []}))
    assert result is False

    # Test with invalid relationship format
    mock_response = json.dumps({
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {
                "simple_facts": [],
                "relationships": [{"subjectIdentifier": "test"}]
            }
        }
    })
    mock_llm_service.generate.return_value = mock_response
    
    result = memory_manager.update_memory(json.dumps({"operation": "update", "messages": []}))
    assert result is False 