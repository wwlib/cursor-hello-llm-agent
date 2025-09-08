#!/usr/bin/env python3
"""
Test the fixed embedding generation for graph entities.
"""

import os
import sys
import asyncio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

async def test_fixed_embeddings():
    print("=== Testing Fixed Graph Embeddings ===\n")
    
    # Configure Ollama service
    ollama_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://192.168.10.28:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.7,
        "debug": True
    }
    
    llm_service = OllamaService(ollama_config)
    
    # Domain config
    domain_config = {
        "domain_name": "test_fixed_embeddings",
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object", "concept", "event"],
            "relationship_types": ["related_to", "located_in", "uses", "participates_in", "owns"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager with fresh memory file
    memory_manager = MemoryManager(
        memory_guid="embed_test_001",
        memory_file="test_memories/fixed_embeddings_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True
    )
    
    print("✅ Memory manager initialized")
    
    # Add a conversation with new entities
    print("\n--- Adding conversation with entities ---")
    
    await memory_manager.add_conversation_entry_async({
        "role": "user",
        "content": "Bob is a chef who lives in Paris and loves cooking pasta. He owns a famous restaurant.",
        "guid": "embed_test_001"
    })
    
    # Give background processing time to complete
    print("⏳ Waiting for background processing...")
    await asyncio.sleep(1)
    
    # Process background queue
    print("🔄 Processing background queue...")
    while memory_manager.has_pending_operations():
        result = memory_manager.process_background_graph_queue(max_tasks=2)
        if result.get('processed', 0) == 0:
            break
        print(f"  Processed {result.get('processed', 0)} tasks")
        await asyncio.sleep(0.1)
    
    # Check the results
    if memory_manager.graph_manager:
        graph = memory_manager.graph_manager
        print(f"\n📊 Graph nodes: {len(graph.nodes)}")
        print(f"🔗 Graph edges: {len(graph.edges)}")
        
        # Check node embeddings
        print("\n--- Node Embedding Status ---")
        for node_id, node in graph.nodes.items():
            try:
                embedding_length = len(node.embedding) if node.embedding is not None and len(node.embedding) > 0 else 0
            except:
                embedding_length = 0
            print(f"• {node.name} ({node.type}): embedding length = {embedding_length}")
        
        # Test text matching
        print("\n--- Testing Text Matching ---")
        graph.embeddings_manager = None  # Disable embeddings temporarily
        results = graph.query_for_context("Bob", max_results=3)
        print(f"Text search for 'Bob': {len(results)} results")
        for result in results:
            print(f"  • {result['name']}: {result['description']}")
        
        # Restore embeddings manager
        graph.embeddings_manager = memory_manager.embeddings_manager
        
        # Test embedding-based search
        print("\n--- Testing Embedding Search ---")
        try:
            results = graph.query_for_context("Bob", max_results=3)
            print(f"Embedding search for 'Bob': {len(results)} results")
            for result in results:
                print(f"  • {result['name']}: {result['description']} (score: {result.get('relevance_score', 0):.3f})")
        except Exception as e:
            print(f"❌ Error in embedding search: {e}")
            import traceback
            traceback.print_exc()
        
        # Test different queries
        print("\n--- Testing Various Queries ---")
        test_queries = ["chef", "Paris", "restaurant", "cooking"]
        
        for query in test_queries:
            try:
                results = graph.query_for_context(query, max_results=2)
                print(f"Query '{query}': {len(results)} results")
                for result in results:
                    print(f"  • {result['name']}: score {result.get('relevance_score', 0):.3f}")
            except Exception as e:
                print(f"❌ Error querying '{query}': {e}")
    else:
        print("❌ No graph manager available")
    
    print("\n=== Fixed Embeddings Test Complete ===")

if __name__ == "__main__":
    # Clean up previous test data
    import shutil
    test_dir = "test_memories"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    asyncio.run(test_fixed_embeddings())