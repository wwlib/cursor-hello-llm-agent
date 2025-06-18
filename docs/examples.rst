Examples
========

This section provides practical examples of using the LLM Agent Framework.

Basic Memory Management
=======================

Setting up basic conversation memory::

    from src.memory.memory_manager import MemoryManager
    from src.llm_services import GemmaService
    
    # Initialize services
    llm_service = GemmaService()
    
    # Create memory manager
    memory_manager = MemoryManager(
        llm_service=llm_service,
        storage_path="./conversation_memory"
    )
    
    # Add conversation entries
    memory_manager.add_conversation_entry(
        content="I'm planning a camping trip to Yellowstone next month",
        role="user"
    )
    
    memory_manager.add_conversation_entry(
        content="That sounds exciting! Here are some tips for camping in Yellowstone...",
        role="assistant"
    )
    
    # Retrieve relevant context
    context = memory_manager.get_relevant_context("camping gear")
    print(context)

D&D Campaign Tracking
=====================

Using graph memory for D&D campaign management::

    from src.memory.memory_manager import MemoryManager
    from src.memory.graph_memory.domain_configs import dnd_config
    
    # Initialize with D&D domain configuration
    memory_manager = MemoryManager(
        llm_service=llm_service,
        storage_path="./dnd_campaign",
        domain_config=dnd_config,
        enable_graph_memory=True
    )
    
    # Add campaign events
    memory_manager.add_conversation_entry(
        content="""
        The party arrives in the bustling market town of Riverwatch. 
        Eldara, a fire wizard, runs the local magic shop called 'Arcane Embers'. 
        She offers to sell them healing potions and enchanted scrolls.
        """,
        role="assistant"
    )
    
    # The system automatically extracts:
    # - Entities: Riverwatch (location), Eldara (character), Arcane Embers (location)
    # - Relationships: Eldara located_in Riverwatch, Eldara owns Arcane Embers

Entity Extraction Example
=========================

Direct entity extraction from text::

    from src.memory.graph_memory.entity_extractor import EntityExtractor
    from src.memory.graph_memory.domain_configs import dnd_config
    
    extractor = EntityExtractor(
        llm_service=llm_service,
        domain_config=dnd_config
    )
    
    entities = extractor.extract_entities(
        "Sir Gareth the paladin wields the legendary sword Lightbringer"
    )
    
    # Returns:
    # [
    #     {
    #         "name": "Sir Gareth",
    #         "type": "character",
    #         "description": "A paladin who wields the legendary sword Lightbringer"
    #     },
    #     {
    #         "name": "Lightbringer", 
    #         "type": "object",
    #         "description": "A legendary sword wielded by Sir Gareth the paladin"
    #     }
    # ]

Graph Queries
=============

Querying the knowledge graph::

    from src.memory.graph_memory.graph_queries import GraphQueries
    
    queries = GraphQueries(graph_manager)
    
    # Find all information about a character
    character_info = queries.find_entity_context("Eldara")
    
    # Find path between entities
    path = queries.find_path_between_entities("Sir Gareth", "Lightbringer")
    
    # Get recent entities
    recent = queries.get_recent_entities(limit=5, entity_type="character")

Custom Domain Configuration
===========================

Creating a custom domain for laboratory work::

    lab_config = {
        "domain_name": "laboratory_research",
        "entity_types": {
            "equipment": "Laboratory instruments, devices, and apparatus",
            "material": "Chemical compounds, biological samples, reagents",
            "procedure": "Experimental methods, protocols, techniques",
            "result": "Measurements, observations, data points",
            "person": "Researchers, collaborators, lab personnel",
            "concept": "Scientific theories, principles, hypotheses"
        },
        "relationship_types": {
            "uses": "Equipment or material used in procedure",
            "produces": "Procedure or equipment produces result",
            "located_in": "Equipment or material located in lab space",
            "collaborates_with": "People working together",
            "measures": "Equipment measures specific parameters",
            "contains": "Material contains specific compounds"
        }
    }
    
    # Use with memory manager
    memory_manager = MemoryManager(
        llm_service=llm_service,
        storage_path="./lab_research",
        domain_config=lab_config,
        enable_graph_memory=True
    )

Advanced Graph Operations
=========================

Working directly with the graph manager::

    from src.memory.graph_memory.graph_manager import GraphManager
    
    graph_manager = GraphManager(
        storage_path="./advanced_graph",
        embeddings_manager=embeddings_manager,
        llm_service=llm_service,
        domain_config=dnd_config
    )
    
    # Add nodes manually
    node, is_new = graph_manager.add_or_update_node(
        name="Dragon's Lair",
        node_type="location",
        description="Ancient cave system inhabited by a red dragon",
        danger_level="extreme",
        discovered_by="The Brave Company"
    )
    
    # Add relationships
    graph_manager.add_edge(
        from_node="Ancient Red Dragon",
        to_node="Dragon's Lair", 
        relationship_type="located_in",
        weight=1.0,
        evidence="The dragon lives deep within the cave system"
    )
    
    # Query for context
    context = graph_manager.query_for_context("dangerous locations")

Embeddings and Similarity
=========================

Using embeddings for semantic similarity::

    from src.memory.embeddings_manager import EmbeddingsManager
    
    embeddings_manager = EmbeddingsManager(
        storage_path="./embeddings",
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Generate embeddings
    embedding = embeddings_manager.generate_embedding(
        "A magical sword with fire enchantments"
    )
    
    # Find similar content
    similar_items = embeddings_manager.find_similar(
        query="enchanted weapon",
        top_k=5,
        min_similarity=0.7
    )

Integration Example
===================

Complete integration example::

    import logging
    from src.memory.memory_manager import MemoryManager
    from src.llm_services import GemmaService
    from src.memory.graph_memory.domain_configs import dnd_config
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize services
    llm_service = GemmaService(model="gemma2:2b")
    
    # Create comprehensive memory system
    memory_manager = MemoryManager(
        llm_service=llm_service,
        storage_path="./complete_system",
        domain_config=dnd_config,
        enable_graph_memory=True,
        max_memory_entries=1000,
        similarity_threshold=0.8
    )
    
    # Simulate a conversation
    conversation = [
        "Tell me about the town of Riverwatch",
        "Riverwatch is a peaceful trading town...",
        "Who are the important people there?",
        "Eldara the fire wizard runs the magic shop...",
        "What about the surrounding area?",
        "To the north lies the Whispering Woods..."
    ]
    
    for i, message in enumerate(conversation):
        role = "user" if i % 2 == 0 else "assistant"
        memory_manager.add_conversation_entry(
            content=message,
            role=role
        )
    
    # Generate comprehensive response using all memory
    context = memory_manager.get_comprehensive_context(
        query="Tell me everything about Riverwatch and its surroundings"
    )
    
    print("Context from memory:")
    print(context) 