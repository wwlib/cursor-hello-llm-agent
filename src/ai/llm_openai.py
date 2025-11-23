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
                - max_tokens: Default maximum tokens (default: 1000)
                - default_temperature: float - Default sampling temperature (0.0 to 1.0)
        """
        super().__init__(config)
        self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise LLMServiceError("OpenAI API key not found in config or environment")
            
        self.model = self.config.get('model', 'gpt-4')
        self.default_max_tokens = self.config.get('max_tokens', 1000)
        openai.api_key = self.api_key

    def _generate_impl(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Generate a response using OpenAI's API.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - max_tokens: int - Maximum tokens to generate
            debug_generate_scope: Optional scope identifier for debugging
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=options.get('temperature', self.default_temperature),
                max_tokens=options.get('max_tokens', self.default_max_tokens)
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
        is_valid = isinstance(response, str) and len(response.strip()) > 0
        self.logger.error(f"Invalid response format: {response}")
        return is_valid
