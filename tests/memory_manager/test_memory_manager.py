import pytest
import json
import os
from unittest.mock import Mock, patch
from datetime import datetime
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService


@pytest.fixture
def mock_llm_service():
    """Fixture to provide a mock LLM service."""
    mock = Mock()
    mock.generate.return_value = json.dumps({
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "test_entity_1",
                        "type": "test_type",
                        "name": "Test Entity",
                        "features": ["feature1", "feature2"],
                        "description": "Test description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": []
            }
        }
    })
    return mock

@pytest.fixture
def memory_file(tmp_path):
    """Fixture to provide a temporary memory file path."""
    return str(tmp_path / "test_memory.json")

@pytest.fixture
def memory_manager(memory_file, mock_llm_service):
    """Fixture to provide a MemoryManager instance."""
    return MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)

def test_initialization_requires_llm(memory_file):
    """Test that MemoryManager requires an LLM service."""
    with pytest.raises(ValueError, match="llm_service is required"):
        MemoryManager(memory_file=memory_file)

def test_initialization_with_llm(memory_file, mock_llm_service):
    """Test basic initialization of MemoryManager."""
    manager = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    assert manager.memory == {}
    assert manager.memory_file == memory_file
    assert isinstance(manager.domain_config, dict)
    assert manager.llm == mock_llm_service

def test_create_initial_memory_success(memory_manager, mock_llm_service):
    """Test creating initial memory structure."""
    result = memory_manager.create_initial_memory("test input")
    
    assert result is True
    assert "static_memory" in memory_manager.memory
    assert "working_memory" in memory_manager.memory
    assert "metadata" in memory_manager.memory
    assert "conversation_history" in memory_manager.memory
    
    # Verify static_memory structure
    static_memory = memory_manager.memory["static_memory"]
    assert "structured_data" in static_memory
    assert "knowledge_graph" in static_memory
    assert "entities" in static_memory["structured_data"]
    assert "relationships" in static_memory["knowledge_graph"]
    
    # Verify working_memory structure
    working_memory = memory_manager.memory["working_memory"]
    assert "structured_data" in working_memory
    assert "knowledge_graph" in working_memory
    assert isinstance(working_memory["structured_data"], dict)
    assert "entities" in working_memory["knowledge_graph"]
    assert "relationships" in working_memory["knowledge_graph"]
    
    # Verify metadata
    assert "created_at" in memory_manager.memory["metadata"]
    assert "last_updated" in memory_manager.memory["metadata"]
    assert "version" in memory_manager.memory["metadata"]

def test_create_initial_memory_failure(memory_manager, mock_llm_service):
    """Test handling of invalid LLM response during memory creation."""
    mock_llm_service.generate.return_value = "invalid json"
    
    result = memory_manager.create_initial_memory("test input")
    
    assert result is False
    assert memory_manager.memory == {}

def test_query_memory_success(memory_manager, mock_llm_service):
    """Test successful memory query."""
    # Setup initial memory state
    memory_manager.memory = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "test_entity_1",
                        "type": "test_type",
                        "name": "Test Entity",
                        "features": ["feature1"],
                        "description": "Test description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": []
    }
    
    # Setup mock response
    mock_response = {
        "response": "Test response",
        "digest": {
            "topic": "test_topic",
            "key_points": ["point1", "point2"],
            "context": "test context",
            "importance": "high"
        }
    }
    mock_llm_service.generate.return_value = json.dumps(mock_response)
    
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
    # Setup initial memory state with both static and working memory
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
                "relationships": [
                    {
                        "subjectIdentifier": "static_entity_1",
                        "predicate": "STATIC_RELATION",
                        "objectIdentifier": "static_entity_2"
                    }
                ]
            }
        },
        "working_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "working_entity_1",
                        "type": "test_type",
                        "name": "Working Entity",
                        "features": ["feature1"],
                        "description": "Initial description"
                    }
                ]
            },
            "knowledge_graph": {
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

    # Setup mock response with updated working memory
    mock_response = {
        "working_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "working_entity_1",
                        "type": "test_type",
                        "name": "Working Entity",
                        "features": ["feature1", "feature2"],
                        "description": "Updated description"
                    },
                    {
                        "identifier": "working_entity_2",
                        "type": "test_type",
                        "name": "New Entity",
                        "features": ["new_feature"],
                        "description": "New description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": [
                    {
                        "subjectIdentifier": "working_entity_1",
                        "predicate": "TEST_RELATION",
                        "objectIdentifier": "working_entity_2"
                    }
                ]
            }
        }
    }
    mock_llm_service.generate.return_value = json.dumps(mock_response)

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

    # Verify update was successful
    assert result is True

    # Verify static memory was not modified
    static_memory = memory_manager.memory["static_memory"]
    assert len(static_memory["structured_data"]["entities"]) == 1
    assert static_memory["structured_data"]["entities"][0]["identifier"] == "static_entity_1"
    assert len(static_memory["knowledge_graph"]["relationships"]) == 1
    assert static_memory["knowledge_graph"]["relationships"][0]["predicate"] == "STATIC_RELATION"

    # Verify working memory was updated
    working_memory = memory_manager.memory["working_memory"]
    assert len(working_memory["structured_data"]["entities"]) == 2
    assert working_memory["structured_data"]["entities"][0]["features"] == ["feature1", "feature2"]
    assert working_memory["structured_data"]["entities"][0]["description"] == "Updated description"
    assert working_memory["structured_data"]["entities"][1]["identifier"] == "working_entity_2"
    assert len(working_memory["knowledge_graph"]["relationships"]) == 1
    assert working_memory["knowledge_graph"]["relationships"][0]["predicate"] == "TEST_RELATION"

    # Verify metadata was preserved and updated
    assert "created_at" in memory_manager.memory["metadata"]
    assert "last_updated" in memory_manager.memory["metadata"]
    assert memory_manager.memory["metadata"]["version"] == "1.0"

