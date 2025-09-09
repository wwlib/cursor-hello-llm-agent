#!/usr/bin/env python3
"""
Test the refactored graph memory architecture without node embeddings.
"""

import os
import sys
import asyncio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

async def test_refactored_embeddings():
    print("=== Testing Refactored Graph Memory Architecture ===\n")
    
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
        "domain_name": "test_refactored_embeddings",
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object", "concept", "event"],
            "relationship_types": ["related_to", "located_in", "uses", "participates_in", "owns"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager with fresh memory file
    memory_manager = MemoryManager(
        memory_guid="refactor_test_001",
        memory_file="test_memories/refactored_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True
    )
    
    print("✅ Memory manager initialized")
    
    # Add a conversation with entities
    print("\n--- Adding conversation with entities ---")
    
    await memory_manager.add_conversation_entry_async({
        "role": "user",
        "content": "Bob is a chef who lives in Paris and loves cooking pasta. He owns a famous restaurant.",
        "guid": "refactor_test_001"
    })
    
    # Give background processing time to complete
    print("⏳ Waiting for background processing...")
    await asyncio.sleep(1)
    
    # Process background queue properly
    print("🔄 Processing background queue...")
    iteration = 0
    while memory_manager.has_pending_operations() and iteration < 10:
        result = memory_manager.process_background_graph_queue(max_tasks=5)
        processed = result.get('processed', 0)
        print(f"  Iteration {iteration}: Processed {processed} tasks")
        if processed == 0:
            break
        await asyncio.sleep(0.1)
        iteration += 1
    
    # Check the results
    if memory_manager.graph_manager:
        graph = memory_manager.graph_manager
        print(f"\n📊 Graph nodes: {len(graph.nodes)}")
        print(f"🔗 Graph edges: {len(graph.edges)}")
        
        # Check node embedding status (should be 0 since we removed them)
        print("\n--- Node Embedding Status ---")
        for node_id, node in graph.nodes.items():
            # Nodes should not have embeddings anymore
            has_embedding_attr = hasattr(node, 'embedding')
            print(f"• {node.name} ({node.type}): has embedding attribute = {has_embedding_attr}")
        
        # Check EmbeddingsManager for graph entity embeddings
        print("\n--- EmbeddingsManager Search Test ---")
        if memory_manager.embeddings_manager:
            embeddings_mgr = memory_manager.embeddings_manager
            
            # Test direct search
            search_results = embeddings_mgr.search(query="Bob", k=10)
            print(f"Total search results: {len(search_results)}")
            
            # Filter for graph entities
            graph_entities = [r for r in search_results if r.get('metadata', {}).get('source') == 'graph_entity']
            print(f"Graph entity results: {len(graph_entities)}")
            for result in graph_entities:
                metadata = result.get('metadata', {})
                score = result.get('similarity_score', 0.0)
                print(f"  • {metadata.get('entity_name')} ({metadata.get('entity_type')}): {score:.3f}")
        
        # Test new query_for_context method
        print("\n--- Testing New query_for_context Method ---")
        try:
            results = graph.query_for_context("Bob", max_results=3)
            print(f"Query results for 'Bob': {len(results)} results")
            for result in results:
                print(f"  • {result['name']}: {result['description']} (score: {result.get('relevance_score', 0):.3f})")
        except Exception as e:
            print(f"❌ Error in graph query: {e}")
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
    
    print("\n=== Refactored Architecture Test Complete ===")

if __name__ == "__main__":
    # Clean up previous test data
    import shutil
    test_dir = "test_memories"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    asyncio.run(test_refactored_embeddings())