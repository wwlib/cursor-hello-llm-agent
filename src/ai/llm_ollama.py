from typing import Dict, Any, Optional
import requests
import json
from .llm import LLMService, LLMServiceError
import time

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
                - debug: bool, Enable debug logging (default: False)
                - debug_file: str, Path to debug log file (default: llm_debug.log)
                - log_chunks: bool, Log individual stream chunks (default: False)
        """
        super().__init__(config)
        self.base_url = self.config.get('base_url', 'http://localhost:11434')
        self.model = self.config.get('model', 'llama3')
        self.temperature = self.config.get('temperature', 0.7)
        self.stream = self.config.get('stream', True)
        self.log_chunks = self.config.get('log_chunks', False)
        
        if self.debug:
            self.logger.debug(f"Initialized Ollama service with model: {self.model}")
            if self.log_chunks:
                self.logger.debug("Stream chunk logging enabled")

    def _generate_impl(self, prompt: str) -> str:
        """Generate a response using Ollama's API.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            if self.debug:
                self.logger.debug(f"Making request to Ollama API at {self.base_url}")
                self.logger.debug(f"Model: {self.model}, Temperature: {self.temperature}")
            
            api_start_time = time.time()
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
                api_end_time = time.time()
                raw_response = response.text
                if self.debug:
                    api_duration_ms = (api_end_time - api_start_time) * 1000
                    self.logger.debug(f"Ollama API request completed in {api_duration_ms:.2f}ms")
                    self.logger.debug(f"Raw response: {raw_response}")
                
                try:
                    json_response = response.json()
                except json.JSONDecodeError as e:
                    if self.debug:
                        self.logger.error(f"Failed to parse JSON response: {str(e)}")
                        self.logger.error(f"Raw response that failed parsing: {raw_response}")
                    raise LLMServiceError(f"Invalid JSON response from Ollama: {str(e)}")
                
                if 'response' not in json_response:
                    if self.debug:
                        self.logger.error(f"Response missing 'response' field. Full response: {json_response}")
                    raise LLMServiceError("Ollama response missing 'response' field")
                
                return json_response['response']
            
            # Handle streaming response
            full_response = ""
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    try:
                        raw_chunk = line.decode('utf-8')
                        if self.debug and self.log_chunks:
                            self.logger.debug(f"Raw chunk {chunk_count + 1}: {raw_chunk}")
                        
                        json_response = json.loads(raw_chunk)
                        if 'response' in json_response:
                            chunk = json_response['response']
                            full_response += chunk
                            chunk_count += 1
                            if self.debug and self.log_chunks:
                                self.logger.debug(f"Processed chunk {chunk_count}: {chunk}")
                    except json.JSONDecodeError as e:
                        if self.debug:
                            self.logger.error(f"Error decoding JSON in stream chunk {chunk_count + 1}: {str(e)}")
                            self.logger.error(f"Raw chunk that failed parsing: {raw_chunk}")
                        raise LLMServiceError(f"Invalid JSON in stream: {str(e)}")
            
            api_end_time = time.time()
            if self.debug:
                api_duration_ms = (api_end_time - api_start_time) * 1000
                if self.stream:
                    self.logger.debug(f"Ollama streaming completed in {api_duration_ms:.2f}ms ({chunk_count} chunks)")
                
            return full_response

        except requests.exceptions.RequestException as e:
            if self.debug:
                api_end_time = time.time()
                api_duration_ms = (api_end_time - api_start_time) * 1000
                self.logger.error(f"Ollama API request error after {api_duration_ms:.2f}ms: {str(e)}")
                if hasattr(e.response, 'text'):
                    self.logger.error(f"Error response body: {e.response.text}")
            raise LLMServiceError(f"Ollama API error: {str(e)}")
        except (KeyError, ValueError) as e:
            if self.debug:
                api_end_time = time.time()
                api_duration_ms = (api_end_time - api_start_time) * 1000
                self.logger.error(f"Invalid response format from Ollama after {api_duration_ms:.2f}ms: {str(e)}")
            raise LLMServiceError(f"Invalid response format from Ollama: {str(e)}")

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
