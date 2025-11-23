import os
import pytest
import asyncio
from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("OLLAMA_BASE_URL"),
    reason="Requires OLLAMA_BASE_URL environment variable and running LLM service."
)
async def test_create_and_query_memory_with_real_llm(tmp_path):
    """
    Integration test: Uses the real LLM service to create and query memory.
    Requires OLLAMA_BASE_URL and a running LLM endpoint.
    """
    memory_file = str(tmp_path / "integration_memory.json")
    llm_config = {
        "base_url": os.environ.get("OLLAMA_BASE_URL"),
        "model": os.environ.get("OLLAMA_LLM_MODEL", "gemma3"),
        "embed_model": os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "console_output": False
    }
    try:
        llm_service = OllamaService(llm_config)
    except Exception as e:
        pytest.skip(f"Could not connect to LLM service: {e}")

    memory_guid = "test_memory_manager_integration"
    memory_manager = MemoryManager(memory_guid=memory_guid, memory_file=memory_file, llm_service=llm_service)
    # Create initial memory
    result = memory_manager.create_initial_memory("Integration test data")
    assert result is True
    assert "static_memory" in memory_manager.memory
    print("\n[Integration] Static memory:")
    print(memory_manager.memory["static_memory"])

    # Query memory
    query_result = memory_manager.query_memory({"user_message": "What do I know about integration tests?"})
    assert isinstance(query_result, dict)
    print("\n[Integration] Query response:")
    print(query_result["response"])
    
    # Wait a bit for async processing to complete
    await asyncio.sleep(1)