def test_update_memory_failure(memory_manager, mock_llm_service):
    mock_llm_service.generate.return_value = "invalid json"
    
    # Test with update operation
    update_context = {
        "operation": "update",
        "message": {
            "role": "system",
            "content": "Update triggered"
        }
    }
    
    result = memory_manager.update_memory(json.dumps(update_context))
    
    assert result is False

def test_clear_memory(memory_manager):
    """Test clearing memory and file removal."""
    # Setup initial memory and file
    memory_manager.memory = {"test": "data"}
    memory_manager.save_memory()
    
    memory_manager.clear_memory()
    
    assert memory_manager.memory == {}
    assert not os.path.exists(memory_manager.memory_file)

def test_save_and_load_memory(memory_file, mock_llm_service):
    """Test memory persistence between instances."""
    # Create and setup first instance
    manager1 = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    test_memory = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "test_entity_1",
                        "type": "test_type",
                        "name": "Test Entity",
                        "features": ["feature1"],
                        "description": "Test description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": []
    }
    manager1.memory = test_memory
    manager1.save_memory()
    
    # Create second instance and verify data
    manager2 = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    assert "static_memory" in manager2.memory
    assert "working_memory" in manager2.memory
    assert "metadata" in manager2.memory
    assert "conversation_history" in manager2.memory
    
    # Verify static_memory structure
    static_memory = manager2.memory["static_memory"]
    assert "structured_data" in static_memory
    assert "knowledge_graph" in static_memory
    assert len(static_memory["structured_data"]["entities"]) == 1
    assert len(static_memory["knowledge_graph"]["relationships"]) == 0
    
    # Verify working_memory structure
    working_memory = manager2.memory["working_memory"]
    assert "structured_data" in working_memory
    assert "knowledge_graph" in working_memory
    assert len(working_memory["structured_data"]["entities"]) == 0
    assert len(working_memory["knowledge_graph"]["relationships"]) == 0

