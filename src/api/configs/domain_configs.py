"""Domain-specific configurations for the API Agent system."""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to the Python path to import from examples
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the domain configurations from local file
try:
    from .domain_configs_data import CONFIG_MAP as EXAMPLES_CONFIG_MAP
except ImportError:
    # Fallback if domain_configs_data is not available
    EXAMPLES_CONFIG_MAP = {}

# Re-export the configuration map for API use
CONFIG_MAP = EXAMPLES_CONFIG_MAP

def get_domain_config(domain_name: str) -> Optional[Dict[str, Any]]:
    """Get domain configuration by name.
    
    Args:
        domain_name: The domain identifier (e.g., 'dnd', 'lab_assistant', 'user_story')
        
    Returns:
        Domain configuration dictionary or None if not found
    """
    return CONFIG_MAP.get(domain_name)

def get_available_domains() -> list[str]:
    """Get list of available domain names.
    
    Returns:
        List of available domain configuration names
    """
    return list(CONFIG_MAP.keys())

def get_default_domain() -> str:
    """Get the default domain name.
    
    Returns:
        Default domain name ('dnd' if available, otherwise first available)
    """
    if 'dnd' in CONFIG_MAP:
        return 'dnd'
    elif CONFIG_MAP:
        return next(iter(CONFIG_MAP.keys()))
    else:
        return 'general' 