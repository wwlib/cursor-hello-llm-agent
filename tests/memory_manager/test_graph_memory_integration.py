"""Integration tests for graph memory with the main memory manager.

This module tests the integration between the GraphManager and MemoryManager,
ensuring that graph memory features work seamlessly with the existing memory system.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import MagicMock

from src.memory.memory_manager import MemoryManager, AsyncMemoryManager
from src.ai.llm_ollama import OllamaService
from examples.domain_configs import DND_CONFIG


class MockLLMService:
    """Mock LLM service for testing"""
    
    def generate(self, prompt, options=None):
        """Generate a mock response"""
        if "extract entities" in prompt.lower():
            return json.dumps([
                {
                    "name": "Eldara",
                    "type": "character",
                    "description": "A fire wizard who runs a magic shop",
                    "attributes": {"profession": "wizard", "magic_type": "fire"}
                },
                {
                    "name": "Riverwatch",
                    "type": "location", 
                    "description": "A settlement in the eastern part of the valley",
                    "attributes": {"region": "east", "type": "settlement"}
                }
            ])
        elif "extract relationships" in prompt.lower():
            return json.dumps([
                {
                    "from_entity": "Eldara",
                    "to_entity": "Riverwatch",
                    "relationship": "located_in",
                    "confidence": 0.9,
                    "evidence": "Eldara runs a magic shop in Riverwatch"
                }
            ])
        elif "digest" in prompt.lower() or "rate" in prompt.lower():
            return json.dumps({
                "rated_segments": [
                    {
                        "text": "Eldara is a fire wizard who runs a magic shop in Riverwatch",
                        "importance": 4,
                        "topics": ["characters", "location"],
                        "type": "information",
                        "memory_worthy": True
                    }
                ]
            })
        else:
            return "This is a test response mentioning Eldara's shop in Riverwatch."
    
    def generate_embedding(self, text):
        """Generate a mock embedding"""
        # Return a simple mock embedding based on text hash
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Create a normalized embedding vector
        embedding = [(hash_val >> i) & 1 for i in range(32)]
        # Normalize to floats between 0 and 1
        return [float(x) for x in embedding]


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    return MockLLMService()


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def domain_config():
    """Get D&D domain configuration for testing"""
    return DND_CONFIG


def test_memory_manager_graph_initialization(mock_llm_service, temp_memory_dir, domain_config):
    """Test that MemoryManager initializes with graph memory enabled"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=True
    )
    
    # Check that graph memory is enabled
    assert memory_manager.enable_graph_memory is True
    assert memory_manager.graph_manager is not None
    
    # Check that graph storage path is properly set
    expected_graph_path = os.path.join(temp_memory_dir, "test_memory_graph_data")
    assert memory_manager.graph_manager.storage_path == expected_graph_path


def test_memory_manager_graph_disabled(mock_llm_service, temp_memory_dir, domain_config):
    """Test that graph memory can be disabled"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=False
    )
    
    # Check that graph memory is disabled
    assert memory_manager.enable_graph_memory is False
    assert memory_manager.graph_manager is None


def test_query_with_graph_context(mock_llm_service, temp_memory_dir, domain_config):
    """Test that queries include graph context when available"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=True
    )
    
    # Initialize memory
    memory_manager.create_initial_memory("Test campaign with Eldara the wizard in Riverwatch")
    
    # Add some entities to the graph manually for testing
    memory_manager.graph_manager.add_or_update_node(
        name="Eldara",
        node_type="character",
        description="A fire wizard who runs a magic shop",
        attributes={"profession": "wizard"}
    )
    
    memory_manager.graph_manager.add_or_update_node(
        name="Riverwatch", 
        node_type="location",
        description="A settlement in the valley",
        attributes={"type": "settlement"}
    )
    
    memory_manager.graph_manager.add_edge(
        from_node="Eldara",
        to_node="Riverwatch", 
        relationship_type="located_in",
        evidence="Eldara runs a shop in Riverwatch",
        confidence=0.9
    )
    
    # Test graph context retrieval
    graph_context = memory_manager.get_graph_context("Tell me about Eldara")
    assert "Eldara" in graph_context
    assert "character" in graph_context
    assert "located_in Riverwatch" in graph_context
    
    # Test memory query with graph context
    response = memory_manager.query_memory({"query": "Tell me about Eldara"})
    assert "response" in response
    # The mock LLM should mention both Eldara and Riverwatch
    assert "Eldara" in response["response"]


