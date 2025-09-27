#!/usr/bin/env python3
"""
Concurrent CLI with heartbeat, background LLM processing, and user input.
Demonstrates true async concurrency with non-blocking operations.
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

class PoemCLI:
    def __init__(self):
        self.running = True
        self.llm_service = OllamaService({
            "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.environ.get("OLLAMA_MODEL", "gemma3"),
            "temperature": 0.8,
            "stream": False
        })
        self.poem_count = 0
        self.current_status = "Starting up..."
        self.last_poem_topic = None
        self.start_time = datetime.now()
        
    async def heartbeat(self):
        """Print heartbeat every second."""
        heartbeat_count = 0
        while self.running:
            heartbeat_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            uptime = (datetime.now() - self.start_time).total_seconds()
            print(f"=� [{timestamp}] Beat #{heartbeat_count} ({uptime:.0f}s) - {self.current_status}")
            await asyncio.sleep(1)
    
    async def generate_poems(self):
        """Generate poems continuously in background."""
        topics = [
            "nature", "technology", "friendship", "adventure", "mystery", 
            "love", "space", "music", "ocean", "mountains", "coding", 
            "coffee", "rain", "sunset", "books", "dreams", "time"
        ]
        topic_index = 0
        
        while self.running:
            try:
                topic = topics[topic_index % len(topics)]
                topic_index += 1
                self.last_poem_topic = topic
                
                self.current_status = f"<� Generating poem #{self.poem_count + 1} about '{topic}'..."
                
                prompt = f"""Write a short, beautiful poem about {topic}. 
Make it creative and meaningful, around 4-8 lines. 
Focus on vivid imagery and emotion."""
                
                # This will take several seconds - heartbeat continues during this time
                response = await self.llm_service.generate_async(prompt)
                
                if not self.running:  # Check if we were stopped during generation
                    break
                    
                self.poem_count += 1
                self.current_status = f" Completed {self.poem_count} poem{'s' if self.poem_count != 1 else ''}. Resting..."
                
                # Display the poem with nice formatting
                print(f"\n{'='*60}")
                print(f"<� POEM #{self.poem_count} - Topic: {topic.upper()}")
                print(f"{'='*60}")
                print()
                for line in response.strip().split('\n'):
                    if line.strip():  # Skip empty lines
                        print(f"   {line.strip()}")
                print()
                print(f"{'='*60}\n")
                
                # Wait before next poem (but can be interrupted)
                self.current_status = f"=4 Resting after poem #{self.poem_count}. Next poem in 5s..."
                for i in range(5):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
            except Exception as e:
                self.current_status = f"L Error generating poem: {str(e)[:50]}..."
                print(f"�  Error: {e}")
                # Wait before retrying
                for i in range(5):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
    
    async def user_input_handler(self):
        """Handle user commands without blocking other operations."""
        print("=' Commands available: 'status' (s), 'help' (h), 'quit' (q)")
        print("=� You can type commands at any time, even while poems are being generated!\n")
        
        while self.running:
            try:
                # Non-blocking input using asyncio
                user_input = await asyncio.to_thread(input, "Command> ")
                command = user_input.strip().lower()
                
                if command in ["quit", "q", "exit"]:
                    print("=K Shutting down gracefully...")
                    self.running = False
                    
                elif command in ["status", "s"]:
                    uptime = (datetime.now() - self.start_time).total_seconds()
                    print(f"\n=� STATUS REPORT")
                    print(f"   <� Poems generated: {self.poem_count}")
                    print(f"   <� Last topic: {self.last_poem_topic or 'None yet'}")
                    print(f"   � Current activity: {self.current_status}")
                    print(f"   =� System running: {self.running}")
                    print(f"   �  Uptime: {uptime:.0f} seconds")
                    print(f"   < LLM Model: {self.llm_service.model}")
                    print(f"   = LLM URL: {self.llm_service.base_url}")
                    print()
                    
                elif command in ["help", "h", "?"]:
                    print(f"\n=' AVAILABLE COMMANDS:")
                    print(f"   =� status (s) - Show current system status")
                    print(f"   =� quit (q)   - Exit the application gracefully") 
                    print(f"   S help (h)   - Show this help message")
                    print(f"\n=� Pro tip: You can interrupt at any time with these commands!")
                    print(f"   The heartbeat and poem generation will continue in the background.\n")
                    
                elif command == "":
                    # Just pressed enter, ignore
                    continue
                    
                else:
                    print(f"S Unknown command: '{command}'. Type 'help' for available commands.")
                    
            except EOFError:
                # Handle Ctrl+D
                print("\n=K EOF received, shutting down...")
                self.running = False
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\n=K Interrupt received, shutting down...")
                self.running = False
            except Exception as e:
                print(f"�  Input error: {e}")
    
    async def run(self):
        """Run all concurrent tasks."""
        print("=� POEM CLI - Concurrent Async Demo")
        print("="*50)
        print("<� This demonstrates true async concurrency:")
        print("   =� Heartbeat prints every second")
        print("   <� Poems generate continuously (takes 10-30 seconds each)")
        print("   (  User commands work instantly at any time")
        print("   = All operations are truly concurrent and non-blocking")
        print()
        print("< LLM Configuration:")
        print(f"   Model: {self.llm_service.model}")
        print(f"   URL: {self.llm_service.base_url}")
        print()
        
        try:
            # Start all tasks concurrently
            await asyncio.gather(
                self.heartbeat(),
                self.generate_poems(), 
                self.user_input_handler(),
                return_exceptions=True
            )
        except Exception as e:
            print(f"=� Unexpected error in main loop: {e}")
        finally:
            print("\n All tasks completed. Goodbye!")

async def main():
    # Check environment
    if not os.environ.get("OLLAMA_BASE_URL"):
        print("�  Note: OLLAMA_BASE_URL not set, using default localhost:11434")
    if not os.environ.get("OLLAMA_MODEL"):
        print("�  Note: OLLAMA_MODEL not set, using default 'gemma3'")
    
    cli = PoemCLI()
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n=K Keyboard interrupt - Goodbye!")
    except Exception as e:
        print(f"=� Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)