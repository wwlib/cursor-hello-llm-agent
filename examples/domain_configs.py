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
    "domain_specific_prompt_instructions": {
        "create_memory": "You are creating a memory for a D&D campaign. You are given a all of the information needed to run the campaign. Please organize the data in a rich and concose way. Keep in mind that the memory data structure you are creating will be included in subsequent prompts as context. The memory will be used to inform the agent's behavior and decision-making.",
        "query": "You are analyzing conversational interactions between the player and the agent and returning an apppriate response. Please also include structured data that captures the important data in the conversation.",
        "update": "You are analyzing the conversation history and updating the memory to incorporate the important information learned during the session."
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
    "domain_specific_prompt_instructions": {
        "create_memory": "",
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