from typing import Dict, Any, Optional
import requests
import json
from .llm import LLMService, LLMServiceError
import time

class OllamaService(LLMService):
    """LLM service implementation using Ollama"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Ollama service.
        
        Args:
            config: Configuration dictionary with required fields:
                   - base_url: str - Ollama server URL
                   - model: str - Model name to use
                   Optional fields:
                   - temperature: float - Sampling temperature
                   - debug: bool - Enable debug logging
                   - debug_file: str - Path to debug log file
                   - debug_scope: str - Scope identifier for debug logs
                   - console_output: bool - Whether to also log to console
        """
        # Set default debug scope if not provided
        if 'debug' in config and 'debug_scope' not in config:
            config['debug_scope'] = 'ollama'
            
        super().__init__(config)
        
        # Required config
        self.base_url = config['base_url']
        self.model = config['model']
        
        # Optional config
        self.temperature = config.get('temperature', 0.7)
        
        if self.debug:
            self.logger.debug(f"Initialized Ollama service with model: {self.model}")
    
    def _generate_impl(self, prompt: str) -> str:
        """Generate a response using Ollama.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        import requests
        
        try:
            # Prepare request
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model,
                "prompt": prompt,
                "temperature": self.temperature,
                "stream": False
            }
            
            if self.debug:
                self.logger.debug(f"Sending request to Ollama API:\nURL: {url}\nData: {json.dumps(data, indent=2)}")
            
            # Make request
            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise LLMServiceError(f"Failed to make request to Ollama API: {str(e)}")
            
            # Parse response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                raise LLMServiceError(f"Failed to parse Ollama API response: {str(e)}")
            
            if self.debug:
                self.logger.debug(f"Received response from Ollama API:\n{json.dumps(result, indent=2)}")
            
            if not isinstance(result, dict) or 'response' not in result:
                raise LLMServiceError("Invalid response format from Ollama API")
            
            return result['response']
            
        except Exception as e:
            if not isinstance(e, LLMServiceError):
                raise LLMServiceError(f"Unexpected error in Ollama API call: {str(e)}")
            raise

    def validate_response(self, response: str) -> bool:
        """Validate the Ollama response.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid (non-empty string)
        """
        is_valid = isinstance(response, str) and len(response.strip()) > 0
        if self.debug and not is_valid:
            self.logger.warning(f"Invalid response format: {response}")
        return is_valid
