"""Domain-specific configurations for the Agent system."""

dnd_initial_data = """
Campaign Setting: The Lost Valley

World Details:
- Hidden valley surrounded by impassable mountains
- Ancient ruins scattered throughout
- Mysterious magical anomalies
- Three main settlements: Haven (central), Riverwatch (east), Mountainkeep (west)

Key NPCs:
1. Elena
   - Role: Mayor of Haven
   - Motivation: Protect the valley's inhabitants
   - Current Quest: Investigate strange occurrences in Haven

2. Theron
   - Role: Master Scholar
   - Expertise: Ancient ruins and artifacts
   - Current Research: Decoding ruin inscriptions

3. Sara
   - Role: Captain of Riverwatch
   - Responsibility: Valley's defense
   - Current Concern: Increased monster activity

Current Situations:
1. Trade Routes
   - Main road between settlements disrupted
   - Merchants seeking protection
   - Alternative routes needed

2. Ancient Ruins
   - New chambers discovered
   - Strange energy emanations
   - Valuable artifacts found

3. Magical Anomalies
   - Random magical effects
   - Affecting local wildlife
   - Possible connection to ruins"""


DND_CONFIG = {
    "domain_name": "dnd_campaign",
    "domain_specific_prompt_instructions": {
        "query": "You are a DM for a D&D campaign. ANSWER PLAYER QUESTIONS DIRECTLY. For simple questions (like 'are there goblins nearby?'), give specific answers based on the campaign state. For exploration questions (like 'what do I see?'), provide vivid but concise descriptions. Avoid starting every response with 'Okay, let's investigate' or similar repetitive phrases. Move the story forward with actionable information and clear choices.",
        "update": "You are analyzing the input from both the user and the agent and extracting and classifying the important information into the conversation history data structure."
    },
    "initial_data": dnd_initial_data,
    "topic_taxonomy": {
        "world": ["setting", "geography", "location", "environment", "terrain"],
        "characters": ["npc", "player", "personality", "motivation", "background"],
        "narrative": ["story", "plot", "quest", "adventure", "campaign"],
        "mechanics": ["rules", "dice", "combat", "magic", "spells"],
        "objects": ["items", "equipment", "artifacts", "treasure", "inventory"],
        "history": ["lore", "ruins", "archaeology", "ancient", "past"],
        "society": ["politics", "trade", "settlements", "culture", "religion"],
        "threats": ["monsters", "enemies", "dangers", "conflict", "war"],
        "exploration": ["discovery", "investigation", "research", "mystery"],
        "events": ["happenings", "situations", "incidents", "occurrences"]
    },
    "topic_normalizations": {
        # Geography variations
        "locations": "location",
        "geography": "location", 
        "terrain": "environment",
        "area": "location",
        "place": "location",
        "region": "location",
        
        # Character variations
        "character": "characters",
        "key npc": "npc",
        "npcs": "npc",
        "people": "characters",
        
        # Ruins/archaeology variations
        "ruins": "archaeology",
        "ancient ruins": "archaeology",
        "artifacts": "archaeology",
        "archaeological": "archaeology",
        
        # Events variations
        "situation": "events",
        "situations": "events",
        "happenings": "events",
        "occurrences": "events",
        
        # Investigation variations
        "research": "investigation",
        "exploration": "investigation",
        "discovery": "investigation",
        
        # Magic variations
        "magical": "magic",
        "anomalies": "magic",
        "magical anomalies": "magic",
        
        # DnD-specific normalizations
        "setting": "world",
        "world": "setting",
        "lore": "history", 
        "ancient": "history",
        "monsters": "threats",
        "enemies": "threats",
        "monster activity": "threats",
        "defense": "threats",
        "trade routes": "trade",
        "settlements": "society",
        "politics": "society",
        "value": "objects",
        "treasure": "objects",
        "skills": "mechanics",
        "expertise": "mechanics",
        "decryption": "investigation",
        "wildlife": "environment"
    },
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["character", "location", "object", "event", "concept", "organization"],
        "relationship_types": [
            "located_in", "owns", "member_of", "allies_with", "enemies_with", 
            "uses", "created_by", "leads_to", "participates_in", "related_to", "mentions"
        ],
        "entity_extraction_prompt": "Extract entities from this D&D campaign text. Focus on characters, locations, objects, events, concepts, and organizations that are important to the campaign world and story.",
        "relationship_extraction_prompt": "Identify relationships between entities in this D&D campaign text. Look for spatial relationships (located_in), ownership (owns), social relationships (allies_with, enemies_with), and story connections.",
        "similarity_threshold": 0.8
    }
}

