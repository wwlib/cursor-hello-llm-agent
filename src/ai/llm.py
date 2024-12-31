from typing import Dict, Any, Optional

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM service with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
    
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
