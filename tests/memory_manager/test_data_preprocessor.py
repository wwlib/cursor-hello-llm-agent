"""Tests for the DataPreprocessor class and preprocess_data.prompt."""

import pytest
import os
from src.memory.data_preprocessor import DataPreprocessor
from src.ai.llm_ollama import OllamaService

# Configure Ollama connection
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3")

@pytest.fixture
def llm_service():
    """Create an LLM service for testing."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "data_preprocessor_test"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    general_debug_file = os.path.join(guid_logs_dir, "general.log")
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_LLM_MODEL,
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": general_debug_file,
        "debug_scope": "test_data_preprocessor",
        "console_output": False
    })

@pytest.fixture
def data_preprocessor(llm_service):
    """Create a DataPreprocessor instance for testing."""
    return DataPreprocessor(llm_service)

def test_preprocess_data_typical(data_preprocessor):
    """Test preprocessing typical multi-fact input."""
    input_data = """
The lab is a place for invention. The lab contains cool equipment, including 3D printers, soldering irons, woodworking tools, and more. There are two main workspaces: electronics and fabrication. Safety goggles are required in the fabrication area.
"""
    prose, segments = data_preprocessor.preprocess_data(input_data)
    print(f"\n\nProse: {prose}\n\n")
    assert isinstance(prose, str), "Output should be a string"
    # assert len(phrases) >= 2, "Should return multiple phrases for multi-fact input"
    # for phrase in phrases:
    #     assert isinstance(phrase, str), "Each phrase should be a string"
    #     assert phrase.strip(), "Each phrase should be non-empty"

    # print(phrases)
    # Check that key facts are present
    # combined = " ".join(phrases).lower()
    # for fact in ["lab is a place for invention", "3d printers", "soldering irons", "woodworking tools", "safety goggles"]:
    #     assert fact in combined, f"Fact '{fact}' not found in output"
    # print("\nPreprocessed Phrases (typical):")
    # for i, phrase in enumerate(phrases):
    #     print(f"Phrase {i+1}: {phrase}")

def test_preprocess_data_empty(data_preprocessor):
    """Test preprocessing empty input."""
    prose, segments = data_preprocessor.preprocess_data("")
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 0, "Should return an empty list for empty input"
    prose, segments = data_preprocessor.preprocess_data("   \n\t  ")
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 0, "Should return an empty list for whitespace-only input"

def test_preprocess_data_single_sentence(data_preprocessor):
    """Test preprocessing a single sentence."""
    content = "The quick brown fox jumps over the lazy dog."
    prose, segments  = data_preprocessor.preprocess_data(content)
    print(f"\n\nProse: {prose}\n\n")
    print(f"\n\nSegments: {segments}\n\n")
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 1, "Should return exactly one phrase for a single sentence"
    print(segments)
    # assert phrases[0] == content, "Should return the original content as a single phrase"

def test_preprocess_data_bulleted(data_preprocessor):
    input_data ="""D&D Campaign: The Lost Valley

World Details:
- Hidden valley surrounded by impassable mountains
- Ancient ruins scattered throughout
- Mysterious magical anomalies
- Three main settlements: Haven (central), Riverwatch (east), Mountainkeep (west)

Key NPCs:
1. Elena
   - Role: Mayor of Haven
   - Motivation: Protect the valley's inhabitants
   - Current Quest: Investigate strange occurrences in Haven

2. Theron
   - Role: Master Scholar
   - Expertise: Ancient ruins and artifacts
   - Current Research: Decoding ruin inscriptions

3. Sara
   - Role: Captain of Riverwatch
   - Responsibility: Valley's defense
   - Current Concern: Increased monster activity

Current Situations:
1. Trade Routes
   - Main road between settlements disrupted
   - Merchants seeking protection
   - Alternative routes needed

2. Ancient Ruins
   - New chambers discovered
   - Strange energy emanations
   - Valuable artifacts found

3. Magical Anomalies
   - Random magical effects
   - Affecting local wildlife
   - Possible connection to ruins
"""
    prose, segments = data_preprocessor.preprocess_data(input_data)
    print(f"\n\nProse: {prose}\n\n")
    print(f"\n\nSegments: {segments}\n\n")
    # assert isinstance(phrases, list), "Should return a list"
    # assert len(phrases) >= 2, "Should return multiple phrases for bulleted input"
    # print(phrases)

    # combined = " ".join(phrases).lower()
    # for fact in ["task management system", "user authentication", "task creation", "due date reminders", "project manager", "team members"]:
    #     assert fact in combined, f"Fact '{fact}' not found in output"
    # print("\nPreprocessed Phrases (bulleted):")
    # for i, phrase in enumerate(phrases):
    #     print(f"Phrase {i+1}: {phrase}")
