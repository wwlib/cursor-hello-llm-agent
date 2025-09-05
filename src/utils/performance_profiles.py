"""
Performance Profiles Configuration

Provides predefined performance profiles for different use cases:
- Speed: Maximum performance, minimal features
- Balanced: Good performance with essential features
- Comprehensive: Full features, slower but complete processing
"""

from typing import Dict, Any

# Performance profile configurations
PERFORMANCE_PROFILES = {
    "speed": {
        "description": "Maximum speed, minimal features",
        "enable_graph_memory": False,
        "enable_graph_memory_fast_mode": True,
        "graph_memory_processing_level": "speed",
        "rag_limit": 3,
        "max_recent_conversation_entries": 2,
        "enable_digest_generation": False,
        "importance_threshold": 4,  # Only keep very important segments
        "embeddings_batch_size": 1,
        "async_processing": "minimal"
    },
    "balanced": {
        "description": "Good performance with essential features",
        "enable_graph_memory": True,
        "enable_graph_memory_fast_mode": False,
        "graph_memory_processing_level": "balanced",
        "rag_limit": 5,
        "max_recent_conversation_entries": 4,
        "enable_digest_generation": True,
        "importance_threshold": 3,
        "embeddings_batch_size": 3,
        "async_processing": "optimized"
    },
    "comprehensive": {
        "description": "Full features, complete processing",
        "enable_graph_memory": True,
        "enable_graph_memory_fast_mode": False,
        "graph_memory_processing_level": "comprehensive",
        "rag_limit": 10,
        "max_recent_conversation_entries": 8,
        "enable_digest_generation": True,
        "importance_threshold": 2,  # Keep more segments
        "embeddings_batch_size": 5,
        "async_processing": "full"
    }
}

def get_performance_profile(profile_name: str) -> Dict[str, Any]:
    """
    Get a performance profile configuration.
    
    Args:
        profile_name: Name of the profile ("speed", "balanced", "comprehensive")
        
    Returns:
        Dictionary containing the profile configuration
        
    Raises:
        ValueError: If profile_name is not recognized
    """
    if profile_name not in PERFORMANCE_PROFILES:
        available_profiles = ", ".join(PERFORMANCE_PROFILES.keys())
        raise ValueError(f"Unknown performance profile '{profile_name}'. Available profiles: {available_profiles}")
    
    return PERFORMANCE_PROFILES[profile_name].copy()

def list_performance_profiles() -> Dict[str, str]:
    """
    List all available performance profiles with descriptions.
    
    Returns:
        Dictionary mapping profile names to descriptions
    """
    return {
        name: config["description"] 
        for name, config in PERFORMANCE_PROFILES.items()
    }

def apply_performance_profile(profile_name: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a performance profile to a base configuration.
    
    Args:
        profile_name: Name of the profile to apply
        base_config: Base configuration dictionary
        
    Returns:
        Updated configuration with profile settings applied
    """
    profile = get_performance_profile(profile_name)
    
    # Create a copy of the base config
    updated_config = base_config.copy()
    
    # Apply profile settings
    updated_config.update(profile)
    
    return updated_config

def get_memory_manager_config(profile_name: str) -> Dict[str, Any]:
    """
    Get MemoryManager-specific configuration for a performance profile.
    
    Args:
        profile_name: Name of the profile
        
    Returns:
        Dictionary containing MemoryManager configuration parameters
    """
    profile = get_performance_profile(profile_name)
    
    return {
        "enable_graph_memory": profile["enable_graph_memory"],
        "enable_graph_memory_fast_mode": profile["enable_graph_memory_fast_mode"], 
        "graph_memory_processing_level": profile["graph_memory_processing_level"],
        "max_recent_conversation_entries": profile["max_recent_conversation_entries"],
        "importance_threshold": profile["importance_threshold"]
    }

def print_performance_profiles():
    """Print all available performance profiles with their settings."""
    print("Available Performance Profiles:")
    print("=" * 50)
    
    for name, config in PERFORMANCE_PROFILES.items():
        print(f"\n{name.upper()}: {config['description']}")
        print(f"  Graph Memory: {'Enabled' if config['enable_graph_memory'] else 'Disabled'}")
        if config['enable_graph_memory']:
            print(f"  Graph Mode: {config['graph_memory_processing_level']}")
        print(f"  RAG Limit: {config['rag_limit']}")
        print(f"  Memory Entries: {config['max_recent_conversation_entries']}")
        print(f"  Digest Generation: {'Enabled' if config['enable_digest_generation'] else 'Disabled'}")
        print(f"  Importance Threshold: {config['importance_threshold']}")

if __name__ == "__main__":
    print_performance_profiles()

