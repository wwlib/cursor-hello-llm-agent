#!/usr/bin/env python3
"""
Test to see what entities and relationships were extracted.
"""

import os
import sys
import asyncio
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

async def check_graph_contents():
    print("=== Checking Graph Contents ===\n")
    
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
        "domain_name": "test_background_processing",
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object", "concept", "event"],
            "relationship_types": ["related_to", "located_in", "uses", "participates_in", "owns"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_guid="bg_test_001",
        memory_file="test_memories/background_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True,
        graph_memory_processing_level="balanced"
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
            
        # Test graph query
        print("\n--- Graph Query Test ---")
        query_results = memory_manager.graph_manager.query_for_context("Alice", max_results=3)
        print(f"Query results for 'Alice': {len(query_results)} results")
        for result in query_results:
            print(f"• {result['name']} ({result['type']}): {result['description']} (score: {result['relevance_score']:.3f})")
            
    else:
        print("❌ No graph manager available")
    
    print("\n=== Graph Contents Check Complete ===")

if __name__ == "__main__":
    asyncio.run(check_graph_contents())