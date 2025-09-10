$ DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/agent_usage_example.py --verbose --guid sep10b --config dnd 

================================================================================
  Agent Usage Example
================================================================================

Using domain config: dnd
Domain config: {'domain_name': 'dnd_campaign', 'domain_specific_prompt_instructions': {'query': "You are a DM for a D&D campaign. ANSWER PLAYER QUESTIONS DIRECTLY. For simple questions (like 'are there goblins nearby?'), give specific answers based on the campaign state. For exploration questions (like 'what do I see?'), provide vivid but concise descriptions. Avoid starting every response with 'Okay, let's investigate' or similar repetitive phrases. Move the story forward with actionable information and clear choices.", 'update': 'You are analyzing the input from both the user and the agent and extracting and classifying the important information into the conversation history data structure.'}, 'initial_data': "\nCampaign Setting: The Lost Valley\n\nWorld Details:\n- Hidden valley surrounded by impassable mountains\n- Ancient ruins scattered throughout\n- Mysterious magical anomalies\n- Three main settlements: Haven (central), Riverwatch (east), Mountainkeep (west)\n\nKey NPCs:\n1. Elena\n   - Role: Mayor of Haven\n   - Motivation: Protect the valley's inhabitants\n   - Current Quest: Investigate strange occurrences in Haven\n\n2. Theron\n   - Role: Master Scholar\n   - Expertise: Ancient ruins and artifacts\n   - Current Research: Decoding ruin inscriptions\n\n3. Sara\n   - Role: Captain of Riverwatch\n   - Responsibility: Valley's defense\n   - Current Concern: Increased monster activity\n\nCurrent Situations:\n1. Trade Routes\n   - Main road between settlements disrupted\n   - Merchants seeking protection\n   - Alternative routes needed\n\n2. Ancient Ruins\n   - New chambers discovered\n   - Strange energy emanations\n   - Valuable artifacts found\n\n3. Magical Anomalies\n   - Random magical effects\n   - Affecting local wildlife\n   - Possible connection to ruins", 'topic_taxonomy': {'world': ['setting', 'geography', 'location', 'environment', 'terrain'], 'characters': ['npc', 'player', 'personality', 'motivation', 'background'], 'narrative': ['story', 'plot', 'quest', 'adventure', 'campaign'], 'mechanics': ['rules', 'dice', 'combat', 'magic', 'spells'], 'objects': ['items', 'equipment', 'artifacts', 'treasure', 'inventory'], 'history': ['lore', 'ruins', 'archaeology', 'ancient', 'past'], 'society': ['politics', 'trade', 'settlements', 'culture', 'religion'], 'threats': ['monsters', 'enemies', 'dangers', 'conflict', 'war'], 'exploration': ['discovery', 'investigation', 'research', 'mystery'], 'events': ['happenings', 'situations', 'incidents', 'occurrences']}, 'topic_normalizations': {'locations': 'location', 'geography': 'location', 'terrain': 'environment', 'area': 'location', 'place': 'location', 'region': 'location', 'character': 'characters', 'key npc': 'npc', 'npcs': 'npc', 'people': 'characters', 'ruins': 'archaeology', 'ancient ruins': 'archaeology', 'artifacts': 'archaeology', 'archaeological': 'archaeology', 'situation': 'events', 'situations': 'events', 'happenings': 'events', 'occurrences': 'events', 'research': 'investigation', 'exploration': 'investigation', 'discovery': 'investigation', 'magical': 'magic', 'anomalies': 'magic', 'magical anomalies': 'magic', 'setting': 'world', 'world': 'setting', 'lore': 'history', 'ancient': 'history', 'monsters': 'threats', 'enemies': 'threats', 'monster activity': 'threats', 'defense': 'threats', 'trade routes': 'trade', 'settlements': 'society', 'politics': 'society', 'value': 'objects', 'treasure': 'objects', 'skills': 'mechanics', 'expertise': 'mechanics', 'decryption': 'investigation', 'wildlife': 'environment'}, 'graph_memory_config': {'enabled': True, 'entity_types': ['character', 'location', 'object', 'event', 'concept', 'organization'], 'relationship_types': ['located_in', 'owns', 'member_of', 'allies_with', 'enemies_with', 'uses', 'created_by', 'leads_to', 'participates_in', 'related_to', 'mentions'], 'entity_extraction_prompt': 'Extract entities from this D&D campaign text. Focus on characters, locations, objects, events, concepts, and organizations that are important to the campaign world and story.', 'relationship_extraction_prompt': 'Identify relationships between entities in this D&D campaign text. Look for spatial relationships (located_in), ownership (owns), social relationships (allies_with, enemies_with), and story connections.', 'similarity_threshold': 0.8}}
Setting up services...
Initializing session with guid: sep10b
Done initializing session
Using performance profile: balanced
Graph memory: enabled
Graph processing level: balanced
Domain name: dnd_campaign
Services initialized successfully
Initializing memory...
Creating new memory...
🔄 Processing initial domain data...
🔄   This may take a moment for complex domains...
🔄   Converting domain data to prose format...
🔄     Preprocessing domain data...
✅     Preprocessing domain data (17.36s)
🔄     Generating digest for domain data...
✅     Generating digest for domain data (20.57s)
🔄     Creating embeddings for semantic search...
✅     Creating embeddings for semantic search (1.07s)
🔄     Building knowledge graph from domain data...
🔄       Analyzing digest segments...
✅       Found 7 important segments
🔄       Preparing text for entity extraction...
✅       Prepared 1191 chars for processing
🔄       Extracting entities and relationships...
🔄         Stage 1: Extracting candidate entities...
✅         Found 12 candidate entities
🔄         Stage 2: Converting to resolver candidates...
✅         Prepared 12 candidates for resolution
🔄         Stage 3: Resolving entities (this may take time)...
✅         Resolved 12 entities
✅       Extracted 12 entities, 9 relationships
✅     Building knowledge graph from domain data (132.49s)
Memory initialized successfully!