def test_memory_update_process(memory_manager, mock_llm_service):
    """Test the complete memory update process with real data"""
    # Setup initial memory state from test_memory.json
    initial_memory = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "Haven",
                        "type": "Settlement",
                        "name": "Haven",
                        "features": ["central"],
                        "description": "A main settlement in the Lost Valley"
                    },
                    {
                        "identifier": "Elena",
                        "type": "NPC",
                        "name": "Elena",
                        "features": ["Mayor of Haven"],
                        "description": "The mayor of Haven"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": [
                    {
                        "subjectIdentifier": "Elena",
                        "predicate": "mayor_of",
                        "objectIdentifier": "Haven"
                    }
                ]
            }
        },
        "working_memory": {
            "structured_data": {
                "entities": []
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": [
            {
                "role": "user",
                "content": "What's happening at the Eastside Well?",
                "timestamp": "2024-01-01T00:00:01"
            },
            {
                "role": "assistant",
                "content": "You've cleared the blockage at the Eastside Well, and water flow to the valley's crops is now restored. Sara thanks you for your help, and Elena offers 100 gold as a reward.",
                "timestamp": "2024-01-01T00:00:02"
            }
        ]
    }
    memory_manager.memory = initial_memory

    # Setup mock response for memory update - this should create new entities and relationships in working memory
    mock_response = {
        "working_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "eastside_well",
                        "type": "Location",
                        "name": "Eastside Well",
                        "features": ["water_source", "agricultural"],
                        "description": "A well that provides water to the valley's crops"
                    },
                    {
                        "identifier": "valley_crops",
                        "type": "Resource",
                        "name": "Valley Crops",
                        "features": ["agricultural"],
                        "description": "Agricultural crops in the valley requiring water"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": [
                    {
                        "subjectIdentifier": "eastside_well",
                        "predicate": "provides_water_to",
                        "objectIdentifier": "valley_crops"
                    },
                    {
                        "subjectIdentifier": "Elena",
                        "predicate": "offers_reward",
                        "objectIdentifier": "player"
                    }
                ]
            }
        }
    }
    mock_llm_service.generate.return_value = json.dumps(mock_response)

    # Trigger memory update
    update_context = {
        "operation": "update",
        "messages": memory_manager.memory["conversation_history"]
    }
    result = memory_manager.update_memory(json.dumps(update_context))

    # Verify update was successful
    assert result is True

    # Verify static memory was not modified
    static_memory = memory_manager.memory["static_memory"]
    assert len(static_memory["structured_data"]["entities"]) == 2
    assert static_memory["structured_data"]["entities"][0]["identifier"] == "Haven"
    assert static_memory["structured_data"]["entities"][1]["identifier"] == "Elena"
    assert len(static_memory["knowledge_graph"]["relationships"]) == 1
    assert static_memory["knowledge_graph"]["relationships"][0]["predicate"] == "mayor_of"

    # Verify working memory was updated with new information
    working_memory = memory_manager.memory["working_memory"]
    assert len(working_memory["structured_data"]["entities"]) == 2
    assert working_memory["structured_data"]["entities"][0]["identifier"] == "eastside_well"
    assert working_memory["structured_data"]["entities"][1]["identifier"] == "valley_crops"
    assert len(working_memory["knowledge_graph"]["relationships"]) == 2
    assert any(r["predicate"] == "provides_water_to" for r in working_memory["knowledge_graph"]["relationships"])
    assert any(r["predicate"] == "offers_reward" for r in working_memory["knowledge_graph"]["relationships"])

    # Verify conversation history was cleared
    assert len(memory_manager.memory["conversation_history"]) == 0

    # Verify metadata was updated
    assert "created_at" in memory_manager.memory["metadata"]
    assert "last_updated" in memory_manager.memory["metadata"]
    assert memory_manager.memory["metadata"]["version"] == "1.0"

