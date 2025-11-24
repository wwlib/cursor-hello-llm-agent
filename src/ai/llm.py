from typing import Dict, Any, Optional, List
import json
import logging
import time

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM service.
        
        Args:
            config: Configuration dictionary with service settings
                   Required fields depend on specific implementation
                   Optional fields:
                   - logger: logging.Logger - Logger to use for logging
                   - default_temperature: float - Default sampling temperature (0.0 to 1.0)
        """
        self.config = config or {}
        self.logger = self.config.get('logger', logging.getLogger(__name__))
        self.logger.debug(f"[init]:LLM service initialized")
        self.default_temperature = self.config.get('default_temperature', 0)
    
    def _clean_response(self, llm_response: str) -> str:
        """Clean up special characters and Unicode escape sequences from LLM response.
        
        Args:
            response: The raw response from the LLM
            
        Returns:
            str: Cleaned response with normalized characters
        """
        if not llm_response:
            return llm_response
            
        try:
            # Comprehensive dictionary of Unicode replacements
            replacements = {
                '\u2013': '-',  # en-dash
                '\u2014': '--', # em-dash
                '\u2018': "'",  # left single quote
                '\u2019': "'",  # right single quote
                '\u201c': '"',  # left double quote
                '\u201d': '"',  # right double quote
                '\u2026': '...', # ellipsis
                '\u00a0': ' ',  # non-breaking space
                '\u00b0': ' degrees', # degree symbol
                '\u00b7': '.',  # middle dot
                '\u00e9': 'e',  # e with acute
                '\u00e8': 'e',  # e with grave
                '\u00e0': 'a',  # a with grave
                '\u00e1': 'a',  # a with acute
                '\u00e2': 'a',  # a with circumflex
                '\u00e4': 'a',  # a with diaeresis
                '\u00e7': 'c',  # c with cedilla
                '\u00f1': 'n',  # n with tilde
                '\u00f3': 'o',  # o with acute
                '\u00f6': 'o',  # o with diaeresis
                '\u00fa': 'u',  # u with acute
                '\u00fc': 'u',  # u with diaeresis
            }

            # Apply all replacements
            cleaned = llm_response
            for unicode_char, ascii_char in replacements.items():
                cleaned = cleaned.replace(unicode_char, ascii_char)
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error cleaning response: {str(e)}")
            return llm_response  # Return original response if cleaning fails
    
    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None, debug_generate_scope: str = "") -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The input prompt
            options: Optional dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - max_tokens: int - Maximum tokens to generate
                    - stream: bool - Whether to stream the response
            debug_generate_scope: Optional scope identifier for this specific generate call
            
        Returns:
            str: The generated response
        """
        self.logger.debug(f"[{debug_generate_scope}]:Generating response for prompt:\n{prompt}")
        if options:
            self.logger.debug(f"[{debug_generate_scope}]:Generation options:\n{json.dumps(options, indent=2)}")
        
        try:
            response = self._generate_impl(prompt, options or {}, debug_generate_scope)
            
            # Clean the response
            cleaned_response = self._clean_response(response)
            
            self.logger.debug(f"[{debug_generate_scope}]:Generated response:\n{response}\n\n\n\n\n")
            
            return cleaned_response
            
        except Exception as e:
            self.logger.error(f"[{debug_generate_scope}]:Error generating response: {str(e)}")
            raise
    
    def _generate_impl(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Implementation specific generation logic.
        Must be implemented by derived classes.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options
            debug_generate_scope: Optional scope identifier for debugging
            
        Returns:
            str: The generated response
        """
        raise NotImplementedError("_generate_impl must be implemented by derived class")
    
    async def generate_async(self, prompt: str, options: Optional[Dict[str, Any]] = None, debug_generate_scope: str = "") -> str:
        """Generate a response for the given prompt asynchronously.
        
        Args:
            prompt: The input prompt
            options: Optional dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - max_tokens: int - Maximum tokens to generate
                    - stream: bool - Whether to stream the response
            debug_generate_scope: Optional scope identifier for this specific generate call
            
        Returns:
            str: The generated response
        """
        self.logger.debug(f"[{debug_generate_scope}]:Generating async response for prompt:\n{prompt}")
        if options:
            self.logger.debug(f"[{debug_generate_scope}]:Generation options:\n{json.dumps(options, indent=2)}")
        
        try:
            response = await self._generate_impl_async(prompt, options or {}, debug_generate_scope)
            
            # Clean the response
            cleaned_response = self._clean_response(response)
            
            self.logger.debug(f"[{debug_generate_scope}]:Generated async response:\n{response}\n\n\n\n\n")
            
            return cleaned_response
            
        except Exception as e:
            self.logger.error(f"[{debug_generate_scope}]:Error generating async response: {str(e)}")
            raise
    
    async def _generate_impl_async(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Implementation-specific async generation logic. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _generate_impl_async")
    
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
            LLMServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            raise LLMServiceError("Cannot generate embedding for empty text")
            
        self.logger.debug(f"[embedding]:Generating embedding for text:\n{text}")
        if options:
            self.logger.debug(f"[embedding]:Embedding options:\n{json.dumps(options, indent=2)}")
        
        try:
            embedding = self._generate_embedding_impl(text, options or {})
            
            self.logger.debug(f"[embedding]:Generated embedding vector of length {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"[embedding]:Error generating embedding: {str(e)}")
            raise LLMServiceError(f"Failed to generate embedding: {str(e)}")
    
    def _generate_embedding_impl(self, text: str, options: Dict[str, Any]) -> List[float]:
        """Implementation specific embedding generation logic.
        Must be implemented by derived classes.
        
        Args:
            text: The text to generate an embedding for
            options: Dictionary of embedding options
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("_generate_embedding_impl must be implemented by derived class")
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding vector format.
        
        Args:
            embedding: The embedding vector to validate
            
        Returns:
            bool: True if embedding is valid, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError
