#!/usr/bin/env python3

import json
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.digest_generator import DigestGenerator

def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_json(data, indent=2):
    """Print JSON in a readable format"""
    print(json.dumps(data, indent=indent))

def main():
    """Demonstrate the DigestGenerator class"""
    print_section_header("DigestGenerator Example")
    
    # Verify that template files exist
    template_dir = os.path.join(project_root, "src", "memory", "templates")
    segment_template_path = os.path.join(template_dir, "segment_conversation.prompt") 
    extract_template_path = os.path.join(template_dir, "extract_digest.prompt")
    
    if not os.path.exists(segment_template_path) or not os.path.exists(extract_template_path):
        print(f"Error: Template files not found. Please ensure they exist at:")
        print(f"  - {segment_template_path}")
        print(f"  - {extract_template_path}")
        return
    
    # Initialize LLM service
    print("Initializing LLM service...")
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": "digest_generator_example.log",
        "debug_scope": "digest_example",
        "console_output": False
    })
    
    # Initialize DigestGenerator
    print("Initializing DigestGenerator...")
    digest_generator = DigestGenerator(llm_service)
    
    # Sample conversation entries
    print_section_header("Sample Conversation Entries")
    
    conversation_entries = [
        {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": "The air hangs heavy with the scent of pine and damp earth as you recall the recent events. Just yesterday, Captain Silas, a grizzled veteran of the Merchant Guard, approached you with a proposition. He'd detected unusual activity near the Blackwood Caves – whispers of monstrous spiders weaving webs of shadow and venom. He offered a reward of 50 gold pieces plus a share of any recovered goods, a considerable sum considering the dangers. You accepted, eager for adventure and a bit of coin. The task: track down these venomous spiders and eliminate the threat to the surrounding settlements. The caves themselves are known to be a labyrinthine network, riddled with traps and, as Silas ominously warned, the spiders themselves.",
            "timestamp": datetime.now().isoformat()
        },
        {
            "guid": str(uuid.uuid4()),
            "role": "user",
            "content": "I need to get prepared for this adventure. What kind of equipment should I bring to deal with venomous spiders? Also, do I know anyone who might have knowledge about these caves?",
            "timestamp": datetime.now().isoformat()
        },
        {
            "guid": str(uuid.uuid4()),
            "role": "assistant",
            "content": "For tackling venomous spiders, you'd be wise to bring antivenom potions if available from the local apothecary. Torches or lanterns are essential given the darkness of caves. A sturdy shield would help deflect any lunging attacks, while ranged weapons like a bow or crossbow could let you strike before entering their webbed domains. As for knowledge of the Blackwood Caves, you recall that Old Marta, the herbalist who lives at the edge of the village, once mentioned gathering rare fungi from those caves in her younger days. She might have valuable insights about the cave layout. There's also Durgan, a retired miner who frequents the Sleeping Dragon tavern - he's mapped many local cave systems and might have some information about Blackwood's tunnels for the price of a few ales.",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # Process each conversation entry
    for i, entry in enumerate(conversation_entries):
        print(f"\nEntry {i+1} - {entry['role']}:")
        print("-" * 40)
        print(entry['content'][:100] + "...")  # Print just the first 100 chars to save space
        
    # Generate digests for each entry
    print_section_header("Generated Digests")
    
    for i, entry in enumerate(conversation_entries):
        print(f"\nGenerating digest for entry {i+1} - {entry['role']}...")
        
        # Generate digest
        digest = digest_generator.generate_digest(entry)
        
        # Print the results
        print(f"\nDigest for entry {i+1} - {entry['role']}:")
        print("-" * 40)
        
        # Print segment count
        print(f"\nSegments: {len(digest['segments'])}")
        if len(digest['segments']) > 0:
            print("\nFirst 3 segments:")
            for j, segment in enumerate(digest['segments'][:3]):
                print(f"  {j}: {segment}")
            if len(digest['segments']) > 3:
                print(f"  ... ({len(digest['segments']) - 3} more segments)")
        
        # Print context
        print(f"\nContext: {digest['context']}")
        
        # Print facts
        print(f"\nExtracted Facts: {len(digest['new_facts'])}")
        if len(digest['new_facts']) > 0:
            print("\nSample facts:")
            for j, fact in enumerate(digest['new_facts'][:2]):  # Print just first 2 facts
                print(f"  Fact {j}:")
                print(f"    Key: {fact.get('key')}")
                print(f"    Value: {fact.get('value')}")
                print(f"    Importance: {fact.get('importance', 'N/A')}")
                print(f"    Topic: {fact.get('topic', 'N/A')}")
                print(f"    Segments: {fact.get('segmentIndexes', [])}")
            if len(digest['new_facts']) > 2:
                print(f"  ... ({len(digest['new_facts']) - 2} more facts)")
        
        # Print relationships
        print(f"\nExtracted Relationships: {len(digest['new_relationships'])}")
        if len(digest['new_relationships']) > 0:
            print("\nSample relationships:")
            for j, rel in enumerate(digest['new_relationships'][:2]):  # Print just first 2 relationships
                print(f"  Relationship {j}:")
                print(f"    Subject: {rel.get('subject')}")
                print(f"    Predicate: {rel.get('predicate')}")
                print(f"    Object: {rel.get('object')}")
                print(f"    Importance: {rel.get('importance', 'N/A')}")
                print(f"    Topic: {rel.get('topic', 'N/A')}")
                print(f"    Segments: {rel.get('segmentIndexes', [])}")
            if len(digest['new_relationships']) > 2:
                print(f"  ... ({len(digest['new_relationships']) - 2} more relationships)")
    
    print_section_header("Example Complete")

if __name__ == "__main__":
    main() 