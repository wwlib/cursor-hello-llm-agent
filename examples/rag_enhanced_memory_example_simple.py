#!/usr/bin/env python3
"""
Slightly Enhanced RAG-Enhanced Memory Example

This script demonstrates a single, simple RAG-enhanced query using the same test data as the main example.
"""
import os
import json
from pathlib import Path
import tempfile
import uuid
from datetime import datetime

from src.memory.memory_manager import MemoryManager
from src.memory.embeddings_manager import EmbeddingsManager
from src.memory.rag_manager import RAGManager
from src.ai.llm_ollama import OllamaService

# --- Configuration and Test Data ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.173:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# File paths (from main example)
TEST_DATA_DIR = Path("tests/memory_manager/memory_snapshots/rag")
MEMORY_FILE = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162.json"
CONVERSATION_FILE = TEST_DATA_DIR / "agent_memory_f1ce087f-76b3-4383-865f-4179c927d162_conversations.json"

# --- Helper functions ---
def get_llm_service():
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "temperature": 0.0,
        "debug": False
    })

def get_embed_service():
    return OllamaService({
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_EMBED_MODEL,
        "debug": False
    })

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

# --- Main Test Logic ---
def main():
    # Load test data
    memory_data = load_json(MEMORY_FILE)
    conversation_data = load_json(CONVERSATION_FILE)
    static_memory = memory_data.get("static_memory", "")
    domain_config = {
        "domain_specific_prompt_instructions": memory_data.get("domain_specific_prompt_instructions", {
            "query": "You are a helpful fantasy assistant. Answer concisely and accurately.",
            "update": ""
        })
    }
    conversation_history = conversation_data.get("entries", [])

    # Use temp files for memory and embeddings
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_file = os.path.join(temp_dir, "memory.json")
        embeddings_file = os.path.join(temp_dir, "embeddings.jsonl")

        print(f"Memory file: {memory_file}")
        print(f"Embeddings file: {embeddings_file}")

        # Set up services
        llm_service = get_llm_service()
        embed_service = get_embed_service()

        # Set up managers
        memory_manager = MemoryManager(
            memory_file=memory_file,
            domain_config=domain_config,
            llm_service=llm_service,
            max_recent_conversation_entries=4,
            importance_threshold=3
        )
        embeddings_manager = EmbeddingsManager(
            embeddings_file=embeddings_file,
            llm_service=embed_service
        )
        rag_manager = RAGManager(
            llm_service=llm_service,
            embeddings_manager=embeddings_manager
        )

        # Initialize memory with loaded data
        memory_manager.memory = {
            "guid": str(uuid.uuid4()),
            "static_memory": static_memory,
            "context": memory_data.get("context", []),
            "metadata": memory_data.get("metadata", {}),
            "conversation_history": conversation_history.copy()
        }
        memory_manager.save_memory("init_simple")

        # Add conversation entries to embeddings
        embeddings_manager.update_embeddings(conversation_history)

        # Prepare a RAG query
        query = "What do I know about the ancient ruins?"
        query_context = {
            "query": query,
            "domain_specific_prompt_instructions": domain_config["domain_specific_prompt_instructions"].get("query", ""),
            "static_memory": static_memory,
            "previous_context": "",
            "conversation_history": ""
        }

        # Enhance with RAG
        enhanced_context = rag_manager.enhance_memory_query(query_context)
        print("\n--- RAG CONTEXT ---")
        print(enhanced_context.get("rag_context", "No RAG context generated"))

        # Query memory with RAG context
        response = memory_manager.query_memory(enhanced_context)
        print("\n--- FINAL RESPONSE ---")
        print(response.get("response", "No response generated"))

if __name__ == "__main__":
    main()
