import unittest
from unittest.mock import Mock, patch, mock_open
import json
import uuid
import os
from src.memory.digest_generator import DigestGenerator

class MockLLMService:
    """Mock LLM service for testing the DigestGenerator."""
    
    def __init__(self, segment_response=None, extract_response=None):
        self.segment_response = segment_response
        self.extract_response = extract_response
        self.generate_call_count = 0
        self.last_prompt = None
    
    def generate(self, prompt):
        """Mock the generate method of the LLM service."""
        self.generate_call_count += 1
        self.last_prompt = prompt
        
        # Return different responses based on the prompt content
        if "SEGMENTED CONTENT" in prompt:
            # This is an extract call
            return self.extract_response
        else:
            # This is a segment call
            return self.segment_response


class TestDigestGenerator(unittest.TestCase):
    """Test cases for the DigestGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample test data
        self.sample_segments = [
            "Captain Sara patrols the eastern border with her squad of ten guards.",
            "She's concerned about recent monster sightings.",
            "She has requested additional resources."
        ]
        
        self.sample_extracted_info = {
            "context": "Discussing border patrol operations and resource needs",
            "new_facts": [
                {
                    "segmentIndexes": [0],
                    "key": "patrol_location",
                    "value": "eastern border",
                    "context": "Where Captain Sara conducts patrols",
                    "source": "assistant",
                    "importance": "high",
                    "topic": "Border Security"
                },
                {
                    "segmentIndexes": [1],
                    "key": "security_concern",
                    "value": "monster sightings",
                    "context": "Current security concern in the region",
                    "source": "assistant",
                    "importance": "high",
                    "topic": "Threats"
                }
            ],
            "new_relationships": [
                {
                    "segmentIndexes": [0, 2],
                    "subject": "Captain Sara",
                    "predicate": "REQUESTED",
                    "object": "additional resources",
                    "context": "Sara needs more resources for patrol operations",
                    "source": "inferred",
                    "importance": "medium",
                    "topic": "Resource Management"
                }
            ]
        }
        
        # Create a conversation entry for testing
        self.test_entry = {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": "Captain Sara patrols the eastern border with her squad of ten guards. She's concerned about recent monster sightings. She has requested additional resources.",
            "timestamp": "2025-04-15T10:30:00"
        }
        
        # Set up mock responses
        self.segment_response = json.dumps(self.sample_segments)
        self.extract_response = json.dumps(self.sample_extracted_info)
        
        # Create a mock LLM service
        self.mock_llm = MockLLMService(
            segment_response=self.segment_response,
            extract_response=self.extract_response
        )
        
        # Mock template content
        self.segment_template = "You are a text analysis system. Your task is to segment the provided content into meaningful phrases.\n\nCONTENT:\n{content}\n\nINSTRUCTIONS:\n1. Divide the content into segments"
        self.extract_template = "You are a knowledge extraction system. Your task is to analyze the segmented content.\n\nSEGMENTED CONTENT:\n{segments}\n\nINSTRUCTIONS:\n1. Analyze each segment"
        
        # Mock the open function to return our template content
        self.mock_open_impl = mock_open()
        self.mock_open_impl.return_value.__enter__.side_effect = [
            Mock(read=Mock(return_value=self.segment_template)),
            Mock(read=Mock(return_value=self.extract_template))
        ]
        
        # Create the DigestGenerator with the mock LLM service and mocked template files
        with patch('builtins.open', self.mock_open_impl):
            self.digest_generator = DigestGenerator(self.mock_llm)
            # Set the templates manually
            self.digest_generator.templates = {
                "segment": self.segment_template,
                "extract": self.extract_template
            }
    
    def test_segment_content(self):
        """Test the _segment_content method."""
        content = "This is a test content. It should be segmented."
        
        # Configure mock LLM response
        self.mock_llm.segment_response = json.dumps(["This is a test content.", "It should be segmented."])
        
        # Call the method
        segments = self.digest_generator._segment_content(content)
        
        # Verify the result
        self.assertEqual(2, len(segments))
        self.assertEqual("This is a test content.", segments[0])
        self.assertEqual("It should be segmented.", segments[1])
        
        # Verify the LLM was called with the correct prompt
        self.assertIn(content, self.mock_llm.last_prompt)
    
    def test_extract_information(self):
        """Test the _extract_information method."""
        # Call the method
        extracted_info = self.digest_generator._extract_information(self.sample_segments)
        
        # Verify the result
        self.assertEqual("Discussing border patrol operations and resource needs", extracted_info["context"])
        self.assertEqual(2, len(extracted_info["new_facts"]))
        self.assertEqual(1, len(extracted_info["new_relationships"]))
        
        # Verify a specific fact
        fact = extracted_info["new_facts"][0]
        self.assertEqual("patrol_location", fact["key"])
        self.assertEqual("eastern border", fact["value"])
        
        # Verify a relationship
        relationship = extracted_info["new_relationships"][0]
        self.assertEqual("Captain Sara", relationship["subject"])
        self.assertEqual("REQUESTED", relationship["predicate"])
        self.assertEqual("additional resources", relationship["object"])
    
    def test_generate_digest(self):
        """Test the generate_digest method."""
        # Call the method
        digest = self.digest_generator.generate_digest(self.test_entry)
        
        # Verify the result
        self.assertEqual(self.test_entry["guid"], digest["conversationHistoryGuid"])
        self.assertEqual(3, len(digest["segments"]))
        self.assertEqual("Discussing border patrol operations and resource needs", digest["context"])
        self.assertEqual(2, len(digest["new_facts"]))
        self.assertEqual(1, len(digest["new_relationships"]))
    
    def test_generate_digest_with_no_guid(self):
        """Test the generate_digest method with an entry that has no GUID."""
        # Create a test entry without a GUID
        test_entry_no_guid = {
            "role": "assistant", 
            "content": "Test content",
            "timestamp": "2025-04-15T10:30:00"
        }
        
        # Call the method
        digest = self.digest_generator.generate_digest(test_entry_no_guid)
        
        # Verify a GUID was generated and added to the entry
        self.assertIsNotNone(test_entry_no_guid.get("guid"))
        self.assertEqual(test_entry_no_guid["guid"], digest["conversationHistoryGuid"])
    
    def test_segment_content_json_error(self):
        """Test the _segment_content method when JSON parsing fails."""
        content = "Test content"
        
        # Configure mock to return invalid JSON
        self.mock_llm.segment_response = "This is not JSON"
        
        # Call the method
        segments = self.digest_generator._segment_content(content)
        
        # Verify fallback behavior
        self.assertEqual(1, len(segments))
        self.assertEqual(content, segments[0])
    
    def test_extract_information_json_error(self):
        """Test the _extract_information method when JSON parsing fails."""
        # Configure mock to return invalid JSON
        self.mock_llm.extract_response = "This is not JSON"
        
        # Call the method
        extracted_info = self.digest_generator._extract_information(self.sample_segments)
        
        # Verify fallback to empty structure
        self.assertEqual("", extracted_info["context"])
        self.assertEqual(0, len(extracted_info["new_facts"]))
        self.assertEqual(0, len(extracted_info["new_relationships"]))
    
    def test_generate_digest_with_empty_content(self):
        """Test the generate_digest method with empty content."""
        # Create a test entry with empty content
        test_entry_empty = {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": "",
            "timestamp": "2025-04-15T10:30:00"
        }
        
        # Call the method
        digest = self.digest_generator.generate_digest(test_entry_empty)
        
        # Verify empty digest creation
        self.assertEqual(test_entry_empty["guid"], digest["conversationHistoryGuid"])
        self.assertEqual(0, len(digest["segments"]))
        self.assertEqual("", digest["context"])
        self.assertEqual(0, len(digest["new_facts"]))
        self.assertEqual(0, len(digest["new_relationships"]))
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_templates(self, mock_file, mock_exists):
        """Test template loading functionality."""
        # Setup mock to simulate that template files exist
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.side_effect = [
            self.segment_template,
            self.extract_template
        ]
        
        # Create a new DigestGenerator instance to test template loading
        digest_generator = DigestGenerator(self.mock_llm)
        
        # Verify that the templates were loaded
        self.assertIn("segment", digest_generator.templates)
        self.assertIn("extract", digest_generator.templates)
        self.assertEqual(self.segment_template, digest_generator.templates["segment"])
        self.assertEqual(self.extract_template, digest_generator.templates["extract"])


if __name__ == "__main__":
    unittest.main() 