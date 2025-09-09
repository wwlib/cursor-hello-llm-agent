#!/usr/bin/env python3
"""
Debug embedding search to verify the similarity score field fix works.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

def test_embedding_search_debug():
    print("=== Debug Embedding Search ===")
    
    # Initialize components
    ollama_service = OllamaService({
        'base_url': 'http://192.168.10.28:11434',
        'model': 'gemma3',
        'embed_model': 'mxbai-embed-large',
        'debug': True
    })
    
    # Use existing test memory
    memory_guid = "fixed_embeddings_test"
    memory_dir = "test_memories"
    
    # Basic domain config for testing
    domain_config = {
        "domain_name": "test",
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object"],
            "relationship_types": ["located_in", "owns", "cooks"],
            "similarity_threshold": 0.8
        }
    }
    
    memory_file = os.path.join(memory_dir, memory_guid, f"{memory_guid}.json")
    memory_manager = MemoryManager(
        memory_guid=memory_guid,
        memory_file=memory_file,
        domain_config=domain_config,
        llm_service=ollama_service,
        enable_graph_memory=True
    )
    
    print(f"✅ Memory manager initialized with GUID: {memory_guid}")
    
    # Check embeddings manager directly
    embeddings_manager = memory_manager.graph_manager.embeddings_manager
    print(f"📊 Total embeddings in manager: {len(embeddings_manager.embeddings)}")
    print(f"📁 Embeddings file path: {embeddings_manager.embeddings_file}")
    print(f"📁 File exists: {os.path.exists(embeddings_manager.embeddings_file)}")
    
    if embeddings_manager.embeddings:
        for i, (embedding, metadata) in enumerate(embeddings_manager.embeddings):
            print(f"  Embedding {i+1}: {len(embedding)} dims, metadata keys: {list(metadata.keys())}")
            if 'entity_name' in metadata:
                print(f"    Entity: {metadata['entity_name']} ({metadata.get('entity_type', 'unknown')})")
    
    # Test direct search
    print("\n--- Direct EmbeddingsManager Search ---")
    search_results = embeddings_manager.search(query="Bob", k=5)
    print(f"Direct search results for 'Bob': {len(search_results)}")
    for i, result in enumerate(search_results):
        print(f"  Result {i+1}: score={result.get('score', 'missing')}, text='{result.get('text', '')[:50]}...'")
        print(f"    Metadata keys: {list(result.get('metadata', {}).keys())}")
    
    # Test graph manager search
    print("\n--- GraphManager query_for_context ---")
    graph_results = memory_manager.graph_manager.query_for_context("Bob", max_results=5)
    print(f"Graph search results for 'Bob': {len(graph_results)}")
    for i, result in enumerate(graph_results):
        print(f"  Result {i+1}: relevance_score={result.get('relevance_score', 'missing')}")
        print(f"    Name: {result.get('name', '')}, Type: {result.get('type', '')}")
        print(f"    Description: {result.get('description', '')[:100]}...")
        print(f"    Source: {result.get('source', '')}")
    
    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    test_embedding_search_debug()