#!/usr/bin/env python3
"""
Comprehensive test suite for EntityResolver class.

Tests the new dedicated entity resolution functionality including:
- RAG-based candidate selection
- Individual vs batch processing modes
- Confidence-based decision making
- Conversation GUID tracking
- Integration with existing graph data

Uses sample data from tests/graph_memory/sample_data/ for realistic testing.
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

from memory.graph_memory.entity_resolver import EntityResolver
from memory.graph_memory.graph_storage import GraphStorage
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService

# Import domain config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sample_data'))
from domain_configs import DND_CONFIG


class MockLLMService:
    """Mock LLM service for testing without external dependencies."""
    
    def __init__(self):
        self.call_count = 0
        self.last_prompt = ""
    
    def generate(self, prompt: str) -> str:
        """Generate mock resolution responses based on prompt content."""
        self.call_count += 1
        self.last_prompt = prompt
        
        # Mock resolution responses based on prompt content
        if "Eldara" in prompt:
            return '''[
    ["candidate_001", "character_eldara", "Both describe fire wizards with magic shops", 0.9]
]'''
        elif "Ancient Tower" in prompt:
            return '''[
    ["candidate_002", "<NEW>", "", 0.0]
]'''
        elif "Fire Wizard" in prompt:
            return '''[
    ["candidate_003", "character_eldara", "Similar description of fire magic user", 0.85]
]'''
        else:
            # Default response for unknown candidates
            return '''[
    ["candidate_unknown", "<NEW>", "No similar entity found", 0.0]
]'''


class MockEmbeddingsManager:
    """Mock embeddings manager for testing RAG functionality."""
    
    def __init__(self):
        self.search_calls = []
        
    def semantic_search(self, query: str, max_results: int = 5, 
                       similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Mock semantic search with predefined results."""
        self.search_calls.append({
            "query": query,
            "max_results": max_results,
            "threshold": similarity_threshold
        })
        
        # Return mock results based on query
        if "fire" in query.lower() or "wizard" in query.lower():
            return [
                {
                    "entity_name": "Eldara",
                    "entity_type": "character",
                    "text": "A powerful fire wizard who runs a magic shop in Riverwatch",
                    "similarity": 0.9
                }
            ]
        elif "ancient" in query.lower() or "ruins" in query.lower():
            return [
                {
                    "entity_name": "Ancient Ruins", 
                    "entity_type": "location",
                    "text": "Mysterious ancient structures scattered throughout the valley",
                    "similarity": 0.75
                }
            ]
        else:
            return []  # No similar results found


@pytest.fixture
def temp_storage_path():
    """Create temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_graph_data():
    """Load sample graph data for testing."""
    sample_data_dir = Path(__file__).parent / "sample_data" / "graph_data"
    
    nodes_file = sample_data_dir / "graph_nodes.json"
    edges_file = sample_data_dir / "graph_edges.json"
    metadata_file = sample_data_dir / "graph_metadata.json"
    
    if not all([nodes_file.exists(), edges_file.exists(), metadata_file.exists()]):
        pytest.skip("Sample graph data not available")
    
    with open(nodes_file, 'r') as f:
        nodes = json.load(f)
    with open(edges_file, 'r') as f:
        edges = json.load(f)
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    return {"nodes": nodes, "edges": edges, "metadata": metadata}


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service for testing."""
    return MockLLMService()


@pytest.fixture
def mock_embeddings_manager():
    """Create mock embeddings manager for testing."""
    return MockEmbeddingsManager()


@pytest.fixture
def entity_resolver(temp_storage_path, mock_llm_service, mock_embeddings_manager):
    """Create EntityResolver instance for testing."""
    return EntityResolver(
        llm_service=mock_llm_service,
        embeddings_manager=mock_embeddings_manager,
        storage_path=temp_storage_path,
        confidence_threshold=0.8
    )


class TestEntityResolverBasic:
    """Test basic EntityResolver functionality."""
    
    def test_initialization(self, temp_storage_path, mock_llm_service):
        """Test EntityResolver initialization."""
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            storage_path=temp_storage_path
        )
        
        assert resolver.llm_service == mock_llm_service
        assert resolver.confidence_threshold == 0.8
        assert resolver.storage is not None
        assert resolver.resolution_template is not None
    
    def test_initialization_with_custom_threshold(self, temp_storage_path, mock_llm_service):
        """Test EntityResolver with custom confidence threshold."""
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            storage_path=temp_storage_path,
            confidence_threshold=0.9
        )
        
        assert resolver.confidence_threshold == 0.9
    
    def test_template_loading(self, entity_resolver):
        """Test that resolution template is loaded correctly."""
        template = entity_resolver.resolution_template
        assert "existing_node_data" in template
        assert "candidate_nodes" in template
        assert "confidence" in template


