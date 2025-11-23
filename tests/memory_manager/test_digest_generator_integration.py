import logging
import pytest
import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.digest_generator import DigestGenerator

def _get_ollama_config():
    """Get Ollama configuration from environment variables with fallbacks."""
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    model = os.getenv('OLLAMA_MODEL', 'gemma3')
    embed_model = os.getenv('OLLAMA_EMBED_MODEL', 'mxbai-embed-large')
    dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
    
    return {
        'base_url': base_url,
        'model': model,
        'embed_model': embed_model,
        'dev_mode': dev_mode
    }

@pytest.fixture(scope="module")
def llm_service():
    """Create an LLM service instance for testing."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    folder_name = "test_digest_generator_integration"
    guid_logs_dir = os.path.join(logs_dir, folder_name)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "ollama_digest.log")
    
    config = _get_ollama_config()
    
    service = OllamaService({
        "base_url": config['base_url'],
        "model": config['model'],
        "default_temperature": 0,
        "stream": False,
        "debug": config['dev_mode'],
        "debug_file": debug_file,
        "debug_scope": "test_digest_generator_integration",
        "console_output": False
    })
    return service

@pytest.fixture(scope="module")
def digest_generator(llm_service):
    """Create a DigestGenerator instance for testing."""
    # Import here to avoid circular imports
    from examples.domain_configs import DND_CONFIG
    # Instantiate a logger for the DigestGenerator
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    folder_name = "test_digest_generator_integration"
    guid_logs_dir = os.path.join(logs_dir, folder_name)
    os.makedirs(guid_logs_dir, exist_ok=True)
    debug_file = os.path.join(guid_logs_dir, "digest_generator.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(debug_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.debug(f"Initialized DigestGenerator for test: test_digest_generator_integration")
    return DigestGenerator(llm_service, domain_name="dnd_campaign", domain_config=DND_CONFIG, logger=logger)

@pytest.fixture(scope="module")
def test_conversation_entry():
    """Provide a test conversation entry."""
    # return {
    #     "guid": "d7be8a68-0c2e-4f84-9be1-a93133866f0e",
    #     "role": "agent",
    #     "content": "The Lost Valley: it's a place of both incredible beauty and unsettling mystery. It's a hidden valley, completely encircled by mountains that are, for reasons no one truly understands, utterly impassable. That's what makes it so special, and so vulnerable.\n\nWithin the valley, you'll find ancient ruins - scattered throughout, some recently discovered to contain new chambers pulsing with strange energy and, of course, valuable artifacts. These ruins are linked to the magical anomalies that plague the area; random magical effects are occurring, and some believe there's a connection between the anomalies and the ruins themselves.\n\nCurrently, there are three main settlements: Haven, where you serve as Mayor, Riverwatch, and Mountainkeep. The valley's inhabitants are concerned about increased monster activity and disrupted trade routes - merchants are seeking protection. And, of course, Theron, a Master Scholar specializing in ancient ruins and artifacts, is currently focused on decoding ruin inscriptions. Sara, the Captain of Riverwatch, bears the responsibility for the valley's defense, and is acutely aware of the threat posed by these disturbances.",
    #     "timestamp": "2025-05-01T16:26:59.498857"
    # }
    return {
        "guid": "d7be8a68-0c2e-4f84-9be1-a93133866f0e",
        "role": "agent",
        "content": "The campaign setting is known as The Lost Valley, a hidden location encircled by impassable mountains. Within this valley, ancient ruins are scattered throughout, and mysterious magical anomalies are prevalent. There are three main settlements: Haven, located centrally; Riverwatch, situated to the east; and Mountainkeep, located to the west. Key non-player characters include Elena, who serves as the Mayor of Haven and whose primary motivation is to protect the valley's inhabitants; Theron, a Master Scholar specializing in ancient ruins and artifacts, currently focused on decoding ruin inscriptions; and Sara, the Captain of Riverwatch, responsible for the valley's defense and currently concerned by increased monster activity. Currently, several situations are unfolding. The main trade route between the settlements has been disrupted, leading merchants to seek protection. Exploratory efforts have uncovered new chambers within the ancient ruins, accompanied by strange energy emanations and the discovery of valuable artifacts. Furthermore, random magical effects are occurring, impacting local wildlife, and there is a suspected connection to the ruins.",
        "timestamp": "2025-05-01T16:26:59.498857"
    }

def test_segment_content(digest_generator, test_conversation_entry):
    """Test segmenting content into meaningful chunks."""
    segments = digest_generator.content_segmenter.segment_content(test_conversation_entry["content"])
    
    assert isinstance(segments, list), "Segments should be a list"
    assert len(segments) > 1, "Should produce multiple segments"
    
    # Print the segments for inspection
    print("\nSegmentation Results:")
    for i, segment in enumerate(segments):
        print(f"Segment {i}: {segment}")

def test_rate_segments(digest_generator, test_conversation_entry):
    """Test rating and classifying segments."""
    # First segment the content
    segments = digest_generator.content_segmenter.segment_content(test_conversation_entry["content"])

    # Print the segments for inspection
    print("\nSegments:")
    print(json.dumps(segments, indent=2))

    # Then rate the segments
    rated_segments = digest_generator._rate_segments(segments)

    # Print the rated segments for inspection
    print("\nRated Segments:")
    print(json.dumps(rated_segments, indent=2))

    assert isinstance(rated_segments, list), "Rated segments should be a list"
    assert len(rated_segments) == len(segments), "Should have same number of rated segments as input segments"
    
    # Verify each rated segment has required fields
    for segment in rated_segments:
        assert isinstance(segment, dict), "Each rated segment should be a dictionary"
        assert "text" in segment, "Each segment should have text"
        assert "importance" in segment, "Each segment should have importance"
        assert "topics" in segment, "Each segment should have topics"
        assert "type" in segment, "Each segment should have type"
        assert segment["type"] in ["query", "information", "action", "command"], "Invalid segment type"

def test_generate_digest(digest_generator, test_conversation_entry):
    """Test generating a digest from a conversation entry."""
    # Generate the digest
    digest = digest_generator.generate_digest(test_conversation_entry)
    
    # Basic structure validation
    assert isinstance(digest, dict), "Digest should be a dictionary"
    assert "conversation_history_entry_guid" in digest, "Digest should include conversation_history_entry_guid"
    assert "rated_segments" in digest, "Digest should include rated_segments"
    assert "role" in digest, "Digest should include role"
    assert "timestamp" in digest, "Digest should include timestamp"
    
    # Validate GUID
    assert digest["conversation_history_entry_guid"] == test_conversation_entry["guid"], "GUID should match"
    
    # Validate rated segments
    rated_segments = digest["rated_segments"]
    assert isinstance(rated_segments, list), "rated_segments should be a list"
    assert len(rated_segments) > 0, "Should have at least one rated segment"
    
    # Validate each segment
    for segment in rated_segments:
        assert isinstance(segment, dict), "Each segment should be a dictionary"
        assert "text" in segment, "Each segment should have text"
        assert "importance" in segment, "Each segment should have importance"
        assert "topics" in segment, "Each segment should have topics"
        assert "type" in segment, "Each segment should have type"
        
        # Validate importance is between 1 and 5
        assert 1 <= segment["importance"] <= 5, "Importance should be between 1 and 5"
        
        # Validate type is one of the allowed values
        assert segment["type"] in ["query", "information", "action", "command"], \
            "Type should be one of: query, information, action, command"
        
        # Validate topics is a list
        assert isinstance(segment["topics"], list), "Topics should be a list"
    
    # Print the digest for inspection
    print("\nGenerated Digest:")
    print(json.dumps(digest, indent=2))


    


