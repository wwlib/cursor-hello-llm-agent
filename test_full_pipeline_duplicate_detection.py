#!/usr/bin/env python3
"""
Test the full pipeline duplicate detection by mimicking exactly what the memory manager does.

This tests the complete flow: EntityExtractor -> GraphManager.add_or_update_node
to verify that duplicates are prevented in the real processing pipeline.
"""

import json
import time
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory.graph_memory.graph_manager import GraphManager
from memory.graph_memory.entity_extractor import EntityExtractor
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService
from examples.domain_configs import DND_CONFIG

def test_full_pipeline_duplicate_detection():
    """Test duplicate detection in the full pipeline that mimics memory manager."""
    
    print("🔧 Testing Full Pipeline Duplicate Detection")
    print("=" * 60)
    
    # Load conversation data
    conversation_file = "agent_memories/standard/dnd5g7/agent_memory_conversations.json"
    print(f"📂 Loading conversation data from: {conversation_file}")
    
    try:
        with open(conversation_file, 'r') as f:
            conversation_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Could not find {conversation_file}")
        return False
    
    # Find the system entry with rich content
    system_entry = None
    for entry in conversation_data["entries"]:
        if entry["role"] == "system" and "digest" in entry:
            system_entry = entry
            break
    
    if not system_entry:
        print("❌ No system entry with digest found")
        return False
    
    print(f"✅ Found system entry with {len(system_entry['digest']['rated_segments'])} segments")
    
    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp(prefix="full_pipeline_test_")
    print(f"📂 Using temp directory: {temp_dir}")
    
    try:
        # Setup LLM service
        llm_config = {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "gemma3"),
            "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
            "debug": False,  # Reduce noise
            "debug_scope": "full_pipeline_test"
        }
        
        llm_service = OllamaService(llm_config)
        
        # Setup components exactly like memory manager
        embeddings_file = os.path.join(temp_dir, "embeddings.jsonl")
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=llm_service
        )
        
        graph_manager = GraphManager(
            storage_path=temp_dir,
            embeddings_manager=embeddings_manager,
            llm_service=llm_service,
            domain_config=DND_CONFIG
        )
        
        print("🏗️ GraphManager initialized")
        
        # Process each segment exactly like memory manager does
        entities_by_segment = {}
        segment_count = 0
        
        for segment in system_entry['digest']['rated_segments']:
            if (segment.get('importance', 0) >= 3 and 
                segment.get('memory_worthy', False) and
                segment.get('type') in ['information', 'action']):
                
                segment_count += 1
                segment_text = segment['text']
                
                print(f"\n📍 Processing segment {segment_count}: '{segment_text[:50]}...'")
                
                # Extract entities from this segment (like memory manager does)
                entities = graph_manager.extract_entities_from_segments([{
                    "text": segment_text,
                    "importance": segment.get("importance", 0),
                    "type": segment.get("type", "information"),
                    "memory_worthy": segment.get("memory_worthy", True),
                    "topics": segment.get("topics", [])
                }])
                
                print(f"   📊 Extracted {len(entities)} entities")
                entities_by_segment[segment_count] = entities
                
                # Add entities to graph exactly like memory manager does
                for entity in entities:
                    node, is_new = graph_manager.add_or_update_node(
                        name=entity.get("name", ""),
                        node_type=entity.get("type", "concept"),
                        description=entity.get("description", ""),
                        attributes=entity.get("attributes", {})
                    )
                    print(f"     • {entity['name']} ({entity['type']}): {node.id}, is_new={is_new}")
        
        # Analyze results
        print(f"\n📊 Pipeline Results Analysis:")
        print(f"   Segments processed: {segment_count}")
        print(f"   Total nodes in graph: {len(graph_manager.nodes)}")
        
        # Look for Haven duplicates specifically
        haven_nodes = [node for node in graph_manager.nodes.values() 
                      if "haven" in node.name.lower() or 
                      any("haven" in alias.lower() for alias in node.aliases)]
        
        print(f"\n🎯 Haven Duplicate Analysis:")
        print(f"   Haven nodes found: {len(haven_nodes)}")
        
        for i, node in enumerate(haven_nodes, 1):
            print(f"     {i}. {node.id}: '{node.name}'")
            print(f"        Description: {node.description}")
            print(f"        Aliases: {node.aliases}")
            print(f"        Mentions: {node.mention_count}")
            print(f"        Type: {node.type}")
        
        # Check for other potential duplicates
        name_counts = {}
        for node in graph_manager.nodes.values():
            name_key = (node.type, node.name.lower().strip())
            if name_key in name_counts:
                name_counts[name_key].append(node)
            else:
                name_counts[name_key] = [node]
        
        duplicates = {k: v for k, v in name_counts.items() if len(v) > 1}
        
        print(f"\n🔍 All Potential Duplicates:")
        if duplicates:
            for (node_type, name), nodes in duplicates.items():
                print(f"   '{name}' ({node_type}): {len(nodes)} instances")
                for node in nodes:
                    print(f"     • {node.id}: {node.description[:50]}...")
        else:
            print("   ✅ No duplicates found!")
        
        # Final assessment
        success = len(haven_nodes) <= 1 and len(duplicates) == 0
        
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}: Duplicate Prevention")
        print(f"   Haven nodes: {len(haven_nodes)} (should be ≤ 1)")
        print(f"   Other duplicates: {len(duplicates)} (should be 0)")
        
        # Save graph files to graph-viewer before cleanup
        try:
            print(f"\n💾 Saving graph files to graph-viewer...")
            
            # Ensure graph-viewer sample-data directory exists
            viewer_data_dir = "graph-viewer/public/sample-data"
            os.makedirs(viewer_data_dir, exist_ok=True)
            
            # Copy graph files from temp directory to graph-viewer
            temp_nodes_file = os.path.join(temp_dir, "graph_nodes.json")
            temp_edges_file = os.path.join(temp_dir, "graph_edges.json") 
            temp_metadata_file = os.path.join(temp_dir, "graph_metadata.json")
            
            viewer_nodes_file = os.path.join(viewer_data_dir, "graph_nodes.json")
            viewer_edges_file = os.path.join(viewer_data_dir, "graph_edges.json")
            viewer_metadata_file = os.path.join(viewer_data_dir, "graph_metadata.json")
            
            if os.path.exists(temp_nodes_file):
                shutil.copy2(temp_nodes_file, viewer_nodes_file)
                print(f"   ✅ Copied graph_nodes.json")
            
            if os.path.exists(temp_edges_file):
                shutil.copy2(temp_edges_file, viewer_edges_file)
                print(f"   ✅ Copied graph_edges.json")
            
            if os.path.exists(temp_metadata_file):
                shutil.copy2(temp_metadata_file, viewer_metadata_file)
                print(f"   ✅ Copied graph_metadata.json")
            
            print(f"   📂 Graph files saved to: {viewer_data_dir}")
            print(f"   🌐 Start graph-viewer with: cd graph-viewer && npm start")
            
        except Exception as e:
            print(f"   ⚠️  Warning: Could not save graph files: {e}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n🧹 Cleaned up temp directory")

if __name__ == "__main__":
    success = test_full_pipeline_duplicate_detection()
    print(f"\n{'🎉 ALL TESTS PASSED!' if success else '💥 TESTS FAILED!'}")
    sys.exit(0 if success else 1)