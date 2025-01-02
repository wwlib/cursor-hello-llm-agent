from typing import Dict, Any, Optional
import json
import logging

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM service with optional configuration.
        
        Args:
            config: Optional configuration dictionary with possible keys:
                - debug: bool, Enable debug logging (default: False)
                - debug_file: str, Path to debug log file (default: llm_debug.log)
                - console_output: bool, Print logs to console (default: False)
        """
        self.config = config or {}
        self.debug = self.config.get('debug', False)
        
        if self.debug:
            # Setup debug logging
            debug_file = self.config.get('debug_file', 'llm_debug.log')
            handlers = [logging.FileHandler(debug_file)]
            
            # Add console handler if requested
            if self.config.get('console_output', False):
                handlers.append(logging.StreamHandler())
            
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.debug("Initialized LLM service with debug mode")
    
    def generate(self, prompt: str) -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: The input prompt for the LLM
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If generation fails
            NotImplementedError: If not implemented by subclass
        """
        if self.debug:
            self.logger.debug(f"\n{'='*80}\nPROMPT:\n{prompt}\n{'='*80}")
        
        try:
            response = self._generate_impl(prompt)
            
            if self.debug:
                self.logger.debug(f"\n{'-'*80}\nRESPONSE:\n{response}\n{'-'*80}")
            
            return response
        except Exception as e:
            if self.debug:
                self.logger.error(f"Error generating response: {str(e)}")
            raise
    
    def _generate_impl(self, prompt: str) -> str:
        """Implementation of generate to be provided by subclasses.
        
        Args:
            prompt: The input prompt for the LLM
            
        Returns:
            str: The generated response
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError
    
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
