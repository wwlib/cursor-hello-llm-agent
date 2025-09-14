#!/usr/bin/env python3
"""
Test Entity Processing Fix

This test verifies that the EntityResolver data structure fix allows entities
to be properly saved to graph files.
"""

import asyncio
import os
import sys
import json
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.graph_memory.graph_manager import GraphManager
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService

# Import D&D config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples'))
from domain_configs import DND_CONFIG


async def test_entity_fix():
    """Test that the entity processing fix works."""
    print("Entity Processing Fix Test")
    print("=" * 40)
    
    # Create temporary directory for test
    test_dir = os.path.join(os.getcwd(), "test_entity_fix_output")
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Set up services
        llm_service = OllamaService({
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "gemma3"),
            "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
            "debug": True,
            "debug_scope": "entity_fix_test"
        })
        
        # Create embeddings manager
        embeddings_file = os.path.join(test_dir, "embeddings.jsonl")
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=llm_service
        )
        
        # Create graph manager
        graph_manager = GraphManager(
            storage_path=test_dir,
            embeddings_manager=embeddings_manager,
            llm_service=llm_service,
            domain_config=DND_CONFIG
        )
        
        # Start background processing
        await graph_manager.start_background_processing()
        
        print("✓ Graph manager initialized")
        
        # Test with simple D&D content
        test_text = "Mayor Elena of Haven discovered a magical crystal in the ancient ruins. The crystal emanates mysterious energy."
        
        print(f"Processing: {test_text}")
        
        # Process the conversation
        result = await graph_manager.process_conversation_entry_with_resolver_async(
            conversation_text=test_text,
            conversation_guid="test_fix_conv"
        )
        
        print(f"✅ Processing completed: {len(result.get('entities', []))} entities, {len(result.get('relationships', []))} relationships")
        
        # Give time for file operations to complete
        await asyncio.sleep(2)
        
        # Check the generated files
        print("\n=== Checking Generated Files ===")
        
        graph_files = ['graph_nodes.json', 'graph_edges.json', 'graph_metadata.json']
        
        for file_name in graph_files:
            file_path = os.path.join(test_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                print(f"\n--- {file_name} ---")
                if content.strip() and content.strip() not in ['{}', '[]']:
                    # File has content
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            if data:  # Non-empty dict
                                print(f"✅ Contains data: {len(data)} items")
                                # Show first few keys/items
                                for key in list(data.keys())[:3]:
                                    item = data[key]
                                    if isinstance(item, dict) and 'name' in item:
                                        print(f"  - {key}: {item.get('name', 'Unknown')} ({item.get('type', 'Unknown')})")
                                    else:
                                        print(f"  - {key}: {str(item)[:100]}...")
                            else:
                                print("❌ Empty dictionary")
                        elif isinstance(data, list):
                            if data:  # Non-empty list
                                print(f"✅ Contains data: {len(data)} items")
                                for i, item in enumerate(data[:3]):
                                    if isinstance(item, dict):
                                        name = item.get('from_entity_id', '') + ' -> ' + item.get('to_entity_id', '') if 'from_entity_id' in item else str(item)[:50]
                                        print(f"  - Item {i+1}: {name}")
                            else:
                                print("❌ Empty list")
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON: {content[:100]}...")
                else:
                    print("❌ Empty or minimal content")
            else:
                print(f"❌ File not found: {file_name}")
        
        await graph_manager.stop_background_processing()
        
        print(f"\n✅ Test completed. Check files in: {test_dir}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_entity_fix())