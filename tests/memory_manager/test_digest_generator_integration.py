import unittest
import json
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime
import time

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.digest_generator import DigestGenerator


class TestDigestGeneratorIntegration(unittest.TestCase):
    """Integration tests for the DigestGenerator class using a real LLM."""
    
    @classmethod
    def setUpClass(cls):
        """Set up shared test fixtures that run once for the entire test class."""
        # Skip the tests if we're in CI or don't want to call real LLMs
        if os.environ.get("SKIP_LLM_TESTS") == "1":
            raise unittest.SkipTest("Skipping integration tests that call real LLMs")
        
        # Models to try in order of preference
        models_to_try = ["gemma3", "llama3", "llama2"]
        cls.ollama_available = False
        cls.model_used = None
        
        try:
            # Try to connect to Ollama with different models
            for model in models_to_try:
                try:
                    print(f"Attempting to connect to Ollama with model: {model}")
                    cls.llm_service = OllamaService({
                        "base_url": "http://192.168.1.173:11434",
                        "model": model,
                        "temperature": 0.2,  # Lower temperature for more consistent results
                        "stream": False,
                        "debug": True,
                        "debug_file": "test_digest_generator_integration.log",
                        "debug_scope": "digest_integration_test",
                        "console_output": False
                    })
                    
                    # Test connection with a simple query
                    cls.llm_service.generate("Hello, is this model available?")
                    
                    # If we get here, the model is available
                    cls.ollama_available = True
                    cls.model_used = model
                    print(f"Successfully connected to Ollama using model: {model}")
                    break
                except Exception as e:
                    print(f"Failed to use model {model}: {str(e)}")
                    # Wait a bit before trying the next model
                    time.sleep(1)
                
            if not cls.ollama_available:
                print("Could not connect to Ollama with any of the available models")
                
        except Exception as e:
            print(f"Error setting up LLM service: {str(e)}")
            cls.ollama_available = False
    
    def setUp(self):
        """Set up test fixtures."""
        # Skip individual tests if Ollama is not available
        if not getattr(self.__class__, "ollama_available", False):
            self.skipTest("Ollama service is not available")
        
        print(f"\nRunning test with Ollama model: {self.__class__.model_used}")
        
        # Initialize DigestGenerator with the real LLM service
        self.digest_generator = DigestGenerator(self.__class__.llm_service)
        
        # Create sample test data
        self.test_entry = {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": "Captain Sara patrols the eastern border with her squad of ten guards. She's concerned about recent monster sightings and has requested additional resources. The village council is meeting tomorrow to discuss her requests.",
            "timestamp": datetime.now().isoformat()
        }
        
        self.user_test_entry = {
            "guid": str(uuid.uuid4()),
            "role": "user",
            "content": "I need to get prepared for this adventure. What kind of equipment should I bring to deal with venomous spiders? Also, do I know anyone who might have knowledge about these caves?",
            "timestamp": datetime.now().isoformat()
        }
    
    def test_segment_content_integration(self):
        """Integration test for segmenting content with a real LLM."""
        # Call the segmentation method
        segments = self.digest_generator._segment_content(self.test_entry["content"])
        
        # Basic validation
        self.assertIsInstance(segments, list, "Segments should be a list")
        self.assertGreater(len(segments), 1, "Should produce multiple segments")
        
        # Print the segments for inspection
        print("\nSegmentation Results:")
        for i, segment in enumerate(segments):
            print(f"Segment {i}: {segment}")
    
    def test_extract_information_integration(self):
        """Integration test for extracting information from segments with a real LLM."""
        # First segment the content
        segments = self.digest_generator._segment_content(self.test_entry["content"])
        
        # Then extract information
        extracted_info = self.digest_generator._extract_information(segments)
        
        # Basic validation
        self.assertIsInstance(extracted_info, dict, "Extracted info should be a dictionary")
        self.assertIn("context", extracted_info, "Should include a context field")
        self.assertIn("new_facts", extracted_info, "Should include new_facts field")
        self.assertIn("new_relationships", extracted_info, "Should include new_relationships field")
        
        # Print the extracted information for inspection
        print("\nExtracted Information:")
        print(f"Context: {extracted_info['context']}")
        print("\nFacts:")
        for i, fact in enumerate(extracted_info.get("new_facts", [])):
            print(f"Fact {i}:")
            print(f"  Key: {fact.get('key')}")
            print(f"  Value: {fact.get('value')}")
            print(f"  Importance: {fact.get('importance', 'N/A')}")
            print(f"  Segments: {fact.get('segmentIndexes', [])}")
            
        print("\nRelationships:")
        for i, rel in enumerate(extracted_info.get("new_relationships", [])):
            print(f"Relationship {i}:")
            print(f"  Subject: {rel.get('subject')}")
            print(f"  Predicate: {rel.get('predicate')}")
            print(f"  Object: {rel.get('object')}")
            print(f"  Importance: {rel.get('importance', 'N/A')}")
    
    def test_generate_digest_integration(self):
        """Integration test for generating a complete digest with a real LLM."""
        # Generate digest for the assistant message
        digest = self.digest_generator.generate_digest(self.test_entry)
        
        # Basic validation
        self.assertIsInstance(digest, dict, "Digest should be a dictionary")
        self.assertEqual(digest["conversationHistoryGuid"], self.test_entry["guid"], "GUID should match")
        self.assertIn("segments", digest, "Should include segments")
        self.assertIn("context", digest, "Should include context")
        self.assertIn("new_facts", digest, "Should include new_facts")
        self.assertIn("new_relationships", digest, "Should include new_relationships")
        
        # Print summary of the digest
        print("\nDigest Summary for Assistant Message:")
        print(f"Segments: {len(digest['segments'])}")
        print(f"Context: {digest['context']}")
        print(f"Facts: {len(digest['new_facts'])}")
        print(f"Relationships: {len(digest['new_relationships'])}")
        
        # Generate digest for the user message
        user_digest = self.digest_generator.generate_digest(self.user_test_entry)
        
        # Basic validation for user message
        self.assertIsInstance(user_digest, dict, "User digest should be a dictionary")
        self.assertEqual(user_digest["conversationHistoryGuid"], self.user_test_entry["guid"], "User GUID should match")
        
        # Print summary of the user digest
        print("\nDigest Summary for User Message:")
        print(f"Segments: {len(user_digest['segments'])}")
        print(f"Context: {user_digest['context']}")
        print(f"Facts: {len(user_digest['new_facts'])}")
        print(f"Relationships: {len(user_digest['new_relationships'])}")
    
    def test_complex_content_integration(self):
        """Integration test with more complex content to test robustness."""
        # Create a more complex entry with multiple themes and details
        complex_entry = {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": """The Blackwood Caves are located approximately three miles northeast of Haven Village. 
            According to local legends, they were once used as a temple by an ancient civilization that worshipped 
            spider deities. The entrance is marked by stone pillars carved with web-like patterns.
            
            The venomous spiders that have been spotted are unusual - they have a distinctive blue marking on their 
            abdomens and can grow up to the size of a dinner plate. Their venom causes paralysis within minutes, 
            though it's rarely fatal if treated quickly with the proper antidote.
            
            Captain Silas has already lost two scouts to these creatures. The first scout, Elara, returned with 
            severe bite wounds and died the next day. The second, Jormund, never returned at all. Silas believes 
            the spider population is growing rapidly and fears they may soon venture beyond the caves toward 
            populated areas.""",
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate digest
        digest = self.digest_generator.generate_digest(complex_entry)
        
        # Basic validation
        self.assertIsInstance(digest, dict, "Digest should be a dictionary")
        self.assertGreater(len(digest["segments"]), 5, "Complex content should produce many segments")
        
        # Validate facts and relationships
        if digest["new_facts"]:
            for fact in digest["new_facts"]:
                self.assertIn("key", fact, "Each fact should have a key")
                self.assertIn("value", fact, "Each fact should have a value")
                self.assertIn("segmentIndexes", fact, "Each fact should reference source segments")
        
        if digest["new_relationships"]:
            for rel in digest["new_relationships"]:
                self.assertIn("subject", rel, "Each relationship should have a subject")
                self.assertIn("predicate", rel, "Each relationship should have a predicate")
                self.assertIn("object", rel, "Each relationship should have an object")
                self.assertIn("segmentIndexes", rel, "Each relationship should reference source segments")
        
        # Print summary
        print("\nComplex Content Digest Summary:")
        print(f"Segments: {len(digest['segments'])}")
        print(f"Context: {digest['context']}")
        print(f"Facts: {len(digest['new_facts'])}")
        print(f"Relationships: {len(digest['new_relationships'])}")
        
        # Print a few sample segments
        print("\nSample Segments:")
        for i, segment in enumerate(digest["segments"][:3]):
            print(f"Segment {i}: {segment}")
        
        # Print a few sample facts if available
        if digest["new_facts"]:
            print("\nSample Facts:")
            for i, fact in enumerate(digest["new_facts"][:3]):
                print(f"Fact {i}:")
                print(f"  Key: {fact.get('key')}")
                print(f"  Value: {fact.get('value')}")
                print(f"  Topic: {fact.get('topic', 'N/A')}")


if __name__ == "__main__":
    unittest.main() 