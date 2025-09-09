#!/usr/bin/env python3
"""
Test graph context retrieval using the fresh fixed_embeddings_test data
to verify the similarity score field fix works.
"""

import os
import sys
import asyncio
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

async def test_graph_query_context():
    print("=== Testing Graph Query Context ===\n")
    
    # Configure Ollama service
    ollama_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://192.168.10.28:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.7,
        "debug": True
    }
    
    llm_service = OllamaService(ollama_config)
    
    # Domain config matching the fresh test
    domain_config = {
        "domain_name": "test",
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object"],
            "relationship_types": ["located_in", "owns", "cooks"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager with our fresh test data
    memory_manager = MemoryManager(
        memory_guid="fixed_embeddings_test",
        memory_file="test_memories/fixed_embeddings_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True
    )
    
    print("✅ Memory manager initialized")
    
    # Check if graph manager exists and has data
    if memory_manager.graph_manager:
        print(f"📊 Graph nodes: {len(memory_manager.graph_manager.nodes)}")
        print(f"🔗 Graph edges: {len(memory_manager.graph_manager.edges)}")
        
        print("\n--- Entities ---")
        for node_id, node in memory_manager.graph_manager.nodes.items():
            print(f"• {node.name} ({node.type}): {node.description}")
            
        print("\n--- Relationships ---")
        for edge in memory_manager.graph_manager.edges:
            from_node = memory_manager.graph_manager.nodes.get(edge.from_node_id)
            to_node = memory_manager.graph_manager.nodes.get(edge.to_node_id)
            print(f"• {from_node.name if from_node else edge.from_node_id} --[{edge.relationship}]--> {to_node.name if to_node else edge.to_node_id}")
            
        # Test graph queries (this tests our similarity score fix!)
        print("\n--- Graph Query Tests (Testing Similarity Score Fix) ---")
        
        test_queries = ["Bob", "chef", "Paris", "restaurant", "cooking", "pasta"]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            query_results = memory_manager.graph_manager.query_for_context(query, max_results=3)
            print(f"  Results: {len(query_results)}")
            
            for i, result in enumerate(query_results):
                score = result.get('relevance_score', 'missing')
                source = result.get('source', 'unknown')
                print(f"    {i+1}. {result['name']} ({result['type']})")
                print(f"       Score: {score} | Source: {source}")
                print(f"       Description: {result['description'][:80]}...")
        
        # Check embeddings status
        print("\n--- Embeddings Status ---")
        if hasattr(memory_manager.graph_manager, 'embeddings_manager'):
            embeddings_count = len(memory_manager.graph_manager.embeddings_manager.embeddings)
            print(f"📊 Embeddings loaded: {embeddings_count}")
            if embeddings_count > 0:
                print("✅ Embeddings available - semantic search should work")
            else:
                print("⚠️ No embeddings loaded - falling back to text matching")
        else:
            print("❌ No embeddings manager available")
            
    else:
        print("❌ No graph manager available")
    
    print("\n=== Graph Query Context Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_graph_query_context())