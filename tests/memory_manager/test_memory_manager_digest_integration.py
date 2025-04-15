#!/usr/bin/env python3
"""
Integration test to verify the DigestGenerator integration with MemoryManager.
"""

import os
import sys
import json
import unittest
import uuid
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService

class TestMemoryManagerDigestIntegration(unittest.TestCase):
    """Test the integration between MemoryManager and DigestGenerator."""

    @classmethod
    def setUpClass(cls):
        """Set up resources once before all tests."""
        # Create unique filename for this test run
        cls.test_id = str(uuid.uuid4())[:8]
        
        # Ensure test_files directory exists
        cls.test_files_dir = os.path.join(project_root, "tests/test_files")
        os.makedirs(cls.test_files_dir, exist_ok=True)
        
        cls.memory_file = os.path.join(cls.test_files_dir, f"test_digest_integration_{cls.test_id}.json")
        
        # Set up debug log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.debug_file = os.path.join(cls.test_files_dir, f"digest_integration_debug_{timestamp}.log")
        
        # Initialize LLM service
        cls.llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",
            "model": "gemma3",
            "temperature": 0.7,
            "stream": False,
            "debug": True,
            "debug_file": cls.debug_file,
            "debug_scope": "test_digest_integration",
            "console_output": False
        })
        
        # Create memory manager
        cls.memory_manager = MemoryManager(
            memory_file=cls.memory_file,
            llm_service=cls.llm_service
        )
        
        # Initial data for memory
        cls.initial_data = """
        The kingdom of Eldoria is a magical realm with four major regions:
        1. The Northern Mountains, home to the dwarves who mine precious metals
        2. The Western Forests, where elves maintain ancient groves and magical creatures roam
        3. The Eastern Plains, where humans farm and tend to livestock
        4. The Southern Coast, where merchants trade goods with distant lands
        
        King Alaric rules from the central city of Luminara, supported by his council of advisors.
        A dark force has recently emerged from beneath the mountains, threatening the peace.
        """
        
        # Initialize memory
        cls.memory_manager.create_initial_memory(cls.initial_data)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up resources after all tests."""
        # Clean up memory file
        if os.path.exists(cls.memory_file):
            os.remove(cls.memory_file)
        
        # Clean up backup files
        for backup_file in Path(cls.test_files_dir).glob(f"*{cls.test_id}*_bak_*.json"):
            backup_file.unlink()
    
    def test_01_memory_initialization(self):
        """Test that memory was initialized with proper structure."""
        # Verify memory contains expected sections
        self.assertIn("guid", self.memory_manager.memory)
        self.assertIn("static_memory", self.memory_manager.memory)
        self.assertIn("working_memory", self.memory_manager.memory)
        self.assertIn("conversation_history", self.memory_manager.memory)
        
        # Verify conversation history starts empty
        self.assertEqual(len(self.memory_manager.memory["conversation_history"]), 0)
        
        # Verify GUID was generated
        self.assertIsNotNone(self.memory_manager.memory_guid)
    
    def test_02_user_message_digest_generation(self):
        """Test that user message digests are generated correctly."""
        # Send a user message
        response = self.memory_manager.query_memory({
            "user_message": "Tell me about the threat emerging from the mountains. What do we know about it?"
        })
        
        # Verify response
        self.assertIn("response", response)
        self.assertIsInstance(response["response"], str)
        
        # Verify conversation history has been updated
        conversation_history = self.memory_manager.memory["conversation_history"]
        self.assertEqual(len(conversation_history), 2)  # User message + assistant response
        
        # Verify user message has a digest
        user_message = conversation_history[0]
        self.assertEqual(user_message["role"], "user")
        self.assertIn("digest", user_message)
        
        # Validate user digest structure
        user_digest = user_message["digest"]
        self._validate_digest_structure(user_digest)
        
        # Verify digest contains the user's GUID
        self.assertEqual(user_digest["conversation_history_entry_guid"], user_message["guid"])
        self.assertEqual(user_digest["role"], "user")
    
    def test_03_assistant_message_digest_generation(self):
        """Test that assistant message digests are generated correctly."""
        # Get conversation history after previous test
        conversation_history = self.memory_manager.memory["conversation_history"]
        
        # There should be at least 2 messages by now (user + assistant)
        self.assertGreaterEqual(len(conversation_history), 2)
        
        # Get the assistant message (should be the second message)
        assistant_message = conversation_history[1]
        self.assertEqual(assistant_message["role"], "assistant")
        self.assertIn("digest", assistant_message)
        
        # Validate assistant digest structure
        assistant_digest = assistant_message["digest"]
        self._validate_digest_structure(assistant_digest)
        
        # Verify digest contains the assistant's GUID
        self.assertEqual(assistant_digest["conversation_history_entry_guid"], assistant_message["guid"])
        self.assertEqual(assistant_digest["role"], "assistant")
        
        # Assistant digest should typically have more segments and facts
        self.assertGreaterEqual(len(assistant_digest["segments"]), 1)
    
    def test_04_multi_turn_conversation(self):
        """Test digest generation in a multi-turn conversation."""
        # Send another user message
        response = self.memory_manager.query_memory({
            "user_message": "How is King Alaric planning to respond to this threat? Can the dwarves help since they live in the mountains?"
        })
        
        # Verify response
        self.assertIn("response", response)
        
        # Verify conversation history has been updated
        conversation_history = self.memory_manager.memory["conversation_history"]
        self.assertEqual(len(conversation_history), 4)  # 2 user messages + 2 assistant responses
        
        # Check the latest user message
        latest_user = conversation_history[2]
        self.assertEqual(latest_user["role"], "user")
        self.assertIn("digest", latest_user)
        
        # Check the latest assistant message
        latest_assistant = conversation_history[3]
        self.assertEqual(latest_assistant["role"], "assistant")
        self.assertIn("digest", latest_assistant)
        
        # Validate both digests
        self._validate_digest_structure(latest_user["digest"])
        self._validate_digest_structure(latest_assistant["digest"])
        
        # Verify GUIDs are linked correctly
        self.assertEqual(latest_user["digest"]["conversation_history_entry_guid"], latest_user["guid"])
        self.assertEqual(latest_assistant["digest"]["conversation_history_entry_guid"], latest_assistant["guid"])
    
    def _validate_digest_structure(self, digest):
        """Helper to validate the structure of a digest."""
        # Check required fields
        self.assertIn("conversation_history_entry_guid", digest)
        self.assertIn("role", digest)
        self.assertIn("segments", digest)
        self.assertIn("new_facts", digest)
        self.assertIn("new_relationships", digest)
        
        # Check types
        self.assertIsInstance(digest["conversation_history_entry_guid"], str)
        self.assertIsInstance(digest["role"], str)
        self.assertIsInstance(digest["segments"], list)
        self.assertIsInstance(digest["new_facts"], list)
        self.assertIsInstance(digest["new_relationships"], list)
        
        # Check deeper structure if facts exist
        if digest["new_facts"]:
            fact = digest["new_facts"][0]
            self.assertIn("subject", fact)
            self.assertIn("fact", fact)
        
        # Check deeper structure if relationships exist
        if digest["new_relationships"]:
            rel = digest["new_relationships"][0]
            self.assertIn("subject", rel)
            self.assertIn("predicate", rel)
            self.assertIn("object", rel)

if __name__ == "__main__":
    unittest.main() 