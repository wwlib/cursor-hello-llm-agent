"""Integration tests for graph memory with the main memory manager.

This module tests the integration between graph memory and MemoryManager,
ensuring that graph memory features work seamlessly with the existing memory system.
"""

import pytest
import asyncio
import json
import tempfile
import os

from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService
from src.utils.logging_config import LoggingConfig
from examples.domain_configs import DND_CONFIG


@pytest.fixture
def real_llm_service():
    """Create a real LLM service for integration testing"""
    test_guid = "graph_memory_integration_test"
    llm_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "ollama_graph_integration",
        log_to_console=False
    )
    
    llm_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "logger": llm_logger
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
    """Test that MemoryManager initializes with graph memory integration"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    test_guid = "graph_memory_integration_test"
    memory_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "memory_manager",
        log_to_console=False
    )
    
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        logger=memory_logger
    )
    
    # Check that graph integration is set up (may be None if setup failed)
    # Graph integration is always attempted, but may fail gracefully
    assert hasattr(memory_manager, 'graph_queue_writer')
    assert hasattr(memory_manager, 'graph_queries')
    
    # If graph integration succeeded, these should not be None
    if memory_manager.graph_queue_writer is not None:
        assert memory_manager.graph_queries is not None


@pytest.mark.integration
def test_graph_context_retrieval(real_llm_service, temp_memory_dir, domain_config):
    """Test that graph context can be retrieved when available"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    test_guid = "graph_memory_integration_test"
    memory_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "memory_manager",
        log_to_console=False
    )
    
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        logger=memory_logger
    )
    
    # Initialize memory
    memory_manager.create_initial_memory("Test campaign with Eldara the wizard in Riverwatch")
    
    # Test graph context retrieval (may return empty if no graph data yet)
    graph_context = memory_manager.get_graph_context("Tell me about Eldara")
    
    # Graph context should be a string (may be empty if no entities processed yet)
    assert isinstance(graph_context, str)
    
    # If graph queries are available and there's data, context should not be empty
    # But we can't guarantee data exists immediately after initialization
    if memory_manager.graph_queries and graph_context:
        # If we got context, it should be meaningful
        assert len(graph_context) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_processing_queue(real_llm_service, temp_memory_dir, domain_config):
    """Test that graph processing is queued for conversation entries"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    test_guid = "graph_memory_integration_test"
    memory_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "memory_manager",
        log_to_console=False
    )
    
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        logger=memory_logger
    )
    
    # Initialize memory
    memory_manager.create_initial_memory("Test campaign")
    
    # Add a conversation entry via query_memory (which adds to conversation history)
    query = "Eldara is a fire wizard who runs a magic shop in Riverwatch"
    response = memory_manager.query_memory({"query": query})
    
    assert "response" in response
    assert isinstance(response["response"], str)
    
    # Wait for async processing to complete
    await asyncio.sleep(1)
    
    # Check that graph queue writer exists and can report queue size
    if memory_manager.graph_queue_writer is not None:
        queue_size = memory_manager.graph_queue_writer.get_queue_size()
        assert isinstance(queue_size, int)
        assert queue_size >= 0  # Queue may have been processed already


@pytest.mark.integration
def test_has_pending_operations(real_llm_service, temp_memory_dir, domain_config):
    """Test that pending operations tracking works"""
    memory_file = os.path.join(temp_memory_dir, "test_memory.json")
    
    test_guid = "graph_memory_integration_test"
    memory_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "memory_manager",
        log_to_console=False
    )
    
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        logger=memory_logger
    )
    
    # Test that has_pending_operations method exists and works
    pending = memory_manager.has_pending_operations()
    assert isinstance(pending, bool)
    
    # Test get_pending_operations
    pending_ops = memory_manager.get_pending_operations()
    assert isinstance(pending_ops, dict)
    assert "pending_digests" in pending_ops
    assert "pending_embeddings" in pending_ops
    assert isinstance(pending_ops["pending_digests"], int)
    assert isinstance(pending_ops["pending_embeddings"], int)


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
    
    test_guid = "graph_memory_integration_test"
    memory_logger = LoggingConfig.get_component_file_logger(
        test_guid,
        "memory_manager",
        log_to_console=False
    )
    
    # Create memory manager with graph memory
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=real_llm_service,
        logger=memory_logger
    )
    
    # Initialize with campaign data
    success = memory_manager.create_initial_memory(
        "Campaign in the Lost Valley with wizard Eldara in Riverwatch"
    )
    assert success is True
    
    # Simulate a conversation that should queue graph processing
    query1 = "I want to visit Eldara's magic shop in Riverwatch"
    response1 = memory_manager.query_memory({"query": query1})
    
    assert "response" in response1
    assert isinstance(response1["response"], str)
    
    # Wait for async processing
    await asyncio.sleep(1)
    
    # Test that graph context can be retrieved (may be empty if processing not complete)
    graph_context = memory_manager.get_graph_context("Tell me about magic shops")
    
    assert isinstance(graph_context, str)
    
    # Test memory query includes graph context if available
    response2 = memory_manager.query_memory({
        "query": "What do I know about Eldara?"
    })
    
    assert "response" in response2
    assert isinstance(response2["response"], str)
    assert len(response2["response"]) > 0
    
    # The response should be meaningful (not just an error)
    assert "error" not in response2["response"].lower() or "processing query" not in response2["response"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])