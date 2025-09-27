#!/usr/bin/env python3
"""Quick agent test with the background processor fix."""

import asyncio
import os
import sys
from pathlib import Path
import json

# Add project root to path  
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from examples.domain_configs import LAB_ASSISTANT_CONFIG

# Environment setup
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3") 
EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

async def quick_test():
    """Quick test of agent with fixed background processing."""
    print("=" * 50)
    print("QUICK AGENT BACKGROUND PROCESSOR TEST")
    print("=" * 50)
    
    test_guid = "quick_bg_test_1"
    
    # Create LLM services
    general_llm = OllamaService({
        "base_url": BASE_URL,
        "model": MODEL,
        "temperature": 0.7
    })
    
    digest_llm = OllamaService({
        "base_url": BASE_URL, 
        "model": MODEL,
        "temperature": 0
    })
    
    embed_llm = OllamaService({
        "base_url": BASE_URL,
        "model": EMBEDDING_MODEL
    })
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_guid=test_guid,
        memory_file=f"agent_memories/standard/{test_guid}/agent_memory.json",
        domain_config=LAB_ASSISTANT_CONFIG,
        llm_service=general_llm,
        digest_llm_service=digest_llm,
        embeddings_llm_service=embed_llm,
        enable_graph_memory=True
    )
    
    print("Creating initial memory...")
    success = memory_manager.create_initial_memory(LAB_ASSISTANT_CONFIG["initial_data"])
    print(f"✓ Memory created: {success}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    print("Testing query...")
    response = memory_manager.query_memory({"query": "What equipment is in the lab?"})
    print(f"Response: {response.get('response', 'No response')}")
    
    # Wait for background processing
    print("Waiting for background processing...")
    await asyncio.sleep(3)
    
    # Check graph status
    if hasattr(memory_manager, 'graph_manager') and memory_manager.graph_manager:
        status = memory_manager.graph_manager.get_background_processing_status()
        print(f"Graph status: processed={status.get('total_processed', 0)}, failed={status.get('total_failed', 0)}")
        
        # Check graph files
        graph_dir = f"agent_memories/standard/{test_guid}/agent_memory_graph_data"
        try:
            with open(f"{graph_dir}/graph_metadata.json", "r") as f:
                metadata = json.load(f)
                print(f"Graph metadata: {metadata.get('node_count', 0)} nodes, {metadata.get('edge_count', 0)} edges")
        except:
            print("No graph metadata found")
            
        # Stop processing
        await memory_manager.graph_manager.stop_background_processing()
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(quick_test())