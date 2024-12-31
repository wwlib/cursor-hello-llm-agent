from typing import Dict, Any, Optional
import requests
import json
from .llm import LLMService, LLMServiceError

class OllamaService(LLMService):
    """Ollama implementation of the LLM service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Ollama service.
        
        Args:
            config: Optional configuration with keys:
                - base_url: Ollama API endpoint (default: http://localhost:11434)
                - model: Model to use (default: llama3)
                - temperature: Generation temperature (default: 0.7)
                - stream: Whether to stream the response (default: True)
        """
        super().__init__(config)
        self.base_url = self.config.get('base_url', 'http://localhost:11434')
        self.model = self.config.get('model', 'llama3')
        self.temperature = self.config.get('temperature', 0.7)
        self.stream = self.config.get('stream', True)

    def generate(self, prompt: str) -> str:
        """Generate a response using Ollama's API.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": self.stream
                },
                stream=self.stream
            )
            response.raise_for_status()

            if not self.stream:
                # Handle non-streaming response
                return response.json()['response']
            
            # Handle streaming response
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        if 'response' in json_response:
                            full_response += json_response['response']
                    except json.JSONDecodeError as e:
                        raise LLMServiceError(f"Invalid JSON in stream: {str(e)}")
            
            return full_response

        except requests.exceptions.RequestException as e:
            raise LLMServiceError(f"Ollama API error: {str(e)}")
        except (KeyError, ValueError) as e:
            raise LLMServiceError(f"Invalid response format from Ollama: {str(e)}")

    def validate_response(self, response: str) -> bool:
        """Validate the Ollama response.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid (non-empty string)
        """
        return isinstance(response, str) and len(response.strip()) > 0
