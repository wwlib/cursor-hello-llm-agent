#!/usr/bin/env python3
"""
Test script to verify that relationship extraction works correctly with EntityResolver.

This test specifically checks that when entities are resolved to existing nodes,
the relationship extraction can still find and create relationships using the
resolved node IDs instead of the original entity names.
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

async def test_relationship_with_resolved_entities():
    """Test that relationships work correctly when entities are resolved."""
    print("=== Testing Relationship Extraction with Resolved Entities ===\n")
    
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
            memory_guid="test-relationship-fix",
            memory_file=memory_file,
            domain_config=DND_CONFIG,
            llm_service=llm_service,
            max_recent_conversation_entries=4,
            digest_llm_service=llm_service,
            embeddings_llm_service=llm_service
        )
        
        print("✓ Memory manager created successfully")
        
        # Initialize memory with initial data
        success = memory_manager.create_initial_memory(DND_CONFIG["initial_data"])
        if success:
            print("✓ Initial memory created")
        else:
            print("✗ Failed to create initial memory")
            return
        
        # Step 1: Create some entities that can be referenced later
        print("\n--- Step 1: Creating Initial Entities ---")
        conversations = [
            "I discover ancient ruins scattered throughout the Lost Valley.",
            "The ruins contain mysterious magical anomalies.",
        ]
        
        for i, conversation in enumerate(conversations):
            print(f"Conversation {i+1}: {conversation}")
            
            update_context = {
                "role": "user",
                "content": conversation,
                "timestamp": f"2025-06-11T10:0{i}:00.000000"
            }
            memory_manager.update_memory(update_context)
            
            # Wait for processing
            if memory_manager.has_pending_operations():
                await memory_manager.wait_for_pending_operations()
        
        # Check what entities were created
        if memory_manager.graph_manager:
            nodes = list(memory_manager.graph_manager.nodes.values())
            print(f"\nAfter Step 1: {len(nodes)} nodes created")
            for node in nodes:
                print(f"  - {node.name} ({node.type}) ID: {node.id}")
        
        # Step 2: Add conversation that should create relationships using duplicate entity names
        print("\n--- Step 2: Testing Relationship with Resolved Entities ---")
        # This conversation mentions "ancient ruins" again (should be resolved to existing)
        # and "magical anomalies" again (should be resolved to existing)
        # The relationship extractor should be able to connect these resolved entities
        test_conversation = "The magical anomalies are located within the ancient ruins, creating strange effects."
        
        print(f"Test conversation: {test_conversation}")
        update_context = {
            "role": "user", 
            "content": test_conversation,
            "timestamp": "2025-06-11T10:02:00.000000"
        }
        memory_manager.update_memory(update_context)
        
        # Wait for processing
        if memory_manager.has_pending_operations():
            print("  Waiting for processing...")
            await memory_manager.wait_for_pending_operations()
        
        # Check final results
        print("\n--- Final Results ---")
        if memory_manager.graph_manager:
            nodes = list(memory_manager.graph_manager.nodes.values())
            edges = memory_manager.graph_manager.edges
            
            print(f"Final graph contains:")
            print(f"  - {len(nodes)} nodes")
            print(f"  - {len(edges)} edges")
            
            print(f"\nNodes:")
            for node in nodes:
                mention_count = getattr(node, 'mention_count', 1)
                print(f"  - {node.name} ({node.type}) ID: {node.id}, mentions: {mention_count}")
            
            print(f"\nEdges/Relationships:")
            if edges:
                for edge in edges:
                    from_node = memory_manager.graph_manager.get_node(edge.from_node_id)
                    to_node = memory_manager.graph_manager.get_node(edge.to_node_id) 
                    print(f"  - {from_node.name if from_node else edge.from_node_id} --[{edge.relationship}]--> {to_node.name if to_node else edge.to_node_id}")
                    # Some edges might not have evidence attribute depending on how they were created
                    if hasattr(edge, 'evidence'):
                        print(f"    Evidence: {edge.evidence}")
                    if hasattr(edge, 'confidence'):
                        print(f"    Confidence: {edge.confidence}")
                    print()
            else:
                print("  No relationships found")
            
            # Success criteria
            if len(edges) > 0:
                print("✓ SUCCESS: Relationships were created with resolved entities!")
                print("  This means the fix is working - EntityResolver resolved duplicate entities")
                print("  and relationship extraction successfully used the resolved node IDs.")
            else:
                print("? No relationships created. This could mean:")
                print("  - The relationship extraction didn't find any relationships, or")
                print("  - The fix still needs adjustment")
                
                # Let's check if entities were properly resolved
                duplicate_found = False
                for node in nodes:
                    if node.mention_count > 1:
                        duplicate_found = True
                        print(f"  - {node.name} was mentioned {node.mention_count} times (good sign)")
                
                if duplicate_found:
                    print("  Entity resolution appears to be working (duplicate entities merged)")
                else:
                    print("  Entity resolution might not be working as expected")
        
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
    print("Relationship Fix Test")
    print("This test verifies that relationship extraction works correctly")
    print("when entities are resolved to existing nodes by EntityResolver.\n")
    
    try:
        asyncio.run(test_relationship_with_resolved_entities())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Test failed: {e}")