class TestEntityResolverParsing:
    """Test EntityResolver response parsing functionality."""
    
    def test_parse_resolution_response_valid(self, entity_resolver):
        """Test parsing valid resolution response."""
        response = '''[
    ["candidate_001", "character_eldara", "Both describe fire wizards", 0.9],
    ["candidate_002", "<NEW>", "", 0.0]
]'''
        
        resolutions = entity_resolver._parse_resolution_response(response)
        
        assert len(resolutions) == 2
        
        # Check first resolution
        assert resolutions[0]["candidate_id"] == "candidate_001"
        assert resolutions[0]["resolved_node_id"] == "character_eldara"
        assert resolutions[0]["resolution_justification"] == "Both describe fire wizards"
        assert resolutions[0]["confidence"] == 0.9
        
        # Check second resolution
        assert resolutions[1]["candidate_id"] == "candidate_002"
        assert resolutions[1]["resolved_node_id"] == "<NEW>"
        assert resolutions[1]["confidence"] == 0.0
    
    def test_parse_resolution_response_malformed(self, entity_resolver):
        """Test parsing malformed resolution response."""
        response = "Invalid JSON response"
        
        resolutions = entity_resolver._parse_resolution_response(response)
        assert len(resolutions) == 0
    
    def test_parse_resolution_response_partial_tuples(self, entity_resolver):
        """Test parsing response with incomplete tuples."""
        response = '''[
    ["candidate_001", "character_eldara", "Match found"],
    ["candidate_002"]
]'''
        
        resolutions = entity_resolver._parse_resolution_response(response)
        
        # Invalid tuples should be rejected, so only 1 valid resolution
        assert len(resolutions) == 1
        assert resolutions[0]["candidate_id"] == "candidate_001"
        assert resolutions[0]["confidence"] == 0.0  # Default when missing
        assert resolutions[0]["resolved_node_id"] == "character_eldara"


class TestEntityResolverRAG:
    """Test RAG-based candidate selection functionality."""
    
    def test_rag_candidates_with_embeddings(self, entity_resolver, mock_embeddings_manager):
        """Test RAG candidate selection with embeddings manager."""
        candidate = {
            "candidate_id": "test_001",
            "type": "character",
            "name": "Fire Mage",
            "description": "A wizard specializing in fire magic"
        }
        
        rag_candidates = entity_resolver._get_rag_candidates_for_entity(candidate)
        
        # Check that embeddings manager was called
        assert len(mock_embeddings_manager.search_calls) == 1
        search_call = mock_embeddings_manager.search_calls[0]
        assert "Fire Mage" in search_call["query"]
        assert "fire magic" in search_call["query"]
        
        # Check returned candidates
        assert len(rag_candidates) == 1
        assert rag_candidates[0]["type"] == "character"
        assert "character_eldara" in rag_candidates[0]["existing_node_id"]
    
    def test_rag_candidates_no_embeddings(self, temp_storage_path, mock_llm_service):
        """Test RAG candidate selection without embeddings manager."""
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            embeddings_manager=None,
            storage_path=temp_storage_path
        )
        
        candidate = {
            "candidate_id": "test_001",
            "type": "character",
            "description": "A fire wizard"
        }
        
        rag_candidates = resolver._get_rag_candidates_for_entity(candidate)
        assert len(rag_candidates) == 0
    
    def test_rag_candidates_type_filtering(self, entity_resolver, mock_embeddings_manager):
        """Test that RAG results are filtered by entity type."""
        candidate = {
            "candidate_id": "test_001",
            "type": "location",  # Different type than mock results
            "description": "An ancient tower"
        }
        
        rag_candidates = entity_resolver._get_rag_candidates_for_entity(candidate)
        
        # Should filter out character results for location candidate
        assert len(rag_candidates) == 0


class TestEntityResolverProcessing:
    """Test entity resolution processing modes."""
    
    def test_resolve_candidates_empty_list(self, entity_resolver):
        """Test resolving empty candidate list."""
        resolutions = entity_resolver.resolve_candidates([])
        assert len(resolutions) == 0
    
    def test_resolve_candidates_individual_mode(self, entity_resolver, mock_llm_service):
        """Test individual processing mode."""
        candidates = [
            {
                "candidate_id": "candidate_001",
                "type": "character",
                "name": "Eldara",
                "description": "A fire wizard who runs a magic shop"
            },
            {
                "candidate_id": "candidate_002",
                "type": "location",
                "name": "Ancient Tower",
                "description": "A mysterious tower in the ruins"
            }
        ]
        
        resolutions = entity_resolver.resolve_candidates(
            candidates, 
            process_individually=True
        )
        
        assert len(resolutions) == 2
        assert mock_llm_service.call_count == 2  # One call per candidate
        
        # Check first resolution (should match existing)
        eldara_resolution = next(r for r in resolutions if r["candidate_id"] == "candidate_001")
        assert eldara_resolution["resolved_node_id"] == "character_eldara"
        assert eldara_resolution["confidence"] == 0.9
        assert eldara_resolution["auto_matched"] == True  # Above threshold
        
        # Check second resolution (should be new)
        tower_resolution = next(r for r in resolutions if r["candidate_id"] == "candidate_002")
        assert tower_resolution["resolved_node_id"] == "<NEW>"
        assert tower_resolution["confidence"] == 0.0
        assert tower_resolution["auto_matched"] == False
    
    def test_resolve_candidates_batch_mode(self, entity_resolver, mock_llm_service):
        """Test batch processing mode."""
        candidates = [
            {
                "candidate_id": "candidate_001",
                "type": "character",
                "name": "Eldara",
                "description": "A fire wizard"
            }
        ]
        
        resolutions = entity_resolver.resolve_candidates(
            candidates, 
            process_individually=False
        )
        
        assert len(resolutions) == 1
        assert mock_llm_service.call_count == 1  # Single batch call
    
    def test_confidence_threshold_override(self, entity_resolver, mock_llm_service):
        """Test confidence threshold override."""
        candidates = [
            {
                "candidate_id": "candidate_003",
                "type": "character",
                "name": "Fire Wizard",
                "description": "A wizard who uses fire magic"
            }
        ]
        
        # Use higher threshold - should not auto-match
        resolutions = entity_resolver.resolve_candidates(
            candidates,
            confidence_threshold=0.9  # Higher than 0.85 returned by mock
        )
        
        assert len(resolutions) == 1
        assert resolutions[0]["confidence"] == 0.85
        assert resolutions[0]["auto_matched"] == False  # Below new threshold
        
        # Use lower threshold - should auto-match
        resolutions = entity_resolver.resolve_candidates(
            candidates,
            confidence_threshold=0.8  # Lower than 0.85 returned by mock
        )
        
        assert resolutions[0]["auto_matched"] == True  # Above new threshold


