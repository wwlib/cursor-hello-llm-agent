#!/usr/bin/env python3
"""
Test script to verify EntityResolver integration with agent usage example.

This script tests that the EntityResolver is properly integrated into the 
GraphManager and MemoryManager flow, providing enhanced duplicate detection
when entities are extracted from conversation segments.
"""

import asyncio
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import AsyncMemoryManager
from examples.domain_configs import DND_CONFIG

async def test_entity_resolver_integration():
    """Test that EntityResolver is properly integrated and working."""
    print("=== Testing EntityResolver Integration ===\n")
    
    # Create temporary directory for this test
    temp_dir = tempfile.mkdtemp()
    memory_file = os.path.join(temp_dir, "test_memory.json")
    
    try:
        # Create LLM service
        llm_service = OllamaService({
            "base_url": "http://192.168.1.173:11434",
            "model": "gemma3",
            "temperature": 0.7,
            "debug": True,
            "console_output": False
        })
        
        # Create memory manager with graph memory enabled
        memory_manager = AsyncMemoryManager(
            memory_guid="test-entity-resolver-integration",
            memory_file=memory_file,
            domain_config=DND_CONFIG,
            llm_service=llm_service,
            max_recent_conversation_entries=4,
            digest_llm_service=llm_service,
            embeddings_llm_service=llm_service
        )
        
        print("✓ Memory manager created successfully")
        
        # Check if EntityResolver is enabled
        if hasattr(memory_manager, 'graph_manager') and memory_manager.graph_manager:
            if hasattr(memory_manager.graph_manager, 'entity_resolver') and memory_manager.graph_manager.entity_resolver:
                print("✓ EntityResolver is enabled and available")
                resolver = memory_manager.graph_manager.entity_resolver
                print(f"  - Confidence threshold: {resolver.confidence_threshold}")
                print(f"  - Storage path: {resolver.storage.storage_path}")
            else:
                print("✗ EntityResolver is not available")
                print("  - This may be because embeddings_manager is not available")
                print("  - Or EntityResolver initialization failed")
        else:
            print("✗ GraphManager is not available")
        
        # Test entity processing with some sample conversation
        print("\n--- Testing Entity Processing ---")
        
        # Initialize memory with initial data
        success = memory_manager.create_initial_memory(DND_CONFIG["initial_data"])
        if success:
            print("✓ Initial memory created")
        else:
            print("✗ Failed to create initial memory")
            return
        
        # Add some conversation entries that should create entities
        test_conversations = [
            "I'm exploring the Lost Valley and I meet Elena, the mayor of Haven.",
            "Elena tells me about Theron, a scholar who studies the ancient ruins.",
            "I find a mysterious Crystal Orb in the ruins near the valley.",
            "The valley contains Haven, which is protected by Elena the Mayor.",  # Should match existing Elena
            "There's a Hidden Valley with ancient stone structures."  # Should match existing Lost Valley
        ]
        
        print(f"\nProcessing {len(test_conversations)} test conversations...")
        
        for i, conversation in enumerate(test_conversations):
            print(f"\nConversation {i+1}: {conversation}")
            
            # Update memory (this triggers entity extraction and resolution)
            update_context = {
                "role": "user",
                "content": conversation,
                "timestamp": "2025-06-11T10:00:00.000000"
            }
            memory_manager.update_memory(update_context)
            
            # Wait for any background processing
            if memory_manager.has_pending_operations():
                print("  Waiting for background processing...")
                await memory_manager.wait_for_pending_operations()
            
            print("  ✓ Processed")
        
        # Check final graph state
        print("\n--- Final Graph State ---")
        if memory_manager.graph_manager:
            nodes = list(memory_manager.graph_manager.nodes.values())
            edges = memory_manager.graph_manager.edges
            
            print(f"Final graph contains:")
            print(f"  - {len(nodes)} nodes")
            print(f"  - {len(edges)} edges")
            
            print(f"\nNodes created:")
            for node in nodes:
                mention_count = getattr(node, 'mention_count', 1)
                print(f"  - {node.name} ({node.type}): mentions={mention_count}")
                if hasattr(node, 'attributes') and 'conversation_history_guids' in node.attributes:
                    guids = node.attributes['conversation_history_guids']
                    print(f"    Mentioned in conversations: {len(guids)}")
            
            # Test successful if we have reasonable number of nodes
            # (Should have fewer nodes than conversations due to duplicate detection)
            if len(nodes) > 0 and len(nodes) < len(test_conversations):
                print(f"\n✓ EntityResolver successfully detected duplicates!")
                print(f"  {len(test_conversations)} conversations → {len(nodes)} unique entities")
            else:
                print(f"\n? Results unclear: {len(nodes)} nodes from {len(test_conversations)} conversations")
        
        print(f"\n=== Test completed ===")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")

if __name__ == "__main__":
    print("EntityResolver Integration Test")
    print("This test verifies that EntityResolver is properly integrated")
    print("into the GraphManager and MemoryManager flow.\n")
    
    try:
        asyncio.run(test_entity_resolver_integration())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Test failed: {e}")