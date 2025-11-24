# API Domain Configurations

This module provides domain-specific configurations for the Agent API, allowing different behavioral profiles and memory structures for different use cases.

## Comparison: SessionManager vs agent_usage_example.py

### Before (SessionManager):
- Used simple `domain` string field in `SessionConfig`
- Memory manager created without `domain_config` parameter
- Agent created with just `domain_name` string
- No access to rich domain-specific configurations

### After (Updated SessionManager):
- Imports domain configurations from `src/api/configs/domain_configs.py`
- Resolves domain string to full domain configuration object
- Memory manager created with complete `domain_config` parameter
- Agent created with proper `domain_name` from config
- Supports fallback to default domain if specified domain not found

## Available Domain Configurations

The domain configurations are imported from `examples/domain_configs.py` and include:

### D&D Campaign (`dnd`)
- Rich fantasy campaign management
- NPCs, locations, quests, magic systems
- Graph memory for character/location relationships

### Lab Assistant (`lab_assistant`) 
- Laboratory work and experiment tracking
- Equipment, procedures, results, safety
- Technical documentation and collaboration

### User Story Creation (`user_story`)
- Software requirements and feature tracking
- Stakeholders, features, technologies
- Project planning and dependencies

## API Endpoints

### List Available Domains
```
GET /domains
```
Returns all available domain configurations with basic info.

### Get Domain Configuration
```
GET /domains/{domain_name}
```
Returns detailed configuration for a specific domain (sanitized for security).

## Usage in Sessions

When creating a session, specify the domain:

```json
{
  "config": {
    "domain": "dnd",
    "llm_model": "gemma3",
    "enable_graph": true
  }
}
```

The SessionManager will:
1. Resolve the domain string to full configuration
2. Pass complete `domain_config` to MemoryManager
3. Extract `domain_name` for Agent initialization
4. Enable domain-specific behaviors and memory structures

## Architecture Benefits

1. **Consistency**: Same domain configs used in both CLI and API
2. **Rich Configuration**: Full access to domain-specific prompts, schemas, and behaviors
3. **Fallback Handling**: Graceful degradation to default domain
4. **Extensibility**: Easy to add new domains by updating config files
5. **Memory Structure**: Domain-aware memory organization and graph relationships 