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
        "query": "You are an agent acting as a DM for a D&D campaign. You should respond in a way that moves the gameplay forward and adds details and richness to the story.",
        "update": "You are analyzing the input from both the user and the agent and extracting and classifying the important information into the conversation history data structure."
    },
    "initial_data": dnd_initial_data
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
    "initial_data": user_story_initial_data
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
    "initial_data": lab_assistant_initial_data
}


CONFIG_MAP = {
    "dnd": DND_CONFIG,
    "user_story": USER_STORY_CONFIG,
    "lab_assistant": LAB_ASSISTANT_CONFIG
}