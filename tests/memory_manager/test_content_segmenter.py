"""Tests for the ContentSegmenter class."""

import pytest
from src.memory.content_segmenter import ContentSegmenter
from src.ai.llm_ollama import OllamaService
import os

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
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
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
    content = """The world is known as The Lost Valley, a place shielded by towering, impassable mountains.
    Within this valley, you'll find ancient ruins scattered across the landscape.
    These ruins are the source of strange occurrences: mysterious magical anomalies, and even random magical effects!
    Currently, there are three main settlements: Haven, governed by Mayor Elena; Riverwatch, and Mountainkeep.
    The valley's inhabitants are increasingly concerned about a rise in monster activity."""
    
    segments = content_segmenter.segment_content(content)
    
    assert isinstance(segments, list), "Segments should be a list"
    assert len(segments) > 1, "Should produce multiple segments"
    
    # Print the segments for inspection
    print("\nComplex Segmentation Results:")
    for i, segment in enumerate(segments):
        print(f"Segment {i}: {segment}")
    
    # Verify that all content is covered by checking for key phrases
    key_phrases = [
        "Lost Valley",
        "impassable mountains",
        "ancient ruins",
        "magical anomalies",
        "three main settlements",
        "Haven",
        "Mayor Elena",
        "Riverwatch",
        "Mountainkeep",
        "monster activity"
    ]
    combined_segments = " ".join(segments).lower()
    for phrase in key_phrases:
        assert phrase.lower() in combined_segments, f"Key phrase '{phrase}' not found in segments" 