class TestEntityResolverErrorHandling:
    """Test EntityResolver error handling."""
    
    def test_llm_service_error(self, entity_resolver):
        """Test handling of LLM service errors."""
        # Mock LLM service that raises exception
        entity_resolver.llm_service = Mock(side_effect=Exception("LLM Error"))
        
        candidates = [
            {
                "candidate_id": "test_001",
                "type": "character",
                "description": "A test character"
            }
        ]
        
        resolutions = entity_resolver.resolve_candidates(candidates)
        
        assert len(resolutions) == 1
        assert resolutions[0]["resolved_node_id"] == "<NEW>"
        assert resolutions[0]["confidence"] == 0.0
        assert "LLM error" in resolutions[0]["resolution_justification"]
    
    def test_embeddings_service_error(self, entity_resolver):
        """Test handling of embeddings service errors."""
        # Mock embeddings manager that raises exception
        entity_resolver.embeddings_manager.semantic_search = Mock(side_effect=Exception("Embeddings Error"))
        
        candidate = {
            "candidate_id": "test_001",
            "type": "character",
            "description": "A test character"
        }
        
        # Should not crash and return empty list
        rag_candidates = entity_resolver._get_rag_candidates_for_entity(candidate)
        assert len(rag_candidates) == 0


@pytest.mark.integration
class TestEntityResolverIntegration:
    """Integration tests with real sample data."""
    
    def test_with_sample_graph_data(self, sample_graph_data, temp_storage_path, mock_llm_service):
        """Test EntityResolver with actual sample graph data."""
        # Set up storage with sample data
        storage = GraphStorage(temp_storage_path)
        
        # Copy sample data to temp storage
        storage.nodes = sample_graph_data["nodes"]
        storage.edges = sample_graph_data["edges"] 
        storage.metadata = sample_graph_data["metadata"]
        storage._save_all()
        
        # Create resolver
        resolver = EntityResolver(
            llm_service=mock_llm_service,
            storage_path=temp_storage_path
        )
        
        # Test with candidates similar to existing nodes
        candidates = [
            {
                "candidate_id": "test_valley",
                "type": "location",
                "name": "Lost Valley",
                "description": "A hidden valley surrounded by mountains"
            }
        ]
        
        resolutions = resolver.resolve_candidates(candidates)
        assert len(resolutions) == 1
    
    def test_conversation_guid_integration(self, entity_resolver):
        """Test integration with conversation GUID tracking."""
        # This would be tested as part of the full memory manager integration
        # For now, verify that the resolver can handle candidate data with conversation GUIDs
        candidates = [
            {
                "candidate_id": "conv_test_001",
                "type": "character", 
                "name": "Test Character",
                "description": "A character from conversation",
                "conversation_guid": "test-guid-123"
            }
        ]
        
        resolutions = entity_resolver.resolve_candidates(candidates)
        assert len(resolutions) == 1
        # The conversation GUID would be handled by the calling code (memory_manager.py)


def run_comprehensive_tests():
    """Run all EntityResolver tests with detailed output."""
    print("=" * 80)
    print("ENTITYRESOLVER COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    # Run pytest with verbose output
    test_args = [
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ]
    
    # Add integration mark if environment supports it
    if os.getenv("OLLAMA_BASE_URL"):
        test_args.append("-m")
        test_args.append("integration")
        print("Integration tests enabled (Ollama detected)")
    else:
        print("Integration tests skipped (no Ollama service detected)")
    
    print("\nRunning tests...")
    return pytest.main(test_args)


if __name__ == "__main__":
    exit_code = run_comprehensive_tests()
    sys.exit(exit_code)