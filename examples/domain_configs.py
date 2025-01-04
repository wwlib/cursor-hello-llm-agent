"""Domain-specific configurations for the Agent system."""

DND_CONFIG = {
    "schema": {
        "structured_data": {
            "world": {
                "geography": [],
                "settlements": []
            },
            "npcs": [],
            "events": []
        },
        "knowledge_graph": {
            "npcs": {},
            "settlements": {},
            "events": {}
        }
    },
    "prompts": {
        "create_memory": """You are a helpful assistant that communicates using JSON.
        Create a structured memory for the following D&D campaign information:
        {input_data}
        
        Use this schema:
        {schema}
        
        Return ONLY a valid JSON object with no additional text.""",
        
        "query": """You are a helpful assistant that communicates using JSON.
        Process this D&D campaign query using the current memory state and schema:
        
        Memory State:
        {memory_state}
        
        Schema:
        {schema}
        
        User Query:
        {query}
        
        Return ONLY a valid JSON object with no additional text.""",
        
        "reflect": """You are a helpful assistant that communicates using JSON.
        Analyze these recent D&D campaign interactions and update the knowledge state:
        
        Current State:
        {memory_state}
        
        Recent Messages:
        {messages}
        
        Schema:
        {schema}
        
        Return ONLY a valid JSON object with no additional text."""
    }
}

USER_STORY_CONFIG = {
    "schema": {
        "structured_data": {
            "features": [],
            "stakeholders": [],
            "requirements": [],
            "dependencies": []
        },
        "knowledge_graph": {
            "feature_relationships": {},
            "stakeholder_relationships": {},
            "requirement_dependencies": {}
        }
    },
    "prompts": {
        "create_memory": """You are a helpful assistant that communicates using JSON.
        Create a structured memory for the following project information:
        {input_data}
        
        Use this schema:
        {schema}
        
        Return ONLY a valid JSON object with no additional text.""",
        
        "query": """You are a helpful assistant that communicates using JSON.
        Process this project query using the current memory state and schema:
        
        Memory State:
        {memory_state}
        
        Schema:
        {schema}
        
        User Query:
        {query}
        
        Return ONLY a valid JSON object with no additional text.""",
        
        "reflect": """You are a helpful assistant that communicates using JSON.
        Analyze these recent project interactions and update the knowledge state:
        
        Current State:
        {memory_state}
        
        Recent Messages:
        {messages}
        
        Schema:
        {schema}
        
        Return ONLY a valid JSON object with no additional text."""
    }
} 