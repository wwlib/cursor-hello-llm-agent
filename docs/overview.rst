Overview
========

The LLM Agent Framework is a comprehensive system for building intelligent conversational agents with persistent memory capabilities.

Key Features
============

**Memory Management**
  - Persistent conversation memory with importance scoring
  - Automatic content segmentation and summarization
  - RAG-based retrieval for contextual responses

**Graph Memory System**
  - Knowledge graph construction from conversations
  - Entity extraction with domain-specific types
  - Relationship detection and semantic linking
  - Duplicate prevention through similarity matching

**Domain Configuration**
  - Configurable for different use cases (D&D, lab work, etc.)
  - Customizable entity and relationship types
  - Domain-specific prompting strategies

**LLM Integration**
  - Support for multiple LLM providers
  - Structured prompting for reliable extraction
  - Embedding-based semantic similarity

Architecture
============

The framework consists of several interconnected components:

1. **Memory Manager**: Orchestrates all memory operations
2. **Content Segmenter**: Breaks conversations into meaningful segments
3. **RAG Manager**: Handles semantic search and retrieval
4. **Graph Manager**: Manages knowledge graph operations
5. **Entity Extractor**: LLM-based entity identification
6. **Relationship Extractor**: Discovers connections between entities
7. **Embeddings Manager**: Handles vector embeddings for similarity

Getting Started
===============

Basic usage involves initializing the framework with your LLM services and domain configuration::

    from src.memory import MemoryManager
    from src.llm_services import YourLLMService
    
    # Initialize LLM service
    llm_service = YourLLMService()
    
    # Create memory manager
    memory_manager = MemoryManager(
        llm_service=llm_service,
        storage_path="./memory_data",
        domain_config=your_domain_config
    )
    
    # Add conversation entry
    memory_manager.add_conversation_entry(
        content="The wizard Eldara runs a magic shop in Riverwatch",
        role="user"
    )
    
    # Query for context
    context = memory_manager.get_relevant_context("Tell me about magic shops")

Use Cases
=========

**D&D Campaign Management**
  - Track characters, locations, and story elements
  - Build rich world knowledge over time
  - Provide context for consistent storytelling

**Laboratory Documentation**
  - Extract equipment, procedures, and results
  - Link experimental data and protocols
  - Support research documentation

**General Knowledge Building**
  - Convert conversations into structured knowledge
  - Enable intelligent context retrieval
  - Support long-term memory for AI agents 