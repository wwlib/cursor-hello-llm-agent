#!/usr/bin/env python3
"""
Populate Queue from Existing Conversations

This script reads existing conversation data and populates the conversation queue
for the standalone GraphManager to process.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.memory.graph_memory.queue_writer import QueueWriter


def populate_queue_from_conversations(guid: str, memory_type: str = "standard"):
    """Populate the conversation queue from existing conversation data.
    
    Args:
        guid: Agent GUID
        memory_type: Memory manager type
    """
    # Determine paths
    base_memory_dir = "agent_memories"
    memory_dir = os.path.join(base_memory_dir, memory_type, guid)
    conversations_file = os.path.join(memory_dir, "agent_memory_conversations.json")
    graph_storage_path = os.path.join(memory_dir, "agent_memory_graph_data")
    
    # Check if files exist
    if not os.path.exists(conversations_file):
        print(f"Error: Conversations file not found: {conversations_file}")
        return False
    
    if not os.path.exists(graph_storage_path):
        print(f"Creating graph storage directory: {graph_storage_path}")
        os.makedirs(graph_storage_path, exist_ok=True)
    
    # Load conversation data
    print(f"Loading conversations from: {conversations_file}")
    with open(conversations_file, 'r') as f:
        conversations_data = json.load(f)
    
    entries = conversations_data.get("entries", [])
    print(f"Found {len(entries)} conversation entries")
    
    # Initialize queue writer
    queue_writer = QueueWriter(graph_storage_path)
    
    # Clear existing queue to start fresh
    queue_writer.clear_queue()
    print("Cleared existing queue")
    
    # Process each conversation entry and extract digest segments
    queued_count = 0
    for entry in entries:
        # Extract conversation details
        conversation_guid = entry.get("guid", "")
        role = entry.get("role", "")
        content = entry.get("content", "")
        
        # Skip empty entries
        if not content.strip():
            continue
        
        # Process digest segments if available
        if "digest" in entry:
            digest_data = entry["digest"]
            rated_segments = digest_data.get("rated_segments", [])
            
            if rated_segments:
                # Queue each important segment separately
                for i, segment in enumerate(rated_segments):
                    # Use same filtering criteria as MemoryManager: memory_worthy + importance >= 3 + type in ["information", "action"]
                    if (segment.get("memory_worthy", False) and 
                        segment.get("importance", 0) >= 3 and 
                        segment.get("type") in ["information", "action"]):
                        segment_text = segment["text"]
                        segment_guid = f"{conversation_guid}_seg_{i}"
                        
                        # Queue the segment with digest metadata
                        success = queue_writer.write_conversation_entry(
                            conversation_text=segment_text,
                            digest_text=segment_text,  # Segment is already digested
                            conversation_guid=segment_guid,
                            importance=segment.get("importance"),
                            memory_worthy=segment.get("memory_worthy"),
                            segment_type=segment.get("type"),
                            topics=segment.get("topics")
                        )
                        
                        if success:
                            queued_count += 1
                            importance = segment.get("importance", 0)
                            seg_type = segment.get("type", "unknown")
                            print(f"✓ Queued {role} segment: {segment_guid[:20]}... (imp:{importance}, type:{seg_type})")
                        else:
                            print(f"✗ Failed to queue {role} segment: {segment_guid[:20]}...")
                            
            else:
                # No segments, queue the full entry as fallback
                digest_text = content[:200] + "..." if len(content) > 200 else content
                success = queue_writer.write_conversation_entry(
                    conversation_text=content,
                    digest_text=digest_text,
                    conversation_guid=conversation_guid
                )
                
                if success:
                    queued_count += 1
                    print(f"✓ Queued {role} full entry: {conversation_guid[:8]}... (no segments)")
                else:
                    print(f"✗ Failed to queue {role} full entry: {conversation_guid[:8]}...")
        else:
            # No digest, queue the full entry
            digest_text = content[:200] + "..." if len(content) > 200 else content
            success = queue_writer.write_conversation_entry(
                conversation_text=content,
                digest_text=digest_text,
                conversation_guid=conversation_guid
            )
            
            if success:
                queued_count += 1
                print(f"✓ Queued {role} raw entry: {conversation_guid[:8]}... (no digest)")
            else:
                print(f"✗ Failed to queue {role} raw entry: {conversation_guid[:8]}...")
    
    final_queue_size = queue_writer.get_queue_size()
    print(f"\nQueue populated successfully!")
    print(f"- Conversation entries processed: {len(entries)}")
    print(f"- Segments/entries queued: {queued_count}")
    print(f"- Final queue size: {final_queue_size}")
    print(f"\nNote: Each important digest segment is queued separately for better entity extraction.")
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate queue from existing conversations")
    parser.add_argument("--guid", required=True, help="Agent GUID")
    parser.add_argument("--memory-type", default="standard", help="Memory type (default: standard)")
    
    args = parser.parse_args()
    
    success = populate_queue_from_conversations(args.guid, args.memory_type)
    
    if success:
        print(f"\nReady to start standalone GraphManager:")
        print(f"python launcher.py --guid {args.guid} --config lab_assistant --verbose")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()