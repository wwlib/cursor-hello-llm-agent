"""
Graph Memory Configuration

Configuration system for background graph memory processing.
Provides configurable processing modes, frequencies, and optimization settings.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import os


@dataclass
class GraphProcessingConfig:
    """Configuration for background graph memory processing."""
    
    # Background processing settings
    enable_background_processing: bool = True
    processing_frequency: float = 30.0  # seconds between processing cycles
    batch_size: int = 5
    max_queue_size: int = 100
    
    # Processing modes
    default_processing_mode: str = "balanced"  # speed, balanced, comprehensive
    enable_priority_processing: bool = True
    
    # Performance settings
    processing_timeout: float = 60.0  # seconds
    max_retries: int = 3
    retry_delay: float = 5.0  # seconds
    
    # Real-time query settings
    enable_realtime_context: bool = True
    context_cache_ttl: float = 300.0  # seconds
    max_context_results: int = 5
    
    # Monitoring settings
    enable_performance_monitoring: bool = True
    stats_update_frequency: float = 60.0  # seconds
    enable_detailed_logging: bool = False


class GraphConfigManager:
    """Manages graph memory processing configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.config = GraphProcessingConfig()
        
        if config:
            self._apply_config(config)
        
        # Load from environment variables
        self._load_from_environment()
    
    def _apply_config(self, config: Dict[str, Any]) -> None:
        """Apply configuration from dictionary."""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            "GRAPH_BACKGROUND_PROCESSING": "enable_background_processing",
            "GRAPH_PROCESSING_FREQUENCY": "processing_frequency",
            "GRAPH_BATCH_SIZE": "batch_size",
            "GRAPH_MAX_QUEUE_SIZE": "max_queue_size",
            "GRAPH_DEFAULT_MODE": "default_processing_mode",
            "GRAPH_PRIORITY_PROCESSING": "enable_priority_processing",
            "GRAPH_PROCESSING_TIMEOUT": "processing_timeout",
            "GRAPH_MAX_RETRIES": "max_retries",
            "GRAPH_RETRY_DELAY": "retry_delay",
            "GRAPH_REALTIME_CONTEXT": "enable_realtime_context",
            "GRAPH_CONTEXT_CACHE_TTL": "context_cache_ttl",
            "GRAPH_MAX_CONTEXT_RESULTS": "max_context_results",
            "GRAPH_PERFORMANCE_MONITORING": "enable_performance_monitoring",
            "GRAPH_STATS_UPDATE_FREQUENCY": "stats_update_frequency",
            "GRAPH_DETAILED_LOGGING": "enable_detailed_logging"
        }
        
        for env_var, config_attr in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if config_attr in ["enable_background_processing", "enable_priority_processing", 
                                 "enable_realtime_context", "enable_performance_monitoring", 
                                 "enable_detailed_logging"]:
                    value = env_value.lower() in ("true", "1", "yes", "on")
                elif config_attr in ["processing_frequency", "batch_size", "max_queue_size",
                                   "processing_timeout", "max_retries", "retry_delay",
                                   "context_cache_ttl", "max_context_results", "stats_update_frequency"]:
                    value = float(env_value) if "." in env_value else int(env_value)
                else:
                    value = env_value
                
                setattr(self.config, config_attr, value)
    
    def get_processing_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined processing profiles for different use cases."""
        return {
            "realtime": {
                "enable_background_processing": True,
                "processing_frequency": 10.0,  # Process every 10 seconds
                "batch_size": 3,
                "max_queue_size": 50,
                "default_processing_mode": "speed",
                "enable_priority_processing": True,
                "processing_timeout": 30.0,
                "enable_realtime_context": True,
                "context_cache_ttl": 60.0,
                "max_context_results": 3
            },
            "balanced": {
                "enable_background_processing": True,
                "processing_frequency": 30.0,  # Process every 30 seconds
                "batch_size": 5,
                "max_queue_size": 100,
                "default_processing_mode": "balanced",
                "enable_priority_processing": True,
                "processing_timeout": 60.0,
                "enable_realtime_context": True,
                "context_cache_ttl": 300.0,
                "max_context_results": 5
            },
            "comprehensive": {
                "enable_background_processing": True,
                "processing_frequency": 60.0,  # Process every minute
                "batch_size": 3,
                "max_queue_size": 200,
                "default_processing_mode": "comprehensive",
                "enable_priority_processing": True,
                "processing_timeout": 120.0,
                "enable_realtime_context": True,
                "context_cache_ttl": 600.0,
                "max_context_results": 10
            },
            "background_only": {
                "enable_background_processing": True,
                "processing_frequency": 120.0,  # Process every 2 minutes
                "batch_size": 10,
                "max_queue_size": 500,
                "default_processing_mode": "balanced",
                "enable_priority_processing": False,
                "processing_timeout": 180.0,
                "enable_realtime_context": False,
                "context_cache_ttl": 0.0,
                "max_context_results": 0
            },
            "disabled": {
                "enable_background_processing": False,
                "processing_frequency": 0.0,
                "batch_size": 0,
                "max_queue_size": 0,
                "default_processing_mode": "speed",
                "enable_priority_processing": False,
                "processing_timeout": 0.0,
                "enable_realtime_context": False,
                "context_cache_ttl": 0.0,
                "max_context_results": 0
            }
        }
    
    def apply_profile(self, profile_name: str) -> None:
        """Apply a predefined processing profile."""
        profiles = self.get_processing_profiles()
        if profile_name not in profiles:
            raise ValueError(f"Unknown profile: {profile_name}. Available: {list(profiles.keys())}")
        
        profile_config = profiles[profile_name]
        self._apply_config(profile_config)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get current configuration as dictionary."""
        return {
            "enable_background_processing": self.config.enable_background_processing,
            "processing_frequency": self.config.processing_frequency,
            "batch_size": self.config.batch_size,
            "max_queue_size": self.config.max_queue_size,
            "default_processing_mode": self.config.default_processing_mode,
            "enable_priority_processing": self.config.enable_priority_processing,
            "processing_timeout": self.config.processing_timeout,
            "max_retries": self.config.max_retries,
            "retry_delay": self.config.retry_delay,
            "enable_realtime_context": self.config.enable_realtime_context,
            "context_cache_ttl": self.config.context_cache_ttl,
            "max_context_results": self.config.max_context_results,
            "enable_performance_monitoring": self.config.enable_performance_monitoring,
            "stats_update_frequency": self.config.stats_update_frequency,
            "enable_detailed_logging": self.config.enable_detailed_logging
        }
    
    def update_config(self, **kwargs) -> None:
        """Update specific configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")
    
    def validate_config(self) -> bool:
        """Validate current configuration for consistency."""
        issues = []
        
        if self.config.processing_frequency <= 0:
            issues.append("processing_frequency must be positive")
        
        if self.config.batch_size <= 0:
            issues.append("batch_size must be positive")
        
        if self.config.max_queue_size <= 0:
            issues.append("max_queue_size must be positive")
        
        if self.config.default_processing_mode not in ["speed", "balanced", "comprehensive"]:
            issues.append("default_processing_mode must be one of: speed, balanced, comprehensive")
        
        if self.config.processing_timeout <= 0:
            issues.append("processing_timeout must be positive")
        
        if self.config.max_retries < 0:
            issues.append("max_retries must be non-negative")
        
        if self.config.retry_delay < 0:
            issues.append("retry_delay must be non-negative")
        
        if self.config.context_cache_ttl < 0:
            issues.append("context_cache_ttl must be non-negative")
        
        if self.config.max_context_results < 0:
            issues.append("max_context_results must be non-negative")
        
        if self.config.stats_update_frequency <= 0:
            issues.append("stats_update_frequency must be positive")
        
        if issues:
            raise ValueError(f"Configuration validation failed: {'; '.join(issues)}")
        
        return True
    
    def get_recommended_settings(self, use_case: str) -> Dict[str, Any]:
        """Get recommended settings for specific use cases."""
        recommendations = {
            "high_frequency_chat": {
                "processing_frequency": 15.0,
                "batch_size": 3,
                "default_processing_mode": "speed",
                "enable_realtime_context": True,
                "context_cache_ttl": 60.0
            },
            "document_analysis": {
                "processing_frequency": 60.0,
                "batch_size": 5,
                "default_processing_mode": "comprehensive",
                "enable_realtime_context": True,
                "context_cache_ttl": 600.0
            },
            "low_resource": {
                "processing_frequency": 120.0,
                "batch_size": 10,
                "default_processing_mode": "speed",
                "enable_realtime_context": False,
                "max_queue_size": 50
            },
            "high_accuracy": {
                "processing_frequency": 45.0,
                "batch_size": 3,
                "default_processing_mode": "comprehensive",
                "enable_realtime_context": True,
                "context_cache_ttl": 900.0
            }
        }
        
        return recommendations.get(use_case, {})
    
    def __str__(self) -> str:
        """String representation of current configuration."""
        config_dict = self.get_config_dict()
        return "\n".join([f"{key}: {value}" for key, value in config_dict.items()])