Initial Memory State
====================
Memory GUID: sep10b
Memory Manager Type: standard
Memory File: agent_memories/standard/sep10b/agent_memory.json
Metadata:
------------------------------
{
  "created_at": "2025-09-10T06:32:06.495964",
  "updated_at": "2025-09-10T06:32:06.495964",
  "version": "2.0.0",
  "domain": "general",
  "saved_during": "create_initial_memory"
}

Conversation History: 1 messages
Static memory present.
------------------------------
The Lost Valley is a campaign setting defined by a hidden valley, completely encircled by impassable mountains.

Throughout the valley, ancient ruins are scattered, and mysterious magical anomalies are present.

There are three main settlements: Haven, located at the valley's center; Riverwatch, situated to the east; and Mountainkeep, found to the west.

Key non-player characters include Elena, who serves as the Mayor of Haven and is motivated to protect the valley's inhabitants; Theron, a Master Scholar with expertise in ancient ruins and artifacts, currently focused on decoding ruin inscriptions; and Sara, the Captain of Riverwatch, responsible for the valley's defense, who is currently concerned about increased monster activity.

Currently, trade routes between the settlements have been disrupted, with merchants seeking protection. Explorers are attempting to find alternative routes.

New chambers have been discovered within the ancient ruins, accompanied by strange energy emanations and the discovery of valuable artifacts.

Furthermore, random magical effects are occurring, influencing local wildlife, and there is a suspected connection between these anomalies and the ruins.

Type "help" to see available commands

You: Tell me about theron

Processing message...
🔄 Processing query: 'tell me about theron...'
🔄   Enhancing query with relevant context (RAG)...
✅     Generated and cached RAG context
🔄   Retrieving graph context...
✅     Generated graph context (optimized)
✅     Cached graph context
🔄   Generating response with LLM...
✅     Generated response (149 chars)
🔄   Starting background processing (batch, graph: balanced)...

Agent: Theron is a Master Scholar specializing in ancient ruins and artifacts within The Lost Valley. He is currently focused on decoding ruin inscriptions.
ℹ️        Graph processing queued (queue size: 1)
ℹ️        Graph processing queued (queue size: 2)

You: Tell me about Elena

Processing message...
🔄 Processing query: 'tell me about elena...'
🔄   Enhancing query with relevant context (RAG)...
✅     Generated and cached RAG context
🔄   Retrieving graph context...
✅     Generated graph context (optimized)
✅     Cached graph context
🔄   Generating response with LLM...
✅     Generated response (157 chars)
🔄   Starting background processing (batch, graph: balanced)...

Agent: Elena serves as the Mayor of Haven and is motivated to protect the valley's inhabitants. She's currently investigating strange occurrences within the valley.
🔄         Stage 1: Extracting candidate entities...
✅         Found 1 candidate entities
🔄         Stage 2: Converting to resolver candidates...
✅         Prepared 1 candidates for resolution
🔄         Stage 3: Resolving entities (this may take time)...
✅         Resolved 1 entities
ℹ️        Graph processing queued (queue size: 2)
ℹ️        Graph processing queued (queue size: 3)

