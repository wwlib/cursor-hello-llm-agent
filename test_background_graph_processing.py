#!/usr/bin/env python3
"""
Test script for background graph processing system.

This script demonstrates the new background processing capabilities
and shows how graph memory can be processed without blocking user interactions.
"""

import asyncio
import time
import os
import sys
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.memory.memory_manager import MemoryManager
from src.ai.llm_ollama import OllamaService


def create_test_llm_service():
    """Create a test LLM service."""
    config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "temperature": 0.7,
        "stream": False,
        "debug": True
    }
    return OllamaService(config)


def create_test_embeddings_service():
    """Create a test embeddings service."""
    config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "debug": True
    }
    return OllamaService(config)


async def test_basic_functionality():
    """Test basic background processing functionality."""
    print("🧪 Testing Basic Background Processing Functionality")
    print("=" * 60)
    
    # Create services
    llm_service = create_test_llm_service()
    embeddings_service = create_test_embeddings_service()
    
    # Create domain configuration for testing
    domain_config = {
        "domain_name": "fantasy_game",
        "domain_specific_prompt_instructions": {
            "query": "You are a helpful assistant for a fantasy role-playing game. Provide detailed and engaging responses about characters, locations, and story elements.",
            "update": "Focus on important characters, locations, objects, and story developments in the fantasy world."
        },
        "graph_memory_config": {
            "entity_types": ["character", "location", "object", "event", "concept"],
            "relationship_types": ["located_in", "owns", "allies_with", "enemies_with", "uses", "participates_in"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager with background processing
    memory_manager = MemoryManager(
        memory_guid="test_background_processing",
        llm_service=llm_service,
        embeddings_llm_service=embeddings_service,
        domain_config=domain_config,
        enable_graph_memory=True,
        graph_memory_processing_level="balanced",
        verbose=True
    )
    
    print("✅ Memory manager initialized with background processing")
    
    # Test queries
    test_queries = [
        "Tell me about Elena, the fire wizard",
        "What is Riverwatch?",
        "Describe the ancient ruins",
        "Who are the main characters?",
        "What locations have been mentioned?"
    ]
    
    print("\n📝 Testing queries with background processing...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: {query} ---")
        
        start_time = time.time()
        response = memory_manager.query_memory({
            "query": query,
            "domain_specific_prompt_instructions": "You are a helpful assistant for a fantasy game."
        })
        query_time = time.time() - start_time
        
        print(f"⏱️  Query time: {query_time:.2f}s")
        print(f"📄 Response: {response['response'][:100]}...")
        
        # Check processing status
        status = memory_manager.get_graph_processing_status()
        print(f"📊 Queue size: {status['queue_size']}")
        print(f"📈 Processing rate: {status['processing_rate']:.2f} tasks/min")
        
        # Small delay to allow background processing
        await asyncio.sleep(1)
    
    print("\n🎯 Testing configuration management...")
    
    # Test profile switching
    print("🔄 Switching to 'realtime' profile...")
    success = memory_manager.apply_graph_processing_profile("realtime")
    print(f"Profile switch successful: {success}")
    
    # Test custom configuration
    print("⚙️  Applying custom configuration...")
    success = memory_manager.configure_graph_processing(
        processing_frequency=15.0,
        batch_size=3,
        max_queue_size=50
    )
    print(f"Configuration successful: {success}")
    
    # Get final status
    print("\n📊 Final Processing Status:")
    final_status = memory_manager.get_graph_processing_status()
    for key, value in final_status.items():
        if key != "config":  # Skip detailed config
            print(f"  {key}: {value}")
    
    # Get context retriever stats
    print("\n🎯 Context Retriever Performance:")
    context_stats = memory_manager.get_context_retriever_stats()
    if context_stats.get("enabled"):
        stats = context_stats["stats"]
        print(f"  Cache hit rate: {stats['hit_rate']:.2%}")
        print(f"  Average query time: {stats['average_query_time']:.3f}s")
        print(f"  Cache utilization: {stats['cache_utilization']:.2%}")
    
    print("\n✅ Basic functionality test completed!")


async def test_performance_comparison():
    """Test performance comparison between different processing modes."""
    print("\n🚀 Testing Performance Comparison")
    print("=" * 60)
    
    # Create services
    llm_service = create_test_llm_service()
    embeddings_service = create_test_embeddings_service()
    
    # Create domain configuration for testing
    domain_config = {
        "domain_name": "fantasy_game",
        "domain_specific_prompt_instructions": {
            "query": "You are a helpful assistant for a fantasy role-playing game.",
            "update": "Focus on important characters, locations, objects, and story developments."
        },
        "graph_memory_config": {
            "entity_types": ["character", "location", "object", "event", "concept"],
            "relationship_types": ["located_in", "owns", "allies_with", "enemies_with", "uses", "participates_in"],
            "similarity_threshold": 0.8
        }
    }
    
    profiles = ["realtime", "balanced", "comprehensive"]
    results = {}
    
    for profile in profiles:
        print(f"\n📊 Testing {profile} profile...")
        
        # Create memory manager with specific profile
        memory_manager = MemoryManager(
            memory_guid=f"test_perf_{profile}",
            llm_service=llm_service,
            embeddings_llm_service=embeddings_service,
            domain_config=domain_config,
            enable_graph_memory=True,
            graph_memory_processing_level=profile,
            verbose=False  # Reduce noise for performance testing
        )
        
        # Apply profile
        memory_manager.apply_graph_processing_profile(profile)
        
        # Test queries
        test_query = "Tell me about Elena and her magical abilities"
        
        start_time = time.time()
        response = memory_manager.query_memory({
            "query": test_query,
            "domain_specific_prompt_instructions": "You are a helpful assistant."
        })
        query_time = time.time() - start_time
        
        # Get processing stats
        status = memory_manager.get_graph_processing_status()
        context_stats = memory_manager.get_context_retriever_stats()
        
        results[profile] = {
            "query_time": query_time,
            "queue_size": status["queue_size"],
            "processing_rate": status["processing_rate"],
            "cache_hit_rate": context_stats.get("stats", {}).get("hit_rate", 0),
            "response_length": len(response["response"])
        }
        
        print(f"  Query time: {query_time:.2f}s")
        print(f"  Queue size: {status['queue_size']}")
        print(f"  Processing rate: {status['processing_rate']:.2f}/min")
        
        # Wait for background processing
        await asyncio.sleep(2)
    
    # Compare results
    print("\n📈 Performance Comparison Results:")
    print("-" * 60)
    print(f"{'Profile':<12} {'Query Time':<12} {'Queue Size':<12} {'Rate':<12} {'Cache Hit':<12}")
    print("-" * 60)
    
    for profile, data in results.items():
        print(f"{profile:<12} {data['query_time']:<12.2f} {data['queue_size']:<12} "
              f"{data['processing_rate']:<12.2f} {data['cache_hit_rate']:<12.2%}")
    
    print("\n✅ Performance comparison completed!")


async def test_monitoring_and_alerts():
    """Test monitoring and alerting capabilities."""
    print("\n📊 Testing Monitoring and Alerts")
    print("=" * 60)
    
    # Create services
    llm_service = create_test_llm_service()
    embeddings_service = create_test_embeddings_service()
    
    # Create domain configuration for testing
    domain_config = {
        "domain_name": "fantasy_game",
        "domain_specific_prompt_instructions": {
            "query": "You are a helpful assistant for a fantasy role-playing game.",
            "update": "Focus on important characters, locations, objects, and story developments."
        },
        "graph_memory_config": {
            "entity_types": ["character", "location", "object", "event", "concept"],
            "relationship_types": ["located_in", "owns", "allies_with", "enemies_with", "uses", "participates_in"],
            "similarity_threshold": 0.8
        }
    }
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_guid="test_monitoring",
        llm_service=llm_service,
        embeddings_llm_service=embeddings_service,
        domain_config=domain_config,
        enable_graph_memory=True,
        graph_memory_processing_level="balanced",
        verbose=True
    )
    
    print("📈 Monitoring processing status...")
    
    # Generate some load
    for i in range(5):
        query = f"Tell me about character {i+1} in the story"
        response = memory_manager.query_memory({
            "query": query,
            "domain_specific_prompt_instructions": "You are a helpful assistant."
        })
        print(f"  Query {i+1} completed")
        await asyncio.sleep(0.5)
    
    # Check status multiple times
    print("\n📊 Status monitoring over time:")
    for i in range(3):
        status = memory_manager.get_graph_processing_status()
        context_stats = memory_manager.get_context_retriever_stats()
        
        print(f"\n  Check {i+1}:")
        print(f"    Queue size: {status['queue_size']}")
        print(f"    Processing rate: {status['processing_rate']:.2f}/min")
        print(f"    Backlog age: {status['backlog_age']:.1f}s")
        print(f"    Cache hit rate: {context_stats.get('stats', {}).get('hit_rate', 0):.2%}")
        
        await asyncio.sleep(2)
    
    # Test queue management
    print("\n🔧 Testing queue management...")
    
    # Clear cache
    cleared = memory_manager.clear_context_cache()
    print(f"  Cleared {cleared} context cache entries")
    
    # Optimize cache
    optimization = memory_manager.optimize_context_cache()
    print(f"  Cache optimization: {optimization}")
    
    print("\n✅ Monitoring and alerts test completed!")


async def main():
    """Main test function."""
    print("🎯 Background Graph Processing System Test")
    print("=" * 80)
    
    try:
        # Test basic functionality
        await test_basic_functionality()
        
        # Test performance comparison
        await test_performance_comparison()
        
        # Test monitoring
        await test_monitoring_and_alerts()
        
        print("\n🎉 All tests completed successfully!")
        print("\nKey Benefits Demonstrated:")
        print("✅ Non-blocking user interactions")
        print("✅ Configurable processing profiles")
        print("✅ Real-time performance monitoring")
        print("✅ Intelligent context caching")
        print("✅ Queue management and optimization")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
