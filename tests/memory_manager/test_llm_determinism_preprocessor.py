"""Focused determinism tests for the DataPreprocessor class."""

import os
from pathlib import Path

import pytest

from src.memory.data_preprocessor import DataPreprocessor
from src.ai.llm_ollama import OllamaService
from src.utils.logging_config import LoggingConfig


# Use environment variables with fallbacks for different Ollama instances
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_M4_BASE_URL = os.getenv("OLLAMA_M4_BASE_URL", "http://192.168.10.28:11434")
OLLAMA_PC_BASE_URL = os.getenv("OLLAMA_PC_BASE_URL", "http://192.168.10.18:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3")

# Test GUID for logging
TEST_GUID = "data_preprocessor_determinism_test"


def _create_ollama_service(base_url: str, service_label: str) -> OllamaService:
    """Create an OllamaService instance with proper logging."""
    llm_logger = LoggingConfig.get_component_file_logger(
        TEST_GUID,
        f"ollama_{service_label}",
        log_to_console=False
    )
    
    return OllamaService({
        "base_url": base_url,
        "model": OLLAMA_LLM_MODEL,
        "temperature": 0,  # Critical for determinism
        "stream": False,
        "logger": llm_logger
    })


@pytest.fixture(scope="module")
def preprocessor_logger():
    """Create logger for DataPreprocessor."""
    return LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "data_preprocessor",
        log_to_console=False
    )


@pytest.fixture(scope="module")
def llm_service(preprocessor_logger):
    """Provide an Ollama service instance configured for determinism checks."""
    _ = preprocessor_logger  # Ensure logger fixture runs (side effects only)
    return _create_ollama_service(OLLAMA_M4_BASE_URL, "primary")


@pytest.fixture(scope="module")
def data_preprocessor(llm_service, preprocessor_logger):
    """Create DataPreprocessor instance for determinism testing."""
    return DataPreprocessor(llm_service, logger=preprocessor_logger)


@pytest.fixture(scope="module")
def m4_preprocessor(preprocessor_logger):
    """Create DataPreprocessor instance using M4 Ollama instance."""
    service = _create_ollama_service(OLLAMA_M4_BASE_URL, "m4")
    return DataPreprocessor(service, logger=preprocessor_logger)


@pytest.fixture(scope="module")
def pc_preprocessor(preprocessor_logger):
    """Create DataPreprocessor instance using PC Ollama instance."""
    service = _create_ollama_service(OLLAMA_PC_BASE_URL, "pc")
    return DataPreprocessor(service, logger=preprocessor_logger)


def test_preprocess_data_repeatable(data_preprocessor):
    """Repeated calls with identical input should produce identical results."""
    input_text = (
        "Aurora Station maintains a hydroponic garden. "
        "Crew rotations occur every six weeks to tend the crops."
    )

    runs = [data_preprocessor.preprocess_data(input_text) for _ in range(3)]
    baseline_prose, baseline_segments = runs[0]

    assert baseline_prose.strip(), "Expected prose output from preprocessing"
    assert isinstance(baseline_segments, list), "Segments should be returned as a list"

    for prose, segments in runs[1:]:
        assert prose == baseline_prose, "Prose output should remain deterministic"
        assert segments == baseline_segments, "Segment output should remain deterministic"


STRUCTURED_INPUT = """
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


def test_preprocess_data_repeatable_for_structured_input(data_preprocessor):
    """Structured input should also produce deterministic prose and segmentation."""
    structured_input = STRUCTURED_INPUT

    first_prose, first_segments = data_preprocessor.preprocess_data(structured_input)
    second_prose, second_segments = data_preprocessor.preprocess_data(structured_input)

    assert first_prose == second_prose, "Prose output should be consistent across runs"
    assert first_segments == second_segments, "Segment output should be consistent across runs"
    assert all(isinstance(seg, str) and seg.strip() for seg in first_segments), \
        "Segments should be non-empty strings"


def test_preprocess_data_consistent_across_instances(m4_preprocessor, pc_preprocessor):
    """Different hardware instances should yield identical outputs with temperature 0."""
    input_text = (
        "Archive vault access requires dual-authentication. "
        "Maintenance checks occur every Friday at 1400 hours."
    )

    m4_prose, m4_segments = m4_preprocessor.preprocess_data(input_text)
    pc_prose, pc_segments = pc_preprocessor.preprocess_data(input_text)

    assert m4_prose == pc_prose, "Cross-instance prose should match exactly"
    assert m4_segments == pc_segments, "Cross-instance segments should match exactly"


def test_preprocess_structured_input_consistent_across_instances(m4_preprocessor, pc_preprocessor):
    """Structured inputs should remain consistent across hardware instances."""
    m4_prose, m4_segments = m4_preprocessor.preprocess_data(STRUCTURED_INPUT)
    pc_prose, pc_segments = pc_preprocessor.preprocess_data(STRUCTURED_INPUT)

    assert m4_prose == pc_prose, "Cross-instance prose (structured) should match exactly"
    assert m4_segments == pc_segments, "Cross-instance segments (structured) should match exactly"