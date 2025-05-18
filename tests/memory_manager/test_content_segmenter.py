"""Tests for the ContentSegmenter class."""

import pytest
from src.memory.content_segmenter import ContentSegmenter
from src.ai.llm_ollama import OllamaService
import os

# Configure Ollama connection
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3")

@pytest.fixture
def llm_service():
    """Create an LLM service for testing."""
    # Create logs directory structure
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "content_segmenter_test"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    # Create separate debug files for each service
    general_debug_file = os.path.join(guid_logs_dir, "general.log")
    digest_debug_file = os.path.join(guid_logs_dir, "digest.log")
    embed_debug_file = os.path.join(guid_logs_dir, "embed.log")
    
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_LLM_MODEL,
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": general_debug_file,
        "debug_scope": "test_content_segmenter",
        "console_output": False
    })

@pytest.fixture
def content_segmenter(llm_service):
    """Create a ContentSegmenter instance for testing."""
    return ContentSegmenter(llm_service)

def test_segment_content(content_segmenter):
    """Test segmenting content into meaningful chunks."""
    # Test with a simple text
    content = "Captain Sara patrols the eastern border with her squad of ten guards. She's concerned about recent monster sightings and has requested additional resources."
    segments = content_segmenter.segment_content(content)
    
    assert isinstance(segments, list), "Segments should be a list"
    assert len(segments) > 1, "Should produce multiple segments"
    
    # Print the segments for inspection
    print("\nSegmentation Results:")
    for i, segment in enumerate(segments):
        print(f"Segment {i}: {segment}")
    
    # Verify that all content is covered by checking for key phrases
    # This is more flexible than exact character matching
    key_phrases = [
        "Captain Sara",
        "eastern border",
        "squad of ten guards",
        "monster sightings",
        "additional resources"
    ]
    combined_segments = " ".join(segments).lower()
    for phrase in key_phrases:
        assert phrase.lower() in combined_segments, f"Key phrase '{phrase}' not found in segments"

def test_segment_content_empty(content_segmenter):
    """Test segmenting empty content."""
    segments = content_segmenter.segment_content("")
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 0, "Should return an empty list for empty input"
    
    # Test with whitespace-only content
    segments = content_segmenter.segment_content("   \n\t  ")
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 0, "Should return an empty list for whitespace-only input"

def test_segment_content_single_sentence(content_segmenter):
    """Test segmenting a single sentence."""
    content = "This is a single sentence."
    segments = content_segmenter.segment_content(content)
    
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 1, "Should return exactly one segment for a single sentence"
    assert segments[0] == content, "Should return the original content as a single segment"
    
    # Test with another single sentence
    content = "The quick brown fox jumps over the lazy dog"
    segments = content_segmenter.segment_content(content)
    
    assert isinstance(segments, list), "Should return a list"
    assert len(segments) == 1, "Should return exactly one segment for a single sentence"
    assert segments[0] == content, "Should return the original content as a single segment"

def test_segment_content_complex(content_segmenter):
    """Test segmenting complex content with multiple types of sentences."""

#     content = """
# The world is known as The Lost Valley, a place shielded by towering, impassable mountains. Within this valley, you'll find ancient ruins scattered across the landscape. These ruins are the source of strange occurrences: mysterious magical anomalies, and even random magical effects! Currently, there are three main settlements: Haven, governed by Mayor Elena; Riverwatch, and Mountainkeep. The valley's inhabitants are increasingly concerned about a rise in monster activity.
# """

    content = """
The campaign, titled "The Lost Valley," unfolds within a geographically isolated and remarkably ancient region. The core of the setting is a hidden valley, shielded by towering, impassable mountains, a natural fortress that has allowed the valley to remain largely untouched by the outside world for centuries. Within this valley, the remnants of a long-lost civilization are evident - scattered, crumbling ruins dot the landscape, each whispering of a powerful and now vanished people. Adding to the area's mystique are numerous magical anomalies, ranging from subtle distortions to outright chaotic bursts of energy, and these are strongly linked to the ruins.

The valley's inhabitants are centered around three distinct settlements. Haven, located in the heart of the valley, serves as the primary trading hub and administrative center, governed by Mayor Elena. Elena's foremost motivation is the protection of the valley's inhabitants, a responsibility she takes with unwavering dedication. Currently, she is grappling with a series of unsettling events within Haven, investigating a surge in unusual occurrences that threaten the stability of the town.

To the east lies Riverwatch, a strategically positioned settlement captained by Sara, the fiercely protective Captain. Her primary responsibility is the defense of the valley, and she's currently deeply concerned by a marked increase in monster activity along the valley's borders.  Finally, to the west sits Mountainkeep, a smaller, more isolated settlement, though its precise function remains somewhat unclear.

Recent exploration has unveiled new chambers within the ancient ruins, triggering the discovery of powerful and potentially dangerous energy emanations. These emanations are fueling the research of Theron, a Master Scholar dedicated to deciphering the inscriptions found within the ruins.  Theron believes these inscriptions hold the key to understanding the civilization that once thrived in this valley and unlocking the source of the anomalies. He theorizes that a connection exists between the ruins and the magical disturbances.

Currently, the established trade routes between the settlements are severely disrupted, creating a critical need for alternative routes and increased protection for merchants traveling through the valley. The instability has created a climate of vulnerability, with merchants seeking refuge and urging for stronger defenses.  Furthermore, the discovery of valuable artifacts within the newly revealed chambers suggests a potential treasure trove, attracting unwanted attention and complicating matters further. The strange magical anomalies continue to manifest, impacting local wildlife and reinforcing the suspicion that they are intrinsically linked to the ancient ruins.
"""

    # content = "we have several colors of 3d printer filament including white, black, grey, red, green, and blue."

    # content = "we have 2 printers in teh lab. a bambu a1 mini and a creality ender 3 v3 ke"
    
    segments = content_segmenter.segment_content(content)
    
    assert isinstance(segments, list), "Segments should be a list"
    assert len(segments) > 0, "Should produce at least one segment"
    
    # Print the segments for inspection
    print("\nComplex Segmentation Results:")
    for i, segment in enumerate(segments):
        print(f"Segment {i}: {segment}")
    
    # Verify that all content is covered by checking for key phrases
    # key_phrases = [
    #     "Lost Valley",
    #     "impassable mountains",
    #     "ancient ruins",
    #     "magical anomalies",
    #     "three main settlements",
    #     "Haven",
    #     "Mayor Elena",
    #     "Riverwatch",
    #     "Mountainkeep",
    #     "monster activity"
    # ]
    # combined_segments = " ".join(segments).lower()
    # for phrase in key_phrases:
    #     assert phrase.lower() in combined_segments, f"Key phrase '{phrase}' not found in segments" 