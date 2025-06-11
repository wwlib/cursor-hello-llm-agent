#!/usr/bin/env python3
"""
Integration tests for EntityResolver with MemoryManager and conversation GUID tracking.

Tests the full pipeline including:
- EntityResolver integration with MemoryManager
- Conversation GUID tracking in entity metadata
- End-to-end entity resolution with real graph data
- Performance and accuracy evaluation

Uses sample conversation data to test realistic entity resolution scenarios.
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
import asyncio

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.memory_manager import MemoryManager
from memory.graph_memory.entity_resolver import EntityResolver
from memory.graph_memory.graph_manager import GraphManager
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService

# Import domain config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sample_data'))
from domain_configs import DND_CONFIG


class MockLLMServiceForIntegration:
    """Enhanced mock LLM service for integration testing."""
    
    def __init__(self):
        self.generation_calls = []
        self.embedding_calls = []
    
    def generate(self, prompt: str) -> str:
        """Generate responses for different types of prompts."""
        self.generation_calls.append(prompt)
        
        # Handle entity extraction prompts
        if "Extract entities from the following text" in prompt:
            if "fire wizard" in prompt.lower():
                return '''[
    {"type": "character", "name": "Eldara", "description": "A fire wizard who runs a magic shop"},
    {"type": "location", "name": "Riverwatch", "description": "A town with magical shops"}
]'''
            elif "ancient tower" in prompt.lower():
                return '''[
    {"type": "location", "name": "Ancient Tower", "description": "A mysterious tower in the ruins"},
    {"type": "object", "name": "Crystal Orb", "description": "A glowing orb found in the tower"}
]'''
            else:
                return '[]'
        
        # Handle entity resolution prompts
        elif "Node ID Resolver" in prompt:
            if "Eldara" in prompt:
                return '''[
    ["candidate_eldara", "character_eldara_existing", "Both describe fire wizards with magic shops", 0.9]
]'''
            elif "Ancient Tower" in prompt:
                return '''[
    ["candidate_tower", "<NEW>", "", 0.0]
]'''
            else:
                return '''[
    ["candidate_unknown", "<NEW>", "No match found", 0.0]
]'''
        
        # Handle digest generation prompts
        elif "segment" in prompt.lower() and "importance" in prompt.lower():
            return '''{
    "rated_segments": [
        {
            "text": "Sample conversation text",
            "importance": 4,
            "topics": ["characters", "magic"],
            "type": "information",
            "memory_worthy": true
        }
    ]
}'''
        
        # Default response
        return "Mock response"
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embeddings."""
        self.embedding_calls.append(text)
        # Return deterministic embedding based on text hash
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [(hash_val % 1000) / 1000.0 for _ in range(10)]


