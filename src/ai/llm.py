from typing import Dict, Any, Optional
import json
import logging
import time

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM service with configuration.
        
        Args:
            config: Configuration dictionary with service settings
                   Required fields depend on specific implementation
                   Optional fields:
                   - debug: bool - Enable debug logging
                   - debug_file: str - Path to debug log file
                   - debug_scope: str - Scope identifier for debug logs
                   - console_output: bool - Whether to also log to console
        """
        self.config = config
        self.debug = config.get('debug', False)
        self.debug_scope = config.get('debug_scope', '')
        
        if self.debug:
            import logging
            
            # Create logger
            self.logger = logging.getLogger(f'llm_service{self.debug_scope}')
            self.logger.setLevel(logging.DEBUG)
            
            # Create formatters
            scope_prefix = f'[{self.debug_scope}] ' if self.debug_scope else ''
            file_formatter = logging.Formatter(f'{scope_prefix}%(asctime)s - %(levelname)s - %(message)s')
            console_formatter = logging.Formatter(f'{scope_prefix}%(levelname)s - %(message)s')
            
            # Add file handler if debug_file specified
            if 'debug_file' in config:
                file_handler = logging.FileHandler(config['debug_file'])
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            
            # Add console handler if requested
            if config.get('console_output', False):
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)
            
            self.logger.debug("LLM service initialized with debug logging")
    
    def generate(self, prompt: str, debug_generate_scope: str = "") -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The input prompt
            debug_generate_scope: Optional scope identifier for this specific generate call
            
        Returns:
            str: The generated response
        """
        if self.debug:
            scope_prefix = f"[{debug_generate_scope}] " if debug_generate_scope else ""
            self.logger.debug(f"{scope_prefix}Generating response for prompt:\n{prompt}")
        
        try:
            response = self._generate_impl(prompt)
            
            if self.debug:
                scope_prefix = f"[{debug_generate_scope}] " if debug_generate_scope else ""
                self.logger.debug(f"{scope_prefix}Generated response:\n{response}")
            
            return response
            
        except Exception as e:
            if self.debug:
                scope_prefix = f"[{debug_generate_scope}] " if debug_generate_scope else ""
                self.logger.error(f"{scope_prefix}Error generating response: {str(e)}")
            raise
    
    def _generate_impl(self, prompt: str) -> str:
        """Implementation specific generation logic.
        Must be implemented by derived classes.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
        """
        raise NotImplementedError("_generate_impl must be implemented by derived class")
    
    def validate_response(self, response: str) -> bool:
        """Validate LLM response format.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError
