"""Integration tests for graph memory with the main memory manager.

This module tests the integration between the GraphManager and MemoryManager,
ensuring that graph memory features work seamlessly with the existing memory system.
"""

import pytest
import asyncio
import json
import tempfile
import os

from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService
from examples.domain_configs import DND_CONFIG


@pytest.fixture
def real_llm_service():
    """Create a real LLM service for integration testing"""
    llm_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embedding_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "debug": False,
        "console_output": False
    }
    return OllamaService(llm_config)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def domain_config():
    """Get D&D domain configuration for testing"""
    return DND_CONFIG


@pytest.mark.integration
def test_memory_manager_graph_initialization(real_llm_service, temp_memory_dir, domain_config):
    """Test that MemoryManager initializes with graph memory enabled"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        enable_graph_memory=True
    )
    
    # Check that graph memory is enabled
    assert memory_manager.enable_graph_memory is True
    assert memory_manager.graph_manager is not None
    
    # Check that graph storage path is properly set
    expected_graph_path = os.path.join(temp_memory_dir, "test_memory_graph_data")
    assert memory_manager.graph_manager.storage.storage_path == expected_graph_path


@pytest.mark.integration
def test_memory_manager_graph_disabled(real_llm_service, temp_memory_dir, domain_config):
    """Test that graph memory can be disabled"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        enable_graph_memory=False
    )
    
    # Check that graph memory is disabled
    assert memory_manager.enable_graph_memory is False
    assert memory_manager.graph_manager is None


@pytest.mark.integration
def test_query_with_graph_context(real_llm_service, temp_memory_dir, domain_config):
    """Test that queries include graph context when available"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
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
    
    # With real LLM calls, we should get some context but can't predict exact format
    # The context should contain information about Eldara since we manually added her
    assert "Eldara" in graph_context, f"Expected 'Eldara' in graph context: {graph_context}"
    assert "character" in graph_context, f"Expected 'character' in graph context: {graph_context}"
    
    # Since we manually added a relationship, there should be some connection info
    assert ("located_in" in graph_context or "Riverwatch" in graph_context), f"Expected relationship info in graph context: {graph_context}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_graph_memory_updates(real_llm_service, temp_memory_dir, domain_config):
    """Test that async memory manager updates graph memory"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    async_memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
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
    
    # Check that some entities were extracted and added to the graph
    # With real LLM calls, we can't predict exact entities, but there should be some
    assert len(nodes) >= 1, f"Expected at least 1 entity to be extracted, but found {len(nodes)}"
    
    # Log what entities were found for debugging
    print(f"Entities found in graph: {[node['name'] for node in nodes.values()]}")


@pytest.mark.integration
def test_has_pending_operations_includes_graph(real_llm_service, temp_memory_dir, domain_config):
    """Test that pending operations include graph updates"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    async_memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
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
@pytest.mark.integration
async def test_end_to_end_graph_integration(real_llm_service, temp_memory_dir, domain_config):
    """Test complete end-to-end graph memory integration"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    # Create async memory manager with graph memory
    memory_manager = MemoryManager(
        memory_guid="test-guid",
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
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
    
    # Test that graph context is available after processing
    graph_context = memory_manager.get_graph_context("Tell me about magic shops")
    
    # With real LLM calls, we should get some graph context if entities were extracted
    # The exact content depends on what the real LLM extracted
    print(f"Graph context for 'magic shops': {graph_context}")
    
    # Test memory query includes graph context  
    response = memory_manager.query_memory({
        "query": "What do I know about Eldara?"
    })
    
    assert "response" in response
    assert isinstance(response["response"], str)
    assert len(response["response"]) > 0
    
    # The response should be meaningful (not just an error)
    assert "error" not in response["response"].lower() or "processing query" not in response["response"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])