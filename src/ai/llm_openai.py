import os
from typing import Dict, Any, Optional
import openai
from .llm import LLMService, LLMServiceError

class OpenAIService(LLMService):
    """OpenAI implementation of the LLM service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the OpenAI service.
        
        Args:
            config: Optional configuration with keys:
                - api_key: OpenAI API key (optional if set in env)
                - model: Model to use (default: gpt-4)
                - temperature: Generation temperature (default: 0.7)
                - max_tokens: Maximum tokens (default: 1000)
        """
        super().__init__(config)
        self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise LLMServiceError("OpenAI API key not found in config or environment")
            
        self.model = self.config.get('model', 'gpt-4')
        self.temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 1000)
        openai.api_key = self.api_key

    def generate(self, prompt: str) -> str:
        """Generate a response using OpenAI's API.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMServiceError(f"OpenAI API error: {str(e)}")

    def validate_response(self, response: str) -> bool:
        """Validate the OpenAI response.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid (non-empty string)
        """
        return isinstance(response, str) and len(response.strip()) > 0
