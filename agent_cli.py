#!/usr/bin/env python3
"""
Concurrent Agent CLI with proper memory system integration.
Uses the poem_cli.py architecture pattern for robust async processing.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.agent.agent import Agent
from examples.domain_configs import CONFIG_MAP

class AgentCLI:
    def __init__(self, domain_config_name="lab_assistant"):
        self.running = True
        self.start_time = datetime.now()
        
        # Get domain config
        if domain_config_name not in CONFIG_MAP:
            raise ValueError(f"Unknown domain config: {domain_config_name}. Available: {list(CONFIG_MAP.keys())}")
        self.domain_config = CONFIG_MAP[domain_config_name]
        
        # Processing queues for background operations
        self.embedding_queue = asyncio.Queue()
        self.graph_queue = asyncio.Queue()
        self.compression_queue = asyncio.Queue()
        
        # Status tracking
        self.embeddings_processed = 0
        self.graphs_processed = 0
        self.compressions_processed = 0
        self.queries_processed = 0
        
        # Current activity tracking
        self.current_activity = "Starting up..."
        self.current_user_query = None
        self.last_agent_response = None
        
        # Initialize services and components
        self.llm_service = None
        self.memory_manager = None
        self.agent = None
        
    async def initialize_services(self):
        """Initialize all services and components."""
        print("🔧 Initializing services...")
        
        # Create LLM services
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "gemma3")
        embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
        
        self.llm_service = OllamaService({
            "base_url": base_url,
            "model": model,
            "temperature": 0.7,
            "stream": False
        })
        
        digest_llm_service = OllamaService({
            "base_url": base_url,
            "model": model,
            "temperature": 0,
            "stream": False
        })
        
        embeddings_llm_service = OllamaService({
            "base_url": base_url,
            "model": embed_model
        })
        
        # Create memory manager with all components
        test_guid = f"agent_cli_{datetime.now().strftime('%m%d_%H%M')}"
        memory_file = f"agent_memories/standard/{test_guid}/agent_memory.json"
        
        # Ensure directory exists  
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        self.memory_manager = MemoryManager(
            memory_guid=test_guid,
            memory_file=memory_file,
            domain_config=self.domain_config,
            llm_service=self.llm_service,
            digest_llm_service=digest_llm_service,
            embeddings_llm_service=embeddings_llm_service,
            enable_graph_memory=True,
            graph_memory_processing_level="balanced"
        )
        
        # Create agent
        self.agent = Agent(
            llm_service=self.llm_service,
            memory_manager=self.memory_manager,
            domain_name=self.domain_config['domain_name']
        )
        
        print("✅ Services initialized")
        
        # Initialize memory
        print("🧠 Initializing memory...")
        self.current_activity = "Initializing memory..."
        success = self.memory_manager.create_initial_memory(self.domain_config.get("initial_data", ""))
        
        if success:
            print("✅ Memory initialized")
            self.current_activity = "Ready for queries"
        else:
            print("❌ Memory initialization failed")
            self.current_activity = "Memory initialization failed"
        
    async def heartbeat(self):
        """Monitor system status every 2 seconds."""
        heartbeat_count = 0
        while self.running:
            heartbeat_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            # Get queue sizes
            embed_q = self.embedding_queue.qsize()
            graph_q = self.graph_queue.qsize() 
            compress_q = self.compression_queue.qsize()
            
            # Check memory manager status
            memory_busy = self.memory_manager.has_pending_operations() if self.memory_manager else False
            
            print(f"💓 [{timestamp}] Beat #{heartbeat_count} ({uptime:.0f}s) - {self.current_activity}")
            print(f"   📊 Processed: Q:{self.queries_processed} E:{self.embeddings_processed} G:{self.graphs_processed} C:{self.compressions_processed}")
            print(f"   📋 Queued: E:{embed_q} G:{graph_q} C:{compress_q} | Memory:{'busy' if memory_busy else 'idle'}")
            
            await asyncio.sleep(2)
    
    async def process_embeddings_continuously(self):
        """Process embeddings for semantic search in background."""
        while self.running:
            try:
                # Wait for embedding work
                task_data = await self.embedding_queue.get()
                
                self.current_activity = f"🔍 Processing embeddings for {task_data['conversation_id']}"
                
                # Process embeddings through MemoryManager digest generation
                # This will generate segments and add them to embeddings
                conversation_entry = {
                    'text': task_data['conversation_text'],
                    'guid': task_data['conversation_id'],
                    'timestamp': datetime.now().isoformat()
                }
                
                if hasattr(self.memory_manager, 'digest_generator'):
                    # Generate digest which includes segment processing
                    digest_data = self.memory_manager.digest_generator.generate_digest(
                        conversation_entry,
                        self.memory_manager.memory
                    )
                    
                    # Extract segments from digest and add to embeddings
                    if hasattr(self.memory_manager, 'embeddings_manager') and 'segments' in digest_data:
                        important_segments = [s for s in digest_data['segments'] 
                                            if s.get('importance', 0) >= 3 and s.get('memory_worthy', True)]
                        if important_segments:
                            for segment in important_segments:
                                self.memory_manager.embeddings_manager.add_embedding(
                                    segment['text'],
                                    {
                                        'conversation_id': task_data['conversation_id'],
                                        'segment_data': segment
                                    }
                                )
                
                self.embeddings_processed += 1
                self.current_activity = "Ready for queries"
                
            except Exception as e:
                print(f"⚠️ Embeddings error: {e}")
                self.current_activity = f"❌ Embeddings error: {str(e)[:30]}..."
                await asyncio.sleep(1)
    
    async def process_graph_continuously(self):
        """Process graph memory updates in background.""" 
        while self.running:
            try:
                # Wait for graph work
                task_data = await self.graph_queue.get()
                
                self.current_activity = f"🌐 Processing graph for {task_data['guid']}"
                
                # Process using GraphManager directly (no background processor)
                if hasattr(self.memory_manager, 'graph_manager') and self.memory_manager.graph_manager:
                    result = await self.memory_manager.graph_manager.process_conversation_entry_with_resolver_async(
                        conversation_text=task_data['text'],
                        digest_text=task_data.get('digest', ''),
                        conversation_guid=task_data['guid']
                    )
                    
                    entities = len(result.get('entities', []))
                    relationships = len(result.get('relationships', []))
                    print(f"   ✅ Graph processed: {entities} entities, {relationships} relationships")
                
                self.graphs_processed += 1
                self.current_activity = "Ready for queries"
                
            except Exception as e:
                print(f"⚠️ Graph processing error: {e}")
                self.current_activity = f"❌ Graph error: {str(e)[:30]}..."
                await asyncio.sleep(1)
    
    async def process_compression_continuously(self):
        """Handle memory compression operations in background."""
        while self.running:
            try:
                # Wait for compression work
                task_data = await self.compression_queue.get()
                
                self.current_activity = f"🗜️ Compressing {len(task_data['conversations'])} conversations"
                
                # Use MemoryCompressor through MemoryManager
                if hasattr(self.memory_manager, 'memory_compressor'):
                    compressed_context = await self.memory_manager.memory_compressor.compress_conversations_async(
                        task_data['conversations'],
                        task_data['importance_threshold']
                    )
                    
                    # Update memory with compressed context
                    if hasattr(self.memory_manager, '_update_compressed_context_async'):
                        await self.memory_manager._update_compressed_context_async(compressed_context)
                
                self.compressions_processed += 1
                self.current_activity = "Ready for queries"
                
            except Exception as e:
                print(f"⚠️ Compression error: {e}")
                self.current_activity = f"❌ Compression error: {str(e)[:30]}..."
                await asyncio.sleep(1)
    
    async def user_interaction_handler(self):
        """Handle user queries and agent responses."""
        print(f"🤖 Agent CLI ready! Domain: {self.domain_config['domain_name']}")
        print("Commands: 'status' (s), 'help' (h), 'quit' (q)")
        print("💡 Ask any question - all memory processing happens in background!\n")
        
        while self.running:
            try:
                # Non-blocking user input
                user_input = await asyncio.to_thread(input, "You: ")
                command = user_input.strip().lower()
                
                if command in ['quit', 'exit', 'q']:
                    print("👋 Shutting down agent...")
                    self.running = False
                    continue
                
                if command in ['status', 's']:
                    await self._show_detailed_status()
                    continue
                
                if command in ['help', 'h', '?']:
                    await self._show_help()
                    continue
                
                if command == '':
                    continue
                
                # Process query with agent
                self.current_user_query = user_input
                self.current_activity = f"🤖 Processing: '{user_input[:30]}...'"
                
                print("🔄 Processing query...")
                
                # Agent processes query (uses MemoryManager.query_memory which calls RAGManager internally)
                response_data = self.memory_manager.query_memory({"query": user_input})
                response = response_data.get('response', 'No response generated')
                
                self.last_agent_response = response
                self.queries_processed += 1
                self.current_activity = "Ready for queries"
                
                print(f"\n🤖 Agent: {response}\n")
                
                # Queue background processing for this conversation
                await self._queue_background_processing(user_input, response)
                
            except EOFError:
                print("\n👋 EOF received, shutting down...")
                self.running = False
            except KeyboardInterrupt:
                print("\n👋 Interrupt received, shutting down...")
                self.running = False
            except Exception as e:
                print(f"⚠️ Query processing error: {e}")
                self.current_activity = f"❌ Query error: {str(e)[:30]}..."
    
    async def _queue_background_processing(self, user_query: str, agent_response: str):
        """Queue background processing tasks for the conversation."""
        conversation_id = f"conv_{datetime.now().timestamp()}"
        full_text = f"User: {user_query}\nAgent: {agent_response}"
        
        try:
            # Queue embeddings work - will be generated from conversation during processing
            # Skip direct segment generation since it needs digest processing
            # Embeddings processor will handle segment generation internally
            await self.embedding_queue.put({
                'conversation_text': full_text,
                'conversation_id': conversation_id
            })
            
            # Queue graph work
            await self.graph_queue.put({
                'text': full_text,
                'digest': '',  # Digest will be generated in the processor
                'guid': conversation_id
            })
            
            # Queue compression work periodically (every 5 conversations)
            if self.queries_processed % 5 == 0:
                await self.compression_queue.put({
                    'conversations': [{'text': full_text, 'timestamp': datetime.now()}],
                    'importance_threshold': 3
                })
                
        except Exception as e:
            print(f"⚠️ Background processing queue error: {e}")
    
    async def _show_detailed_status(self):
        """Show detailed system status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n📊 AGENT STATUS REPORT")
        print(f"   🤖 Domain: {self.domain_config['domain_name']}")
        print(f"   ⏱️  Uptime: {uptime:.0f} seconds")
        print(f"   ⚡ Current activity: {self.current_activity}")
        print(f"   🔢 Queries processed: {self.queries_processed}")
        print(f"   🔍 Embeddings processed: {self.embeddings_processed}")
        print(f"   🌐 Graphs processed: {self.graphs_processed}")
        print(f"   🗜️  Compressions processed: {self.compressions_processed}")
        
        # Queue status
        embed_q = self.embedding_queue.qsize()
        graph_q = self.graph_queue.qsize()
        compress_q = self.compression_queue.qsize()
        print(f"   📋 Queued: E:{embed_q} G:{graph_q} C:{compress_q}")
        
        # Last interaction
        if self.current_user_query:
            print(f"   💬 Last query: '{self.current_user_query[:50]}...'")
        if self.last_agent_response:
            print(f"   🤖 Last response: '{self.last_agent_response[:50]}...'")
        
        # Memory manager status
        if self.memory_manager:
            memory_busy = self.memory_manager.has_pending_operations()
            print(f"   🧠 Memory: {'busy' if memory_busy else 'idle'}")
        
        print()
    
    async def _show_help(self):
        """Show help information."""
        print(f"\n🔧 AGENT CLI COMMANDS:")
        print(f"   📊 status (s) - Show detailed system status")
        print(f"   🚪 quit (q)   - Exit the agent gracefully")
        print(f"   ❓ help (h)   - Show this help message")
        print(f"\n💡 Usage Tips:")
        print(f"   • Ask any question - the agent will use RAG and graph memory")
        print(f"   • All memory processing happens in background")
        print(f"   • You can type commands while processing continues")
        print(f"   • Domain: {self.domain_config['domain_name']}")
        print()
    
    async def run(self):
        """Run all concurrent tasks."""
        print("🚀 AGENT CLI - Concurrent Memory Processing")
        print("="*60)
        print("🎯 This demonstrates concurrent agent architecture:")
        print("   💓 Heartbeat monitors all system components")
        print("   🔍 Embeddings processed for semantic search")
        print("   🌐 Graph memory updated continuously")
        print("   🗜️  Memory compression runs periodically")
        print("   🤖 Agent responds instantly using existing memory")
        print("   ⌨️  User commands work at any time")
        print()
        
        # Initialize services first
        await self.initialize_services()
        
        try:
            # Start all concurrent tasks - same pattern as poem_cli.py
            await asyncio.gather(
                self.heartbeat(),
                self.process_embeddings_continuously(),
                self.process_graph_continuously(),
                self.process_compression_continuously(), 
                self.user_interaction_handler(),
                return_exceptions=True
            )
        except Exception as e:
            print(f"💥 Unexpected error in main loop: {e}")
        finally:
            print("\n✅ All tasks completed. Agent shutdown complete!")

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent CLI with concurrent processing")
    parser.add_argument('--config', choices=['dnd', 'user_story', 'lab_assistant'], 
                       default='lab_assistant', help='Domain configuration')
    args = parser.parse_args()
    
    # Check environment
    if not os.environ.get("OLLAMA_BASE_URL"):
        print("⚠️  Note: OLLAMA_BASE_URL not set, using default localhost:11434")
    if not os.environ.get("OLLAMA_MODEL"):
        print("⚠️  Note: OLLAMA_MODEL not set, using default 'gemma3'")
    
    cli = AgentCLI(domain_config_name=args.config)
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Keyboard interrupt - Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)