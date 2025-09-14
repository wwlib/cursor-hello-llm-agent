#!/usr/bin/env python3
"""
Test Ollama Streaming with Enhanced Logging

This script tests the enhanced OllamaService with streaming and verbose logging
to monitor LLM call progress and queue behavior.
"""

import asyncio
import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai.llm_ollama import OllamaService

async def test_ollama_streaming():
    """Test Ollama streaming with verbose logging."""
    
    # Set up logging to console
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create OllamaService with debug enabled
    ollama_service = OllamaService({
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "debug": True,
        "debug_scope": "test_streaming",
        "console_output": True  # Enable console output for debug logs
    })
    
    print("=== Testing Ollama Streaming with Enhanced Logging ===")
    
    # Test single request
    print("\n1. Testing single streaming request...")
    try:
        response = await ollama_service.generate_async(
            "Write a short story about a robot learning to paint. Keep it under 200 words.",
            debug_generate_scope="single_request"
        )
        print(f"✅ Single request completed: {len(response)} characters")
        print(f"Response preview: {response[:100]}...")
    except Exception as e:
        print(f"❌ Single request failed: {e}")
    
    # Test concurrent requests to see queueing behavior
    print("\n2. Testing concurrent requests (should show queueing behavior)...")
    try:
        tasks = []
        prompts = [
            "Describe a sunset in 50 words.",
            "Explain quantum physics in simple terms in 50 words.", 
            "Write a haiku about coffee."
        ]
        
        # Start all tasks simultaneously
        for i, prompt in enumerate(prompts):
            task = asyncio.create_task(
                ollama_service.generate_async(
                    prompt,
                    debug_generate_scope=f"concurrent_{i+1}"
                )
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        print("✅ All concurrent requests completed:")
        for i, result in enumerate(results):
            print(f"   Task {i+1}: {len(result)} characters")
            
    except Exception as e:
        print(f"❌ Concurrent requests failed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_ollama_streaming())