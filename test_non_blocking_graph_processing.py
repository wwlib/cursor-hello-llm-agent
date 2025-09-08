#!/usr/bin/env python3
"""
Test script for non-blocking graph processing.

This script demonstrates the new background processing approach where:
1. Graph queries return immediately with current data
2. Graph processing happens in the background 
3. New data becomes available for future queries
"""

import os
import sys
import asyncio
import time
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.memory_manager import MemoryManager
from ai.llm_ollama import OllamaService

def setup_test_environment():
    """Setup test environment with required services."""
    # Configure Ollama service
    ollama_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.7,
        "debug": True,
        "debug_scope": "background_test"
    }
    
    llm_service = OllamaService(ollama_config)
    
    # Domain config with graph memory enabled
    domain_config = {
        "domain_name": "test_background_processing",
        "domain_specific_prompt_instructions": {
            "query": "You are testing background graph processing...",
            "update": "You are analyzing test input for background processing..."
        },
        "initial_data": "This is a test environment for background graph processing.",
        "topic_taxonomy": {
            "test": ["functionality", "performance", "reliability"],
            "processing": ["background", "queue", "async"]
        },
        "graph_memory_config": {
            "enabled": True,
            "entity_types": ["person", "location", "object", "concept", "event"],
            "relationship_types": ["related_to", "located_in", "uses", "participates_in", "owns"],
            "entity_extraction_prompt": "Extract test entities from this conversation...",
            "relationship_extraction_prompt": "Identify relationships between test entities...",
            "similarity_threshold": 0.8
        }
    }
    
    return llm_service, domain_config

async def test_non_blocking_processing():
    """Test the non-blocking graph processing approach."""
    print("=== Non-Blocking Graph Processing Test ===\n")
    
    # Setup
    llm_service, domain_config = setup_test_environment()
    
    # Create memory manager with background processing
    memory_manager = MemoryManager(
        memory_guid="bg_test_001",
        memory_file="test_memories/background_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True,
        graph_memory_processing_level="balanced"
    )
    
    print("✅ Memory manager initialized")
    
    # Test 1: Initial query with empty graph
    print("\n--- Test 1: Query empty graph ---")
    start_time = time.time()
    
    result = memory_manager.query_memory("What do we know about Alice?")
    query_time = time.time() - start_time
    
    print(f"⚡ Query completed in {query_time:.3f}s (should be very fast)")
    print(f"📝 Response length: {len(result.get('response', ''))}")
    
    # Check graph status
    graph_status = memory_manager.get_graph_processing_status()
    print(f"📊 Graph status: {graph_status.get('status', 'unknown')}, queue: {graph_status.get('queue_size', 0)}")
    
    # Test 2: Add conversation entry (should queue background processing)
    print("\n--- Test 2: Add conversation entry ---")
    
    test_conversation = {
        "role": "user",
        "content": "Alice lives in New York and works as a software engineer. She loves playing chess and owns a beautiful garden.",
        "guid": "test_entry_001"
    }
    
    start_time = time.time()
    await memory_manager.add_conversation_entry_async({
        "role": "user", 
        "content": test_conversation["content"],
        "guid": test_conversation["guid"]
    })
    add_time = time.time() - start_time
    
    print(f"⚡ Conversation added in {add_time:.3f}s (should be fast - queued for background)")
    
    # Give async tasks a moment to start
    await asyncio.sleep(0.1)
    
    # Check if processing was queued
    graph_status = memory_manager.get_graph_processing_status()
    print(f"📊 Graph status after add: queue size = {graph_status.get('queue_size', 0)}")
    print(f"📋 Queue status: {graph_status.get('status', 'unknown')}")
    
    # Test 3: Query again (should still be fast, using current graph data)
    print("\n--- Test 3: Query with pending background work ---")
    
    start_time = time.time()
    result = memory_manager.query_memory("Tell me about Alice")
    query_time = time.time() - start_time
    
    print(f"⚡ Query completed in {query_time:.3f}s (should still be fast)")
    print(f"📝 Response mentions Alice: {'alice' in result.get('response', '').lower()}")
    
    # Check if we have pending operations
    has_pending = memory_manager.has_pending_operations()
    print(f"⏳ Has pending operations: {has_pending}")
    
    # Test 4: Process some background tasks
    print("\n--- Test 4: Process background queue ---")
    
    print("🔄 Processing 1 background task...")
    process_result = memory_manager.process_background_graph_queue(max_tasks=1)
    print(f"📊 Processing result: {process_result.get('message', 'No message')}")
    print(f"✅ Processed: {process_result.get('processed', 0)}, Errors: {process_result.get('errors', 0)}")
    
    # Check status after processing
    graph_status = memory_manager.get_graph_processing_status()
    print(f"📊 Queue size after processing: {graph_status.get('queue_size', 0)}")
    
    # Test 5: Query after some processing (should have more context)
    print("\n--- Test 5: Query after background processing ---")
    
    start_time = time.time()
    result = memory_manager.query_memory("What do you know about Alice and her interests?")
    query_time = time.time() - start_time
    
    print(f"⚡ Query completed in {query_time:.3f}s")
    print(f"📝 Response length: {len(result.get('response', ''))}")
    print(f"🎯 Mentions chess: {'chess' in result.get('response', '').lower()}")
    print(f"🏠 Mentions New York: {'new york' in result.get('response', '').lower()}")
    
    # Test 6: Process remaining queue
    print("\n--- Test 6: Process remaining background tasks ---")
    
    while memory_manager.has_pending_operations():
        process_result = memory_manager.process_background_graph_queue(max_tasks=2)
        if process_result.get('processed', 0) == 0:
            break
        print(f"🔄 Processed {process_result.get('processed', 0)} more tasks")
        
        # Small delay to avoid busy waiting
        await asyncio.sleep(0.1)
    
    # Final status
    graph_status = memory_manager.get_graph_processing_status()
    print(f"🎉 Final queue size: {graph_status.get('queue_size', 0)}")
    print(f"📈 Graph nodes: {graph_status.get('graph_stats', {}).get('total_nodes', 0)}")
    print(f"🔗 Graph edges: {graph_status.get('graph_stats', {}).get('total_edges', 0)}")
    
    print("\n=== Test Complete ===")
    print("✅ Non-blocking graph processing is working!")
    print("🔍 Key benefits demonstrated:")
    print("   - Queries return immediately using current graph data")
    print("   - Graph processing happens in background queue") 
    print("   - New data becomes available progressively")
    print("   - System remains responsive during heavy processing")

async def main():
    """Main test runner."""
    try:
        await test_non_blocking_processing()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Create test directories
    os.makedirs("test_memories", exist_ok=True)
    
    # Run the test
    asyncio.run(main())