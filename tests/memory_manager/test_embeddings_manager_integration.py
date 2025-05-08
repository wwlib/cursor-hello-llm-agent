"""Integration tests for the EmbeddingsManager class with actual LLM calls."""

import pytest
import os
import json
import numpy as np
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

from src.memory.embeddings_manager import EmbeddingsManager
from src.ai.llm_ollama import OllamaService

# Test data paths - memory snapshots from a DND game
TEST_DATA_DIR = Path("tests/memory_manager/memory_snapshots/rag")
TEST_MEMORY_PATH = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162.json"
TEST_CONVERSATIONS_PATH = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162_conversations.json"

# Configure Ollama connection
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Development settings for temp files
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")
DEV_TEMP_DIR = Path("tests/test_files/tmp")

def clear_file(file_path):
    """Ensure the file exists and is empty to start with a clean state.
    
    This helps prevent test interference when running in DEV_MODE.
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create or truncate the file to ensure it's empty
    with open(file_path, 'w') as f:
        pass
    
    print(f"Cleared file for testing: {file_path}")

@pytest.fixture
def llm_service():
    """Create an instance of OllamaService for testing."""
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "debug": True,
        "debug_scope": "test_embeddings_manager",
        "console_output": True
    })
    
@pytest.fixture
def temp_embeddings_file():
    """Create a temporary embeddings file for testing.
    
    When DEV_MODE is enabled:
    - Files are created in DEV_TEMP_DIR instead of system temp directory
    - Files are not automatically deleted after tests
    - A timestamp is added to the filename to prevent conflicts
    
    This makes it easier to inspect the files during development.
    """
    if DEV_MODE:
        # Create the dev temp directory if it doesn't exist
        DEV_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"embeddings_test_{timestamp}.jsonl"
        temp_path = DEV_TEMP_DIR / filename
        
        # Create the file
        temp_path.touch()
        print(f"[DEV MODE] Created test file at: {temp_path}")
        
        yield str(temp_path)
        
        # In dev mode, we don't delete the file
        print(f"[DEV MODE] Keeping test file for inspection: {temp_path}")
    else:
        # Standard tempfile behavior for normal test runs
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as temp_file:
            temp_path = temp_file.name
            print(f"Created temporary embeddings file: {temp_path}")
        
        yield temp_path
        
        # Clean up after test
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"Removed temporary file: {temp_path}")

@pytest.fixture
def test_conversation_data():
    """Load test conversation data from the snapshot file."""
    if not TEST_CONVERSATIONS_PATH.exists():
        pytest.skip(f"Test conversation data not found at {TEST_CONVERSATIONS_PATH}")
        
    with open(TEST_CONVERSATIONS_PATH, 'r') as f:
        return json.load(f)

def test_embeddings_manager_init(llm_service, temp_embeddings_file):
    """Test that the EmbeddingsManager initializes correctly."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    assert manager.embeddings_file == temp_embeddings_file
    assert manager.llm_service == llm_service
    assert isinstance(manager.embeddings, list)
    assert len(manager.embeddings) == 0  # Empty initially

def test_generate_embedding(llm_service, temp_embeddings_file):
    """Test generating a single embedding."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    
    # Generate embedding for a test text
    test_text = "This is a test sentence for embedding generation."
    embedding = manager.generate_embedding(test_text)
    
    # Check that we got a valid embedding
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape[0] > 0
    
    # Check that the embedding is normalized (approximately)
    norm = np.linalg.norm(embedding)
    assert abs(norm - 1.0) < 1e-6

def test_add_embedding(llm_service, temp_embeddings_file):
    """Test adding an embedding to the store."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    
    # Add an embedding
    test_text = "This is a test sentence for embedding storage."
    metadata = {
        "guid": "test-guid-1",
        "timestamp": datetime.now().isoformat(),
        "role": "user",
        "type": "full_entry"
    }
    
    success = manager.add_embedding(test_text, metadata)
    assert success is True
    
    # Check that it's in memory
    assert len(manager.embeddings) == 1
    stored_embedding, stored_metadata = manager.embeddings[0]
    assert isinstance(stored_embedding, np.ndarray)
    assert stored_metadata["guid"] == "test-guid-1"
    
    # Check that it's in the file
    assert os.path.exists(temp_embeddings_file)
    with open(temp_embeddings_file, 'r') as f:
        data = json.loads(f.read().strip())
        assert data["metadata"]["guid"] == "test-guid-1"
        assert isinstance(data["embedding"], list)

def test_load_embeddings(llm_service, temp_embeddings_file):
    """Test loading embeddings from a file."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    # Create a file with some test embeddings
    test_embeddings = [
        {
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "metadata": {
                "guid": "test-guid-2",
                "timestamp": datetime.now().isoformat(),
                "role": "agent",
                "type": "full_entry"
            }
        },
        {
            "embedding": [0.5, 0.6, 0.7, 0.8],
            "metadata": {
                "guid": "test-guid-3",
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "type": "segment",
                "importance": 4,
                "topics": ["test", "topic"]
            }
        }
    ]
    
    with open(temp_embeddings_file, 'w') as f:
        for item in test_embeddings:
            f.write(json.dumps(item) + '\n')
    
    # Create a new manager that loads these embeddings
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    
    # Check that embeddings were loaded correctly
    assert len(manager.embeddings) == 2
    assert manager.embeddings[0][1]["guid"] == "test-guid-2"
    assert manager.embeddings[1][1]["guid"] == "test-guid-3"
    assert np.array_equal(manager.embeddings[0][0], np.array([0.1, 0.2, 0.3, 0.4]))

def test_add_multiple_embeddings(llm_service, temp_embeddings_file):
    """Test adding multiple embeddings to the store."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    
    # Add multiple embeddings
    test_texts = [
        "This is the first test sentence.",
        "This is the second test sentence, which is different.",
        "This is a completely unrelated sentence about cats."
    ]
    
    for i, text in enumerate(test_texts):
        metadata = {
            "guid": f"test-guid-multi-{i}",
            "timestamp": datetime.now().isoformat(),
            "role": "user" if i % 2 == 0 else "agent",
            "type": "full_entry"
        }
        
        success = manager.add_embedding(text, metadata)
        assert success is True
    
    # Check that all were added
    assert len(manager.embeddings) == 3
    
    # Check the file contents
    with open(temp_embeddings_file, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 3
        
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["metadata"]["guid"] == f"test-guid-multi-{i}"

@pytest.mark.skipif(not TEST_CONVERSATIONS_PATH.exists(), 
                    reason=f"Test conversation data not found at {TEST_CONVERSATIONS_PATH}")
def test_update_embeddings_from_conversation_history(llm_service, temp_embeddings_file, test_conversation_data):
    """Test updating embeddings from conversation history."""
    # Ensure file is empty at start
    clear_file(temp_embeddings_file)
    
    manager = EmbeddingsManager(temp_embeddings_file, llm_service)
    
    # Get conversation entries
    entries = test_conversation_data.get("entries", [])
    assert len(entries) > 0, "No entries found in test conversation data"
    
    # Update embeddings from this history
    success = manager.update_embeddings(entries)
    assert success is True
    
    # Calculate expected number of embeddings (entries + segments)
    expected_count = 0
    for entry in entries:
        if 'digest' in entry and 'rated_segments' in entry['digest']:
            expected_count += len(entry['digest']['rated_segments'])
    
    # Check that we have the right number of embeddings
    assert len(manager.embeddings) == expected_count
    
    # Check file exists and is not empty
    assert os.path.exists(temp_embeddings_file)
    assert os.path.getsize(temp_embeddings_file) > 0



