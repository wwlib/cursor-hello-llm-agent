"""API Configuration Module

Provides domain configurations for API sessions.
"""

from .domain_configs import CONFIG_MAP, get_domain_config, get_default_domain, get_available_domains

__all__ = ["CONFIG_MAP", "get_domain_config", "get_default_domain", "get_available_domains"] 