.. LLM Agent Framework documentation master file, created by
   sphinx-quickstart on Sun Jun  8 09:39:07 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to LLM Agent Framework's documentation!
================================================

The LLM Agent Framework provides a comprehensive memory system with both traditional RAG-based 
retrieval and advanced graph memory capabilities for building intelligent conversational agents.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   api/index
   examples
   contributing

Overview
========

The framework includes:

* **Memory Management**: Persistent conversation memory with importance scoring
* **Graph Memory**: Knowledge graph construction from conversations with entity extraction
* **RAG Integration**: Semantic search and context retrieval
* **Domain Configuration**: Customizable for different use cases (D&D, lab work, software projects)

Quick Start
===========

.. code-block:: python

   from src.memory.graph_memory import GraphManager
   from src.ai.llm_ollama import OllamaService
   from src.memory.embeddings_manager import EmbeddingsManager

   # Initialize services
   llm_service = OllamaService({"base_url": "http://localhost:11434", "model": "gemma3"})
   embeddings_manager = EmbeddingsManager("embeddings.jsonl", llm_service)

   # Create graph manager
   graph_manager = GraphManager(
       llm_service=llm_service,
       embeddings_manager=embeddings_manager,
       storage_path="graph_data",
       domain_config=domain_config
   )

   # Extract entities and build knowledge graph
   entities = graph_manager.extract_entities_from_segments(conversation_segments)

Key Features
============

Graph Memory System
-------------------

* **Automatic Entity Extraction**: LLM-driven identification of domain-specific entities
* **Duplicate Prevention**: Multi-stage similarity matching using semantic embeddings
* **Relationship Detection**: Automatic discovery of connections between entities
* **Domain Adaptation**: Configurable for different domains and use cases

Memory Management
-----------------

* **Conversation Persistence**: Long-term memory storage with JSON serialization
* **Importance Scoring**: Automatic relevance assessment of conversation segments
* **Context Retrieval**: Semantic search for relevant historical context
* **Async Processing**: Non-blocking memory updates

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

