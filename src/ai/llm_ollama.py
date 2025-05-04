from typing import Dict, Any, Optional, List
import requests
import json
from .llm import LLMService, LLMServiceError
import time
import numpy as np

# CURL example
# curl http://localhost:11434/api/embed -d '{
#   "model": "mxbai-embed-large",
#   "input": "Llamas are members of the camelid family"
# }'

# batch embeddings - returns a list of embeddings
# curl http://192.168.1.173:11434/api/embed -d '{
#   "model": "mxbai-embed-large",
#   "input": "Llamas are members of the camelid family"
# }'

# one embedding at a time - returns a single embedding
# curl http://192.168.1.173:11434/api/embeddings -d '{
#   "model": "mxbai-embed-large",
#   "prompt": "Llamas are members of the camelid family"
# }'

# See: examples/call_ollama_to_generate_embeddings.py for examples of how to call the Ollama API


class OllamaService(LLMService):
    """LLM service implementation using Ollama"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Ollama service.
        
        Args:
            config: Configuration dictionary with required fields:
                   - base_url: str - Ollama server URL
                   - model: str - Model name to use
                   Optional fields:
                   - temperature: float - Default sampling temperature (0.0 to 1.0)
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
        
        # Optional config with defaults
        self.default_temperature = config.get('temperature', 0.7)
        
        if self.debug:
            self.logger.debug(f":[init]:Initialized Ollama service with model: {self.model}")
    
    def _generate_impl(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Generate a response using Ollama.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - stream: bool - Whether to stream the response
            debug_generate_scope: Optional scope identifier for debugging
            
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
                "temperature": options.get('temperature', self.default_temperature),
                "stream": options.get('stream', False)
            }
            
            if self.debug:
                self.logger.debug(f":[{debug_generate_scope}]:Sending request to Ollama API:\nURL: {url}\nData: {json.dumps(data, indent=2)}")
            
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
                # Clean up context data before logging
                debug_result = result.copy()
                if 'context' in debug_result:
                    del debug_result['context']
                self.logger.debug(f":[{debug_generate_scope}]:Received response from Ollama API:\n{json.dumps(debug_result, indent=2)}")
            
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

    def _generate_embedding_impl(self, text: str, options: Dict[str, Any]) -> List[float]:
        """Generate an embedding vector using Ollama.
        
        Args:
            text: The text to generate an embedding for
            options: Dictionary of embedding options:
                    - model: str - Specific embedding model to use (defaults to self.model)
                    - normalize: bool - Whether to normalize the embedding vector
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            LLMServiceError: If the API call fails
        """
        import requests
        
        try:
            # Prepare request
            url = f"{self.base_url}/api/embeddings"
            data = {
                "model": options.get('model', self.model),
                "prompt": text
            }
            
            if self.debug:
                self.logger.debug(f":[embedding]:Sending request to Ollama API:\nURL: {url}\nData: {json.dumps(data, indent=2)}")
            
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
            
            if not isinstance(result, dict) or 'embedding' not in result:
                raise LLMServiceError("Invalid response format from Ollama API")
            
            embedding = result['embedding']
            
            # Normalize if requested
            if options.get('normalize', True):
                embedding = np.array(embedding)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = (embedding / norm).tolist()
            
            return embedding
            
        except Exception as e:
            if not isinstance(e, LLMServiceError):
                raise LLMServiceError(f"Unexpected error in Ollama API call: {str(e)}")
            raise
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate the Ollama embedding vector.
        
        Args:
            embedding: The embedding vector to validate
            
        Returns:
            bool: True if embedding is valid (non-empty list of floats)
        """
        is_valid = (
            isinstance(embedding, list) and 
            len(embedding) > 0 and 
            all(isinstance(x, (int, float)) for x in embedding)
        )
        if self.debug and not is_valid:
            self.logger.warning(f"Invalid embedding format: {embedding}")
        return is_valid

    def generate_embedding(self, text: str, options: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The text to generate an embedding for
            options: Optional dictionary of embedding options:
                    - model: str - Specific embedding model to use
                    - normalize: bool - Whether to normalize the embedding vector
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            LLMServiceError: If embedding generation fails or text is empty
        """
        if not text or not text.strip():
            raise LLMServiceError("Cannot generate embedding for empty text")
            
        if self.debug:
            self.logger.debug(f":[embedding]:Generating embedding for text:\n{text}")
            if options:
                self.logger.debug(f":[embedding]:Embedding options:\n{json.dumps(options, indent=2)}")
        
        try:
            embedding = self._generate_embedding_impl(text, options or {})
            
            if self.debug:
                self.logger.debug(f":[embedding]:Generated embedding vector of length {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            if self.debug:
                self.logger.debug(f":[embedding]:Error generating embedding: {str(e)}")
            raise LLMServiceError(f"Failed to generate embedding: {str(e)}")
