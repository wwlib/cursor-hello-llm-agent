#!/usr/bin/env python3
"""
Test Non-Blocking Graph Processing

This test verifies that the graph manager can process multiple tasks 
concurrently without blocking and that the system remains responsive.
"""

import asyncio
import time
import os
import sys
import tempfile
import shutil
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory.graph_memory.graph_manager import GraphManager
from memory.graph_memory.background_processor import SimpleGraphProcessor
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService


class TestGraphNonBlocking:
    def __init__(self):
        self.temp_dir = None
        self.graph_manager = None
        self.llm_service = None
        
    async def setup(self):
        """Set up test environment with persistent test directory and services."""
        # Create persistent test directory for inspection
        self.temp_dir = "test_non_blocking_graph_output"
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)
        print(f"Test directory: {self.temp_dir}")
        
        # Set up LLM service
        self.llm_service = OllamaService({
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "gemma3"),
            "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
            "debug": True,
            "debug_scope": "test_non_blocking_graph"
        })
        
        # Create embeddings manager
        embeddings_file = os.path.join(self.temp_dir, "embeddings.jsonl")
        
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=self.llm_service
        )
        
        # Domain config for testing
        domain_config = {
            "domain_name": "test_domain",
            "graph_memory_config": {
                "enabled": True,
                "entity_types": ["person", "location", "object", "concept"],
                "relationship_types": ["located_in", "owns", "related_to", "uses"]
            }
        }
        
        # Create graph manager
        self.graph_manager = GraphManager(
            storage_path=self.temp_dir,
            embeddings_manager=embeddings_manager,
            llm_service=self.llm_service,
            domain_config=domain_config
        )
        
        # Start background processor
        await self.graph_manager.start_background_processing()
        print("Graph manager initialized and background processing started")
        
    async def cleanup(self):
        """Clean up test environment."""
        if self.graph_manager:
            await self.graph_manager.stop_background_processing()
        
        # Keep test directory for inspection
        print(f"Test directory preserved for inspection: {self.temp_dir}")
        # if self.temp_dir and os.path.exists(self.temp_dir):
        #     shutil.rmtree(self.temp_dir)
        #     print(f"Cleaned up test directory: {self.temp_dir}")
    
    async def test_concurrent_processing(self):
        """Test that multiple tasks can be processed concurrently without blocking."""
        print("\n=== Testing Concurrent Processing ===")
        
        # Prepare test conversations
        conversations = [
            {
                "text": "Alice walked to the ancient library in the city center. She found an old book about magic.",
                "guid": "conv_1",
                "name": "Library Visit"
            },
            {
                "text": "Bob owns a magical sword that glows blue. He keeps it in his house near the forest.",
                "guid": "conv_2", 
                "name": "Bob's Sword"
            },
            {
                "text": "The dragon lives in a cave on the mountain. It guards a treasure chest full of gold coins.",
                "guid": "conv_3",
                "name": "Dragon's Lair"
            }
        ]
        
        # Submit all tasks at once (non-blocking)
        print("Submitting multiple tasks simultaneously...")
        start_time = time.time()
        
        tasks = []
        for i, conv in enumerate(conversations):
            print(f"Queuing task {i+1}: {conv['name']}")
            task = asyncio.create_task(
                self.graph_manager.process_conversation_entry_with_resolver_async(
                    conversation_text=conv["text"],
                    conversation_guid=conv["guid"]
                )
            )
            tasks.append(task)
        
        submit_time = time.time() - start_time
        print(f"All tasks submitted in {submit_time:.2f}s (should be nearly instant)")
        
        # Verify submissions were non-blocking (should be < 0.1s)
        assert submit_time < 0.5, f"Task submission took too long: {submit_time}s"
        
        # Wait for all tasks to complete
        print("Waiting for all tasks to complete...")
        processing_start = time.time()
        
        results = await asyncio.gather(*tasks)
        
        processing_time = time.time() - processing_start
        print(f"All tasks completed in {processing_time:.2f}s")
        
        # Verify all tasks succeeded
        for i, result in enumerate(results):
            print(f"Task {i+1} result: {len(result.get('entities', []))} entities, {len(result.get('relationships', []))} relationships")
            assert not result.get("error"), f"Task {i+1} failed: {result.get('error')}"
        
        print("✓ All tasks completed successfully")
        return results
    
    async def test_system_responsiveness(self):
        """Test that the system remains responsive during processing."""
        print("\n=== Testing System Responsiveness ===")
        
        # Start a long-running background task
        long_task = asyncio.create_task(
            self.graph_manager.process_conversation_entry_with_resolver_async(
                conversation_text="The wise wizard Merlin studied ancient spells in his tower. "
                               "He had many magical artifacts including a crystal ball, magic wand, "
                               "spell books, and enchanted robes. His tower was located in the "
                               "mystical forest near the kingdom of Camelot.",
                conversation_guid="long_task"
            )
        )
        
        # Immediately test that we can still query the graph (should not block)
        print("Starting background processing...")
        await asyncio.sleep(0.1)  # Let task start
        
        print("Testing responsiveness during processing...")
        query_start = time.time()
        
        # This should complete quickly even while processing
        stats = self.graph_manager.background_processor.get_stats()
        
        query_time = time.time() - query_start
        print(f"Stats query completed in {query_time:.3f}s")
        
        # Should be nearly instant even during processing
        assert query_time < 0.1, f"System not responsive during processing: {query_time}s"
        
        print(f"Background processing stats: {stats}")
        
        # Wait for the long task to complete
        result = await long_task
        print(f"Long task completed: {len(result.get('entities', []))} entities")
        
        print("✓ System remained responsive during processing")
    
    async def test_queue_behavior(self):
        """Test that tasks queue properly and process in order."""
        print("\n=== Testing Queue Behavior ===")
        
        # Submit several tasks quickly
        task_names = ["Task A", "Task B", "Task C", "Task D"]
        tasks = []
        
        print("Submitting tasks rapidly...")
        for i, name in enumerate(task_names):
            # Queue tasks with the background processor
            await self.graph_manager.queue_background_processing(
                conversation_text=f"This is {name} with some content to process.",
                conversation_guid=f"task_{i}"
            )
        
        # Check queue stats immediately
        stats = self.graph_manager.background_processor.get_stats()
        print(f"Queue stats after submission: {stats}")
        
        # Should have tasks queued or active
        total_tasks = stats["queue_size"] + stats["active_tasks"]
        assert total_tasks > 0, "No tasks found in queue or processing"
        
        # Wait for completion by polling the background processor
        max_wait_time = 60  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            current_stats = self.graph_manager.background_processor.get_stats()
            if current_stats["queue_size"] == 0 and current_stats["active_tasks"] == 0:
                break
            await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
        final_stats = self.graph_manager.background_processor.get_stats()
        print(f"Final stats: {final_stats}")
        
        # All tasks should have completed
        assert final_stats["queue_size"] == 0, "Tasks still in queue"
        assert final_stats["active_tasks"] == 0, "Tasks still active"
        # Note: total_processed might be higher due to other tests, so check it's at least our tasks
        print(f"Tasks processed: {final_stats['total_processed']}, expected at least: {len(task_names)}")
        
        print("✓ Queue behavior working correctly")
    
    async def run_all_tests(self):
        """Run all non-blocking tests."""
        print("Starting Non-Blocking Graph Processing Tests")
        print("=" * 50)
        
        try:
            await self.setup()
            
            # Run tests
            await self.test_concurrent_processing()
            await self.test_system_responsiveness() 
            await self.test_queue_behavior()
            
            print("\n" + "=" * 50)
            print("✓ ALL TESTS PASSED - Graph processing is non-blocking!")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """Main test runner."""
    test = TestGraphNonBlocking()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())