user_story_initial_data = """Please structure the following project information into a JSON format with structured_data for facts, knowledge_graph for relationships, and appropriate metadata.

Project: Task Management System

Overview:
- Web-based task management application
- Multiple user support with different roles
- Task organization with projects and tags
- Due date tracking and notifications

Key Features:
- User authentication and authorization
- Task creation and management
- Project organization
- Tag system
- Due date reminders
- Activity tracking

Stakeholders:
- Project Manager (primary user)
- Team Members (task executors)
- Team Leads (task reviewers)
- System Administrator

Requirements:
- Secure user authentication
- Intuitive task creation interface
- Project hierarchy support
- Tag-based task filtering
- Email notifications for due dates
- Activity history and audit logs

Return ONLY a valid JSON object with structured_data and knowledge_graph sections. No additional text or explanation."""

USER_STORY_CONFIG = {
    "domain_name": "user_story_creation",
    "domain_specific_prompt_instructions": {
        "query": "",
        "update": ""
    },
    "domain_specific_schema_suggestions": {
        "structured_data": {
            "entities": [
                {
                    "identifier": "entity_id",
                    "type": "entity_type: feature or user_story",
                    "name": "Entity Name",
                    "technologies": ["technology1", "technology2"],
                    "description": "Entity description"
                }
            ]
        }
    },
    "initial_data": user_story_initial_data,
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["feature", "stakeholder", "requirement", "technology", "component", "process"],
        "relationship_types": [
            "depends_on", "implements", "used_by", "part_of", "manages", 
            "requires", "interacts_with", "supports", "validates", "related_to"
        ],
        "entity_extraction_prompt": "Extract entities from this software requirements text. Focus on features, stakeholders, requirements, technologies, components, and processes that are important to the project.",
        "relationship_extraction_prompt": "Identify relationships between entities in this software requirements text. Look for dependencies (depends_on), implementations (implements), usage patterns (used_by), and hierarchical relationships (part_of).",
        "similarity_threshold": 0.8
    }
} 

lab_assistant_initial_data = """
The lab is a place for invention.
The lab contains cool equipment, including 3D printers, soldering irons, woodworking tools, and more.
"""

lab_assistant_query_instructions = """
You are a lab assistant. You are responsible for helping the user with their lab work.
You have two primary functions: 
1) Receive and remember statements about the user's lab work (i.e. the user's lab notes).
2) Answer questions about the user's lab work using the notes and data provided by the user.
When the user gives you notes, you will automatically add them to your knowledge base. 
Please do not repeat the notes. Simply acknowledge that you have received the notes.
When the user asks a question, data from previous notes will be automatcially available to you.
Simply use the info provided and answer the question as though you are a knowledgable lab assistant who is enthusiastic about the user's work.
The user is very smart and so are you.
"""

LAB_ASSISTANT_CONFIG = {
    "domain_name": "lab_assistant",
    "domain_specific_prompt_instructions": {
        "query": lab_assistant_query_instructions,
        "update": "You are analyzing the input from both the user and the agent and extracting and classifying the important information into the conversation history data structure. Your goal is to keep the most relevant information and filter out the rest. Please do not filter out anything important!"
    },
    "initial_data": lab_assistant_initial_data,
    "topic_taxonomy": {
        "projects": ["experiment", "build", "design", "prototype", "research"],
        "equipment": ["tools", "instruments", "machines", "devices", "hardware"],
        "materials": ["components", "supplies", "resources", "substances"],
        "methods": ["procedures", "techniques", "processes", "protocols"],
        "results": ["data", "measurements", "observations", "outcomes"],
        "analysis": ["evaluation", "testing", "validation", "troubleshooting"],
        "documentation": ["notes", "records", "logs", "reports", "specs"],
        "safety": ["precautions", "hazards", "protection", "risks"],
        "planning": ["goals", "timeline", "requirements", "resources"],
        "collaboration": ["team", "assistance", "consultation", "sharing"]
    },
    "topic_normalizations": {
        "equipment": "tools",
        "instruments": "tools", 
        "devices": "tools",
        "experiment": "projects",
        "build": "projects",
        "prototype": "projects",
        "components": "materials",
        "supplies": "materials",
        "measurements": "results",
        "observations": "results",
        "procedures": "methods",
        "techniques": "methods",
        "specs": "documentation",
        "logs": "documentation",
        "records": "documentation"
    },
    "graph_memory_config": {
        "enabled": True,
        "entity_types": ["equipment", "material", "procedure", "result", "project", "person"],
        "relationship_types": [
            "uses", "produces", "requires", "part_of", "leads_to", 
            "tested_with", "works_with", "owned_by", "located_in", "related_to"
        ],
        "entity_extraction_prompt": "Extract entities from this laboratory text. Focus on equipment, materials, procedures, results, projects, and people that are important to the lab work and experiments.",
        "relationship_extraction_prompt": "Identify relationships between entities in this laboratory text. Look for usage patterns (uses), production relationships (produces), requirements (requires), and experimental connections.",
        "similarity_threshold": 0.8
    }
}


CONFIG_MAP = {
    "dnd": DND_CONFIG,
    "user_story": USER_STORY_CONFIG,
    "lab_assistant": LAB_ASSISTANT_CONFIG
}