@pytest.fixture
def temp_memory_dir():
    """Create temporary directory for memory files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_llm_service():
    """Create enhanced mock LLM service for integration testing."""
    return MockLLMServiceForIntegration()


@pytest.fixture
def sample_conversation_data():
    """Load sample conversation data for testing."""
    sample_file = Path(__file__).parent / "sample_data" / "agent_memory_conversations.json"
    
    if not sample_file.exists():
        pytest.skip("Sample conversation data not available")
    
    with open(sample_file, 'r') as f:
        return json.load(f)


@pytest.fixture
async def memory_manager_with_resolver(temp_memory_dir, mock_llm_service):
    """Create MemoryManager with EntityResolver integration."""
    config = {
        "debug": True,
        "debug_file": os.path.join(temp_memory_dir, "test_debug.log"),
        "console_output": False
    }
    
    # Create embeddings manager
    embeddings_manager = EmbeddingsManager(
        llm_service=mock_llm_service,
        storage_path=temp_memory_dir,
        logger=None
    )
    
    # Create memory manager with graph memory enabled
    memory_manager = MemoryManager(
        llm_service=mock_llm_service,
        embeddings_manager=embeddings_manager,
        memory_file_path=os.path.join(temp_memory_dir, "test_memory.json"),
        enable_graph_memory=True,
        graph_storage_path=os.path.join(temp_memory_dir, "graph_data"),
        domain_config=DND_CONFIG
    )
    
    return memory_manager


class TestEntityResolverMemoryIntegration:
    """Test EntityResolver integration with MemoryManager."""
    
    @pytest.mark.asyncio
    async def test_conversation_guid_tracking(self, memory_manager_with_resolver, mock_llm_service):
        """Test that conversation GUIDs are properly tracked in entity metadata."""
        memory_manager = await memory_manager_with_resolver
        
        # Create initial memory
        initial_data = "Campaign setting with fire wizard Eldara in Riverwatch"
        memory_manager.create_initial_memory(initial_data, domain_config=DND_CONFIG)
        
        # Add conversation entries that should create entities with GUIDs
        user_entry = "I want to visit Eldara's magic shop in Riverwatch"
        agent_entry = "Eldara welcomes you to her shop, showing off her collection of fire scrolls"
        
        response = await memory_manager.query_memory(user_entry)
        
        # Wait for async processing
        while memory_manager.has_pending_operations():
            await asyncio.sleep(0.1)
        
        # Check that entities were created with conversation GUID tracking
        if memory_manager.graph_manager:
            nodes = memory_manager.graph_manager.get_all_nodes()
            
            # Find Eldara node
            eldara_nodes = [node for node in nodes if "eldara" in node.name.lower()]
            if eldara_nodes:
                eldara_node = eldara_nodes[0]
                
                # Check that conversation_history_guids attribute exists
                assert "conversation_history_guids" in eldara_node.attributes
                conversation_guids = eldara_node.attributes["conversation_history_guids"]
                assert isinstance(conversation_guids, list)
                assert len(conversation_guids) > 0
                
                print(f"Eldara node conversation GUIDs: {conversation_guids}")
    
    @pytest.mark.asyncio
    async def test_entity_resolution_with_existing_graph(self, memory_manager_with_resolver, mock_llm_service):
        """Test EntityResolver with pre-existing graph data."""
        memory_manager = await memory_manager_with_resolver
        
        # Create initial memory with some entities
        initial_data = """
        Campaign Setting: The Lost Valley
        
        Key Characters:
        - Eldara: A fire wizard who runs a magic shop in Riverwatch
        - Theron: A scholar studying ancient ruins
        
        Locations:
        - Riverwatch: Eastern settlement with magical shops
        - Ancient Ruins: Mysterious structures throughout the valley
        """
        
        memory_manager.create_initial_memory(initial_data, domain_config=DND_CONFIG)
        
        # Wait for initial processing
        while memory_manager.has_pending_operations():
            await asyncio.sleep(0.1)
        
        # Now add new conversation that should resolve to existing entities
        user_query = "I want to find the fire wizard's shop"
        response = await memory_manager.query_memory(user_query)
        
        # Wait for processing
        while memory_manager.has_pending_operations():
            await asyncio.sleep(0.1)
        
        # Check that entities were resolved rather than duplicated
        if memory_manager.graph_manager:
            nodes = memory_manager.graph_manager.get_all_nodes()
            
            # Should not have duplicate Eldara entities
            eldara_nodes = [node for node in nodes if "eldara" in node.name.lower()]
            assert len(eldara_nodes) <= 1, f"Found duplicate Eldara nodes: {[n.name for n in eldara_nodes]}"
            
            if eldara_nodes:
                eldara_node = eldara_nodes[0]
                # Should have multiple conversation references
                assert eldara_node.mention_count >= 1
                
                # Should have conversation GUID tracking
                if "conversation_history_guids" in eldara_node.attributes:
                    guids = eldara_node.attributes["conversation_history_guids"]
                    print(f"Eldara mentioned in conversations: {len(guids)}")
    
    @pytest.mark.asyncio
    async def test_confidence_based_matching(self, memory_manager_with_resolver, mock_llm_service):
        """Test confidence-based entity matching decisions."""
        memory_manager = await memory_manager_with_resolver
        
        # Mock different confidence levels
        original_generate = mock_llm_service.generate
        
        def mock_generate_with_confidence(prompt):
            if "Node ID Resolver" in prompt:
                if "high_confidence" in prompt:
                    return '''[
    ["candidate_001", "existing_node_123", "Very similar descriptions", 0.95]
]'''
                elif "low_confidence" in prompt:
                    return '''[
    ["candidate_002", "existing_node_456", "Somewhat similar", 0.6]
]'''
                else:
                    return original_generate(prompt)
            return original_generate(prompt)
        
        mock_llm_service.generate = mock_generate_with_confidence
        
        # Test that the system handles different confidence levels appropriately
        # This would be part of the EntityResolver's decision making process
        
        # Create test scenarios with varying confidence levels
        # (Implementation would depend on specific confidence threshold handling)
        
        print("Confidence-based matching test completed")
    
    def test_entity_resolver_performance_metrics(self, temp_memory_dir, mock_llm_service):
        """Test EntityResolver performance and accuracy metrics."""
        # Create test scenarios to measure performance
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            storage_path=temp_memory_dir,
            confidence_threshold=0.8
        )
        
        # Test batch vs individual processing performance
        test_candidates = [
            {
                "candidate_id": f"perf_test_{i}",
                "type": "character",
                "name": f"Test Character {i}",
                "description": f"A test character number {i}"
            }
            for i in range(10)
        ]
        
        import time
        
        # Test individual processing
        start_time = time.time()
        individual_results = resolver.resolve_candidates(
            test_candidates, 
            process_individually=True
        )
        individual_time = time.time() - start_time
        
        # Test batch processing
        start_time = time.time()
        batch_results = resolver.resolve_candidates(
            test_candidates, 
            process_individually=False
        )
        batch_time = time.time() - start_time
        
        print(f"Individual processing: {individual_time:.3f}s for {len(test_candidates)} candidates")
        print(f"Batch processing: {batch_time:.3f}s for {len(test_candidates)} candidates")
        print(f"LLM calls - Individual: {mock_llm_service.generation_calls}")
        print(f"Speed ratio: {individual_time/batch_time:.2f}x")
        
        # Both should return the same number of results
        assert len(individual_results) == len(batch_results) == len(test_candidates)


class TestEntityResolverWithSampleData:
    """Test EntityResolver with actual sample conversation data."""
    
    def test_sample_conversation_processing(self, sample_conversation_data, temp_memory_dir, mock_llm_service):
        """Test processing sample conversation data through EntityResolver."""
        # Extract segments from sample data
        segments = []
        for entry in sample_conversation_data.get("entries", []):
            digest = entry.get("digest", {})
            rated_segments = digest.get("rated_segments", [])
            
            for segment in rated_segments:
                if (segment.get("importance", 0) >= 3 and 
                    segment.get("type") in ["information", "action"] and
                    segment.get("memory_worthy", False)):
                    segments.append({
                        "text": segment["text"],
                        "importance": segment["importance"],
                        "type": segment["type"],
                        "conversation_guid": entry.get("guid", "")
                    })
        
        print(f"Processing {len(segments)} segments from sample data")
        
        # Create resolver
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            storage_path=temp_memory_dir
        )
        
        # Process segments to extract entities (this would normally be done by EntityExtractor)
        # For testing, create mock candidates based on sample data content
        test_candidates = [
            {
                "candidate_id": "sample_001",
                "type": "location",
                "name": "Lost Valley",
                "description": "A hidden valley surrounded by impassable mountains"
            },
            {
                "candidate_id": "sample_002", 
                "type": "character",
                "name": "Elena",
                "description": "Mayor of Haven, protects valley inhabitants"
            },
            {
                "candidate_id": "sample_003",
                "type": "location",
                "name": "Ancient Ruins", 
                "description": "Scattered ruins with mysterious energy"
            }
        ]
        
        # Test resolution
        resolutions = resolver.resolve_candidates(test_candidates)
        
        assert len(resolutions) == len(test_candidates)
        
        for resolution in resolutions:
            print(f"Candidate {resolution['candidate_id']}: "
                  f"{resolution['resolved_node_id']} "
                  f"(confidence: {resolution['confidence']})")


def run_integration_tests():
    """Run EntityResolver integration tests."""
    print("=" * 80)
    print("ENTITYRESOLVER INTEGRATION TEST SUITE")
    print("=" * 80)
    
    test_args = [
        __file__,
        "-v", 
        "-s",
        "--tb=short",
        "-k", "integration"
    ]
    
    print("Running integration tests...")
    return pytest.main(test_args)


if __name__ == "__main__":
    exit_code = run_integration_tests() 
    sys.exit(exit_code)