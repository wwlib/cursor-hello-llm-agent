"""Domain-specific configurations for the Agent system."""

DND_CONFIG = {
    "domain_specific_prompt_instructions": {
        "create_memory": "You are creating a memory for a D&D campaign. You are given a all of the information needed to run the campaign. Please organize the data in a rich and concose way. Keep in mind that the memory data structure you are creating will be included in subsequent prompts as context. The memory will be used to inform the agent's behavior and decision-making.",
        "query": "You are analyzing conversational interactions between the player and the agent and returning an apppriate response. Please also include structured data that captures the important data in the conversation.",
        "update": "You are analyzing the conversation history and updating the memory to incorporate the important information learned during the session."
    }
}

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
    }
} 