You: perf

================================================================================
PERFORMANCE REPORT - Session: sep10b
================================================================================
Total Operations: 28
Active Operations: 2
Total Time: 192.303 seconds

TOP OPERATIONS BY TIME:
--------------------------------------------------
batch_entry_processing           79.325s ( 41.2%) x1
batch_graph_updates              63.056s ( 32.8%) x1
batch_digest_generation          31.553s ( 16.4%) x2
memory_query_total                9.066s (  4.7%) x2
llm_generation                    8.774s (  4.6%) x2

LATEST OPERATION BREAKDOWN:
--------------------------------------------------
batch_entry_processing           79.325s
  batch_digest_generation          16.129s
  batch_embeddings_update           0.138s
  batch_graph_updates              63.056s
    async_graph_memory_update         0.000s
    async_graph_memory_update         0.000s
    memory_query_total                4.585s
      add_user_entry                    0.003s
      format_memory_components          0.000s
      rag_enhancement                   0.085s
      graph_context                     0.051s
      format_prompt                     0.000s
      llm_generation                    4.440s (prompt: 7054 chars)
      add_agent_entry                   0.003s
      start_async_operations            0.000s
================================================================================

You: help

Available Commands:
------------------
help        - Show this help message
memory      - View current memory state
conversation- View full conversation history
history     - View recent session history
guid        - Show the current memory GUID
type        - Show memory manager type
list        - List available memory files
perf        - Show performance report for current session
perfdetail  - Show detailed performance analysis
process     - Process some background graph tasks manually
status      - Show background processing status
quit        - End session

You: memory

Current Memory State
====================
Memory GUID: sep10b
Memory Manager Type: standard
Memory File: agent_memories/standard/sep10b/agent_memory.json
Metadata:
------------------------------
{
  "created_at": "2025-09-10T06:32:06.495964",
  "updated_at": "2025-09-10T06:32:06.495964",
  "version": "2.0.0",
  "domain": "general",
  "saved_during": "batch_digest_generation"
}

Conversation History: 5 messages
Static memory present.
------------------------------
The Lost Valley is a campaign setting defined by a hidden valley, completely encircled by impassable mountains.

Throughout the valley, ancient ruins are scattered, and mysterious magical anomalies are present.

There are three main settlements: Haven, located at the valley's center; Riverwatch, situated to the east; and Mountainkeep, found to the west.

Key non-player characters include Elena, who serves as the Mayor of Haven and is motivated to protect the valley's inhabitants; Theron, a Master Scholar with expertise in ancient ruins and artifacts, currently focused on decoding ruin inscriptions; and Sara, the Captain of Riverwatch, responsible for the valley's defense, who is currently concerned about increased monster activity.

Currently, trade routes between the settlements have been disrupted, with merchants seeking protection. Explorers are attempting to find alternative routes.

New chambers have been discovered within the ancient ruins, accompanied by strange energy emanations and the discovery of valuable artifacts.

Furthermore, random magical effects are occurring, influencing local wildlife, and there is a suspected connection between these anomalies and the ruins.


You: q

============================================================
SESSION PERFORMANCE REPORT
============================================================

================================================================================
PERFORMANCE REPORT - Session: sep10b
================================================================================
Total Operations: 28
Active Operations: 2
Total Time: 192.303 seconds

TOP OPERATIONS BY TIME:
--------------------------------------------------
batch_entry_processing           79.325s ( 41.2%) x1
batch_graph_updates              63.056s ( 32.8%) x1
batch_digest_generation          31.553s ( 16.4%) x2
memory_query_total                9.066s (  4.7%) x2
llm_generation                    8.774s (  4.6%) x2

LATEST OPERATION BREAKDOWN:
--------------------------------------------------
batch_entry_processing           79.325s
  batch_digest_generation          16.129s
  batch_embeddings_update           0.138s
  batch_graph_updates              63.056s
    async_graph_memory_update         0.000s
    async_graph_memory_update         0.000s
    memory_query_total                4.585s
      add_user_entry                    0.003s
      format_memory_components          0.000s
      rag_enhancement                   0.085s
      graph_context                     0.051s
      format_prompt                     0.000s
      llm_generation                    4.440s (prompt: 7054 chars)
      add_agent_entry                   0.003s
      start_async_operations            0.000s
================================================================================

Detailed performance data saved to: logs/sep10b/