import os
from pathlib import Path
import pytest
from src.memory.data_preprocessor import DataPreprocessor
from src.ai.llm_ollama import OllamaService

# Configure Ollama connection
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3")

# Development settings for temp files
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")
DEV_TEMP_DIR = Path("tests/test_files/tmp")

input_data = """
Campaign Setting: The Lost Valley

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

def test_data_preprocessor_integration():
    """Integration test for DataPreprocessor with Ollama LLM service."""
    # Create logs directory structure
    # logs_dir = os.path.join(project_root, "logs")
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "data_preprocessor_test"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    # Create separate debug files for each service
    general_debug_file = os.path.join(guid_logs_dir, "general.log")
    digest_debug_file = os.path.join(guid_logs_dir, "digest.log")
    embed_debug_file = os.path.join(guid_logs_dir, "embed.log")
    
    llm_service = OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_LLM_MODEL,
        "temperature": 0,
        "stream": False,
        "debug": DEV_MODE,
        "debug_file": general_debug_file,
        "debug_scope": "test_data_preprocessor_integration",
        "console_output": DEV_MODE
    })
    preprocessor = DataPreprocessor(llm_service)
    phrases = preprocessor.preprocess_data(input_data)

    print("\nEmbeddable Phrases:")
    for i, phrase in enumerate(phrases):
        print(f"Phrase {i+1}: {phrase}")

    # Assertions
    assert isinstance(phrases, list), "Output should be a list"
    assert 2 <= len(phrases) <= 6, f"Should return 3-5 phrases, got {len(phrases)}"
    for phrase in phrases:
        assert isinstance(phrase, str), "Each phrase should be a string"
        assert phrase.strip(), "Each phrase should be non-empty"