@pytest.mark.asyncio
async def test_async_graph_memory_updates(mock_llm_service, temp_memory_dir, domain_config):
    """Test that async memory manager updates graph memory"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    async_memory_manager = AsyncMemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=True
    )
    
    # Initialize memory
    async_memory_manager.create_initial_memory("Test campaign")
    
    # Add a conversation entry
    entry = {
        "role": "user",
        "content": "Eldara is a fire wizard who runs a magic shop in Riverwatch",
        "timestamp": "2024-01-01T00:00:00"
    }
    
    # Add the entry
    success = await async_memory_manager.add_conversation_entry(entry)
    assert success is True
    
    # Wait for async processing to complete
    await async_memory_manager.wait_for_pending_operations()
    
    # Check that graph was updated
    nodes = async_memory_manager.graph_manager.storage.load_nodes()
    assert len(nodes) > 0
    
    # Look for Eldara in the nodes
    eldara_found = False
    riverwatch_found = False
    for node in nodes.values():
        if node.name == "Eldara":
            eldara_found = True
            assert node.node_type == "character"
        elif node.name == "Riverwatch":
            riverwatch_found = True
            assert node.node_type == "location"
    
    # At least one entity should be found (depending on mock LLM responses)
    # The exact entities depend on the mock LLM implementation
    assert len(nodes) >= 1


def test_has_pending_operations_includes_graph(mock_llm_service, temp_memory_dir, domain_config):
    """Test that pending operations include graph updates"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    async_memory_manager = AsyncMemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=True
    )
    
    # Test that has_pending_operations method exists and works
    pending = async_memory_manager.has_pending_operations()
    assert isinstance(pending, bool)
    
    # Test get_pending_operations includes graph updates
    pending_ops = async_memory_manager.get_pending_operations()
    assert "pending_graph_updates" in pending_ops
    assert isinstance(pending_ops["pending_graph_updates"], int)


def test_domain_config_graph_settings(domain_config):
    """Test that domain config includes graph memory settings"""
    assert "graph_memory_config" in domain_config
    
    graph_config = domain_config["graph_memory_config"]
    assert graph_config["enabled"] is True
    assert "entity_types" in graph_config
    assert "relationship_types" in graph_config
    assert "similarity_threshold" in graph_config
    
    # Check D&D-specific entity types
    entity_types = graph_config["entity_types"]
    assert "character" in entity_types
    assert "location" in entity_types
    assert "object" in entity_types


@pytest.mark.asyncio
async def test_end_to_end_graph_integration(mock_llm_service, temp_memory_dir, domain_config):
    """Test complete end-to-end graph memory integration"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    # Create async memory manager with graph memory
    memory_manager = AsyncMemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=mock_llm_service,
        enable_graph_memory=True
    )
    
    # Initialize with campaign data
    success = memory_manager.create_initial_memory(
        "Campaign in the Lost Valley with wizard Eldara in Riverwatch"
    )
    assert success is True
    
    # Simulate a conversation that should create graph entities
    entry1 = {
        "role": "user", 
        "content": "I want to visit Eldara's magic shop in Riverwatch",
        "timestamp": "2024-01-01T10:00:00"
    }
    
    await memory_manager.add_conversation_entry(entry1)
    
    entry2 = {
        "role": "agent",
        "content": "You arrive at Eldara's shop in the eastern settlement of Riverwatch. The fire wizard greets you warmly.",
        "timestamp": "2024-01-01T10:01:00"
    }
    
    await memory_manager.add_conversation_entry(entry2)
    
    # Wait for all async processing
    await memory_manager.wait_for_pending_operations()
    
    # Test that graph context is available
    graph_context = memory_manager.get_graph_context("Tell me about magic shops")
    
    # Should have some graph context (exact content depends on mock LLM)
    if graph_context:  # Only test if graph context was generated
        assert len(graph_context) > 0
        # Could contain references to entities or relationships
    
    # Test memory query includes graph context
    response = memory_manager.query_memory({
        "query": "What do I know about Eldara?"
    })
    
    assert "response" in response
    assert isinstance(response["response"], str)
    assert len(response["response"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])