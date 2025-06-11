#!/usr/bin/env python3
"""
Real LLM integration tests for EntityResolver.

Tests the EntityResolver with actual Ollama LLM calls to validate:
- Entity resolution with real LLM responses
- Confidence scoring and decision making
- RAG-based candidate selection
- Individual vs batch processing performance
- Integration with sample graph data

Requires running Ollama service with environment variables:
- OLLAMA_BASE_URL
- OLLAMA_MODEL
- OLLAMA_EMBED_MODEL
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional
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


def setup_ollama_service():
    """Set up real Ollama LLM service using environment variables."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
    
    print(f"Setting up Ollama service:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  Embedding Model: {embed_model}")
    
    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure LLM service with detailed logging
    llm_config = {
        "base_url": base_url,
        "model": model,
        "embed_model": embed_model,
        "debug": True,
        "debug_file": os.path.join(logs_dir, "test_ollama_entity_resolution.log"),
        "debug_scope": "entity_resolver_test",
        "console_output": False
    }
    
    return OllamaService(llm_config)


@pytest.fixture
def temp_storage_path():
    """Create temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def ollama_service():
    """Create real Ollama service for testing."""
    return setup_ollama_service()


@pytest.fixture
def embeddings_manager(ollama_service, temp_storage_path):
    """Create embeddings manager with real Ollama service."""
    embeddings_file = os.path.join(temp_storage_path, "test_embeddings.jsonl")
    return EmbeddingsManager(
        embeddings_file=embeddings_file,
        llm_service=ollama_service
    )


@pytest.fixture
def entity_resolver(ollama_service, embeddings_manager, temp_storage_path):
    """Create EntityResolver with real services."""
    return EntityResolver(
        llm_service=ollama_service,
        embeddings_manager=embeddings_manager,
        storage_path=temp_storage_path,
        confidence_threshold=0.8
    )


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


@pytest.mark.integration
class TestEntityResolverRealLLM:
    """Integration tests with real LLM service."""
    
    def test_basic_entity_resolution(self, entity_resolver):
        """Test basic entity resolution with real LLM."""
        print("\n=== Testing Basic Entity Resolution ===")
        
        candidates = [
            {
                "candidate_id": "test_character_001",
                "type": "character",
                "name": "Fire Wizard",
                "description": "A powerful wizard who specializes in fire magic and runs a magic shop"
            },
            {
                "candidate_id": "test_location_001", 
                "type": "location",
                "name": "Ancient Tower",
                "description": "A mysterious tower found in ancient ruins, containing magical artifacts"
            }
        ]
        
        print(f"Testing with {len(candidates)} candidates...")
        print(f"Confidence threshold: {entity_resolver.confidence_threshold}")
        print(f"Log file location: {entity_resolver.llm_service.debug_file}")
        print()
        
        # Test individual processing to see detailed LLM interactions
        print("Testing individual processing mode...")
        resolutions = entity_resolver.resolve_candidates(candidates, process_individually=True)
        
        assert len(resolutions) == len(candidates)
        
        print("\nResolution Results:")
        for i, resolution in enumerate(resolutions):
            candidate = candidates[i]
            print(f"Candidate {i+1}: {candidate['name']} ({candidate['type']})")
            print(f"  Description: {candidate['description']}")
            print(f"  -> Resolution: {resolution['resolved_node_id']}")
            print(f"  -> Confidence: {resolution['confidence']}")
            print(f"  -> Auto-matched: {resolution['auto_matched']}")
            print(f"  -> Justification: {resolution['resolution_justification']}")
            print()
            
            # Basic validation
            assert "candidate_id" in resolution
            assert "resolved_node_id" in resolution
            assert "confidence" in resolution
            assert "auto_matched" in resolution
            assert isinstance(resolution["confidence"], (int, float))
            assert 0 <= resolution["confidence"] <= 1
        
        print(f"Check detailed LLM logs at: {entity_resolver.llm_service.debug_file}")
        print("This includes prompts sent to LLM and raw responses received.")
    
    def test_individual_vs_batch_processing(self, entity_resolver):
        """Test performance difference between individual and batch processing."""
        print("\n=== Testing Individual vs Batch Processing ===")
        
        candidates = [
            {
                "candidate_id": "perf_char_001",
                "type": "character",
                "name": "Elena the Mayor",
                "description": "Mayor of Haven who protects the valley's inhabitants"
            },
            {
                "candidate_id": "perf_char_002",
                "type": "character", 
                "name": "Theron the Scholar",
                "description": "Master scholar who studies ancient ruins and artifacts"
            },
            {
                "candidate_id": "perf_loc_001",
                "type": "location",
                "name": "Lost Valley",
                "description": "A hidden valley surrounded by impassable mountains"
            }
        ]
        
        import time
        
        # Test individual processing
        print("Testing individual processing...")
        start_time = time.time()
        individual_results = entity_resolver.resolve_candidates(
            candidates, 
            process_individually=True
        )
        individual_time = time.time() - start_time
        
        # Test batch processing
        print("Testing batch processing...")
        start_time = time.time()
        batch_results = entity_resolver.resolve_candidates(
            candidates,
            process_individually=False
        )
        batch_time = time.time() - start_time
        
        print(f"\nPerformance Results:")
        print(f"Individual processing: {individual_time:.2f}s")
        print(f"Batch processing: {batch_time:.2f}s")
        print(f"Speed improvement: {individual_time/batch_time:.2f}x")
        
        # Both should return same number of results
        assert len(individual_results) == len(batch_results) == len(candidates)
        
        # Compare results
        print(f"\nResult Comparison:")
        for i in range(len(candidates)):
            ind_res = individual_results[i]
            batch_res = batch_results[i]
            
            print(f"Candidate {candidates[i]['candidate_id']}:")
            print(f"  Individual: {ind_res['resolved_node_id']} (confidence: {ind_res['confidence']:.3f})")
            print(f"  Batch:      {batch_res['resolved_node_id']} (confidence: {batch_res['confidence']:.3f})")
    
    def test_confidence_thresholds(self, entity_resolver):
        """Test confidence threshold behavior with real LLM responses."""
        print("\n=== Testing Confidence Thresholds ===")
        
        # Test with a candidate that might have varying confidence
        candidate = {
            "candidate_id": "threshold_test",
            "type": "character",
            "name": "Village Leader",
            "description": "A leader who protects people in a settlement"
        }
        
        # Test different thresholds
        thresholds = [0.5, 0.7, 0.8, 0.9]
        
        print("Testing different confidence thresholds:")
        for threshold in thresholds:
            resolution = entity_resolver.resolve_candidates(
                [candidate], 
                confidence_threshold=threshold
            )[0]
            
            print(f"Threshold {threshold}: confidence={resolution['confidence']:.3f}, "
                  f"auto_matched={resolution['auto_matched']}")
            
            # Verify auto_matched logic
            expected_auto_match = resolution['confidence'] >= threshold
            assert resolution['auto_matched'] == expected_auto_match
    
    def test_with_sample_graph_data(self, entity_resolver, sample_graph_data, temp_storage_path):
        """Test EntityResolver with existing sample graph data."""
        print("\n=== Testing with Sample Graph Data ===")
        
        # Set up storage with sample data
        storage = GraphStorage(temp_storage_path)
        
        # Load sample nodes for context
        sample_nodes = sample_graph_data["nodes"]
        print(f"Sample graph has {len(sample_nodes)} existing nodes")
        
        # Create candidates that might match existing entities
        candidates = [
            {
                "candidate_id": "sample_test_001",
                "type": "location",
                "name": "The Lost Valley",
                "description": "A hidden valley surrounded by impassable mountains with ancient ruins"
            },
            {
                "candidate_id": "sample_test_002",
                "type": "character", 
                "name": "Elena",
                "description": "Mayor of Haven who protects the valley inhabitants from danger"
            },
            {
                "candidate_id": "sample_test_003",
                "type": "location",
                "name": "Mysterious Ruins",
                "description": "Ancient stone structures with strange magical energy"
            }
        ]
        
        print(f"Testing resolution against existing sample data...")
        resolutions = entity_resolver.resolve_candidates(candidates)
        
        print("\nResolution Results:")
        for resolution in resolutions:
            is_new = resolution['resolved_node_id'] == '<NEW>'
            print(f"{resolution['candidate_id']}: {'NEW' if is_new else 'EXISTING'}")
            if not is_new:
                print(f"  -> {resolution['resolved_node_id']}")
                print(f"  Confidence: {resolution['confidence']:.3f}")
                print(f"  Justification: {resolution['resolution_justification']}")
            print()
        
        # Copy generated graph files for graph viewer
        self._copy_graph_files_for_viewer(temp_storage_path, "sample_data_test")
    
    def test_rag_candidate_selection(self, entity_resolver, embeddings_manager):
        """Test RAG-based candidate selection functionality."""
        print("\n=== Testing RAG Candidate Selection ===")
        
        # First, add some entities to the embeddings store
        print("Adding sample entities to embeddings store...")
        sample_entities = [
            {
                "entity_name": "Eldara",
                "entity_type": "character",
                "text": "A fire wizard who runs a magic shop in Riverwatch",
                "source": "test_setup"
            },
            {
                "entity_name": "Ancient Ruins",
                "entity_type": "location", 
                "text": "Mysterious ancient structures scattered throughout the valley",
                "source": "test_setup"
            },
            {
                "entity_name": "Magic Shop",
                "entity_type": "location",
                "text": "A shop in Riverwatch that sells magical items and scrolls",
                "source": "test_setup"
            }
        ]
        
        for entity in sample_entities:
            embeddings_manager.add_embedding(entity["text"], entity)
        
        # Test RAG candidate selection
        test_candidate = {
            "candidate_id": "rag_test",
            "type": "character",
            "name": "Fire Mage",
            "description": "A wizard who specializes in fire magic and sells magical items"
        }
        
        rag_candidates = entity_resolver._get_rag_candidates_for_entity(test_candidate)
        
        print(f"RAG found {len(rag_candidates)} similar candidates:")
        for candidate in rag_candidates:
            print(f"  - {candidate['existing_node_id']} ({candidate['type']})")
            print(f"    Description: {candidate['description']}")
        
        # Should find the fire wizard
        assert len(rag_candidates) > 0
        
        # Test full resolution with RAG context
        resolution = entity_resolver.resolve_candidates([test_candidate])[0]
        print(f"\nFinal resolution: {resolution['resolved_node_id']}")
        print(f"Confidence: {resolution['confidence']:.3f}")
        print(f"Justification: {resolution['resolution_justification']}")
    
    def test_full_graph_building_workflow(self, ollama_service, temp_storage_path):
        """Test complete workflow that builds a graph from scratch with EntityResolver."""
        print("\n=== Testing Full Graph Building Workflow ===")
        
        # Create a GraphManager with real storage that will generate actual files
        from memory.graph_memory.graph_manager import GraphManager
        
        # Set up embeddings manager for RAG
        embeddings_file = os.path.join(temp_storage_path, "graph_embeddings.jsonl")
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=ollama_service
        )
        
        # Create graph manager with real storage
        graph_manager = GraphManager(
            llm_service=ollama_service,
            embeddings_manager=embeddings_manager,
            storage_path=temp_storage_path,
            domain_config=DND_CONFIG,
            similarity_threshold=0.8
        )
        
        # Create EntityResolver with the same storage
        resolver = EntityResolver(
            llm_service=ollama_service,
            embeddings_manager=embeddings_manager,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        print(f"Graph storage path: {temp_storage_path}")
        
        # Simulate a series of entity extractions and resolutions
        entity_batches = [
            # Batch 1: Initial world setup
            [
                {"candidate_id": "world_001", "type": "location", "name": "The Lost Valley", 
                 "description": "A hidden valley surrounded by impassable mountains"},
                {"candidate_id": "world_002", "type": "location", "name": "Haven", 
                 "description": "Central settlement in the valley, well-protected"},
                {"candidate_id": "world_003", "type": "character", "name": "Elena", 
                 "description": "Mayor of Haven who protects the inhabitants"}
            ],
            # Batch 2: Add more characters and places
            [
                {"candidate_id": "char_001", "type": "character", "name": "Theron", 
                 "description": "Master scholar who studies ancient ruins and artifacts"},
                {"candidate_id": "loc_001", "type": "location", "name": "Ancient Ruins", 
                 "description": "Mysterious stone structures with strange magical energy"},
                {"candidate_id": "char_002", "type": "character", "name": "Sara", 
                 "description": "Captain of Riverwatch, defender of the valley"}
            ],
            # Batch 3: Test duplicate detection
            [
                {"candidate_id": "dup_001", "type": "location", "name": "Lost Valley", 
                 "description": "A secluded valley protected by mountains"},  # Should match existing
                {"candidate_id": "dup_002", "type": "character", "name": "Elena the Mayor", 
                 "description": "The mayor who leads Haven and protects its people"},  # Should match existing
                {"candidate_id": "new_001", "type": "object", "name": "Crystal Orb", 
                 "description": "A glowing magical artifact found in the ruins"}  # Should be new
            ]
        ]
        
        total_processed = 0
        for i, batch in enumerate(entity_batches):
            print(f"\n--- Processing Batch {i+1}: {len(batch)} candidates ---")
            
            # Resolve candidates
            resolutions = resolver.resolve_candidates(batch, process_individually=True)
            
            # Add resolved entities to graph
            for resolution, candidate in zip(resolutions, batch):
                if resolution["auto_matched"] and resolution["resolved_node_id"] != "<NEW>":
                    print(f"  {candidate['name']}: MATCHED to {resolution['resolved_node_id']} "
                          f"(confidence: {resolution['confidence']:.2f})")
                    # Update existing node
                    existing_node = graph_manager.get_node(resolution["resolved_node_id"])
                    if existing_node:
                        existing_node.mention_count += 1
                else:
                    print(f"  {candidate['name']}: CREATING NEW entity")
                    # Add new node to graph
                    node, is_new = graph_manager.add_or_update_node(
                        name=candidate["name"],
                        node_type=candidate["type"],
                        description=candidate["description"],
                        conversation_guid=f"test_batch_{i+1}"
                    )
                    if is_new:
                        print(f"    Created node: {node.id}")
                    else:
                        print(f"    Updated existing node: {node.id}")
            
            total_processed += len(batch)
        
        # Get final graph statistics
        all_nodes = list(graph_manager.nodes.values())
        all_edges = graph_manager.edges
        
        print(f"\n=== Final Graph Statistics ===")
        print(f"Total candidates processed: {total_processed}")
        print(f"Final nodes in graph: {len(all_nodes)}")
        print(f"Final edges in graph: {len(all_edges)}")
        print(f"Graph storage files in: {temp_storage_path}")
        
        # List the created nodes
        print(f"\nCreated Nodes:")
        for node in all_nodes:
            print(f"  {node.id}: {node.name} ({node.type}) - mentions: {node.mention_count}")
        
        # Copy files for graph viewer
        self._copy_graph_files_for_viewer(temp_storage_path, "full_workflow_test")
        
        # Verify files were created
        nodes_file = os.path.join(temp_storage_path, "graph_nodes.json")
        edges_file = os.path.join(temp_storage_path, "graph_edges.json")
        metadata_file = os.path.join(temp_storage_path, "graph_metadata.json")
        
        assert os.path.exists(nodes_file), f"Nodes file not created: {nodes_file}"
        assert os.path.exists(edges_file), f"Edges file not created: {edges_file}"
        assert os.path.exists(metadata_file), f"Metadata file not created: {metadata_file}"
        
        print(f"✓ Graph files successfully created and ready for graph viewer")

    def _copy_graph_files_for_viewer(self, source_path: str, test_name: str):
        """Copy generated graph files to a location for graph viewer."""
        import shutil
        
        # Create test output directory
        test_output_dir = os.path.join(os.path.dirname(__file__), "test_files", "tmp", test_name)
        os.makedirs(test_output_dir, exist_ok=True)
        
        # Define source and destination files
        graph_files = [
            ("graph_nodes.json", "Graph nodes"),
            ("graph_edges.json", "Graph edges"),
            ("graph_metadata.json", "Graph metadata"),
            ("graph_memory_embeddings.jsonl", "Entity embeddings")
        ]
        
        copied_files = []
        for filename, description in graph_files:
            source_file = os.path.join(source_path, filename)
            dest_file = os.path.join(test_output_dir, filename)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, dest_file)
                copied_files.append(f"  ✓ {description}: {dest_file}")
            else:
                copied_files.append(f"  ✗ {description}: NOT FOUND")
        
        print(f"\nCopied graph files to: {test_output_dir}")
        for file_info in copied_files:
            print(file_info)
        
        # Also copy to graph viewer if the directory exists
        graph_viewer_dir = os.path.join(os.path.dirname(__file__), "..", "..", "graph-viewer", "public", "sample-data")
        if os.path.exists(graph_viewer_dir):
            viewer_test_dir = os.path.join(graph_viewer_dir, f"entity_resolver_{test_name}")
            os.makedirs(viewer_test_dir, exist_ok=True)
            
            for filename, description in graph_files:
                source_file = os.path.join(source_path, filename)
                dest_file = os.path.join(viewer_test_dir, filename)
                
                if os.path.exists(source_file):
                    shutil.copy2(source_file, dest_file)
            
            print(f"✓ Also copied to graph viewer: {viewer_test_dir}")


def run_real_llm_tests():
    """Run EntityResolver tests with real LLM."""
    print("=" * 80)
    print("ENTITYRESOLVER REAL LLM INTEGRATION TESTS")
    print("=" * 80)
    
    # Check if Ollama is available
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    
    print(f"Testing with Ollama at: {base_url}")
    print(f"Using model: {model}")
    print()
    
    test_args = [
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "integration"
    ]
    
    return pytest.main(test_args)


if __name__ == "__main__":
    exit_code = run_real_llm_tests()
    sys.exit(exit_code)