@pytest.mark.integration
def test_memory_update_integration_with_llm():
    """Integration test using real LLM to verify memory update behavior"""
    # Setup real LLM service
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "test_memory_update_debug.log",
        "debug_scope": "test_memory_update",
        "console_output": False
    })
    
    # Create memory manager with temp file
    memory_file = "test_memory_update.json"
    memory_manager = MemoryManager(memory_file=memory_file, llm_service=llm_service)
    
    try:
        # Setup initial memory state
        initial_memory = {
            "static_memory": {
                "structured_data": {
                    "entities": [
                        {
                            "identifier": "Haven",
                            "type": "Settlement",
                            "name": "Haven",
                            "features": ["central"],
                            "description": "A main settlement in the Lost Valley"
                        },
                        {
                            "identifier": "Elena",
                            "type": "NPC",
                            "name": "Elena",
                            "features": ["Mayor of Haven"],
                            "description": "The mayor of Haven"
                        }
                    ]
                },
                "knowledge_graph": {
                    "relationships": [
                        {
                            "subjectIdentifier": "Elena",
                            "predicate": "mayor_of",
                            "objectIdentifier": "Haven"
                        }
                    ]
                }
            },
            "working_memory": {
                "structured_data": {
                    "entities": []
                },
                "knowledge_graph": {
                    "relationships": []
                }
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            },
            "conversation_history": [
                {
                    "role": "user",
                    "content": "What's happening at the Eastside Well?",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "role": "assistant",
                    "content": "You've cleared the blockage at the Eastside Well, and water flow to the valley's crops is now restored. Sara thanks you for your help, and Elena offers 100 gold as a reward.",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        memory_manager.memory = initial_memory
        
        # Save initial state
        memory_manager.save_memory()
        
        # Trigger memory update with real LLM
        update_context = {
            "operation": "update",
            "messages": memory_manager.memory["conversation_history"]
        }
        result = memory_manager.update_memory(json.dumps(update_context))
        
        # Verify update was successful
        assert result is True
        
        # Verify static memory was not modified
        static_memory = memory_manager.memory["static_memory"]
        assert len(static_memory["structured_data"]["entities"]) == 2
        assert any(e["identifier"] == "Haven" for e in static_memory["structured_data"]["entities"])
        assert any(e["identifier"] == "Elena" for e in static_memory["structured_data"]["entities"])
        assert len(static_memory["knowledge_graph"]["relationships"]) == 1
        assert static_memory["knowledge_graph"]["relationships"][0]["predicate"] == "mayor_of"
        
        # Verify working memory was updated with new information about the well
        working_memory = memory_manager.memory["working_memory"]
        assert len(working_memory["structured_data"]["entities"]) > 0
        assert any(e["identifier"].lower().startswith("eastside") for e in working_memory["structured_data"]["entities"])
        assert len(working_memory["knowledge_graph"]["relationships"]) > 0
        
        # Verify conversation history was cleared
        assert len(memory_manager.memory["conversation_history"]) == 0
        
        # Print the actual working memory for inspection
        print("\nWorking memory after update:")
        print(json.dumps(working_memory, indent=2))
        
    finally:
        # Cleanup
        if os.path.exists(memory_file):
            os.remove(memory_file)
        backup_pattern = memory_file.replace(".json", "_bak_*.json")
        for f in os.listdir():
            if f.startswith(backup_pattern):
                os.remove(f)

def test_load_existing_valid_memory(memory_file, mock_llm_service):
    """Test that existing valid memory is loaded and not overwritten."""
    # Create initial memory file
    initial_memory = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "test_entity",
                        "type": "test",
                        "name": "Test Entity",
                        "features": ["test"],
                        "description": "Test description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {},
            "knowledge_graph": {
                "entities": [],
                "relationships": []
            }
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "version": "1.0"
        },
        "conversation_history": [
            {
                "role": "user",
                "content": "test message",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
    }
    
    with open(memory_file, 'w') as f:
        json.dump(initial_memory, f)
    
    # Create new manager instance
    manager = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    
    # Try to create new memory - should not overwrite
    result = manager.create_initial_memory("new data")
    
    assert result is True
    # Verify original memory was preserved
    assert manager.memory["static_memory"]["structured_data"]["entities"][0]["identifier"] == "test_entity"
    assert len(manager.memory["conversation_history"]) == 1
    assert manager.memory["conversation_history"][0]["content"] == "test message"

def test_load_existing_invalid_memory(memory_file, mock_llm_service):
    """Test that invalid memory structure is replaced with new memory."""
    # Create initial memory file with invalid structure
    invalid_memory = {
        "static_memory": {
            "structured_data": {
                "entities": []
            }
            # Missing knowledge_graph
        }
        # Missing working_memory, metadata, conversation_history
    }
    
    with open(memory_file, 'w') as f:
        json.dump(invalid_memory, f)
    
    # Create new manager instance
    manager = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    
    # Try to create new memory - should replace invalid memory
    result = manager.create_initial_memory("new data")
    
    assert result is True
    # Verify new memory structure was created
    assert "static_memory" in manager.memory
    assert "working_memory" in manager.memory
    assert "metadata" in manager.memory
    assert "conversation_history" in manager.memory
    assert len(manager.memory["conversation_history"]) == 0

def test_load_existing_partial_memory(memory_file, mock_llm_service):
    """Test that partially complete memory structure is replaced with new memory."""
    # Create initial memory file with partial structure
    partial_memory = {
        "static_memory": {
            "structured_data": {
                "entities": []
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {},
            "knowledge_graph": {
                "entities": [],
                "relationships": []
            }
        }
        # Missing metadata and conversation_history
    }
    
    with open(memory_file, 'w') as f:
        json.dump(partial_memory, f)
    
    # Create new manager instance
    manager = MemoryManager(memory_file=memory_file, llm_service=mock_llm_service)
    
    # Try to create new memory - should replace partial memory
    result = manager.create_initial_memory("new data")
    
    assert result is True
    # Verify complete memory structure was created
    assert "static_memory" in manager.memory
    assert "working_memory" in manager.memory
    assert "metadata" in manager.memory
    assert "conversation_history" in manager.memory
    assert len(manager.memory["conversation_history"]) == 0
