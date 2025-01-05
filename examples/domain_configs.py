"""Domain-specific configurations for the Agent system."""

DND_CONFIG = {
    "domain_specific_prompt_instructions:": {
        "create_memory": "",
        "query": "",
        "reflect": ""
    },
    "domain_specific_schema_suggestions": {
        "structured_data": {
            "entities": [],
            "action_history": [
                {
                    "identifier": "action_id",
                    "type": "action_type: interaction, combat, exploration, etc.",
                    "name": "Action Name",
                    "description": "Action description"
                }
            ]
        }
    }
}

USER_STORY_CONFIG = {
    "domain_specific_prompt_instructions": {
        "create_memory": "",
        "query": "",
        "reflect": ""
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