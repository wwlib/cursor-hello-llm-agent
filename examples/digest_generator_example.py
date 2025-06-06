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
    rate_template_path = os.path.join(template_dir, "rate_segments.prompt")
    
    if not os.path.exists(segment_template_path) or not os.path.exists(rate_template_path):
        print(f"Error: Template files not found. Please ensure they exist at:")
        print(f"  - {segment_template_path}")
        print(f"  - {rate_template_path}")
        return
    
    # Initialize LLM service
    print("Initializing LLM service...")
    llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "llama3",
        "temperature": 0.7,
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
            "role": "agent",
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
            "role": "agent",
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
        
        # Print rated segments
        print(f"\nRated Segments: {len(digest['rated_segments'])}")
        if len(digest['rated_segments']) > 0:
            print("\nFirst 3 segments:")
            for j, segment in enumerate(digest['rated_segments'][:3]):
                print(f"  {j}: {segment['text']}")
                print(f"     Importance: {segment['importance']}")
                print(f"     Topics: {segment['topics']}")
                print(f"     Type: {segment['type']}")
            if len(digest['rated_segments']) > 3:
                print(f"  ... ({len(digest['rated_segments']) - 3} more segments)")
    
    print_section_header("Example Complete")

if __name__ == "__main__":
    main() 