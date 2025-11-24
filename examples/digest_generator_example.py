#!/usr/bin/env python3

"""
Example demonstrating the DigestGenerator class.

This example shows how to:
1. Initialize DigestGenerator with default settings
2. Initialize DigestGenerator with domain-specific configuration
3. Generate digests from conversation entries
4. View the structured output (segments, importance, topics, types)
"""

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

from src.utils.logging_config import LoggingConfig
from src.ai.llm_ollama import OllamaService
from src.memory.digest_generator import DigestGenerator
from examples.domain_configs import DND_CONFIG

# Constants - use environment variables with sensible defaults
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3")
EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Use a fixed example GUID for this standalone example
EXAMPLE_GUID = "digest_generator_example"

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
    
    # Set up logging using LoggingConfig
    print("Setting up logging...")
    llm_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID, 
        "ollama_digest_example", 
        log_to_console=False
    )
    digest_logger = LoggingConfig.get_component_file_logger(
        EXAMPLE_GUID,
        "digest_generator_example",
        log_to_console=False
    )
    
    # Initialize LLM service with proper logging
    print(f"Initializing LLM service (Ollama at {BASE_URL})...")
    llm_service = OllamaService({
        "base_url": BASE_URL,
        "model": MODEL,
        "temperature": 0,  # Lower temperature for more consistent digest generation
        "stream": False,
        "logger": llm_logger
    })
    
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
    
    # Display conversation entries
    for i, entry in enumerate(conversation_entries):
        print(f"\nEntry {i+1} - {entry['role']}:")
        print("-" * 40)
        print(entry['content'][:100] + "...")  # Print just the first 100 chars to save space
    
    # Example 1: Default DigestGenerator (general domain)
    print_section_header("Example 1: Default DigestGenerator (General Domain)")
    
    print("Creating DigestGenerator with default settings (general domain)...")
    default_digest_generator = DigestGenerator(
        llm_service,
        domain_name="general",
        logger=digest_logger
    )
    
    print("\nProcessing first entry with default generator...")
    entry = conversation_entries[0]
    digest = default_digest_generator.generate_digest(entry)
    
    print(f"\nDigest for entry 1 ({entry['role']}):")
    print("-" * 40)
    print(f"Rated Segments: {len(digest['rated_segments'])}")
    if len(digest['rated_segments']) > 0:
        print("\nFirst 3 segments:")
        for j, segment in enumerate(digest['rated_segments'][:3]):
            print(f"  {j+1}. {segment['text'][:80]}...")
            print(f"     Importance: {segment['importance']}/5")
            print(f"     Topics: {segment['topics']}")
            print(f"     Type: {segment['type']}")
        if len(digest['rated_segments']) > 3:
            print(f"  ... ({len(digest['rated_segments']) - 3} more segments)")
    
    # Example 2: Domain-specific DigestGenerator (D&D Campaign)
    print_section_header("Example 2: Domain-Specific DigestGenerator (D&D Campaign)")
    
    print("Creating DigestGenerator with D&D campaign domain configuration...")
    dnd_digest_generator = DigestGenerator(
        llm_service,
        domain_name="dnd_campaign",
        domain_config=DND_CONFIG,
        logger=digest_logger
    )
    
    print("\nProcessing all entries with D&D domain generator...")
    for i, entry in enumerate(conversation_entries):
        print(f"\nGenerating digest for entry {i+1} - {entry['role']}...")
        
        digest = dnd_digest_generator.generate_digest(entry)
        
        print(f"\nDigest for entry {i+1} - {entry['role']}:")
        print("-" * 40)
        
        # Print rated segments
        print(f"Rated Segments: {len(digest['rated_segments'])}")
        if len(digest['rated_segments']) > 0:
            print("\nFirst 3 segments:")
            for j, segment in enumerate(digest['rated_segments'][:3]):
                print(f"  {j+1}. {segment['text'][:80]}...")
                print(f"     Importance: {segment['importance']}/5")
                print(f"     Topics: {segment['topics']}")
                print(f"     Type: {segment['type']}")
                if 'memory_worthy' in segment:
                    print(f"     Memory Worthy: {segment['memory_worthy']}")
            if len(digest['rated_segments']) > 3:
                print(f"  ... ({len(digest['rated_segments']) - 3} more segments)")
    
    # Show full JSON output for one digest
    print_section_header("Full JSON Output Example")
    print("Complete digest structure (first entry):")
    print_json(digest)
    
    print_section_header("Example Complete")
    print(f"\nLogs saved to: {LoggingConfig.get_log_base_dir(EXAMPLE_GUID)}")
    print("\nNote: Domain-specific configuration (D&D) provides more relevant")
    print("topic assignments compared to the general domain configuration.")

if __name__ == "__main__":
    main()