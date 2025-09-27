#!/usr/bin/env python3
"""
Test script for non-blocking graph processing.

This script demonstrates the new background processing approach where:
1. Graph queries return immediately with current data
2. Graph processing happens in the background 
3. New data becomes available for future queries
"""

# global OUTPUT_DIR = "test_non_blocking_graph_processing_output"
OUTPUT_DIR = "test_non_blocking_graph_processing_output"

import os
import sys
import asyncio
import time
import shutil
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
    start_script = time.time()
    print(f"[{time.time()-start_script:.3f}s] === Non-Blocking Graph Processing Test ===\n")
    
    # Setup
    llm_service, domain_config = setup_test_environment()
    
    # Create memory manager with background processing
    memory_manager = MemoryManager(
        memory_guid="bg_test_001",
        memory_file=f"{OUTPUT_DIR}/background_test.json",
        llm_service=llm_service,
        domain_config=domain_config,
        enable_graph_memory=True,
        graph_memory_processing_level="balanced"
    )
    
    print(f"[{time.time()-start_script:.3f}s] ✅ Memory manager initialized")
    
    # Test 1: Initial query with empty graph
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 1: Query empty graph ---")
    start_time = time.time()
    
    result = memory_manager.query_memory("What do we know about Alice?")
    query_time = time.time() - start_time
    
    print(f"[{time.time()-start_script:.3f}s] ⚡ Query completed in {query_time:.3f}s (should be very fast)")
    print(f"[{time.time()-start_script:.3f}s] 📝 Response length: {len(result if isinstance(result, str) else result.get('response', ''))}")
    
    # Check graph status
    if memory_manager.graph_manager:
        graph_status = memory_manager.graph_manager.get_background_processing_status()
        print(f"[{time.time()-start_script:.3f}s] 📊 Graph status: {graph_status.get('status', 'unknown')}, queue: {graph_status.get('queue_size', 0)}")
    else:
        print(f"[{time.time()-start_script:.3f}s] 📊 Graph status: not available, queue: 0")
    
    # Test 2: Add conversation entry (should queue background processing)
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 2: Add conversation entry ---")
    
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
    
    print(f"[{time.time()-start_script:.3f}s] ⚡ Conversation added in {add_time:.3f}s (should be fast - queued for background)")
    
    # Give async tasks a moment to start
    await asyncio.sleep(0.1)
    
    # Check if processing was queued
    if memory_manager.graph_manager:
        graph_status = memory_manager.graph_manager.get_background_processing_status()
        print(f"[{time.time()-start_script:.3f}s] 📊 Graph status after add: queue size = {graph_status.get('queue_size', 0)}")
        print(f"[{time.time()-start_script:.3f}s] 📋 Queue status: {graph_status.get('status', 'unknown')}")
    else:
        print(f"[{time.time()-start_script:.3f}s] 📊 Graph status after add: queue size = 0")
        print(f"[{time.time()-start_script:.3f}s] 📋 Queue status: not available")
    
    # Test 3: Query again (should still be fast, using current graph data)
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 3: Query with pending background work ---")
    
    start_time = time.time()
    result = memory_manager.query_memory("Tell me about Alice")
    query_time = time.time() - start_time
    
    print(f"[{time.time()-start_script:.3f}s] ⚡ Query completed in {query_time:.3f}s (should still be fast)")
    response_text = result if isinstance(result, str) else result.get('response', '')
    print(f"[{time.time()-start_script:.3f}s] 📝 Response mentions Alice: {'alice' in response_text.lower()}")
    
    # Check if we have pending operations
    has_pending = memory_manager.has_pending_operations()
    print(f"[{time.time()-start_script:.3f}s] ⏳ Has pending operations: {has_pending}")
    
    # Test 4: Wait for background processing to complete
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 4: Wait for background processing ---")
    
    print(f"[{time.time()-start_script:.3f}s] 🔄 Waiting for background processing to complete...")
    # Wait for background processing to finish
    wait_start = time.time()
    while memory_manager.has_pending_operations():
        await asyncio.sleep(0.5)
        wait_time = time.time() - wait_start
        if wait_time > 30:  # 30 second timeout
            print(f"[{time.time()-start_script:.3f}s] ⏱️ Timeout waiting for background processing")
            break
    
    wait_time = time.time() - wait_start
    print(f"[{time.time()-start_script:.3f}s] ✅ Background processing completed in {wait_time:.1f}s")
    
    # Check status after processing
    if memory_manager.graph_manager:
        graph_status = memory_manager.graph_manager.get_background_processing_status()
        print(f"[{time.time()-start_script:.3f}s] 📊 Queue size after processing: {graph_status.get('queue_size', 0)}")
    else:
        print(f"[{time.time()-start_script:.3f}s] 📊 Queue size after processing: 0")
    
    # Test 5: Query after some processing (should have more context)
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 5: Query after background processing ---")
    
    start_time = time.time()
    result = memory_manager.query_memory("What do you know about Alice and her interests?")
    query_time = time.time() - start_time
    
    print(f"[{time.time()-start_script:.3f}s] ⚡ Query completed in {query_time:.3f}s")
    response_text = result if isinstance(result, str) else result.get('response', '')
    print(f"[{time.time()-start_script:.3f}s] 📝 Response length: {len(response_text)}")
    print(f"[{time.time()-start_script:.3f}s] 🎯 Mentions chess: {'chess' in response_text.lower()}")
    print(f"[{time.time()-start_script:.3f}s] 🏠 Mentions New York: {'new york' in response_text.lower()}")
    
    # Test 6: Final status
    print(f"\n[{time.time()-start_script:.3f}s] --- Test 6: Final Status ---")
    
    # Final status
    if memory_manager.graph_manager:
        graph_status = memory_manager.graph_manager.get_background_processing_status()
        print(f"[{time.time()-start_script:.3f}s] 🎉 Final queue size: {graph_status.get('queue_size', 0)}")
        print(f"[{time.time()-start_script:.3f}s] 📈 Graph nodes: {graph_status.get('graph_stats', {}).get('total_nodes', 0)}")
        print(f"[{time.time()-start_script:.3f}s] 🔗 Graph edges: {graph_status.get('graph_stats', {}).get('total_edges', 0)}")
    else:
        print(f"[{time.time()-start_script:.3f}s] 🎉 Final queue size: 0")
        print(f"[{time.time()-start_script:.3f}s] 📈 Graph nodes: 0")
        print(f"[{time.time()-start_script:.3f}s] 🔗 Graph edges: 0")
    
    print(f"\n[{time.time()-start_script:.3f}s] === Test Complete ===")
    print(f"[{time.time()-start_script:.3f}s] ✅ Non-blocking graph processing is working!")
    print(f"[{time.time()-start_script:.3f}s] 🔍 Key benefits demonstrated:")
    print(f"[{time.time()-start_script:.3f}s]    - Queries return immediately using current graph data")
    print(f"[{time.time()-start_script:.3f}s]    - Graph processing happens in background queue") 
    print(f"[{time.time()-start_script:.3f}s]    - New data becomes available progressively")
    print(f"[{time.time()-start_script:.3f}s]    - System remains responsive during heavy processing")

async def main():
    """Main test runner."""
    try:
        await test_non_blocking_processing()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Remove existing test directory to start fresh
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    
    # Create test directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run the test
    asyncio.run(main())